import os
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import SubscriptionClient
from app.cloud_providers.azure_client import AzureClient

# Load environment variables from .env file
load_dotenv()

# Print available Azure credentials (masked)
print("Azure credentials status:")
for var in ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_SUBSCRIPTION_ID']:
    value = os.getenv(var)
    if value:
        masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '****'
        print(f"{var}: {masked}")
    else:
        print(f"{var}: Not found")

try:
    # First, let's check what subscriptions are available
    print("\nChecking available subscriptions...")
    credential = ClientSecretCredential(
        tenant_id=os.getenv('AZURE_TENANT_ID'),
        client_id=os.getenv('AZURE_CLIENT_ID'),
        client_secret=os.getenv('AZURE_CLIENT_SECRET')
    )
    subscription_client = SubscriptionClient(credential)
    
    print("Available subscriptions:")
    for sub in subscription_client.subscriptions.list():
        print(f"- {sub.display_name} (ID: {sub.subscription_id})")
        print(f"  State: {sub.state}")

    # Now try to initialize our client
    print("\nTrying to initialize Azure client...")
    client = AzureClient()
    print("Azure connection successful!")
except Exception as e:
    print(f"\nConnection failed: {str(e)}")