import boto3
import os
from typing import Dict, List, Any
from botocore.exceptions import ClientError
import datetime

class AWSClient:
    def __init__(self, aws_access_key_id: str = None, aws_secret_access_key: str = None, region: str = None):
        if not aws_access_key_id or not aws_secret_access_key:
            raise ValueError("AWS credentials are required (access key and secret key)")
        
        try:
            self.session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region or os.getenv('AWS_REGION', 'eu-west-2')
            )
            # Test the credentials
            sts = self.session.client('sts')
            sts.get_caller_identity()
        except ClientError as e:
            raise ValueError(f"Failed to initialize AWS client: {str(e)}")

    def _get_all_regions(self) -> List[str]:
        """Get list of all AWS regions"""
        try:
            ec2 = self.session.client('ec2')
            regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]
            return regions
        except ClientError as e:
            raise Exception(f'Error getting regions: {str(e)}')

    def list_ec2_instances(self, filters: List[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """List EC2 instances across all regions with optional filters"""
        all_instances = {}
        regions = self._get_all_regions()

        for region in regions:
            try:
                ec2 = self.session.client('ec2', region_name=region)
                if filters:
                    response = ec2.describe_instances(Filters=filters)
                else:
                    response = ec2.describe_instances()
                
                instances = []
                for reservation in response['Reservations']:
                    for instance in reservation['Instances']:
                        # Extract instance details with error handling
                        instance_details = {
                            'InstanceId': instance.get('InstanceId', 'Unknown'),
                            'InstanceType': instance.get('InstanceType', 'Unknown'),
                            'State': instance.get('State', {}).get('Name', 'Unknown'),
                            'Region': region,
                            'Tags': instance.get('Tags', []),
                            'PublicIpAddress': instance.get('PublicIpAddress', 'None'),
                            'PrivateIpAddress': instance.get('PrivateIpAddress', 'None'),
                            'VpcId': instance.get('VpcId', 'None'),
                            'SubnetId': instance.get('SubnetId', 'None')
                        }
                        
                        # Add launch time if available
                        if 'LaunchTime' in instance:
                            instance_details['LaunchTime'] = instance['LaunchTime'].isoformat()
                        
                        # Add name tag if available
                        name_tag = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
                        if name_tag:
                            instance_details['Name'] = name_tag
                        
                        instances.append(instance_details)
                if instances:  # Only add regions that have instances
                    all_instances[region] = instances
            except ClientError as e:
                print(f'Error listing EC2 instances in {region}: {str(e)}')
                continue

        return all_instances

    def list_s3_buckets(self) -> Dict[str, Any]:
        """List all S3 buckets with their region information"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets_by_region = {}
            errors = []
            inaccessible_buckets = []

            if not response.get('Buckets'):
                return {
                    "status": "empty",
                    "message": "No S3 buckets found in the account",
                    "data": {}
                }

            for bucket in response['Buckets']:
                bucket_name = bucket['Name']
                try:
                    # Get bucket location (region)
                    location = s3.get_bucket_location(Bucket=bucket_name)
                    region = location['LocationConstraint'] or 'us-east-1'  # None means us-east-1
                    
                    # Initialize bucket info
                    bucket_info = {
                        'Name': bucket_name,
                        'CreationDate': bucket['CreationDate'].isoformat(),
                        'Region': region,
                        'Size': 0,
                        'ObjectCount': 0,
                        'Tags': {},
                        'Versioning': 'Unknown',
                        'Encryption': 'Unknown',
                        'AccessStatus': 'Full'
                    }

                    # Get bucket size and object count
                    try:
                        s3_regional = self.session.client('s3', region_name=region)
                        paginator = s3_regional.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=bucket_name):
                            if 'Contents' in page:
                                for obj in page['Contents']:
                                    bucket_info['Size'] += obj['Size']
                                    bucket_info['ObjectCount'] += 1
                    except ClientError as e:
                        bucket_info['AccessStatus'] = 'Limited'
                        errors.append({
                            'bucket': bucket_name,
                            'operation': 'list_objects',
                            'error': str(e)
                        })

                    # Get bucket tags
                    try:
                        tags_response = s3.get_bucket_tagging(Bucket=bucket_name)
                        bucket_info['Tags'] = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'NoSuchTagSet':
                            bucket_info['AccessStatus'] = 'Limited'
                            errors.append({
                                'bucket': bucket_name,
                                'operation': 'get_bucket_tagging',
                                'error': str(e)
                            })

                    # Get bucket versioning status
                    try:
                        versioning = s3.get_bucket_versioning(Bucket=bucket_name)
                        bucket_info['Versioning'] = versioning.get('Status', 'Disabled')
                    except ClientError as e:
                        bucket_info['AccessStatus'] = 'Limited'
                        errors.append({
                            'bucket': bucket_name,
                            'operation': 'get_bucket_versioning',
                            'error': str(e)
                        })

                    # Get bucket encryption
                    try:
                        encryption = s3.get_bucket_encryption(Bucket=bucket_name)
                        bucket_info['Encryption'] = 'Enabled'
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'ServerSideEncryptionConfigurationNotFoundError':
                            bucket_info['AccessStatus'] = 'Limited'
                            errors.append({
                                'bucket': bucket_name,
                                'operation': 'get_bucket_encryption',
                                'error': str(e)
                            })
                        bucket_info['Encryption'] = 'Disabled'

                    if region not in buckets_by_region:
                        buckets_by_region[region] = []
                    buckets_by_region[region].append(bucket_info)

                except ClientError as e:
                    inaccessible_buckets.append({
                        'bucket': bucket_name,
                        'error': str(e)
                    })

            result = {
                "status": "success" if buckets_by_region else "empty",
                "message": "S3 buckets retrieved successfully" if buckets_by_region else "No accessible S3 buckets found",
                "data": buckets_by_region
            }

            if errors:
                result["warnings"] = {
                    "message": "Some bucket information could not be fully retrieved",
                    "errors": errors
                }

            if inaccessible_buckets:
                result["inaccessible_buckets"] = {
                    "message": "Some buckets were completely inaccessible",
                    "buckets": inaccessible_buckets
                }

            return result

        except ClientError as e:
            return {
                "status": "error",
                "message": f"Error listing S3 buckets: {str(e)}",
                "error": str(e),
                "data": {}
            }

    def get_cost_and_usage(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get AWS cost and usage data for a specific time period"""
        try:
            ce = self.session.client('ce', region_name='us-east-1')  # Cost Explorer is only available in us-east-1
            
            # Get costs grouped by service and region
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'REGION'}
                ]
            )

            # Process the results
            costs_by_service = {}
            costs_by_location = {}
            total_cost = 0

            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    location = group['Keys'][1] or 'global'  # Some services are global
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])

                    costs_by_service[service] = costs_by_service.get(service, 0) + cost
                    costs_by_location[location] = costs_by_location.get(location, 0) + cost
                    total_cost += cost

            return {
                'timeframe': f"{start_date} to {end_date}",
                'startDate': start_date,
                'endDate': end_date,
                'currency': 'USD',
                'totalCost': total_cost,
                'costsByService': costs_by_service,
                'costsByLocation': costs_by_location
            }

        except ClientError as e:
            raise Exception(f'Error getting cost and usage data: {str(e)}')

    def describe_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get the current status and health of an AWS service"""
        try:
            health = self.session.client('health')
            response = health.describe_events(
                filter={
                    'services': [service_name],
                    'eventStatusCodes': ['open', 'upcoming']
                }
            )
            return response['events']
        except ClientError as e:
            raise Exception(f'Error getting service status: {str(e)}')

    def get_cloudwatch_metrics(self, resource_id: str, metric_name: str,
                             start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get CloudWatch metrics for a specific resource.
        
        Args:
            resource_id: AWS resource ID (e.g., i-1234567890abcdef0 for EC2)
            metric_name: Name of the metric to retrieve
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            List of metric data points
        """
        try:
            # Extract region from resource ID if possible, otherwise use default
            region = self.session.region_name
            if resource_id.startswith('i-'):  # EC2 instance
                ec2 = self.session.client('ec2')
                response = ec2.describe_instances(InstanceIds=[resource_id])
                if response['Reservations']:
                    region = response['Reservations'][0]['Instances'][0]['Placement']['AvailabilityZone'][:-1]

            cloudwatch = self.session.client('cloudwatch', region_name=region)
            
            # Get the metric data
            response = cloudwatch.get_metric_data(
                MetricDataQueries=[
                    {
                        'Id': 'm1',
                        'MetricStat': {
                            'Metric': {
                                'Namespace': 'AWS/EC2',
                                'MetricName': metric_name,
                                'Dimensions': [
                                    {
                                        'Name': 'InstanceId',
                                        'Value': resource_id
                                    }
                                ]
                            },
                            'Period': 3600,  # 1-hour intervals
                            'Stat': 'Average'
                        }
                    }
                ],
                StartTime=start_time,
                EndTime=end_time
            )

            # Process the results
            metrics = []
            timestamps = response['MetricDataResults'][0]['Timestamps']
            values = response['MetricDataResults'][0]['Values']

            for timestamp, value in zip(timestamps, values):
                metrics.append({
                    'timestamp': timestamp.isoformat(),
                    'value': value,
                    'unit': 'Percent' if metric_name in ['CPUUtilization'] else 'Count'
                })

            return metrics

        except ClientError as e:
            raise Exception(f'Error getting CloudWatch metrics: {str(e)}')
