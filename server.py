from fastapi import FastAPI, WebSocket, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
import uuid
import asyncio
from datetime import datetime
import uvicorn
import os

app = FastAPI(title="WVCXX mock Lab")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

class MockEndpoint(BaseModel): 
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path: str
    method: str
    response_status: int = 200
    response_body: Any = {'message': 'Mock response'}
    response_headers: Dict [str, str] = {'Content-Type': 'application/json'}
    delay_ms: int = 0
    enabled: bool = True

mock_endpoints: Dict[str, MockEndpoint] = {}
active_websockets = set()

class CreateEndpointRequest(BaseModel):
    path: str
    method: str
    response_status: int = 200
    response_body: Any = {}
    response_headers: Dict [str, str] = {}
    delay_ms: int = 0

@app.get("/api/endpoints")
async def get_endponts():
    return [endpoint.dict() for endpoint in mock_endpoints.values()]

@app.get("/")
async def welcome():
    return {
        "name": "WVCXX MockLab",
        "version": "1.0.0",
        "status": "running",
        "endpoints_count": len(mock_endpoints),
        "message": "Создавай эндпоинты через GUI"
    }

@app.post("/api/endpoints")
async def create_endpoint (request: CreateEndpointRequest):
    endpoint_id = str(uuid.uuid4())
    endpoint = MackEndpoint(
        id = endpoint_id,
        path=request.path,
        method=request.method.upper(),
        response_status = request.response_status,
        response_body = request.response_body,
        response_headers = request.response_headers,
        delay_ms = request.delay_ms
    ) 
    mock_endpoints[endpoint_id] = endpoint

    await broadcast_update()
    return endpoint

@app.put('/api/endpoints/{endpoint_id}')
async def update_endpoint(endpoint_id: str, request: CreateEndpointRequest):
    if endpoint_id not in mock_endpoints:
        raise HTTPException(status_code=404, detail='Endpoint not found')
    
    endpoint = mock_endpoints[endpoint_id]
    endpoint.path = request.path
    endpoint.method = request.method.upper
    endpoint.response_status = request.response_status
    endpoint.response_body = request.response_body
    endpoint.response_headers = request.response_headers
    endpoint.delay_ms = request.delay_ms

    await broadcast_update()
    return {'message': 'Deleted'}

@app.patch('/api/endpoints/{enpoint_id}/toggle')
async def toggle_endpoint(endpoint_id: str):
    if endpoint_id not in mock_endpoints:
        raise HTTPException (status_code=404, detail='Endpoint not found')
    
    mock_endpoints[endpoint_id].enabled = not mock_endpoints[endpoint_id].enabled
    await broadcast_update()

    return{'enabled': mock_endpoints[endpoint_id.enabled]}

@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_websockets.remove(websocket)

async def broadcast_update():
    if active_websockets:
        endpoints_data = [endpoint.dict() for endpoint in mock_endpoints.values()]
        message = json.dumps({'type': 'update', 'data': endpoints_data})
        await asyncio.gather(
            *[ws.send_text(message) for ws in active_websockets]
        )

@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
async def mock_handler(request: Request, path: str):
    method = request.method
    for endpoint in mock_endpoints.values():
        if endpoint.path ==  path and endpoint.method  == method and endpoint.enabled:
            if endpoint.delay_ms > 0:
                await asyncio.sleep(endpoint.delay_ms / 1000)
            
            return JSONResponse(
                status_code = endpoint.response_status,
                content = endpoint.response_body,
                headers = endpoint.response_headers
            )
    return JSONResponse(
        status_code = 404,
        content = {'error': f"No mock endpoint found for {method} {path}"}
    )

from fastapi.responses import HTMLResponse

@app.get("/")
async def root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except:
        return {"message": "WVCXX MockLab API работает", "endpoints": len(mock_endpoints)}
    
if os.path.exists("index.html"):
    app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)