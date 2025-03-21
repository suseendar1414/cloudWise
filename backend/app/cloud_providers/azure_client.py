import os
import logging
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError, ResourceNotFoundError
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureClient:
    def __init__(self, subscription_id: str = None):
        """Initialize Azure client with credentials and required clients.
        
        Args:
            subscription_id: Optional Azure subscription ID. If not provided, will try to get from env.
        """
        # Get credentials from environment variables
        self.tenant_id = os.getenv('AZURE_TENANT_ID')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        self.resource_group = os.getenv('AZURE_RESOURCE_GROUP', 'cloudwise-rg')
        self.location = os.getenv('AZURE_LOCATION', 'eastus')
        
        # Validate required credentials
        if not all([self.tenant_id, self.client_id, self.client_secret, self.subscription_id]):
            missing = [var for var, val in {
                'AZURE_TENANT_ID': self.tenant_id,
                'AZURE_CLIENT_ID': self.client_id,
                'AZURE_CLIENT_SECRET': self.client_secret,
                'AZURE_SUBSCRIPTION_ID': self.subscription_id
            }.items() if not val]
            raise ValueError(f'Missing Azure credentials: {", ".join(missing)}')
        
        try:
            # Initialize credential
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Initialize service clients
            self.subscription_client = SubscriptionClient(self.credential)
            self.compute_client = ComputeManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            self.storage_client = StorageManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            self.cost_client = CostManagementClient(
                credential=self.credential
            )
            self.resource_client = ResourceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            self.monitor_client = MonitorManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            
            # Verify subscription access
            self._verify_subscription()
            
            # Ensure resource group exists
            self.ensure_resource_group_exists()
            if not self.test_connection():
                raise ValueError("Failed to connect to Azure. Please check your credentials.")

        except Exception as e:
            logger.error(f'Error initializing Azure client: {str(e)}')
            raise

    def test_connection(self) -> bool:
        """Test Azure connection and credentials"""
        try:
            # Try to list subscriptions as a connection test
            next(self.subscription_client.subscriptions.list())
            return True
        except Exception as e:
            logging.error(f"Azure connection test failed: {str(e)}")
            return False

    def _verify_subscription(self) -> None:
        """Verify subscription access and existence."""
        try:
            sub = next((s for s in self.subscription_client.subscriptions.list() 
                       if s.subscription_id == self.subscription_id), None)
            if not sub:
                raise ValueError(f'Subscription {self.subscription_id} not found or not accessible')
            logger.info(f'Successfully connected to Azure subscription: {sub.display_name}')
        except Exception as e:
            logger.error(f'Error verifying subscription: {str(e)}')
            raise

    def ensure_resource_group_exists(self) -> None:
        """Ensure the resource group exists, create if it doesn't."""
        try:
            self.resource_client.resource_groups.get(self.resource_group)
            logger.info(f'Resource group {self.resource_group} exists')
        except Exception:
            logger.info(f'Creating resource group {self.resource_group}')
            self.resource_client.resource_groups.create_or_update(
                self.resource_group,
                {"location": self.location}
            )
    
    def list_virtual_machines(self, resource_group: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """List Azure Virtual Machines grouped by region.
        
        Args:
            resource_group: Optional resource group name to filter VMs.
            
        Returns:
            Dict with regions as keys and list of VM details as values.
        """
        try:
            vms_by_region = {}
            if resource_group:
                vm_list = self.compute_client.virtual_machines.list(resource_group_name=resource_group)
            else:
                vm_list = self.compute_client.virtual_machines.list_all()

            for vm in vm_list:
                vm_info = {
                    'name': vm.name,
                    'id': vm.id,
                    'vm_size': vm.hardware_profile.vm_size,
                    'os_type': vm.storage_profile.os_disk.os_type,
                    'provisioning_state': vm.provisioning_state,
                    'resource_group': vm.id.split('/')[4],
                    'tags': vm.tags or {},
                    'status': self.get_vm_status(vm.id.split('/')[4], vm.name)
                }
                
                region = vm.location
                if region not in vms_by_region:
                    vms_by_region[region] = []
                vms_by_region[region].append(vm_info)
            
            return vms_by_region
        except Exception as e:
            logger.error(f'Error listing Azure VMs: {str(e)}')
            raise

    def get_vm_status(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific Virtual Machine.
        
        Args:
            resource_group: Resource group name containing the VM.
            vm_name: Name of the virtual machine.
            
        Returns:
            Dict containing VM status details.
        """
        try:
            instance_view = self.compute_client.virtual_machines.instance_view(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            
            status = {
                'vm_name': vm_name,
                'statuses': [{
                    'code': status.code,
                    'level': status.level,
                    'display_status': status.display_status,
                    'message': status.message
                } for status in instance_view.statuses],
                'maintenance_state': instance_view.maintenance_state,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            return status
        except Exception as e:
            logger.error(f'Error getting VM status for {vm_name}: {str(e)}')
            return {'error': str(e)}

    def list_storage_accounts(self) -> Dict[str, Any]:
        """List all storage accounts grouped by region with detailed information.
        
        Returns:
            Dict containing storage account details, status, and any errors encountered.
        """
        try:
            accounts = list(self.storage_client.storage_accounts.list())
            if not accounts:
                return {
                    "status": "empty",
                    "message": "No storage accounts found in the subscription",
                    "data": {}
                }

            accounts_by_region = {}
            errors = []
            inaccessible_accounts = []
            
            for account in accounts:
                try:
                    # Get account properties for more details
                    properties = self.storage_client.storage_accounts.get_properties(
                        account.id.split('/')[4],  # resource group
                        account.name
                    )
                    
                    # Get blob service properties
                    try:
                        blob_props = self.storage_client.blob_services.get_service_properties(
                            account.id.split('/')[4],
                            account.name
                        )
                        blob_status = {
                            'cors_enabled': bool(blob_props.cors),
                            'delete_retention_enabled': bool(blob_props.delete_retention_policy),
                            'versioning_enabled': bool(blob_props.is_versioning_enabled)
                        }
                    except Exception as e:
                        blob_status = {
                            'error': str(e)
                        }
                    
                    # Get account metrics
                    try:
                        metrics = self.get_resource_metrics(
                            account.id,
                            'UsedCapacity',
                            datetime.now(timezone.utc) - timedelta(hours=24),
                            datetime.now(timezone.utc)
                        )
                        latest_capacity = metrics[-1]['value'] if metrics else 0
                    except Exception:
                        latest_capacity = 0

                    account_info = {
                        'id': account.id,
                        'name': account.name,
                        'location': account.location,
                        'resource_group': account.id.split('/')[4],
                        'type': account.type,
                        'sku': properties.sku.name,
                        'kind': properties.kind,
                        'access_tier': properties.access_tier,
                        'provisioning_state': properties.provisioning_state,
                        'creation_time': properties.creation_time.isoformat() if properties.creation_time else None,
                        'primary_location': properties.primary_location,
                        'status': properties.status_of_primary,
                        'https_only': properties.enable_https_traffic_only,
                        'encryption': {
                            'key_source': properties.encryption.key_source,
                            'services': {
                                'blob': properties.encryption.services.blob.enabled if properties.encryption.services.blob else False,
                                'file': properties.encryption.services.file.enabled if properties.encryption.services.file else False,
                                'table': properties.encryption.services.table.enabled if properties.encryption.services.table else False,
                                'queue': properties.encryption.services.queue.enabled if properties.encryption.services.queue else False
                            }
                        },
                        'network_access': properties.network_rule_set.default_action if properties.network_rule_set else 'Allow',
                        'blob_service': blob_status,
                        'used_capacity_bytes': latest_capacity,
                        'tags': account.tags or {}
                    }
                    
                    region = account.location
                    if region not in accounts_by_region:
                        accounts_by_region[region] = []
                    accounts_by_region[region].append(account_info)
                    
                except ResourceNotFoundError:
                    inaccessible_accounts.append({
                        'account': account.name,
                        'reason': 'Account not found or insufficient permissions'
                    })
                except Exception as e:
                    errors.append({
                        'account': account.name,
                        'error': str(e)
                    })
            
            result = {
                "status": "success" if accounts_by_region else "empty",
                "message": "Storage accounts retrieved successfully" if accounts_by_region else "No accessible storage accounts found",
                "data": accounts_by_region
            }
            
            if errors:
                result["warnings"] = {
                    "message": "Some storage account information could not be fully retrieved",
                    "errors": errors
                }
            
            if inaccessible_accounts:
                result["inaccessible_accounts"] = {
                    "message": "Some storage accounts were completely inaccessible",
                    "accounts": inaccessible_accounts
                }
            
            return result
            
        except Exception as e:
            logger.error(f'Error listing storage accounts: {str(e)}')
            return {
                "status": "error",
                "message": f"Error listing storage accounts: {str(e)}",
                "error": str(e),
                "data": {}
            }

    def get_cost_analysis(self, timeframe: str = 'LastMonth') -> Dict[str, Any]:
        """Get cost analysis for the subscription with optimization recommendations.
        
        Args:
            timeframe: Time period for cost analysis ('LastMonth' or 'LastWeek').
            
        Returns:
            Dict containing cost analysis details including total cost, currency,
            cost breakdowns, and optimization recommendations.
        """
        try:
            # Set time range
            end_date = datetime.now(timezone.utc)
            if timeframe == 'LastMonth':
                start_date = end_date - timedelta(days=30)
            elif timeframe == 'LastWeek':
                start_date = end_date - timedelta(days=7)
            else:
                logger.warning(f'Invalid timeframe: {timeframe}, defaulting to LastMonth')
                start_date = end_date - timedelta(days=30)
            
            logger.info(f'Getting cost analysis from {start_date} to {end_date}')
            
            # Query parameters
            scope = f'/subscriptions/{self.subscription_id}'
            parameters = {
                'type': 'ActualCost',
                'timeframe': 'Custom',
                'timePeriod': {
                    'from': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'to': end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                'dataset': {
                    'granularity': 'Daily',
                    'aggregation': {
                        'totalCost': {
                            'name': 'Cost',
                            'function': 'Sum'
                        }
                    },
                    'grouping': [
                        {
                            'type': 'Dimension',
                            'name': 'ServiceName'
                        },
                        {
                            'type': 'Dimension',
                            'name': 'ResourceLocation'
                        },
                        {
                            'type': 'Dimension',
                            'name': 'ResourceId'
                        }
                    ]
                }
            }
            
            # Get cost data
            cost_data = self.cost_client.query.usage(scope=scope, parameters=parameters)
            
            if not cost_data.rows:
                return {
                    "status": "empty",
                    "message": "No cost data available for the specified timeframe",
                    "data": {}
                }
        except Exception as e:
            logger.error(f'Error getting cost data: {str(e)}')
            return {
                "status": "error",
                "message": f"Error getting cost data: {str(e)}",
                "error": str(e),
                "data": {}
            }

            
            # Process cost data
            result = {
                'timeframe': f"{start_date.date()} to {end_date.date()}",
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'currency': cost_data.columns[0].name,
                'totalCost': 0.0,
                'costsByService': {},
                'costsByLocation': {},
                'costsByResource': {},
                'dailyCosts': [],
                'optimization_recommendations': {
                    'opportunities': [],
                    'recommendations': [],
                    'savings_estimates': []
                }
            }
            
            # Group costs
            try:
                for row in cost_data.rows:
                    cost = float(row[0])
                    service = row[1] or 'Unknown'
                    location = row[2] or 'Unknown'
                    resource_id = row[3] if len(row) > 3 else 'Unknown'
                    
                    result['totalCost'] += cost
                    
                    # By service
                    if service not in result['costsByService']:
                        result['costsByService'][service] = 0.0
                    result['costsByService'][service] += cost
                    
                    # By location
                    if location not in result['costsByLocation']:
                        result['costsByLocation'][location] = 0.0
                    result['costsByLocation'][location] += cost
                    
                    # By resource
                    if resource_id not in result['costsByResource']:
                        result['costsByResource'][resource_id] = {
                            'cost': 0.0,
                            'service': service,
                            'location': location
                        }
                    result['costsByResource'][resource_id]['cost'] += cost
                
                # Generate optimization recommendations
                opportunities = []
                recommendations = []
                savings_estimates = []
                
                # Analyze service costs
                sorted_services = sorted(result['costsByService'].items(), key=lambda x: x[1], reverse=True)
                if sorted_services:
                    top_service = sorted_services[0]
                    if top_service[1] > result['totalCost'] * 0.5:  # More than 50% of total cost
                        opportunities.append(f"High {top_service[0]} costs ({top_service[1]:.2f} {result['currency']}) represent over 50% of total spend")
                        recommendations.append(f"Review {top_service[0]} usage and consider:\n- Rightsizing resources\n- Using reserved instances\n- Implementing auto-scaling")
                        savings_estimates.append(f"Potential {top_service[0]} savings: 10-30% through optimization")
                
                # Analyze location distribution
                if len(result['costsByLocation']) > 1:
                    opportunities.append("Resources distributed across multiple regions may increase data transfer costs")
                    recommendations.append("Consider consolidating resources to fewer regions where possible")
                
                # Analyze resource costs
                expensive_resources = [r for r in result['costsByResource'].items() if r[1]['cost'] > result['totalCost'] * 0.1]
                if expensive_resources:
                    opportunities.append(f"Found {len(expensive_resources)} resources each consuming >10% of total cost")
                    for resource_id, details in expensive_resources:
                        recommendations.append(f"Review resource {resource_id.split('/')[-1]} ({details['service']}) costing {details['cost']:.2f} {result['currency']}")
                
                result['optimization_recommendations']['opportunities'] = opportunities
                result['optimization_recommendations']['recommendations'] = recommendations
                result['optimization_recommendations']['savings_estimates'] = savings_estimates
                
                return {
                    "status": "success",
                    "message": "Cost analysis retrieved successfully",
                    "data": result
                }
                
            except Exception as e:
                logger.error(f'Error processing cost data rows: {str(e)}')
                return {
                    "status": "error",
                    "message": f"Error processing cost data: {str(e)}",
                    "error": str(e),
                    "data": {}
                }
            
    def get_resource_metrics(self, resource_id: str, metric_name: str, 
                           start_time: datetime = None,
                           end_time: datetime = None) -> Dict[str, Any]:
        """Get metrics for a specific resource.
        
        Args:
            resource_id: Azure resource ID
            metric_name: Name of the metric to retrieve
            start_time: Start time for metrics. Defaults to 24 hours ago.
            end_time: End time for metrics. Defaults to now.
            
        Returns:
            Dict containing metric data points and status information
        """
        try:
            # Set default time range if not provided
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(hours=24)
            
            metrics_data = self.monitor_client.metrics.list(
                resource_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval='PT1H',
                metricnames=metric_name,
                aggregation='Average'
            )
            
            if not metrics_data.value:
                return {
                    "status": "empty",
                    "message": f"No metrics data found for {metric_name}",
                    "data": {
                        "resource_id": resource_id,
                        "metric_name": metric_name,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "metrics": []
                    }
                }
            
            # Process metrics data
            metrics = []
            for metric in metrics_data.value:
                for timeseries in metric.timeseries:
                    for datapoint in timeseries.data:
                        if datapoint.average is not None:
                            metrics.append({
                                "timestamp": datapoint.timestamp.isoformat(),
                                "value": datapoint.average,
                                "unit": metric.unit
                            })
            
            return {
                "status": "success",
                "message": f"Successfully retrieved metrics for {metric_name}",
                "data": {
                    "resource_id": resource_id,
                    "metric_name": metric_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "metrics": metrics
                }
            }
            
        except Exception as e:
            logger.error(f'Error getting metrics for {resource_id}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error getting metrics: {str(e)}",
                "error": str(e),
                "data": {
                    "resource_id": resource_id,
                    "metric_name": metric_name,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "metrics": []
                }
            }

        except Exception as e:
            logger.error(f'Error getting resource metrics: {str(e)}')
            return {
                "status": "error",
                "message": f"Error getting resource metrics: {str(e)}",
                "error": str(e),
                "data": {
                    'resource_id': resource_id,
                    'metric_name': metric_name,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'metrics': []
                }
            }

    def list_resource_groups(self) -> Dict[str, Any]:
        """List all resource groups in the subscription with their properties.
        
        Returns:
            Dict containing resource groups and their properties.
        """
        try:
            groups = list(self.resource_client.resource_groups.list())
            if not groups:
                return {
                    "status": "empty",
                    "message": "No resource groups found in the subscription",
                    "data": []
                }
            
            result = [{
                'id': group.id,
                'name': group.name,
                'location': group.location,
                'tags': group.tags or {},
                'provisioning_state': group.properties.provisioning_state,
                'managed_by': group.managed_by
            } for group in groups]
            
            return {
                "status": "success",
                "message": "Resource groups retrieved successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f'Error listing resource groups: {str(e)}')
            return {
                "status": "error",
                "message": f"Error listing resource groups: {str(e)}",
                "error": str(e),
                "data": []
            }
            
    def list_blobs(self, storage_account: str, container: str) -> Dict[str, Any]:
        """List all blobs in a container with detailed information.
        
        Args:
            storage_account: Name of the storage account
            container: Name of the container
            
        Returns:
            Dict containing blob details and metadata.
        """
        try:
            # Get storage account key
            keys = self.storage_client.storage_accounts.list_keys(
                self.resource_group,
                storage_account
            )
            key = keys.keys[0].value
            
            # Create blob service client
            account_url = f"https://{storage_account}.blob.core.windows.net"
            blob_service = BlobServiceClient(
                account_url=account_url,
                credential=key
            )
            
            # Get container client
            container_client = blob_service.get_container_client(container)
            
            # List blobs
            blobs = []
            try:
                for blob in container_client.list_blobs():
                    # Get blob client for additional properties
                    blob_client = container_client.get_blob_client(blob.name)
                    
                    # Get blob properties
                    properties = blob_client.get_blob_properties()
                    
                    blob_info = {
                        'name': blob.name,
                        'size_bytes': properties.size,
                        'content_type': properties.content_settings.content_type,
                        'created_on': properties.creation_time.isoformat() if properties.creation_time else None,
                        'last_modified': properties.last_modified.isoformat() if properties.last_modified else None,
                        'blob_type': properties.blob_type,
                        'lease_state': properties.lease.state if properties.lease else None,
                        'encryption': {
                            'key_id': properties.encryption.key_id if properties.encryption else None,
                            'algorithm': properties.encryption.algorithm if properties.encryption else None
                        },
                        'metadata': properties.metadata,
                        'tags': properties.tag_count,
                        'version_id': properties.version_id,
                        'is_current_version': properties.is_current_version,
                        'etag': properties.etag,
                        'content_hash': properties.content_settings.content_md5
                    }
                    blobs.append(blob_info)
                    
                return {
                    "status": "success",
                    "message": f"Retrieved {len(blobs)} blobs from container {container}",
                    "data": {
                        'storage_account': storage_account,
                        'container': container,
                        'blobs': blobs
                    }
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error listing blobs in container {container}: {str(e)}",
                    "error": str(e),
                    "data": {
                        'storage_account': storage_account,
                        'container': container,
                        'blobs': []
                    }
                }
                
        except Exception as e:
            logger.error(f'Error accessing storage account {storage_account}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error accessing storage account {storage_account}: {str(e)}",
                "error": str(e),
                "data": {
                    'storage_account': storage_account,
                    'container': container,
                    'blobs': []
                }
            }
            
    def list_containers(self, storage_account: str) -> Dict[str, Any]:
        """List all containers in a storage account with detailed information.
        
        Args:
            storage_account: Name of the storage account
            
        Returns:
            Dict containing container details and metadata.
        """
        try:
            # Get storage account key
            keys = self.storage_client.storage_accounts.list_keys(
                self.resource_group,
                storage_account
            )
            key = keys.keys[0].value
            
            # Create blob service client
            account_url = f"https://{storage_account}.blob.core.windows.net"
            blob_service = BlobServiceClient(
                account_url=account_url,
                credential=key
            )
            
            # List containers
            containers = []
            try:
                for container in blob_service.list_containers():
                    # Get container client for properties
                    container_client = blob_service.get_container_client(container.name)
                    properties = container_client.get_container_properties()
                    
                    # Get blob count and size
                    blob_count = 0
                    total_size = 0
                    try:
                        for blob in container_client.list_blobs():
                            blob_count += 1
                            total_size += blob.size
                    except Exception:
                        pass  # Skip if can't access blobs
                    
                    container_info = {
                        'name': container.name,
                        'last_modified': properties.last_modified.isoformat() if properties.last_modified else None,
                        'etag': properties.etag,
                        'lease_state': properties.lease.state if properties.lease else None,
                        'lease_status': properties.lease.status if properties.lease else None,
                        'public_access': properties.public_access,
                        'has_immutability_policy': properties.has_immutability_policy,
                        'has_legal_hold': properties.has_legal_hold,
                        'metadata': properties.metadata,
                        'encryption_scope': properties.default_encryption_scope,
                        'prevent_encryption_scope_override': properties.prevent_encryption_scope_override,
                        'blob_count': blob_count,
                        'total_size_bytes': total_size
                    }
                    containers.append(container_info)
                    
                return {
                    "status": "success",
                    "message": f"Retrieved {len(containers)} containers from storage account {storage_account}",
                    "data": {
                        'storage_account': storage_account,
                        'containers': containers
                    }
                }
                
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error listing containers in storage account {storage_account}: {str(e)}",
                    "error": str(e),
                    "data": {
                        'storage_account': storage_account,
                        'containers': []
                    }
                }
                
        except Exception as e:
            logger.error(f'Error accessing storage account {storage_account}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error accessing storage account {storage_account}: {str(e)}",
                "error": str(e),
                "data": {
                    'storage_account': storage_account,
                    'containers': []
                }
            }
    def start_vm(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """Start a virtual machine.
        
        Args:
            resource_group: Resource group name containing the VM
            vm_name: Name of the virtual machine
            
        Returns:
            Dict containing operation status
        """
        try:
            poller = self.compute_client.virtual_machines.begin_start(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            result = poller.result()  # Wait for operation to complete
            
            # Get updated VM status
            status = self.get_vm_status(resource_group, vm_name)
            
            return {
                "status": "success",
                "message": f"Successfully started VM {vm_name}",
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'current_status': status
                }
            }
            
        except Exception as e:
            logger.error(f'Error starting VM {vm_name}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error starting VM {vm_name}: {str(e)}",
                "error": str(e),
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group
                }
            }
    
    def stop_vm(self, resource_group: str, vm_name: str, deallocate: bool = True) -> Dict[str, Any]:
        """Stop a virtual machine.
        
        Args:
            resource_group: Resource group name containing the VM
            vm_name: Name of the virtual machine
            deallocate: If True, deallocate the VM (stop billing), if False just power off
            
        Returns:
            Dict containing operation status
        """
        try:
            if deallocate:
                poller = self.compute_client.virtual_machines.begin_deallocate(
                    resource_group_name=resource_group,
                    vm_name=vm_name
                )
            else:
                poller = self.compute_client.virtual_machines.begin_power_off(
                    resource_group_name=resource_group,
                    vm_name=vm_name
                )
            
            result = poller.result()  # Wait for operation to complete
            
            # Get updated VM status
            status = self.get_vm_status(resource_group, vm_name)
            
            action = "deallocated" if deallocate else "powered off"
            return {
                "status": "success",
                "message": f"Successfully {action} VM {vm_name}",
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'deallocated': deallocate,
                    'current_status': status
                }
            }
            
        except Exception as e:
            logger.error(f'Error stopping VM {vm_name}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error stopping VM {vm_name}: {str(e)}",
                "error": str(e),
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'deallocated': deallocate
                }
            }
    
    def restart_vm(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """Restart a virtual machine.
        
        Args:
            resource_group: Resource group name containing the VM
            vm_name: Name of the virtual machine
            
        Returns:
            Dict containing operation status
        """
        try:
            poller = self.compute_client.virtual_machines.begin_restart(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            result = poller.result()  # Wait for operation to complete
            
            # Get updated VM status
            status = self.get_vm_status(resource_group, vm_name)
            
            return {
                "status": "success",
                "message": f"Successfully restarted VM {vm_name}",
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'current_status': status
                }
            }
            
        except Exception as e:
            logger.error(f'Error restarting VM {vm_name}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error restarting VM {vm_name}: {str(e)}",
                "error": str(e),
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group
                }
            }
    
    def get_vm_metrics(self, resource_group: str, vm_name: str, 
                      metric_names: List[str] = None) -> Dict[str, Any]:
        """Get metrics for a virtual machine.
        
        Args:
            resource_group: Resource group name containing the VM
            vm_name: Name of the virtual machine
            metric_names: List of metrics to retrieve. If None, gets CPU and memory.
            
        Returns:
            Dict containing VM metrics
        """
        try:
            # Get VM to get its resource ID
            vm = self.compute_client.virtual_machines.get(
                resource_group_name=resource_group,
                vm_name=vm_name
            )
            
            if not metric_names:
                metric_names = [
                    'Percentage CPU',
                    'Available Memory Bytes',
                    'Network In Total',
                    'Network Out Total',
                    'Disk Read Bytes',
                    'Disk Write Bytes'
                ]
            
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            metrics_data = {}
            for metric_name in metric_names:
                try:
                    metric_data = self.get_resource_metrics(
                        vm.id,
                        metric_name,
                        start_time,
                        end_time
                    )
                    if metric_data["status"] == "success":
                        metrics_data[metric_name] = metric_data["data"]["metrics"]
                except Exception as e:
                    logger.warning(f'Error getting metric {metric_name} for VM {vm_name}: {str(e)}')
                    metrics_data[metric_name] = []
            
            return {
                "status": "success",
                "message": f"Retrieved metrics for VM {vm_name}",
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'resource_id': vm.id,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'metrics': metrics_data
                }
            }
            
        except Exception as e:
            logger.error(f'Error getting VM metrics for {vm_name}: {str(e)}')
            return {
                "status": "error",
                "message": f"Error getting VM metrics for {vm_name}: {str(e)}",
                "error": str(e),
                "data": {
                    'vm_name': vm_name,
                    'resource_group': resource_group,
                    'metrics': {}
                }
            }

    def list_resource_groups(self) -> Dict[str, Any]:
        """List all resource groups in the subscription with their properties.
        
        Returns:
            Dict containing resource groups and their properties.
        """
        try:
            groups = list(self.resource_client.resource_groups.list())
            if not groups:
                return {
                    "status": "empty",
                    "message": "No resource groups found in the subscription",
                    "data": []
                }
            
            result = [{
                'id': group.id,
                'name': group.name,
                'location': group.location,
                'tags': group.tags or {},
                'provisioning_state': group.properties.provisioning_state,
                'managed_by': group.managed_by
            } for group in groups]
            
            return {
                "status": "success",
                "message": "Resource groups retrieved successfully",
                "data": result
            }
            
        except Exception as e:
            logger.error(f'Error listing resource groups: {str(e)}')
            return {
                "status": "error",
                "message": f"Error listing resource groups: {str(e)}",
                "error": str(e),
                "data": []
            }
            for group in self.resource_client.resource_groups.list():
                groups.append({
                    'name': group.name,
                    'location': group.location,
                    'provisioning_state': group.properties.provisioning_state,
                    'tags': group.tags or {}
                })
            return groups
        except Exception as e:
            raise Exception(f'Error listing resource groups: {str(e)}')
