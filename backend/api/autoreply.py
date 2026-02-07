"""
Auto-Reply Configuration API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import List
import asyncio

from backend.models.task import AutoReplyConfig, AutoReplyConfigCreate, AutoReplyConfigUpdate, AutoReplyStatus
from backend.database import execute_query, execute_insert

router = APIRouter()

# Global service state
_autoreply_running = False
_autoreply_task = None


@router.get("/config", response_model=List[AutoReplyConfig])
async def list_autoreply_configs():
    """Get all auto-reply configurations."""
    rows = await execute_query("SELECT * FROM autoreply_config ORDER BY priority DESC, id ASC")
    return rows


@router.post("/config", response_model=AutoReplyConfig)
async def create_autoreply_config(config: AutoReplyConfigCreate):
    """Add a new auto-reply configuration."""
    config_id = await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority) VALUES (?, ?, ?)",
        (config.keyword, config.response, config.priority)
    )
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    return rows[0]


@router.put("/config/{config_id}", response_model=AutoReplyConfig)
async def update_autoreply_config(config_id: int, config: AutoReplyConfigUpdate):
    """Update an auto-reply configuration."""
    updates = []
    params = []
    for field, value in config.model_dump(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(config_id)
    await execute_query(f"UPDATE autoreply_config SET {', '.join(updates)} WHERE id = ?", tuple(params))
    
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Config not found")
    return rows[0]


@router.delete("/config/{config_id}")
async def delete_autoreply_config(config_id: int):
    """Delete an auto-reply configuration."""
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Config not found")
    
    await execute_query("DELETE FROM autoreply_config WHERE id = ?", (config_id,))
    return {"message": "Config deleted", "id": config_id}


@router.get("/status", response_model=AutoReplyStatus)
async def get_autoreply_status():
    """Get the current auto-reply service status."""
    accounts = await execute_query("SELECT COUNT(*) as count FROM accounts WHERE is_active = 1")
    return AutoReplyStatus(
        is_running=_autoreply_running,
        active_accounts=accounts[0]["count"] if accounts else 0
    )


@router.post("/start")
async def start_autoreply_service(interval: int = 30):
    """Start the auto-reply polling service."""
    global _autoreply_running, _autoreply_task
    
    if _autoreply_running:
        return {"message": "Auto-reply service is already running"}
    
    # Start background task
    _autoreply_running = True
    
    async def poll_loop():
        from backend.core.bilibili_client import BilibiliClient
        from backend.core.bilibili_auth import BilibiliAuth
        
        while _autoreply_running:
            try:
                accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1")
                configs = await execute_query("SELECT * FROM autoreply_config WHERE is_active = 1 ORDER BY priority DESC")
                
                default_reply = next((c["response"] for c in configs if c["keyword"] is None), "您好，稍后回复。")
                keyword_map = {c["keyword"]: c["response"] for c in configs if c["keyword"]}
                
                for account in accounts:
                    auth = BilibiliAuth.from_db_account(account)
                    
                    client = BilibiliClient(auth, account_index=0)
                    
                    try:
                        sessions = await client.get_recent_sessions()
                        if sessions.get("code") == 0:
                            for session in sessions.get("data", {}).get("session_list", []) or []:
                                last_msg = session.get("last_msg", {})
                                msg_ts = last_msg.get("timestamp", 0)
                                
                                talker_id = session.get("talker_id")
                                own_uid = account.get("uid", 0)
                                if str(talker_id) == str(own_uid):
                                    continue
                                
                                msg_content = str(last_msg.get("content", ""))
                                reply_text = default_reply
                                for kw, resp in keyword_map.items():
                                    if kw in msg_content:
                                        reply_text = resp
                                        break
                                
                                print(f"[AutoReply][{account['name']}] Replying to {talker_id}: {reply_text}")
                                await client.send_private_message(talker_id, reply_text)
                    except Exception as acc_err:
                        print(f"[AutoReply][{account['name']}] Error: {acc_err}")
                    
            except Exception as e:
                print(f"Auto-reply error: {e}")
            
            await asyncio.sleep(interval)
    
    _autoreply_task = asyncio.create_task(poll_loop())
    return {"message": "Auto-reply service started", "interval": interval}


@router.post("/stop")
async def stop_autoreply_service():
    """Stop the auto-reply polling service."""
    global _autoreply_running, _autoreply_task
    
    if not _autoreply_running:
        return {"message": "Auto-reply service is not running"}
    
    _autoreply_running = False
    if _autoreply_task:
        _autoreply_task.cancel()
        _autoreply_task = None
    
    return {"message": "Auto-reply service stopped"}
