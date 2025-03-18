from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from ..cloud_providers.aws_client import AWSClient
from ..cloud_providers.azure_client import AzureClient
from ..services.llm_service import LLMService
from datetime import datetime, timedelta
import os

# Initialize services with optional cloud clients
aws_client = None
azure_client = None
llm_service = None

def init_services():
    """Initialize services if environment variables are available"""
    global aws_client, azure_client, llm_service
    
    # Initialize AWS client if credentials are available
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        try:
            aws_client = AWSClient(
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                region=os.getenv('AWS_REGION', 'us-west-2')
            )
            print("AWS client initialized successfully")
        except Exception as e:
            print(f"Failed to initialize AWS client: {str(e)}")
            aws_client = None
    
    # Initialize Azure client if all Azure credentials are available
    required_azure_vars = [
        'AZURE_SUBSCRIPTION_ID',
        'AZURE_TENANT_ID',
        'AZURE_CLIENT_ID',
        'AZURE_CLIENT_SECRET'
    ]
    
    if all(os.getenv(var) for var in required_azure_vars):
        try:
            azure_client = AzureClient(
                subscription_id=os.getenv('AZURE_SUBSCRIPTION_ID')
            )
            print("Azure client initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Azure client: {str(e)}")
            print("Azure credentials found:")
            for var in required_azure_vars:
                print(f"{var}: {'Present' if os.getenv(var) else 'Missing'}")
            azure_client = None
    else:
        print("Missing required Azure credentials:")
        for var in required_azure_vars:
            print(f"{var}: {'Present' if os.getenv(var) else 'Missing'}")
    
    # Initialize LLM service if API key is available
    if os.getenv('OPENAI_API_KEY'):
        try:
            llm_service = LLMService(
                api_key=os.getenv('OPENAI_API_KEY')
            )
            print("LLM service initialized successfully")
        except Exception as e:
            print(f"Failed to initialize LLM service: {str(e)}")
            llm_service = None

# Try to initialize services
init_services()

# Create API router
router = APIRouter()

# Pydantic models for request/response validation
class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query for cloud management")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the query")

class ErrorAnalysisRequest(BaseModel):
    operation: str = Field(..., description="Operation that caused the error")
    error_message: str = Field(..., description="Error message received")
    platform: str = Field(..., description="Cloud platform (AWS/Azure)")
    resource: str = Field(..., description="Resource type involved")

class CostOptimizationRequest(BaseModel):
    platform: str = Field("all", description="Platform to analyze (aws/azure/all)")

class CloudCommandResponse(BaseModel):
    command_interpreted: Dict[str, Any]
    results: Dict[str, Any]

