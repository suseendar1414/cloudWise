from functools import wraps
from fastapi import HTTPException, Request
from app.cloud_providers.azure_client import AzureClient
from app.cloud_providers.aws_client import AWSClient
import os

# Initialize cloud clients
azure_client = AzureClient(
    subscription_id=os.getenv('AZURE_SUBSCRIPTION_ID'),
    tenant_id=os.getenv('AZURE_TENANT_ID'),
    client_id=os.getenv('AZURE_CLIENT_ID'),
    client_secret=os.getenv('AZURE_CLIENT_SECRET')
)

aws_client = AWSClient(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region=os.getenv('AWS_REGION', 'eu-west-2')
)

def validate_cloud_provider(request: Request):
    provider = request.path_params.get('provider')
    if provider not in ['azure', 'aws']:
        raise HTTPException(status_code=400, detail="Invalid cloud provider")
    
    try:
        if provider == 'azure':
            azure_client.validate_credentials()
        else:
            aws_client.validate_credentials()
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

def require_cloud_auth(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        validate_cloud_provider(request)
        return await func(request, *args, **kwargs)
    return wrapper
