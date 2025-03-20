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
                        instances.append({
                            'InstanceId': instance['InstanceId'],
                            'InstanceType': instance['InstanceType'],
                            'State': instance['State']['Name'],
                            'LaunchTime': instance['LaunchTime'].isoformat(),
                            'Region': region,
                            'Tags': instance.get('Tags', [])
                        })
                if instances:  # Only add regions that have instances
                    all_instances[region] = instances
            except ClientError as e:
                print(f'Error listing EC2 instances in {region}: {str(e)}')
                continue

        return all_instances

    def list_s3_buckets(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all S3 buckets with their region information"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets_by_region = {}

            for bucket in response['Buckets']:
                try:
                    # Get bucket location (region)
                    location = s3.get_bucket_location(Bucket=bucket['Name'])
                    region = location['LocationConstraint'] or 'us-east-1'  # None means us-east-1
                    
                    # Get bucket size and object count
                    size = 0
                    object_count = 0
                    try:
                        s3_regional = self.session.client('s3', region_name=region)
                        paginator = s3_regional.get_paginator('list_objects_v2')
                        for page in paginator.paginate(Bucket=bucket['Name']):
                            if 'Contents' in page:
                                for obj in page['Contents']:
                                    size += obj['Size']
                                    object_count += 1
                    except ClientError:
                        # Skip if we can't access bucket contents
                        pass

                    bucket_info = {
                        'Name': bucket['Name'],
                        'CreationDate': bucket['CreationDate'].isoformat(),
                        'Size': size,
                        'ObjectCount': object_count
                    }

                    if region not in buckets_by_region:
                        buckets_by_region[region] = []
                    buckets_by_region[region].append(bucket_info)

                except ClientError:
                    # Skip if we can't get bucket location
                    continue

            return buckets_by_region
        except ClientError as e:
            raise Exception(f'Error listing S3 buckets: {str(e)}')

    def get_cost_and_usage(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get cost and usage data across all regions"""
        try:
            ce = self.session.client('ce', region_name='us-east-1')  # Cost Explorer is only available in us-east-1
            
            # Get costs grouped by region and service
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'REGION'},
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'}
                ]
            )

            # Process and format the response
            costs_by_region = {}
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    region = group['Keys'][0]
                    service = group['Keys'][1]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])

                    if region not in costs_by_region:
                        costs_by_region[region] = {}
                    
                    if service not in costs_by_region[region]:
                        costs_by_region[region][service] = 0
                    
                    costs_by_region[region][service] += cost

            return {
                'period': {
                    'start': start_date,
                    'end': end_date
                },
                'costs_by_region': costs_by_region,
                'total_cost': sum(sum(services.values()) for services in costs_by_region.values())
            }

        except ClientError as e:
            raise Exception(f'Error getting cost and usage data: {str(e)}')


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
