from fastapi import APIRouter, HTTPException, Query
from typing import Literal
from app.cloud_providers.azure_client import AzureClient
from app.cloud_providers.aws_client import AWSClient
import os

router = APIRouter()

# Initialize cloud clients
azure_client = AzureClient()
aws_client = AWSClient(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

@router.get("/{provider}")
async def get_cost_analysis(
    provider: Literal["azure", "aws"],
    timeframe: str = Query("LastMonth", regex="^(LastMonth|LastWeek)$")
):
    try:
        if provider == "azure":
            return azure_client.get_cost_analysis(timeframe)
        else:
            # Convert timeframe to AWS format
            from datetime import datetime, timedelta
            end_date = datetime.now()
            
            if timeframe == "LastMonth":
                start_date = end_date - timedelta(days=30)
            else:  # LastWeek
                start_date = end_date - timedelta(days=7)
                
            return aws_client.get_cost_and_usage(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