@router.post("/query", response_model=CloudCommandResponse)
async def process_query(request: QueryRequest):
    """Process a natural language cloud management query"""
    try:
        if not llm_service:
            return {
                'status': 'error',
                'message': 'LLM service not initialized. Please check OPENAI_API_KEY.',
                'available_services': {
                    'aws': aws_client is not None,
                    'azure': azure_client is not None,
                    'llm': llm_service is not None
                }
            }

        # Process the query through LLM
        result = llm_service.process_cloud_query(
            user_query=request.query,
            available_platforms=['AWS', 'Azure'] if aws_client and azure_client else 
                        ['AWS'] if aws_client else 
                        ['Azure'] if azure_client else [],
            current_context=request.context
        )

        # Execute the interpreted command
        response = await execute_cloud_command(result)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def execute_cloud_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the interpreted cloud command"""
    try:
        responses = {}
        service_status = {
            'aws': aws_client is not None,
            'azure': azure_client is not None,
            'llm': llm_service is not None
        }
        
        # Handle Azure operations
        if 'Azure' in command['platforms']:
            if not azure_client:
                responses['azure_error'] = 'Azure client not initialized. Please check Azure credentials.'
            else:
                try:
                    # Process each requested resource type
                    for resource in command['resources']:
                        if resource == 'VM':
                            if 'list' in command['action'].lower():
                                region_vms = azure_client.list_virtual_machines(
                                    resource_group=command['parameters'].get('resource_group')
                                )
                                responses['azure_vm'] = {
                                    'regions': region_vms,
                                    'total_vms': sum(len(vms) for vms in region_vms.values())
                                }
                        
                        elif resource == 'Storage':
                            if 'list' in command['action'].lower():
                                region_accounts = azure_client.list_storage_accounts()
                                responses['azure_storage'] = {
                                    'regions': region_accounts,
                                    'total_accounts': sum(len(accounts) for accounts in region_accounts.values())
                                }
                        
                        elif resource in ['cost', 'costs']:
                            timeframe = command['parameters'].get('timeframe', 'LastMonth')
                            responses['azure_costs'] = azure_client.get_cost_analysis(timeframe)
                except Exception as e:
                    responses['azure_error'] = f'Error executing Azure command: {str(e)}'
        
        # Handle AWS operations
        if 'AWS' in command['platforms']:
            if not aws_client:
                responses['aws_error'] = 'AWS client not initialized. Please check AWS credentials.'
            else:
                try:
                    # Process each requested resource type
                    for resource in command['resources']:
                        if resource == 'EC2':
                            if 'list' in command['action'].lower():
                                region_instances = aws_client.list_ec2_instances(
                                    filters=command['parameters'].get('filters')
                                )
                                responses['aws_ec2'] = {
                                    'regions': region_instances,
                                    'total_instances': sum(len(instances) for instances in region_instances.values())
                                }
                        
                        elif resource == 'S3':
                            if 'list' in command['action'].lower():
                                region_buckets = aws_client.list_s3_buckets()
                                responses['aws_s3'] = {
                                    'regions': region_buckets,
                                    'total_buckets': sum(len(buckets) for buckets in region_buckets.values()),
                                    'total_size': sum(sum(b['Size'] for b in buckets) for buckets in region_buckets.values()),
                                    'total_objects': sum(sum(b['ObjectCount'] for b in buckets) for buckets in region_buckets.values())
                                }
                        
                        elif resource in ['cost', 'costs']:
                            end_date = datetime.now().strftime('%Y-%m-%d')
                            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                            responses['aws_costs'] = aws_client.get_cost_and_usage(start_date, end_date)
                except Exception as e:
                    responses['aws_error'] = f'Error executing AWS command: {str(e)}'

        # Handle Azure operations
        if 'Azure' in command['platforms']:
            if not azure_client:
                responses['azure_error'] = 'Azure client not initialized. Please check Azure credentials.'
            else:
                if 'VM' in command['resources']:
                    if 'list' in command['action'].lower():
                        responses['azure_vms'] = azure_client.list_virtual_machines(
                            resource_group=command['parameters'].get('resource_group')
                        )
                    elif 'status' in command['action'].lower():
                        responses['azure_vm_status'] = azure_client.get_vm_status(
                            resource_group=command['parameters']['resource_group'],
                            vm_name=command['parameters']['vm_name']
                        )
                elif 'ResourceGroup' in command['resources']:
                    if 'list' in command['action'].lower():
                        responses['azure_groups'] = azure_client.list_resource_groups()

        return {
            'command_interpreted': command,
            'results': responses,
            'available_services': {
                'aws': aws_client is not None,
                'azure': azure_client is not None,
                'llm': llm_service is not None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-error")
async def analyze_error(request: ErrorAnalysisRequest):
    """Analyze a cloud operation error"""
    try:
        analysis = llm_service.analyze_error(
            operation=request.operation,
            error_message=request.error_message,
            platform=request.platform,
            resource=request.resource
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize-costs")
async def optimize_costs(request: CostOptimizationRequest):
    """Get cost optimization recommendations"""
    try:
        platform = request.platform.lower()
        resource_details = {}
        cost_data = {}
        
        # Gather resource and cost data
        if platform in ['all', 'aws']:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            resource_details['aws_ec2'] = aws_client.list_ec2_instances()
            resource_details['aws_s3'] = aws_client.list_s3_buckets()
            cost_data['aws'] = aws_client.get_cost_and_usage(start_date, end_date)
            
        if platform in ['all', 'azure']:
            resource_details['azure_vms'] = azure_client.list_virtual_machines()
            resource_details['azure_groups'] = azure_client.list_resource_groups()

        recommendations = llm_service.get_cost_optimization(
            resource_details=resource_details,
            cost_data=cost_data
        )
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
