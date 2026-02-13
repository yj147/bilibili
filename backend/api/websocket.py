"""
WebSocket API for Real-time Log Streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import hmac
import json
import os
import time

router = APIRouter()

# Connected clients
_clients: List[WebSocket] = []


async def broadcast_log(log_type: str, message: str, data: dict = None, log_id: int = None):
    """Broadcast a log message to all connected clients."""
    payload_dict = {
        "type": log_type,
        "message": message,
        "data": data or {},
        "timestamp": time.time()
    }
    if log_id is not None:
        payload_dict["id"] = log_id
    payload = json.dumps(payload_dict)
    
    disconnected = []
    for client in _clients:
        try:
            await client.send_text(payload)
        except Exception:
            disconnected.append(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        _clients.remove(client)


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    api_key = os.getenv("SENTINEL_API_KEY", "")
    token = None
    subprotocol = None

    if api_key:
        # Extract token from Sec-WebSocket-Protocol header
        for header_name, header_value in websocket.headers.items():
            if header_name.lower() == "sec-websocket-protocol":
                if header_value.startswith("token."):
                    token = header_value[6:]  # Extract after "token."
                    subprotocol = header_value
                break

    await websocket.accept(subprotocol=subprotocol)

    if api_key:
        if not token:
            await websocket.close(code=1008, reason="API key required")
            return

        if not hmac.compare_digest(token, api_key):
            await websocket.close(code=4001, reason="Unauthorized")
            return
    _clients.append(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Bili-Sentinel log stream"
        })
        
        # Keep connection alive and listen for messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Handle ping/pong or filter commands
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _clients:
            _clients.remove(websocket)
