#!/usr/bin/env python3
"""Full frontend browser automation runner with agent-browser.

Scope:
- Validate all core frontend pages.
- Exercise primary user actions on each page.
- Assert key outcomes via frontend proxy API.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib import error as urlerror
from urllib import request as urlrequest


BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:3000"
API_KEY = "test-key-123"
HEADERS = {"Content-Type": "application/json", "X-API-Key": API_KEY}
SESSION = f"ui-full-{int(time.time())}"
PREFIX = f"ui_full_{int(time.time())}"
DB_PATH = Path("data/sentinel.db")
BACKEND_LOG_PATH = Path(".tmp_backend_ui_full.log")


@dataclass
class CheckResult:
    check_id: str
    title: str
    passed: bool
    detail: str


def _run(cmd: list[str], check: bool = True, retries: int = 0) -> str:
    last_msg = ""
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode == 0:
            return out
        msg = out or err or f"exit={proc.returncode}"
        last_msg = msg
        transient = (
            "Resource temporarily unavailable" in msg
            or "ECONNRESET" in msg
            or "Target closed" in msg
            or "socket hang up" in msg
        )
        if transient and attempt < retries:
            time.sleep(0.8)
            continue
        break
    if check:
        raise RuntimeError(f"{' '.join(cmd)} failed: {last_msg}")
    return last_msg


def _ab(args: list[str], check: bool = True) -> str:
    return _run(["agent-browser", "--session", SESSION, *args], check=check, retries=1)


def _json_or_none(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(raw)
    except Exception:
        return None


def _ab_snapshot_refs() -> dict[str, dict[str, Any]]:
    raw = _ab(["snapshot", "-i", "--json"], check=True)
    obj = _json_or_none(raw)
    if not obj or not obj.get("success"):
        raise RuntimeError(f"invalid snapshot json: {raw[:240]}")
    return (obj.get("data") or {}).get("refs") or {}


def _ref_sort_key(ref: str) -> int:
    try:
        return int(ref[1:])
    except Exception:
        return 0


def _find_refs(
    *,
    role: str | None = None,
    name: str | None = None,
    name_contains: str | None = None,
    allow_empty_name: bool = True,
) -> list[str]:
    refs = _ab_snapshot_refs()
    matches: list[str] = []
    for ref, meta in sorted(refs.items(), key=lambda kv: _ref_sort_key(kv[0])):
        r = str(meta.get("role", ""))
        n = str(meta.get("name", ""))
        if role and r != role:
            continue
        if name is not None and n != name:
            continue
        if name_contains is not None and name_contains not in n:
            continue
        if not allow_empty_name and not n:
            continue
        matches.append(ref)
    return matches


def _pick_ref(refs: list[str], nth: int = 0) -> str:
    if not refs:
        raise RuntimeError("no matching ref")
    idx = nth if nth >= 0 else len(refs) + nth
    if idx < 0 or idx >= len(refs):
        raise RuntimeError(f"nth out of range: nth={nth}, size={len(refs)}")
    return refs[idx]


def click_button(name: str, nth: int = 0, contains: bool = False) -> None:
    refs = _find_refs(role="button", name_contains=name if contains else None, name=name if not contains else None)
    ref = _pick_ref(refs, nth=nth)
    _ab(["click", f"@{ref}"])


def fill_textbox(name: str, value: str, nth: int = 0, contains: bool = False) -> None:
    refs = _find_refs(role="textbox", name_contains=name if contains else None, name=name if not contains else None)
    ref = _pick_ref(refs, nth=nth)
    _ab(["fill", f"@{ref}", value])


def fill_nth_textbox(value: str, nth: int = 0) -> None:
    refs = _find_refs(role="textbox")
    ref = _pick_ref(refs, nth=nth)
    _ab(["fill", f"@{ref}", value])


def fill_nth_spinbutton(value: str, nth: int = 0) -> None:
    refs = _find_refs(role="spinbutton")
    ref = _pick_ref(refs, nth=nth)
    _ab(["fill", f"@{ref}", value])


def click_nth_switch(nth: int = 0) -> None:
    refs = _find_refs(role="switch")
    ref = _pick_ref(refs, nth=nth)
    _ab(["click", f"@{ref}"])


def click_nth_unnamed_button(nth: int = 0) -> None:
    refs = []
    all_refs = _ab_snapshot_refs()
    for ref, meta in sorted(all_refs.items(), key=lambda kv: _ref_sort_key(kv[0])):
        if str(meta.get("role", "")) == "button" and not str(meta.get("name", "")):
            refs.append(ref)
    ref = _pick_ref(refs, nth=nth)
    _ab(["click", f"@{ref}"])


def click_nth_checkbox(nth: int = 0) -> None:
    refs = _find_refs(role="checkbox")
    ref = _pick_ref(refs, nth=nth)
    _ab(["click", f"@{ref}"])


def select_option(option_name: str, combobox_nth: int = 0) -> None:
    c_refs = _find_refs(role="combobox")
    c_ref = _pick_ref(c_refs, nth=combobox_nth)
    _ab(["click", f"@{c_ref}"])
    o_refs = _find_refs(role="option", name=option_name)
    o_ref = _pick_ref(o_refs, nth=0)
    _ab(["click", f"@{o_ref}"])


def select_option_contains(option_text: str, combobox_nth: int = 0) -> None:
    c_refs = _find_refs(role="combobox")
    c_ref = _pick_ref(c_refs, nth=combobox_nth)
    _ab(["click", f"@{c_ref}"])
    o_refs = _find_refs(role="option", name_contains=option_text)
    o_ref = _pick_ref(o_refs, nth=0)
    _ab(["click", f"@{o_ref}"])


def open_page(path: str) -> None:
    url = path if path.startswith("http") else f"{FRONTEND}{path}"
    _ab(["open", url])
    _ab(["wait", "--load", "networkidle"], check=False)


def page_health(path: str) -> tuple[bool, str]:
    open_page(path)
    title = _ab(["get", "title"], check=False)
    ready = _ab(["eval", "document.readyState"], check=False).strip().strip('"')
    errors = _ab(["errors"], check=False).strip()
    ok = bool(title) and ready == "complete" and errors == ""
    return ok, f"title={title or '-'},ready={ready},errors={'none' if not errors else errors}"


def _http_json(method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
    url = f"{FRONTEND}/api{path}"
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(url=url, data=data, headers=HEADERS, method=method)
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urlerror.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def _http_status(url: str, headers: dict[str, str] | None = None) -> int:
    req = urlrequest.Request(url=url, headers=headers or {})
    with urlrequest.urlopen(req, timeout=20) as resp:
        return resp.status


def wait_until(fn: Callable[[], bool], timeout_s: float = 40.0, interval_s: float = 0.5) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(interval_s)
    return False


def _wait_ready(url: str, timeout_s: int = 180) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            if _http_status(url) == 200:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


@contextmanager
def _services() -> Any:
    db_backup: Path | None = None
    if DB_PATH.exists():
        db_backup = DB_PATH.with_name(f"{DB_PATH.name}.bak.{int(time.time())}")
        DB_PATH.replace(db_backup)

    backend_log = Path(".tmp_backend_ui_full.log").open("w", encoding="utf-8")
    frontend_log = Path(".tmp_frontend_ui_full.log").open("w", encoding="utf-8")

    backend_env = dict(os.environ)
    backend_env["SENTINEL_API_KEY"] = API_KEY
    frontend_env = dict(os.environ)
    frontend_env["NEXT_PUBLIC_API_KEY"] = API_KEY

    backend = subprocess.Popen(
        ["uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "1"],
        stdout=backend_log,
        stderr=backend_log,
        env=backend_env,
    )
    frontend = subprocess.Popen(
        ["bash", "-lc", "cd frontend && bun run dev -- --hostname 127.0.0.1 --port 3000"],
        stdout=frontend_log,
        stderr=frontend_log,
        env=frontend_env,
    )

    try:
        if not _wait_ready(f"{BACKEND}/health", timeout_s=120):
            raise RuntimeError("backend not ready")
        if not _wait_ready(f"{FRONTEND}/", timeout_s=180):
            raise RuntimeError("frontend not ready")
        yield
    finally:
        for proc in (backend, frontend):
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        backend_log.close()
        frontend_log.close()
        _ab(["close"], check=False)
        if DB_PATH.exists():
            DB_PATH.unlink()
        if db_backup and db_backup.exists():
            db_backup.replace(DB_PATH)


def _db_cleanup_prefix(prefix: str) -> None:
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM report_logs WHERE action LIKE ? OR error_message LIKE ? OR request_data LIKE ?", (f"%{prefix}%", f"%{prefix}%", f"%{prefix}%"))
        cur.execute("DELETE FROM targets WHERE identifier LIKE ? OR display_text LIKE ? OR reason_text LIKE ?", (f"%{prefix}%", f"%{prefix}%", f"%{prefix}%"))
        cur.execute("DELETE FROM scheduled_tasks WHERE name LIKE ?", (f"%{prefix}%",))
        cur.execute("DELETE FROM autoreply_config WHERE keyword LIKE ? OR response LIKE ?", (f"%{prefix}%", f"%{prefix}%"))
        cur.execute("DELETE FROM accounts WHERE name LIKE ?", (f"%{prefix}%",))
        conn.commit()
    finally:
        conn.close()


def _db_mark_account_valid(account_name: str) -> None:
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE accounts SET status='valid', is_active=1, last_check_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE name=?",
            (account_name,),
        )
        conn.commit()
    finally:
        conn.close()


def _get_accounts() -> list[dict[str, Any]]:
    st, obj = _http_json("GET", "/accounts/?page=1&page_size=200")
    if st != 200 or not isinstance(obj, dict):
        return []
    return obj.get("items", []) or []


def _get_targets() -> list[dict[str, Any]]:
    st, obj = _http_json("GET", "/targets/?page=1&page_size=100")
    if st != 200 or not isinstance(obj, dict):
        return []
    return obj.get("items", []) or []


def _get_autoreply_configs() -> list[dict[str, Any]]:
    st, obj = _http_json("GET", "/autoreply/config")
    if st != 200 or not isinstance(obj, list):
        return []
    return obj


def _get_autoreply_status() -> dict[str, Any]:
    st, obj = _http_json("GET", "/autoreply/status")
    if st != 200 or not isinstance(obj, dict):
        return {"is_running": False}
    return obj


def _get_scheduler_tasks() -> list[dict[str, Any]]:
    st, obj = _http_json("GET", "/scheduler/tasks")
    if st != 200 or not isinstance(obj, list):
        return []
    return obj


def _get_configs() -> dict[str, Any]:
    st, obj = _http_json("GET", "/config/")
    if st != 200 or not isinstance(obj, dict):
        return {}
    return obj


def _backend_log_lines() -> list[str]:
    if not BACKEND_LOG_PATH.exists():
        return []
    try:
        return BACKEND_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []


def _backend_log_line_count() -> int:
    return len(_backend_log_lines())


def _wait_backend_log_regex(pattern: str, *, since_line: int, timeout_s: float = 30.0) -> bool:
    compiled = re.compile(pattern)

    def _has_match() -> bool:
        lines = _backend_log_lines()
        if since_line >= len(lines):
            return False
        for line in lines[since_line:]:
            if compiled.search(line):
                return True
        return False

    return wait_until(_has_match, timeout_s=timeout_s, interval_s=0.4)


def _wait_backend_route(method: str, path_pattern: str, *, since_line: int, timeout_s: float = 30.0) -> bool:
    method_upper = re.escape(method.upper())
    return _wait_backend_log_regex(
        rf'"{method_upper} {path_pattern} HTTP/1\.1"',
        since_line=since_line,
        timeout_s=timeout_s,
    )


def _find_account_by_name(name: str) -> dict[str, Any] | None:
    return next((a for a in _get_accounts() if a.get("name") == name), None)


def _find_target_by_identifier(identifier: str) -> dict[str, Any] | None:
    return next((t for t in _get_targets() if t.get("identifier") == identifier), None)


def _find_task_by_name(name: str) -> dict[str, Any] | None:
    return next((t for t in _get_scheduler_tasks() if t.get("name") == name), None)


def _eval_set_first_dialog_input(value: str) -> bool:
    script = (
        "(() => {"
        "const dlg=document.querySelector('[role=\"dialog\"]');"
        "if(!dlg) return 'no-dialog';"
        "const input=dlg.querySelector('input');"
        "if(!input) return 'no-input';"
        "const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')?.set;"
        "if(!setter) return 'no-setter';"
        f"setter.call(input,{json.dumps(value)});"
        "input.dispatchEvent(new Event('input',{bubbles:true}));"
        "input.dispatchEvent(new Event('change',{bubbles:true}));"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_click_account_row_action(account_name: str, action: str) -> bool:
    action_index = {"edit": 0, "check": 1, "refresh": 2, "delete": 3}
    idx = action_index.get(action)
    if idx is None:
        return False

    script = (
        "(() => {"
        "const rows=[...document.querySelectorAll('tbody tr')];"
        "const row=rows.find(r=>{"
        "const n=r.querySelector('span.font-medium');"
        "return n && n.textContent && n.textContent.trim()=="
        + json.dumps(account_name)
        + ";"
        "});"
        "if(!row) return 'no-row';"
        "const btns=row.querySelectorAll('button');"
        "if(!btns || btns.length<4) return 'no-buttons';"
        f"const b=btns[{idx}];"
        "if(!b) return 'no-button';"
        "b.click();"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_click_target_row_action(identifier: str, action: str) -> bool:
    script = (
        "(() => {"
        "const rows=[...document.querySelectorAll('div.divide-y > div')];"
        "const row=rows.find(r=>{"
        "const idEl=r.querySelector('span.font-mono');"
        "return idEl && idEl.textContent && idEl.textContent.trim()=="
        + json.dumps(identifier)
        + ";"
        "});"
        "if(!row) return 'no-row';"
        "if("
        + json.dumps(action)
        + "==='checkbox'){"
        "const cb=row.querySelector('input[type=\"checkbox\"]');"
        "if(!cb) return 'no-checkbox';"
        "cb.click();"
        "return 'ok';"
        "}"
        "const map={edit:0,execute:1,delete:2};"
        "const idx=map["
        + json.dumps(action)
        + "];"
        "if(idx===undefined) return 'bad-action';"
        "const btns=row.querySelectorAll('button');"
        "if(!btns || btns.length<3) return 'no-buttons';"
        "const b=btns[idx];"
        "if(!b) return 'no-button';"
        "b.click();"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_click_targets_select_all() -> bool:
    script = (
        "(() => {"
        "const headers=[...document.querySelectorAll('div.p-6.border-b')];"
        "const header=headers.find(h=>h.textContent && h.textContent.includes('目标列表'));"
        "if(!header) return 'no-header';"
        "const cb=header.querySelector('input[type=\"checkbox\"]');"
        "if(!cb) return 'no-checkbox';"
        "cb.click();"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_target_selected_count() -> int | None:
    script = (
        "(() => {"
        "return document.querySelectorAll('div.divide-y input[type=\"checkbox\"]:checked').length;"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    try:
        return int(out)
    except Exception:
        return None


def _eval_select_scan_account(account_name: str) -> bool:
    script = (
        "(async () => {"
        "const dlg=document.querySelector('[role=\"dialog\"]');"
        "if(!dlg) return 'no-dialog';"
        "const labels=[...dlg.querySelectorAll('label')];"
        "const accountLabel=labels.find(l=>l.textContent && l.textContent.includes('使用账号'));"
        "let trigger=null;"
        "if(accountLabel && accountLabel.parentElement){"
        "trigger=accountLabel.parentElement.querySelector('[role=\"combobox\"]');"
        "}"
        "if(!trigger){"
        "const boxes=[...dlg.querySelectorAll('[role=\"combobox\"]')];"
        "trigger=boxes[0] || null;"
        "}"
        "if(!trigger) return 'no-combobox';"
        "trigger.click();"
        "await new Promise(resolve => setTimeout(resolve, 120));"
        "const opts=[...document.querySelectorAll('[role=\"option\"]')];"
        "if(!opts.length) return 'no-option';"
        "let opt=opts.find(o=>o.textContent && o.textContent.includes("
        + json.dumps(account_name)
        + "));"
        "if(!opt) opt=opts[0];"
        "if(!opt) return 'no-option';"
        "opt.click();"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_set_config_inputs(
    *,
    min_delay: int,
    max_delay: int,
    log_retention_days: int,
    poll_interval: int,
    poll_min_interval: int,
    account_batch: int,
    session_batch: int,
) -> bool:
    script = (
        "(() => {"
        "const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')?.set;"
        "if(!setter) return 'no-setter';"
        "const setVal=(el,val)=>{"
        "setter.call(el,String(val));"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));"
        "};"
        "const ranges=[...document.querySelectorAll('input[type=\"range\"]')];"
        "if(ranges.length<2) return 'no-ranges';"
        f"setVal(ranges[0],{min_delay});"
        f"setVal(ranges[1],{max_delay});"
        "const nums=[...document.querySelectorAll('input[type=\"number\"]')];"
        "if(nums.length<5) return 'no-number-inputs';"
        f"setVal(nums[0],{log_retention_days});"
        f"setVal(nums[1],{poll_interval});"
        f"setVal(nums[2],{poll_min_interval});"
        f"setVal(nums[3],{account_batch});"
        f"setVal(nums[4],{session_batch});"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_set_default_reply_textarea(value: str) -> bool:
    script = (
        "(() => {"
        "const cards=[...document.querySelectorAll('div')];"
        "const host=cards.find(el=>el.textContent && el.textContent.includes('默认回复') && el.querySelector('textarea'));"
        "if(!host) return 'no-host';"
        "const ta=host.querySelector('textarea');"
        "if(!ta) return 'no-textarea';"
        "const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')?.set;"
        "if(!setter) return 'no-setter';"
        f"setter.call(ta,{json.dumps(value)});"
        "ta.dispatchEvent(new Event('input',{bubbles:true}));"
        "ta.dispatchEvent(new Event('change',{bubbles:true}));"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_click_scheduler_row_action(task_name: str, action: str) -> bool:
    # action: "edit" | "delete"
    which = "0" if action == "edit" else "-1"
    script = (
        "(() => {"
        "const title=[...document.querySelectorAll('h4')].find(el=>el.textContent && el.textContent.trim()=="
        + json.dumps(task_name)
        + ");"
        "if(!title) return 'no-title';"
        "const row=title.closest('div.p-6') || title.closest('div');"
        "if(!row) return 'no-row';"
        "const btns=row.querySelectorAll('button');"
        "if(!btns || btns.length===0) return 'no-buttons';"
        f"const idx=({which});"
        "const b=idx>=0 ? btns[idx] : btns[btns.length+idx];"
        "if(!b) return 'no-target-button';"
        "b.click();"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def _eval_set_scheduler_edit_fields(*, name: str, cron: str, config_json: str) -> bool:
    script = (
        "(() => {"
        "const dlg=document.querySelector('[role=\"dialog\"]');"
        "if(!dlg) return 'no-dialog';"
        "const inputs=dlg.querySelectorAll('input');"
        "if(!inputs || inputs.length<2) return 'no-inputs';"
        "const textareas=dlg.querySelectorAll('textarea');"
        "if(!textareas || textareas.length<1) return 'no-textarea';"
        "const setInput=(el,val)=>{"
        "const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')?.set;"
        "if(!s) return false;"
        "s.call(el,val);"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));"
        "return true;"
        "};"
        "const setTa=(el,val)=>{"
        "const s=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')?.set;"
        "if(!s) return false;"
        "s.call(el,val);"
        "el.dispatchEvent(new Event('input',{bubbles:true}));"
        "el.dispatchEvent(new Event('change',{bubbles:true}));"
        "return true;"
        "};"
        f"if(!setInput(inputs[0],{json.dumps(name)})) return 'set-name-failed';"
        f"if(!setInput(inputs[1],{json.dumps(cron)})) return 'set-cron-failed';"
        f"if(!setTa(textareas[0],{json.dumps(config_json)})) return 'set-json-failed';"
        "return 'ok';"
        "})()"
    )
    out = _ab(["eval", script], check=False).strip().strip('"')
    return out == "ok"


def run_checks() -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    state: dict[str, Any] = {
        "account_name": f"{PREFIX}_acc",
        "account_name_edited": f"{PREFIX}_acc_edit",
        "account_delete_name": f"{PREFIX}_acc_delete",
        "target_single": f"BV{PREFIX}_single",
        "target_batch_ids": [f"BV{PREFIX}_batch_{i}" for i in range(1, 6)],
        "target_delete": f"BV{PREFIX}_delete",
        "target_completed": f"BV{PREFIX}_completed",
        "target_failed": f"BV{PREFIX}_failed",
        "rule_keyword": f"{PREFIX}_kw",
        "rule_keyword_edited": f"{PREFIX}_kw_edit",
        "task_name": f"{PREFIX}_task",
        "task_name_edited": f"{PREFIX}_task_edit",
        "task_cron_name": f"{PREFIX}_task_cron",
        "task_cron_expr": "*/20 * * * *",
        "scan_bvid": f"BV{PREFIX}_scan",
        "webhook_url": f"https://example.com/{PREFIX}",
        "default_reply": f"{PREFIX}_default_reply",
        "orig_default_reply": "",
        "orig_autoreply_running": False,
        "orig_configs": {},
        "config_target": {},
        "rule_id": None,
        "task_id": None,
        "task_cron_id": None,
    }

    def record(check_id: str, title: str, fn: Callable[[], tuple[bool, str]]) -> None:
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, f"exception={exc}"
        results.append(CheckResult(check_id, title, ok, detail))

    def _as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    _ab(["close"], check=False)

    def c01() -> tuple[bool, str]:
        b = _http_status(f"{BACKEND}/health")
        f = _http_status(f"{FRONTEND}/")
        return b == 200 and f == 200, f"backend={b},frontend={f}"

    def c02() -> tuple[bool, str]:
        st, _ = _http_json("GET", "/accounts/?page=1&page_size=1")
        return st == 200, f"proxy_status={st}"

    def c03() -> tuple[bool, str]:
        ok, detail = page_health("/")
        return ok, detail

    def c04() -> tuple[bool, str]:
        open_page("/")
        click_button("成功")
        click_button("失败")
        click_button("全部", nth=0)
        click_button("最近7天")
        click_button("今天")
        fill_textbox("搜索账号名称或操作...", state["account_name"])
        fill_textbox("搜索账号名称或操作...", "")
        return True, "dashboard filters/search interacted"

    def c05() -> tuple[bool, str]:
        open_page("/")
        since_line = _backend_log_line_count()
        click_button("刷新")
        ok = _wait_backend_route("GET", r"/api/accounts/", since_line=since_line, timeout_s=25)
        return ok, "dashboard refresh clicked"

    def c06() -> tuple[bool, str]:
        ok, detail = page_health("/accounts")
        return ok, detail

    def c07() -> tuple[bool, str]:
        open_page("/accounts")
        click_button("手动导入")
        fill_textbox("例如：小号-01", state["account_name"])
        fill_textbox("粘贴 Cookie 中的 SESSDATA 值...", f"sess_{PREFIX}")
        fill_textbox("粘贴 bili_jct 值...", f"jct_{PREFIX}")
        fill_textbox("粘贴 buvid3 值...", f"buvid3_{PREFIX}")
        click_button("添加账号")

        ok = wait_until(lambda: any(a.get("name") == state["account_name"] for a in _get_accounts()), timeout_s=40)
        _db_mark_account_valid(state["account_name"])
        return ok, f"created_account={state['account_name']}"

    def c08() -> tuple[bool, str]:
        open_page("/accounts")
        if not _eval_click_account_row_action(state["account_name"], "edit"):
            return False, f"edit action not found for {state['account_name']}"
        fill_nth_textbox(state["account_name_edited"], nth=0)
        click_button("保存更改")
        ok = wait_until(lambda: any(a.get("name") == state["account_name_edited"] for a in _get_accounts()), timeout_s=40)
        if ok:
            state["account_name"] = state["account_name_edited"]
        return ok, f"edited_account={state['account_name_edited']}"

    def c09() -> tuple[bool, str]:
        account = _find_account_by_name(state["account_name"])
        if not account:
            return False, f"account missing: {state['account_name']}"
        open_page("/accounts")
        since_line = _backend_log_line_count()
        if not _eval_click_account_row_action(state["account_name"], "check"):
            return False, "check action click failed"
        ok = _wait_backend_route("POST", rf"/api/accounts/{account['id']}/check", since_line=since_line, timeout_s=35)
        _db_mark_account_valid(state["account_name"])
        return ok, f"checked_account_id={account['id']}"

    def c10() -> tuple[bool, str]:
        open_page("/accounts")
        since_line = _backend_log_line_count()
        click_button("批量检测")
        ok = _wait_backend_route("POST", r"/api/accounts/check-all", since_line=since_line, timeout_s=35)
        _db_mark_account_valid(state["account_name"])
        return ok, "check-all submitted"

    def c11() -> tuple[bool, str]:
        account = _find_account_by_name(state["account_name"])
        if not account:
            return False, f"account missing: {state['account_name']}"
        open_page("/accounts")
        since_line = _backend_log_line_count()
        if not _eval_click_account_row_action(state["account_name"], "refresh"):
            return False, "refresh-cookie action click failed"
        ok = _wait_backend_route("POST", rf"/api/auth/{account['id']}/refresh", since_line=since_line, timeout_s=35)
        _db_mark_account_valid(state["account_name"])
        return ok, f"refresh_cookie_account_id={account['id']}"

    def c12() -> tuple[bool, str]:
        open_page("/accounts")
        since_line = _backend_log_line_count()
        click_button("刷新列表")
        ok = _wait_backend_route("GET", r"/api/accounts/", since_line=since_line, timeout_s=25)
        return ok, "accounts refresh list clicked"

    def c13() -> tuple[bool, str]:
        open_page("/accounts")
        click_button("扫码登录")
        refs = _ab_snapshot_refs()
        has_alias = any((meta.get("role") == "textbox" and "例如：小号-01" in str(meta.get("name", ""))) for meta in refs.values())
        click_button("Close")
        return has_alias, "qr modal open/close"

    def c14() -> tuple[bool, str]:
        st, obj = _http_json(
            "POST",
            "/accounts/",
            {
                "name": state["account_delete_name"],
                "sessdata": f"sess_delete_{PREFIX}",
                "bili_jct": f"jct_delete_{PREFIX}",
            },
        )
        if st != 200 or not isinstance(obj, dict):
            return False, f"create delete-account failed: status={st}"
        delete_id = obj.get("id")
        if not wait_until(lambda: _find_account_by_name(state["account_delete_name"]) is not None, timeout_s=30):
            return False, "delete-account not visible after create"

        open_page("/accounts")
        since_line = _backend_log_line_count()
        if not _eval_click_account_row_action(state["account_delete_name"], "delete"):
            return False, "delete action click failed"
        click_button("移除")
        route_ok = _wait_backend_route("DELETE", rf"/api/accounts/{delete_id}", since_line=since_line, timeout_s=35)
        removed = wait_until(lambda: _find_account_by_name(state["account_delete_name"]) is None, timeout_s=35)
        return route_ok and removed, f"deleted_account_id={delete_id}"

    def c15() -> tuple[bool, str]:
        ok, detail = page_health("/targets")
        return ok, detail

    def c16() -> tuple[bool, str]:
        open_page("/targets")
        click_button("添加目标")
        fill_textbox("输入 BV 号", state["target_single"])
        click_button("确认添加")
        ok = wait_until(lambda: any(t.get("identifier") == state["target_single"] for t in _get_targets()), timeout_s=40)
        return ok, f"single_target={state['target_single']}"

    def c17() -> tuple[bool, str]:
        open_page("/targets")
        click_button("批量导入")
        batch = state["target_batch_ids"]
        payload = f"{batch[0]}, {batch[1]}\n{batch[2]};{batch[3]}\t{batch[4]}"
        fill_textbox("BV1xx411c7xx", payload, contains=True)
        click_button("确认导入")
        ok = wait_until(lambda: all(any(t.get("identifier") == ident for t in _get_targets()) for ident in batch), timeout_s=40)
        return ok, f"batch_ids={','.join(batch)}"

    def c18() -> tuple[bool, str]:
        open_page("/targets")
        if not _eval_click_target_row_action(state["target_single"], "edit"):
            return False, "target edit action click failed"
        reason = f"{PREFIX}_reason"
        fill_nth_textbox(reason, nth=0)
        click_button("保存更改")
        target = _find_target_by_identifier(state["target_single"])
        tid = target.get("id") if isinstance(target, dict) else None
        ok = wait_until(
            lambda: any(t.get("identifier") == state["target_single"] and t.get("reason_text") == reason for t in _get_targets()),
            timeout_s=40,
        )
        return ok, f"edited_target_id={tid}"

    def c19() -> tuple[bool, str]:
        target = _find_target_by_identifier(state["target_single"])
        if not target:
            return False, f"target missing: {state['target_single']}"
        open_page("/targets")
        since_line = _backend_log_line_count()
        if not _eval_click_target_row_action(state["target_single"], "execute"):
            return False, "execute action click failed"
        ok = _wait_backend_route("POST", r"/api/reports/execute", since_line=since_line, timeout_s=35)
        return ok, f"execute_target_id={target['id']}"

    def c20() -> tuple[bool, str]:
        open_page("/targets")
        if not _eval_click_targets_select_all():
            return False, "select-all click failed"
        selected_all = _eval_target_selected_count()
        if not _eval_click_targets_select_all():
            return False, "clear-select click failed"
        selected_none = _eval_target_selected_count()
        ok = (selected_all is not None and selected_all > 0) and selected_none == 0
        return ok, f"selected_all={selected_all},selected_none={selected_none}"

    def c21() -> tuple[bool, str]:
        open_page("/targets")
        for ident in state["target_batch_ids"][:2]:
            if not _eval_click_target_row_action(ident, "checkbox"):
                return False, f"checkbox click failed for {ident}"
        since_line = _backend_log_line_count()
        click_button("批量执行", contains=True)
        ok = _wait_backend_route("POST", r"/api/reports/execute/batch", since_line=since_line, timeout_s=35)
        return ok, "execute-all submitted"

    def c22() -> tuple[bool, str]:
        st, obj = _http_json(
            "POST",
            "/targets/",
            {"type": "video", "identifier": state["target_completed"], "reason_id": 1, "reason_content_id": 1},
        )
        if st != 200 or not isinstance(obj, dict):
            return False, f"create completed-target failed: status={st}"
        tid = obj.get("id")
        _http_json("PUT", f"/targets/{tid}", {"status": "completed"})
        open_page("/targets")
        since_line = _backend_log_line_count()
        click_button("清除已完成")
        click_button("清除")
        route_ok = _wait_backend_route("DELETE", r"/api/targets/by-status/completed", since_line=since_line, timeout_s=35)
        removed = wait_until(lambda: _find_target_by_identifier(state["target_completed"]) is None, timeout_s=35)
        return route_ok and removed, f"bulk_deleted_completed_target_id={tid}"

    def c23() -> tuple[bool, str]:
        st, obj = _http_json(
            "POST",
            "/targets/",
            {"type": "video", "identifier": state["target_failed"], "reason_id": 1, "reason_content_id": 1},
        )
        if st != 200 or not isinstance(obj, dict):
            return False, f"create failed-target failed: status={st}"
        tid = obj.get("id")
        _http_json("PUT", f"/targets/{tid}", {"status": "failed"})
        open_page("/targets")
        since_line = _backend_log_line_count()
        click_button("清除失败")
        click_button("清除")
        route_ok = _wait_backend_route("DELETE", r"/api/targets/by-status/failed", since_line=since_line, timeout_s=35)
        removed = wait_until(lambda: _find_target_by_identifier(state["target_failed"]) is None, timeout_s=35)
        return route_ok and removed, f"bulk_deleted_failed_target_id={tid}"

    def c24() -> tuple[bool, str]:
        _db_mark_account_valid(state["account_name"])
        wait_until(
            lambda: any(
                a.get("name") == state["account_name"] and a.get("status") == "valid"
                for a in _get_accounts()
            ),
            timeout_s=8,
            interval_s=0.4,
        )
        open_page("/targets")
        click_button("评论扫描")
        fill_textbox("BV1xxxxxxxxxx", state["scan_bvid"], contains=True)
        selected = _eval_select_scan_account(state["account_name"])
        if not selected:
            for idx in (3, 4, 2, 1, 0):
                try:
                    select_option_contains(state["account_name"], combobox_nth=idx)
                    selected = True
                    break
                except Exception:
                    continue
        if not selected:
            accounts_debug = [
                (a.get("id"), a.get("name"), a.get("status"), a.get("uid"))
                for a in _get_accounts()
            ]
            return False, f"scan account selection failed accounts={accounts_debug}"
        fill_nth_spinbutton("1", nth=0)
        since_line = _backend_log_line_count()
        click_button("开始扫描", contains=True)
        ok = _wait_backend_route("POST", r"/api/reports/scan-comments", since_line=since_line, timeout_s=50)
        try:
            click_button("Close", nth=0, contains=True)
        except Exception:
            pass
        return ok, f"scan_bvid={state['scan_bvid']}"

    def c25() -> tuple[bool, str]:
        st, obj = _http_json(
            "POST",
            "/targets/",
            {"type": "video", "identifier": state["target_delete"], "reason_id": 1, "reason_content_id": 1},
        )
        if st != 200 or not isinstance(obj, dict):
            return False, f"create delete-target failed: status={st}"
        tid = obj.get("id")
        open_page("/targets")
        since_line = _backend_log_line_count()
        if not _eval_click_target_row_action(state["target_delete"], "delete"):
            return False, "target delete action click failed"
        click_button("删除")
        route_ok = _wait_backend_route("DELETE", rf"/api/targets/{tid}", since_line=since_line, timeout_s=35)
        removed = wait_until(lambda: _find_target_by_identifier(state["target_delete"]) is None, timeout_s=35)
        return route_ok and removed, f"deleted_target_id={tid}"

    def c26() -> tuple[bool, str]:
        ok, detail = page_health("/autoreply")
        return ok, detail

    def c27() -> tuple[bool, str]:
        configs = _get_autoreply_configs()
        default_cfg = next((c for c in configs if c.get("keyword") is None), None)
        state["orig_default_reply"] = str(default_cfg.get("response", "")) if default_cfg else ""
        state["orig_autoreply_running"] = bool(_get_autoreply_status().get("is_running", False))

        open_page("/autoreply")
        click_button("新增规则")
        fill_textbox("例如：你好", state["rule_keyword"])
        fill_textbox("自动回复内容...", f"{PREFIX}_rule_resp", contains=True)
        fill_nth_spinbutton("99", nth=0)
        click_button("确认添加")
        ok = wait_until(lambda: any(c.get("keyword") == state["rule_keyword"] for c in _get_autoreply_configs()), timeout_s=40)
        cfg = next((c for c in _get_autoreply_configs() if c.get("keyword") == state["rule_keyword"]), None)
        state["rule_id"] = cfg.get("id") if isinstance(cfg, dict) else None
        return ok, f"rule_keyword={state['rule_keyword']}"

    def c28() -> tuple[bool, str]:
        open_page("/autoreply")
        fill_textbox("搜索关键词或回复内容...", state["rule_keyword"])
        visible = _ab(
            [
                "eval",
                "(() => [...document.querySelectorAll('h3.font-semibold')].map(el => (el.textContent || '').trim()).join('|'))()",
            ],
            check=False,
        ).strip().strip('"')
        fill_textbox("搜索关键词或回复内容...", "")
        ok = state["rule_keyword"] in visible
        return ok, f"search_visible={visible}"

    def c29() -> tuple[bool, str]:
        rid = state.get("rule_id")
        if not rid:
            return False, "rule_id missing"
        before_cfg = next((c for c in _get_autoreply_configs() if c.get("id") == rid), None)
        before = bool(before_cfg.get("is_active")) if isinstance(before_cfg, dict) else None
        if before is None:
            return False, "rule not found before toggle"
        open_page("/autoreply")
        click_nth_switch(0)
        ok = wait_until(
            lambda: any(c.get("id") == rid and bool(c.get("is_active")) != before for c in _get_autoreply_configs()),
            timeout_s=40,
        )
        return ok, f"rule_id={rid},before={before}"

    def c30() -> tuple[bool, str]:
        rid = state.get("rule_id")
        if not rid:
            return False, "rule_id missing"
        open_page("/autoreply")
        click_button("编辑", nth=0)
        fill_nth_textbox(state["rule_keyword_edited"], nth=0)
        click_button("保存更改")
        ok = wait_until(lambda: any(c.get("id") == rid and c.get("keyword") == state["rule_keyword_edited"] for c in _get_autoreply_configs()), timeout_s=40)
        if ok:
            state["rule_keyword"] = state["rule_keyword_edited"]
        return ok, f"rule_id={rid},keyword={state['rule_keyword_edited']}"

    def c31() -> tuple[bool, str]:
        open_page("/autoreply")
        if not _eval_set_default_reply_textarea(state["default_reply"]):
            return False, "failed to set default reply textarea by eval"
        click_button("保存默认回复")
        ok = wait_until(
            lambda: any(c.get("keyword") is None and c.get("response") == state["default_reply"] for c in _get_autoreply_configs()),
            timeout_s=40,
        )
        return ok, "default reply saved"

    def c32() -> tuple[bool, str]:
        before = bool(_get_autoreply_status().get("is_running", False))
        open_page("/autoreply")
        click_button("停用自动回复" if before else "启用自动回复")
        toggled = wait_until(lambda: bool(_get_autoreply_status().get("is_running", False)) != before, timeout_s=30)
        if not toggled:
            return False, f"status did not toggle from {before}"
        open_page("/autoreply")
        click_button("停用自动回复" if not before else "启用自动回复")
        restored = wait_until(lambda: bool(_get_autoreply_status().get("is_running", False)) == before, timeout_s=30)
        return restored, f"restored_to={before}"

    def c33() -> tuple[bool, str]:
        rid = state.get("rule_id")
        if not rid:
            return False, "rule_id missing"
        open_page("/autoreply")
        click_button("删除", nth=0)
        click_button("删除")
        ok = wait_until(lambda: all(c.get("id") != rid for c in _get_autoreply_configs()), timeout_s=40)
        return ok, f"deleted_rule_id={rid}"

    def c34() -> tuple[bool, str]:
        ok, detail = page_health("/scheduler")
        return ok, detail

    def c35() -> tuple[bool, str]:
        open_page("/scheduler")
        click_button("新建任务")
        fill_textbox("例如：每日清理", state["task_name"])
        fill_nth_spinbutton("45", nth=0)
        click_button("确认创建")
        ok = wait_until(lambda: _find_task_by_name(state["task_name"]) is not None, timeout_s=40)
        task = _find_task_by_name(state["task_name"])
        state["task_id"] = task.get("id") if isinstance(task, dict) else None
        return ok, f"task_name={state['task_name']}"

    def c36() -> tuple[bool, str]:
        tid = state.get("task_id")
        if not tid:
            return False, "task_id missing"
        before_task = next((t for t in _get_scheduler_tasks() if t.get("id") == tid), None)
        before = bool(before_task.get("is_active")) if isinstance(before_task, dict) else None
        if before is None:
            return False, "task not found before toggle"
        open_page("/scheduler")
        click_nth_switch(-1)
        ok = wait_until(
            lambda: any(t.get("id") == tid and bool(t.get("is_active")) != before for t in _get_scheduler_tasks()),
            timeout_s=40,
        )
        return ok, f"task_id={tid},before={before}"

    def c37() -> tuple[bool, str]:
        tid = state.get("task_id")
        if not tid:
            return False, "task_id missing"
        open_page("/scheduler")
        if not _eval_click_scheduler_row_action(state["task_name"], "edit"):
            return False, "failed to open edit modal for scheduler row"
        if not _eval_set_first_dialog_input(state["task_name_edited"]):
            return False, "failed to set scheduler edit name"
        click_button("保存更改")
        ok = wait_until(lambda: any(t.get("id") == tid and t.get("name") == state["task_name_edited"] for t in _get_scheduler_tasks()), timeout_s=40)
        if ok:
            state["task_name"] = state["task_name_edited"]
        return ok, f"task_id={tid},name={state['task_name_edited']}"

    def c38() -> tuple[bool, str]:
        tid = state.get("task_id")
        if not tid:
            return False, "task_id missing"
        open_page("/scheduler")
        if not _eval_click_scheduler_row_action(state["task_name"], "edit"):
            return False, "failed to open edit modal for config_json check"
        config_json = json.dumps({"dry_run": True, "tag": PREFIX})
        cron = "*/15 * * * *"
        if not _eval_set_scheduler_edit_fields(name=state["task_name"], cron=cron, config_json=config_json):
            return False, "failed to set scheduler edit fields"
        since_line = _backend_log_line_count()
        click_button("保存更改")
        route_ok = _wait_backend_route("PUT", rf"/api/scheduler/tasks/{tid}", since_line=since_line, timeout_s=35)

        def _updated() -> bool:
            task = next((t for t in _get_scheduler_tasks() if t.get("id") == tid), None)
            if not isinstance(task, dict):
                return False
            cfg = task.get("config_json") or {}
            return task.get("cron_expression") == cron and isinstance(cfg, dict) and cfg.get("tag") == PREFIX

        ok = wait_until(_updated, timeout_s=40)
        return ok and route_ok, f"task_id={tid},cron={cron}"

    def c39() -> tuple[bool, str]:
        open_page("/scheduler")
        click_button("新建任务")
        fill_textbox("例如：每日清理", state["task_cron_name"])
        fill_textbox("例如：0 2 * * *", state["task_cron_expr"], contains=True)
        click_button("确认创建")
        ok = wait_until(
            lambda: any(
                t.get("name") == state["task_cron_name"] and t.get("cron_expression") == state["task_cron_expr"]
                for t in _get_scheduler_tasks()
            ),
            timeout_s=40,
        )
        task = _find_task_by_name(state["task_cron_name"])
        state["task_cron_id"] = task.get("id") if isinstance(task, dict) else None
        return ok, f"cron_task_name={state['task_cron_name']}"

    def c40() -> tuple[bool, str]:
        tid = state.get("task_cron_id")
        if not tid:
            return False, "task_cron_id missing"
        open_page("/scheduler")
        if not _eval_click_scheduler_row_action(state["task_cron_name"], "delete"):
            return False, "failed to click cron task delete action"
        click_button("删除")
        ok = wait_until(lambda: all(t.get("id") != tid for t in _get_scheduler_tasks()), timeout_s=40)
        return ok, f"deleted_cron_task_id={tid}"

    def c41() -> tuple[bool, str]:
        tid = state.get("task_id")
        if not tid:
            return False, "task_id missing"
        open_page("/scheduler")
        if not _eval_click_scheduler_row_action(state["task_name"], "delete"):
            return False, "failed to click scheduler delete action"
        click_button("删除")
        ok = wait_until(lambda: all(t.get("id") != tid for t in _get_scheduler_tasks()), timeout_s=40)
        return ok, f"deleted_task_id={tid}"

    def c42() -> tuple[bool, str]:
        ok, detail = page_health("/config")
        return ok, detail

    def c43() -> tuple[bool, str]:
        cfg = _get_configs()
        keys = [
            "min_delay",
            "max_delay",
            "ua_rotation",
            "webhook_url",
            "notify_level",
            "auto_clean_logs",
            "log_retention_days",
            "autoreply_poll_interval_seconds",
            "autoreply_poll_min_interval_seconds",
            "autoreply_account_batch_size",
            "autoreply_session_batch_size",
        ]
        state["orig_configs"] = {k: cfg.get(k) for k in keys if k in cfg}
        target = {
            "min_delay": 4 if _as_int(cfg.get("min_delay"), 3) != 4 else 5,
            "max_delay": 20 if _as_int(cfg.get("max_delay"), 12) != 20 else 25,
            "ua_rotation": not _as_bool(cfg.get("ua_rotation")),
            "webhook_url": state["webhook_url"],
            "notify_level": "warn" if str(cfg.get("notify_level", "error")) != "warn" else "info",
            "auto_clean_logs": not _as_bool(cfg.get("auto_clean_logs")),
            "log_retention_days": 35 if _as_int(cfg.get("log_retention_days"), 30) != 35 else 40,
            "autoreply_poll_interval_seconds": 31 if _as_int(cfg.get("autoreply_poll_interval_seconds"), 30) != 31 else 32,
            "autoreply_poll_min_interval_seconds": 11 if _as_int(cfg.get("autoreply_poll_min_interval_seconds"), 10) != 11 else 12,
            "autoreply_account_batch_size": 2 if _as_int(cfg.get("autoreply_account_batch_size"), 0) != 2 else 3,
            "autoreply_session_batch_size": 6 if _as_int(cfg.get("autoreply_session_batch_size"), 5) != 6 else 7,
        }
        state["config_target"] = target

        open_page("/config")
        if not _eval_set_config_inputs(
            min_delay=target["min_delay"],
            max_delay=target["max_delay"],
            log_retention_days=target["log_retention_days"],
            poll_interval=target["autoreply_poll_interval_seconds"],
            poll_min_interval=target["autoreply_poll_min_interval_seconds"],
            account_batch=target["autoreply_account_batch_size"],
            session_batch=target["autoreply_session_batch_size"],
        ):
            return False, "failed to set config range/number inputs"

        if target["ua_rotation"] != _as_bool(cfg.get("ua_rotation")):
            click_nth_switch(0)
        if target["auto_clean_logs"] != _as_bool(cfg.get("auto_clean_logs")):
            click_nth_switch(1)

        notify_label = {
            "error": "仅失败时",
            "warn": "失败和异常时",
            "info": "所有情况",
        }[target["notify_level"]]
        select_option(notify_label, combobox_nth=0)

        fill_textbox("https://...", target["webhook_url"])
        click_button("保存所有更改")

        def _config_matches() -> bool:
            latest = _get_configs()
            return (
                _as_int(latest.get("min_delay")) == target["min_delay"]
                and _as_int(latest.get("max_delay")) == target["max_delay"]
                and _as_bool(latest.get("ua_rotation")) == target["ua_rotation"]
                and str(latest.get("webhook_url", "")) == target["webhook_url"]
                and str(latest.get("notify_level", "")) == target["notify_level"]
                and _as_bool(latest.get("auto_clean_logs")) == target["auto_clean_logs"]
                and _as_int(latest.get("log_retention_days")) == target["log_retention_days"]
                and _as_int(latest.get("autoreply_poll_interval_seconds")) == target["autoreply_poll_interval_seconds"]
                and _as_int(latest.get("autoreply_poll_min_interval_seconds")) == target["autoreply_poll_min_interval_seconds"]
                and _as_int(latest.get("autoreply_account_batch_size")) == target["autoreply_account_batch_size"]
                and _as_int(latest.get("autoreply_session_batch_size")) == target["autoreply_session_batch_size"]
            )

        ok = wait_until(_config_matches, timeout_s=40)
        return ok, "config batch fields saved"

    records: list[tuple[str, str, Callable[[], tuple[bool, str]]]] = [
        ("C01", "backend/frontend health", c01),
        ("C02", "frontend proxy health", c02),
        ("C03", "dashboard page health", c03),
        ("C04", "dashboard filters/search interaction", c04),
        ("C05", "dashboard refresh interaction", c05),
        ("C06", "accounts page health", c06),
        ("C07", "accounts manual import", c07),
        ("C08", "accounts edit account", c08),
        ("C09", "accounts single check action", c09),
        ("C10", "accounts check-all action", c10),
        ("C11", "accounts refresh cookie action", c11),
        ("C12", "accounts refresh list action", c12),
        ("C13", "accounts qr modal open/close", c13),
        ("C14", "accounts delete account action", c14),
        ("C15", "targets page health", c15),
        ("C16", "targets add single target", c16),
        ("C17", "targets batch import mixed delimiters", c17),
        ("C18", "targets edit target", c18),
        ("C19", "targets execute single action", c19),
        ("C20", "targets select-all toggle action", c20),
        ("C21", "targets execute-all action", c21),
        ("C22", "targets bulk-delete completed action", c22),
        ("C23", "targets bulk-delete failed action", c23),
        ("C24", "targets scan-comments submit action", c24),
        ("C25", "targets delete target action", c25),
        ("C26", "autoreply page health", c26),
        ("C27", "autoreply create rule", c27),
        ("C28", "autoreply search interaction", c28),
        ("C29", "autoreply toggle rule", c29),
        ("C30", "autoreply edit rule", c30),
        ("C31", "autoreply save default reply", c31),
        ("C32", "autoreply service toggle and restore", c32),
        ("C33", "autoreply delete rule", c33),
        ("C34", "scheduler page health", c34),
        ("C35", "scheduler create interval task", c35),
        ("C36", "scheduler toggle interval task", c36),
        ("C37", "scheduler edit task name", c37),
        ("C38", "scheduler edit config_json path", c38),
        ("C39", "scheduler create cron task", c39),
        ("C40", "scheduler delete cron task", c40),
        ("C41", "scheduler delete interval task", c41),
        ("C42", "config page health", c42),
        ("C43", "config save range/switch/select/number fields", c43),
    ]

    for cid, title, fn in records:
        record(cid, title, fn)

    # Restore mutable global settings.
    if state["orig_configs"]:
        _http_json("POST", "/config/batch", {"configs": state["orig_configs"]})
    if state["orig_default_reply"] != "":
        _http_json("PUT", "/autoreply/config/default", {"response": state["orig_default_reply"]})
    now_running = bool(_get_autoreply_status().get("is_running", False))
    if now_running != bool(state["orig_autoreply_running"]):
        _http_json("POST", "/autoreply/enable" if state["orig_autoreply_running"] else "/autoreply/disable")

    passed = sum(1 for r in results if r.passed)
    return results, passed


def write_reports(results: list[CheckResult], passed: int) -> tuple[Path, Path]:
    total = len(results)
    today = time.strftime("%Y-%m-%d")
    checklist = Path(f"tests/automation-checklist-{today}-agent-browser-full.md")
    report = Path(f"tests/test-report-{today}-agent-browser-full.md")

    lines = [
        f"# UI Automation Checklist ({today}, agent-browser full)",
        "",
        "Baseline: `tests/prd-test-cases-v2.md`",
        "",
        "| ID | Check | Status | Detail |",
        "|---|---|---|---|",
    ]
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        detail = item.detail.replace("|", "\\|")
        lines.append(f"| {item.check_id} | {item.title} | {status} | {detail} |")
    checklist.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary = [
        f"# UI Automation Report ({today}, agent-browser full)",
        "",
        f"Checklist: `{checklist}`",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total checks | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {total - passed} |",
        "",
        "Conclusion: " + ("PASS" if passed == total else "FAIL"),
    ]
    report.write_text("\n".join(summary) + "\n", encoding="utf-8")
    return checklist, report


def main() -> int:
    try:
        _run(["agent-browser", "--help"], check=True)
    except Exception as exc:
        print(f"agent-browser unavailable: {exc}")
        return 2

    results: list[CheckResult] = []
    passed = 0
    try:
        with _services():
            results, passed = run_checks()
    finally:
        _db_cleanup_prefix(PREFIX)

    checklist, report = write_reports(results, passed)
    total = len(results)
    failed = total - passed
    print(
        {
            "total": total,
            "passed": passed,
            "failed": failed,
            "checklist": str(checklist),
            "report": str(report),
            "session": SESSION,
            "prefix": PREFIX,
        }
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
