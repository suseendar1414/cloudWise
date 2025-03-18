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

class AzureClient:
    def __init__(self, subscription_id: str = None):
        # Get credentials from environment variables
        tenant_id = os.getenv('AZURE_TENANT_ID')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        
        logging.info(f'Initializing Azure client with:')
        logging.info(f'Tenant ID: {tenant_id}')
        logging.info(f'Client ID: {client_id}')
        logging.info(f'Subscription ID: {self.subscription_id}')
        
        if not all([tenant_id, client_id, client_secret, self.subscription_id]):
            raise ValueError('Missing required Azure credentials in environment variables')
        
        try:
            # Create credential object
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Initialize subscription client and validate access
            sub_client = SubscriptionClient(self.credential)
            sub = next((s for s in sub_client.subscriptions.list() 
                       if s.subscription_id == self.subscription_id), None)
            if not sub:
                raise ValueError(f'Subscription {self.subscription_id} not found or not accessible')
            
            logging.info(f'Successfully connected to Azure subscription: {sub.display_name}')
        except Exception as e:
            logging.error(f'Error validating Azure credentials: {str(e)}')
            raise
        
        # Get or create resource group
        self.resource_group = os.getenv('AZURE_RESOURCE_GROUP_NAME', 'cloudwise-rg')
        self.location = os.getenv('AZURE_LOCATION', 'eastus')
        
        # Initialize clients
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

    def ensure_resource_group_exists(self):
        """Ensure the resource group exists, create if it doesn't"""
        try:
            self.resource_client.resource_groups.get(self.resource_group)
        except Exception:
            self.resource_client.resource_groups.create_or_update(
                self.resource_group,
                {"location": self.location}
            )
    
    def list_virtual_machines(self, resource_group: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """List Azure Virtual Machines grouped by region with optional resource group filter"""
        try:
            # Ensure resource group exists
            self.ensure_resource_group_exists()
            vms_by_region = {}
            if resource_group:
                vm_list = self.compute_client.virtual_machines.list(resource_group_name=resource_group)
            else:
                vm_list = self.compute_client.virtual_machines.list_all()

            for vm in vm_list:
                vm_info = {
                    'name': vm.name,
                    'vm_size': vm.hardware_profile.vm_size,
                    'os_type': vm.storage_profile.os_disk.os_type,
                    'provisioning_state': vm.provisioning_state,
                    'resource_group': vm.id.split('/')[4],
                    'tags': vm.tags or {}
                }
                
                region = vm.location
                if region not in vms_by_region:
                    vms_by_region[region] = []
                vms_by_region[region].append(vm_info)
                
            return vms_by_region
        except Exception as e:
            raise Exception(f'Error listing Azure VMs: {str(e)}')

    def get_vm_status(self, resource_group: str, vm_name: str) -> Dict[str, Any]:
        """Get detailed status of a specific Virtual Machine"""
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
            raise Exception(f'Error getting VM status: {str(e)}')

    def list_storage_accounts(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all storage accounts grouped by region"""
        try:
            accounts_by_region = {}
            for account in self.storage_client.storage_accounts.list():
                account_info = {
                    'name': account.name,
                    'resource_group': account.id.split('/')[4],
                    'kind': account.kind,
                    'sku': account.sku.name,
                    'provisioning_state': account.provisioning_state,
                    'creation_time': account.creation_time.isoformat() if account.creation_time else None,
                    'tags': account.tags or {}
                }
                
                # Get storage metrics
                try:
                    metrics = self.storage_client.blob_services.get_service_properties(
                        account_info['resource_group'],
                        account.name
                    )
                    account_info['metrics'] = {
                        'hour_metrics': metrics.hour_metrics.to_dict() if metrics.hour_metrics else None,
                        'minute_metrics': metrics.minute_metrics.to_dict() if metrics.minute_metrics else None
                    }
                except Exception:
                    account_info['metrics'] = None
                
                region = account.location
                if region not in accounts_by_region:
                    accounts_by_region[region] = []
                accounts_by_region[region].append(account_info)
                
            return accounts_by_region
        except Exception as e:
            raise Exception(f'Error listing storage accounts: {str(e)}')
            
    def get_cost_analysis(self, timeframe: str = 'LastMonth') -> Dict[str, Any]:
        """Get cost analysis for the subscription"""
        try:
            # Set time range
            end_date = datetime.now(timezone.utc)
            if timeframe == 'LastMonth':
                start_date = end_date - timedelta(days=30)
            elif timeframe == 'LastWeek':
                start_date = end_date - timedelta(days=7)
            else:
                start_date = end_date - timedelta(days=30)  # Default to last 30 days
            
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
                            'name': 'Location'
                        }
                    ]
                }
            }
            
            # Get cost data
            cost_data = self.cost_client.query.usage(scope=scope, parameters=parameters)
            
            # Process and format the response
            result = {
                'timeframe': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'total_cost': 0.0,
                'currency': cost_data.currency,
                'costs_by_service': {},
                'costs_by_location': {}
            }
            
            # Aggregate costs
            if cost_data.rows:
                for row in cost_data.rows:
                    cost = float(row[0])
                    service = row[2]
                    location = row[3]
                    
                    result['total_cost'] += cost
                    
                    if service not in result['costs_by_service']:
                        result['costs_by_service'][service] = 0.0
                    result['costs_by_service'][service] += cost
                    
                    if location not in result['costs_by_location']:
                        result['costs_by_location'][location] = 0.0
                    result['costs_by_location'][location] += cost
            
            return result
        except Exception as e:
            raise Exception(f'Error getting cost analysis: {str(e)}')
            
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
