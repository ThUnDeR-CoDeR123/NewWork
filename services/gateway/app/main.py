from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, Request,Depends
import requests
from fastapi.middleware.cors import CORSMiddleware
import json
from app.config import settings
import time
from urllib.parse import urlencode
from app.routes import router 
from app.routes import get_current_user
from typing import Annotated
from app.schemas import TokenData
# Services
services = {
    "auth": settings.auth,
    "user": settings.user,
    "referral": settings.referral,
    "transaction": settings.transaction  # Add the transaction service here
}


app = FastAPI()
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.include_router(router)


async def forward_request(service_url, method, path, body, headers):
    url = f"{service_url}{path}"
    print(url,method,body)
    try:
        req=requests.request(method, url, json=body, headers=headers,timeout=60)
    except requests.RequestException as e:
        return {"status_code": 501 ,"error": str(e)}
    # print("after request")
    return req



@app.get("/health")
async def root():
    print(services)
    for service in services:
        response = await forward_request(services[service], "GET", "/health", None, {})
       
        if isinstance(response, dict):  # Check if the response is a dict (error case)
            raise HTTPException(status_code=response["status_code"], detail=f"Service {service} is down: {response['error']}")
       
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Service {service} is down, {services[service]}")
        print(service)
        
    return {"status":"ok"}


# Gateway root
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway(service: str, path: str, request: Request, token : Annotated[TokenData,Depends(get_current_user)]):
    """
    Body schema will always be {data,'token_data':TokenData}
    """
    if service not in services:
        raise HTTPException(status_code=404, detail="Service not found")
    service_url = services[service]

    query_params = request.query_params
    query_string = f"?{urlencode(query_params)}" if query_params else ""

    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = None
    
    if token :
        token_data= {'id':token.id, 'username':token.username, 'flag':token.flag, 'is_admin':token.is_admin}
        print("adding token to request")
        if body is not None :
            body ['token_data']=token_data
        else:
            body = token_data
    
    headers = dict(request.headers)

    start = time.time()
    response = await forward_request(service_url, request.method, f"/{path}{query_string}", body, headers)
    print("time taken", time.time() - start)

    if type(response) == dict :
        return response
    
    try:
        if response.status_code != 200 and "message" not in response.json():
            data = response.json()  
            data['message'] = "Something went wrong, please try again!"
            if "detail" in data:
                data["message"] = data["detail"]
            return JSONResponse(status_code=response.status_code, content=data)
        return JSONResponse(status_code=response.status_code, content=response.json())
    except Exception as e:
        return response

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
