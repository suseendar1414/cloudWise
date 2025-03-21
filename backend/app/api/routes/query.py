from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.config import config
from app.cloud_providers.aws_client import AWSClient
from app.cloud_providers.azure_client import AzureClient
from app.llm.llm_service import LLMService
from datetime import datetime, timedelta
from typing import Union

router = APIRouter()

class Query(BaseModel):
    query: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None

def get_aws_client() -> AWSClient:
    """Dependency to get AWS client"""
    try:
        return AWSClient(
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region=config.AWS_DEFAULT_REGION
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize AWS client: {str(e)}")

def get_azure_client() -> AzureClient:
    """Dependency to get Azure client"""
    try:
        return AzureClient()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Azure client: {str(e)}")

def get_llm_service() -> LLMService:
    """Dependency to get LLM service"""
    try:
        return LLMService(api_key=config.OPENAI_API_KEY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize LLM service: {str(e)}")

def convert_to_aws_filters(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert LLM service parameters to AWS filter format"""
    filters = []
    for key, value in parameters.items():
        # Skip empty values
        if not value:
            continue
            
        if isinstance(value, list):
            # Filter out empty values from lists
            valid_values = [str(v) for v in value if v and str(v).strip()]
            if valid_values:
                filters.append({"Name": key, "Values": valid_values})
        elif value and str(value).strip():
            filters.append({"Name": key, "Values": [str(value)]})
    return filters

@router.post("/query")
def process_query(
    query: Query,
    aws: AWSClient = Depends(get_aws_client),
    azure: AzureClient = Depends(get_azure_client),
    llm: LLMService = Depends(get_llm_service)
):
    try:
        # Get available cloud platforms
        available_platforms = ["AWS", "Azure"]
        
        # Process the query using LLM service
        parsed = llm.process_cloud_query(
            user_query=query.query,
            available_platforms=available_platforms,
            current_context={
                "start_date": query.start_date,
                "end_date": query.end_date
            }
        )
        
        print("DEBUG - Parsed Query:", parsed)  # Debug log
        
        # Process based on the parsed query
        try:
            print("DEBUG - Resources:", parsed['resources'])  # Debug log
            print("DEBUG - Action:", parsed['action'])  # Debug log
            
            # Determine cloud platform
            platform = parsed.get('platform', 'aws').lower()
            
            # Handle compute instances (EC2/VMs)
            if any(r.lower() in ['ec2', 'instance', 'instances', 'vm', 'vms'] for r in parsed.get('resources', [])):
                if platform == 'aws':
                    filters = convert_to_aws_filters(parsed.get('parameters', {}))
                    data = aws.list_ec2_instances(filters=filters)
                    if not data:
                        return {
                            "message": "No EC2 instances found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "empty",
                                "reason": "No EC2 instances match your query criteria. This could be because:",
                                "possible_reasons": [
                                    "No EC2 instances exist in your AWS account",
                                    "No instances match the specified filters",
                                    "Instances exist in regions not currently accessible"
                                ],
                                "applied_filters": filters
                            }
                        }
                else:  # Azure
                    resource_group = parsed.get('parameters', {}).get('resource_group')
                    data = azure.list_virtual_machines(resource_group=resource_group)
                    if not data:
                        return {
                            "message": "No Azure VMs found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "empty",
                                "reason": "No Azure VMs match your query criteria. This could be because:",
                                "possible_reasons": [
                                    "No VMs exist in your Azure subscription",
                                    "No VMs exist in the specified resource group",
                                    "VMs exist but are not accessible with current permissions"
                                ],
                                "resource_group": resource_group
                            }
                        }
            
            # Handle storage (S3/Blob Storage)
            elif any(r.lower() in ['s3', 'storage', 'blob'] for r in parsed['resources']):
                if platform == 'aws':
                    data = aws.list_s3_buckets()
                    if not data:
                        return {
                            "message": "No S3 buckets found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "empty",
                                "reason": "No S3 buckets were found. This could be because:",
                                "possible_reasons": [
                                    "No S3 buckets exist in your AWS account",
                                    "Buckets exist but are not accessible with current permissions",
                                    "Buckets exist in regions not currently accessible"
                                ]
                            }
                        }
                else:  # Azure
                    data = azure.list_storage_accounts()
                    if data.get('status') == 'empty':
                        return {
                            "message": "No Azure storage accounts found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "empty",
                                "reason": "No Azure storage accounts were found. This could be because:",
                                "possible_reasons": [
                                    "No storage accounts exist in your Azure subscription",
                                    "Storage accounts exist but are not accessible with current permissions",
                                    "Storage accounts exist in regions not currently accessible"
                                ]
                            }
                        }
            
            # Handle costs and usage
            elif any(r in ['costs', 'cost'] for r in parsed['resources']) or 'cost' in parsed['action'].lower():
                # Use provided dates or default to last 30 days
                end_date = query.end_date or datetime.now().strftime('%Y-%m-%d')
                start_date = query.start_date or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                if platform == 'aws':
                    data = aws.get_cost_and_usage(start_date=start_date, end_date=end_date)
                else:  # Azure
                    data = azure.get_cost_analysis(timeframe='LastMonth' if (datetime.now() - datetime.strptime(start_date, '%Y-%m-%d')).days >= 30 else 'LastWeek')
                
                # Get cost optimization recommendations if available
                try:
                    recommendations = llm.get_cost_optimization(
                        resource_details={"costs": data},
                        cost_data=data
                    )
                    if isinstance(data, dict) and 'data' in data:
                        data['data']['optimization_recommendations'] = recommendations
                    else:
                        data['optimization_recommendations'] = recommendations
                except Exception:
                    # Don't fail if optimization recommendations fail
                    pass
            
            # Handle metrics
            elif "metrics" in parsed.get('resources', []) or "get_metrics" in parsed.get('action', '').lower():
                # Get time range
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=24)
                
                if platform == 'aws':
                    # Extract instance ID from parameters
                    instance_id = parsed.get('parameters', {}).get('instance-id', '')
                    if not instance_id:
                        raise HTTPException(status_code=400, detail="Instance ID is required for metrics queries")
                    
                    # Clean up instance ID (remove quotes if present)
                    instance_id = instance_id.strip('"')
                    
                    # First verify if the instance exists
                    instances = aws.list_ec2_instances(filters=[{"Name": "instance-id", "Values": [instance_id]}])
                    if not instances:
                        return {
                            "message": "Instance not found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "error",
                                "reason": f"EC2 instance {instance_id} not found. This could be because:",
                                "possible_reasons": [
                                    "The instance ID is incorrect",
                                    "The instance has been terminated",
                                    "The instance exists in a different region",
                                    "Insufficient permissions to access the instance"
                                ]
                            }
                        }
                    
                    data = aws.get_cloudwatch_metrics(
                        resource_id=instance_id,
                        metric_name=parsed.get('parameters', {}).get('metric_name', 'CPUUtilization').strip('"'),
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if not data:
                        return {
                            "message": "No metrics data found",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "empty",
                                "reason": f"No metrics data found for instance {instance_id}. This could be because:",
                                "possible_reasons": [
                                    "CloudWatch metrics are not enabled for this instance",
                                    "No metric data available for the last 24 hours",
                                    "The instance was stopped during this period",
                                    "Insufficient permissions to access CloudWatch metrics"
                                ],
                                "instance_id": instance_id,
                                "metric_name": parsed.get('parameters', {}).get('metric_name', 'CPUUtilization').strip('"'),
                                "time_range": {
                                    "start": start_time.isoformat(),
                                    "end": end_time.isoformat()
                                }
                            }
                        }
                else:  # Azure
                    # Extract VM details from parameters
                    resource_group = parsed.get('parameters', {}).get('resource_group')
                    vm_name = parsed.get('parameters', {}).get('vm_name')
                    
                    if not all([resource_group, vm_name]):
                        raise HTTPException(status_code=400, detail="Resource group and VM name are required for Azure metrics queries")
                    
                    data = azure.get_vm_metrics(
                        resource_group=resource_group,
                        vm_name=vm_name,
                        metric_names=parsed.get('parameters', {}).get('metric_names', None)
                    )
                    
                    if data.get('status') == 'error':
                        return {
                            "message": "Failed to get VM metrics",
                            "query": query.query,
                            "parsed_query": parsed,
                            "data": {},
                            "details": {
                                "status": "error",
                                "reason": f"Failed to get metrics for VM {vm_name}. This could be because:",
                                "possible_reasons": [
                                    "The VM does not exist",
                                    "The VM exists in a different resource group",
                                    "The VM is not running",
                                    "Azure Monitor is not enabled for this VM",
                                    "Insufficient permissions to access metrics"
                                ],
                                "resource_group": resource_group,
                                "vm_name": vm_name,
                                "time_range": {
                                    "start": start_time.isoformat(),
                                    "end": end_time.isoformat()
                                }
                            }
                        }
            
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported resource type or action")

        except Exception as operation_error:
            # Analyze the error using LLM service
            error_analysis = llm.analyze_error(
                operation=parsed.get('action', 'unknown'),
                error_message=str(operation_error),
                platform="AWS",
                resource=str(parsed.get('resources', []))
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(operation_error),
                    "analysis": error_analysis
                }
            )

        return {
            "message": "Success",
            "query": query.query,
            "parsed_query": parsed,
            "data": data
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
