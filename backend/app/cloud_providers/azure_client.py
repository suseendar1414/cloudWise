import os
import logging
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.core.exceptions import AzureError
from typing import Dict, List, Any
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

    def list_storage_accounts(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all storage accounts grouped by region.
        
        Returns:
            Dict with regions as keys and list of storage account details as values.
        """
        try:
            accounts = self.storage_client.storage_accounts.list()
            accounts_by_region = {}
            
            for account in accounts:
                account_info = {
                    'id': account.id,
                    'name': account.name,
                    'location': account.location,
                    'resource_group': account.id.split('/')[4],
                    'type': account.type,
                    'provisioning_state': account.provisioning_state
                }
                
                region = account.location
                if region not in accounts_by_region:
                    accounts_by_region[region] = []
                accounts_by_region[region].append(account_info)
            
            return accounts_by_region
            
        except Exception as e:
            logger.error(f'Error listing storage accounts: {str(e)}')
            raise

    def get_cost_analysis(self, timeframe: str = 'LastMonth') -> Dict[str, Any]:
        """Get cost analysis for the subscription.
        
        Args:
            timeframe: Time period for cost analysis ('LastMonth' or 'LastWeek').
            
        Returns:
            Dict containing cost analysis details including total cost, currency,
            and cost breakdowns by service and location.
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
                        }
                    ]
                }
            }
            
            # Get cost data
            cost_data = self.cost_client.query.usage(scope=scope, parameters=parameters)
            
            # Process and return cost data
            result = {
                'timeframe': timeframe,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'currency': cost_data.columns[0].name,
                'total_cost': 0.0,
                'costs_by_service': {},
                'costs_by_location': {}
            }
            
            # Group costs by service and location
            try:
                for row in cost_data.rows:
                    cost = float(row[0])
                    service = row[1] or 'Unknown'
                    location = row[2] or 'Unknown'
                    
                    result['total_cost'] += cost
                    
                    if service not in result['costs_by_service']:
                        result['costs_by_service'][service] = 0.0
                    result['costs_by_service'][service] += cost
                    
                    if location not in result['costs_by_location']:
                        result['costs_by_location'][location] = 0.0
                    result['costs_by_location'][location] += cost
            except Exception as e:
                logger.error(f'Error processing cost data rows: {str(e)}')
                raise
            
            logger.info(f'Retrieved cost analysis for {timeframe}')
            logger.info(f'Total cost: {result["total_cost"]} {result["currency"]}')
            logger.info(f'Services with costs: {len(result["costs_by_service"])}')
            logger.info(f'Locations with costs: {len(result["costs_by_location"])}')
            
            return result
        except Exception as e:
            logger.error(f'Error getting cost analysis: {str(e)}')
            raise
            
    def get_resource_metrics(self, resource_id: str, metric_name: str, 
                           start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Get metrics for a specific resource.
        
        Args:
            resource_id: Azure resource ID
            metric_name: Name of the metric to retrieve
            start_time: Start time for metrics
            end_time: End time for metrics
            
        Returns:
            List of metric data points
        """
        try:
            metrics_data = self.monitor_client.metrics.list(
                resource_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval='PT1H',  # 1-hour intervals
                metricnames=metric_name,
                aggregation='Average'
            )

            # Process metrics data
            metrics = []
            for metric in metrics_data.value:
                for timeseries in metric.timeseries:
                    for data in timeseries.data:
                        if data.average is not None:
                            metrics.append({
                                'timestamp': data.time_stamp.isoformat(),
                                'value': data.average,
                                'unit': metric.unit
                            })

            return metrics

        except Exception as e:
            logger.error(f'Error getting resource metrics: {str(e)}')
            raise

    def list_resource_groups(self) -> List[Dict[str, Any]]:
        """List all resource groups in the subscription"""
        try:
            groups = []
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
