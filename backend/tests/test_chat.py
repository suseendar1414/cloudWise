import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_aws_costs():
    response = client.post("/api/chat", json={
        "query": "Show me AWS costs for last month"
    })
    assert response.status_code == 200
    assert "AWS Costs" in response.json()["response"]

def test_chat_azure_vms():
    response = client.post("/api/chat", json={
        "query": "List all Azure VMs"
    })
    assert response.status_code == 200
    assert "Azure VMs" in response.json()["response"]


def test_chat_aws_volumes():
    response = client.post("/api/chat", json={
        "query": "Show me AWS volumes"
    })
    assert response.status_code == 200
    assert "AWS Volumes" in response.json()["response"]