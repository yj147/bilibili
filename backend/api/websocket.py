"""
WebSocket API for Real-time Log Streaming
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json

router = APIRouter()

# Connected clients
_clients: List[WebSocket] = []


async def broadcast_log(log_type: str, message: str, data: dict = None):
    """Broadcast a log message to all connected clients."""
    payload = json.dumps({
        "type": log_type,
        "message": message,
        "data": data or {},
        "timestamp": asyncio.get_event_loop().time()
    })
    
    disconnected = []
    for client in _clients:
        try:
            await client.send_text(payload)
        except:
            disconnected.append(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        _clients.remove(client)


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
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
