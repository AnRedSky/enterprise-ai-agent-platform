from __future__ import annotations
import json, os, sys, uuid
from pathlib import Path
import httpx
BASE_URL=os.getenv("API_BASE_URL","http://127.0.0.1:8000/api/v1").rstrip("/")
TIMEOUT=20.0
ENV_FILE=Path(__file__).with_name(".real_api_context.json")
def request(client, method, path, **kwargs):
    response=client.request(method,path,**kwargs)
    if response.status_code>=400: raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text}")
    return response
def main():
    username=os.getenv("API_TEST_USERNAME") or f"api_real_test_{uuid.uuid4().hex[:12]}"
    password=os.getenv("API_TEST_PASSWORD") or f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    with httpx.Client(base_url=BASE_URL,timeout=TIMEOUT) as client:
        if not os.getenv("API_TEST_USERNAME"): request(client,"POST","/auth/register",json={"username":username,"password":password})
        login=request(client,"POST","/auth/login",json={"username":username,"password":password})
        token=login.json().get("access_token")
        if not token: raise RuntimeError("Login response does not contain access_token")
        client.headers["Authorization"]=f"Bearer {token}"
        workflows=request(client,"GET","/workflows").json()
        workflow_id=next((item["id"] for item in workflows if item.get("published_version_id")),None)
        if workflow_id is None:
            workflow=request(client,"POST","/workflows",json={"name":f"API Real Validation {uuid.uuid4().hex[:8]}","description":"Automated real API validation fixture"}).json()
            workflow_id=workflow["id"]
            version=request(client,"POST",f"/workflows/{workflow_id}/versions",json={"definition":{"nodes":[],"edges":[]}}).json()
            request(client,"POST",f"/workflows/{workflow_id}/versions/{version['id']}/publish")
        execution=request(client,"POST",f"/workflows/{workflow_id}/executions",json={"input_data":{"source":"real_api_validation"}}).json()
    ENV_FILE.write_text(json.dumps({"ACCESS_TOKEN":token,"WORKFLOW_ID":str(workflow_id),"WORKFLOW_EXECUTION_ID":str(execution["id"]) }),encoding="utf-8")
    print(f"Real API context prepared: {username}")
    return 0
if __name__=="__main__": sys.exit(main())
