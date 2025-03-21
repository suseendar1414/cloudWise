import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from cloud_providers.azure_client import AzureClient

def main():
    try:
        # Initialize Azure client
        azure_client = AzureClient()
        
        print("\n=== Testing Azure Connection ===")
        if azure_client.test_connection():
            print("✅ Successfully connected to Azure")
        else:
            print("❌ Failed to connect to Azure")
            return
        
        print("\n=== Listing Resource Groups ===")
        resource_groups = azure_client.list_resource_groups()
        print(f"Found {len(resource_groups.get('resource_groups', []))} resource groups")
        for rg in resource_groups.get('resource_groups', []):
            print(f"- {rg.get('name')} ({rg.get('location')})")
        
        print("\n=== Listing Virtual Machines ===")
        vms = azure_client.list_virtual_machines()
        for region, machines in vms.get('vms', {}).items():
            print(f"\nRegion: {region}")
            for vm in machines:
                print(f"- {vm.get('name')} ({vm.get('status')})")
        
        print("\n=== Listing Storage Accounts ===")
        storage = azure_client.list_storage_accounts()
        for region, accounts in storage.get('accounts', {}).items():
            print(f"\nRegion: {region}")
            for account in accounts:
                print(f"- {account.get('name')} ({account.get('kind')})")
        
        print("\n=== Getting Cost Analysis ===")
        costs = azure_client.get_cost_analysis(timeframe='LastMonth')
        if costs.get('status') == 'success':
            print(f"Total Cost: {costs.get('data', {}).get('total_cost', 0)} {costs.get('data', {}).get('currency', 'USD')}")
        else:
            print(f"Failed to get costs: {costs.get('message')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
