#!/usr/bin/env python3
"""UI smoke runner with agent-browser for Bili-Sentinel pages.

Checks:
- backend/frontend are reachable
- frontend proxy endpoint is reachable
- 6 core pages load successfully for 3 rounds
- document.readyState is complete and no page errors are reported
"""

from __future__ import annotations

import subprocess
import time
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request as urlrequest


BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:3000"
API_KEY = "test-key-123"
PAGES = [
    ("/", "dashboard"),
    ("/accounts", "accounts"),
    ("/targets", "targets"),
    ("/autoreply", "autoreply"),
    ("/scheduler", "scheduler"),
    ("/config", "config"),
]
AGENT_BROWSER_SESSION = f"ui-smoke-{int(time.time())}"


@dataclass
class CheckResult:
    check_id: str
    title: str
    passed: bool
    detail: str


def _run(cmd: list[str], check: bool = True) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if check and proc.returncode != 0:
        msg = out or err or f"exit={proc.returncode}"
        raise RuntimeError(f"{' '.join(cmd)} failed: {msg}")
    return out


def _ab(args: list[str], check: bool = True) -> str:
    return _run(["agent-browser", "--session", AGENT_BROWSER_SESSION, *args], check=check)


def _http_status(url: str, headers: dict[str, str] | None = None) -> int:
    req = urlrequest.Request(url=url, headers=headers or {})
    with urlrequest.urlopen(req, timeout=20) as resp:
        return resp.status


def _wait_ready(url: str, timeout_s: int = 120) -> bool:
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
    backend_log = Path(".tmp_backend_ui_smoke.log").open("w", encoding="utf-8")
    frontend_log = Path(".tmp_frontend_ui_smoke.log").open("w", encoding="utf-8")

    backend_env = dict(**os.environ)
    backend_env["SENTINEL_API_KEY"] = API_KEY
    frontend_env = dict(**os.environ)
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
        try:
            _ab(["close"], check=False)
        except Exception:
            pass


def run_checks() -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    _ab(["close"], check=False)

    # C01: backend/frontend ready
    st_backend = _http_status(f"{BACKEND}/health")
    st_frontend = _http_status(f"{FRONTEND}/")
    c01_ok = st_backend == 200 and st_frontend == 200
    results.append(CheckResult("C01", "backend/frontend health", c01_ok, f"backend={st_backend}, frontend={st_frontend}"))

    # C02: frontend proxy GET
    st_proxy = _http_status(f"{FRONTEND}/api/accounts/", headers={"X-API-Key": API_KEY})
    c02_ok = st_proxy == 200
    results.append(CheckResult("C02", "frontend proxy /api/accounts/", c02_ok, f"status={st_proxy}"))

    rounds = 3
    page_pass: dict[str, bool] = {route: True for route, _ in PAGES}
    page_details: dict[str, list[str]] = {route: [] for route, _ in PAGES}
    any_error = False

    for round_no in range(1, rounds + 1):
        for route, _ in PAGES:
            url = f"{FRONTEND}{route}"
            try:
                _ab(["open", url])
                _ab(["wait", "--load", "networkidle"], check=False)
                title = _ab(["get", "title"], check=False)
                ready = _ab(["eval", "document.readyState"], check=False).strip().strip('"')
                errors = _ab(["errors"], check=False).strip()
            except RuntimeError:
                page_pass[route] = False
                any_error = True
                page_details[route].append(f"R{round_no}:open_failed")
                continue
            ok = bool(title) and ready == "complete" and errors == ""
            page_pass[route] = page_pass[route] and ok
            if not ok:
                any_error = True
            page_details[route].append(f"R{round_no}:ready={ready},errors={'none' if not errors else errors}")

    page_to_check = {
        "/": ("C03", "dashboard"),
        "/accounts": ("C04", "accounts"),
        "/targets": ("C05", "targets"),
        "/autoreply": ("C06", "autoreply"),
        "/scheduler": ("C07", "scheduler"),
        "/config": ("C08", "config"),
    }
    for route, (cid, name) in page_to_check.items():
        detail = "; ".join(page_details[route])
        results.append(CheckResult(cid, f"{name} page load", page_pass[route], detail))

    results.append(CheckResult("C17", "3-round page巡检 no error", not any_error, "3 rounds over 6 pages"))

    passed = sum(1 for it in results if it.passed)
    return results, passed


def write_reports(results: list[CheckResult], passed: int) -> tuple[Path, Path]:
    total = len(results)
    today = time.strftime("%Y-%m-%d")
    checklist = Path(f"tests/automation-checklist-{today}-agent-browser.md")
    report = Path(f"tests/test-report-{today}-agent-browser.md")

    lines = [
        f"# UI Automation Checklist ({today}, agent-browser)",
        "",
        f"Baseline: `tests/prd-test-cases-v2.md`",
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
        f"# UI Automation Report ({today}, agent-browser)",
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

    with _services():
        results, passed = run_checks()
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
        }
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
