from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class Query(BaseModel):
    query: str

@router.post("/query")
def process_query(query: Query):
    try:
        return {
            "message": "Success",
            "query": query.query,
            "data": {
                "instances": [
                    {"id": "i-123", "state": "running"},
                    {"id": "i-456", "state": "stopped"}
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
