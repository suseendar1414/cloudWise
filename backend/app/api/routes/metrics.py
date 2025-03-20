from fastapi import APIRouter, HTTPException, Query
from typing import Literal
from app.cloud_providers.azure_client import AzureClient
from app.cloud_providers.aws_client import AWSClient
import os
from datetime import datetime, timedelta

router = APIRouter()

# Initialize cloud clients
azure_client = AzureClient()
aws_client = AWSClient(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

@router.get("/{provider}/{resource_id}")
async def get_resource_metrics(
    provider: Literal["azure", "aws"],
    resource_id: str,
    metric_name: str = Query(..., description="Name of the metric to retrieve"),
    timeframe: str = Query("LastDay", regex="^(LastDay|LastWeek|LastMonth)$")
):
    try:
        end_time = datetime.utcnow()
        if timeframe == "LastDay":
            start_time = end_time - timedelta(days=1)
        elif timeframe == "LastWeek":
            start_time = end_time - timedelta(days=7)
        else:  # LastMonth
            start_time = end_time - timedelta(days=30)

        if provider == "azure":
            # Implement Azure metrics retrieval
            metrics = azure_client.get_resource_metrics(
                resource_id=resource_id,
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time
            )
        else:
            # Implement AWS CloudWatch metrics retrieval
            metrics = aws_client.get_cloudwatch_metrics(
                resource_id=resource_id,
                metric_name=metric_name,
                start_time=start_time,
                end_time=end_time
            )

        return {
            "resourceId": resource_id,
            "resourceType": metric_name,
            "metrics": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
