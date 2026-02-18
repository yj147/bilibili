# UI Automation Checklist (2026-02-18, agent-browser)

Baseline: `tests/prd-test-cases-v2.md`

| ID | Check | Status | Detail |
|---|---|---|---|
| C01 | backend/frontend health | PASS | backend=200, frontend=200 |
| C02 | frontend proxy /api/accounts/ | PASS | status=200 |
| C03 | dashboard page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C04 | accounts page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C05 | targets page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C06 | autoreply page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C07 | scheduler page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C08 | config page load | PASS | R1:ready=complete,errors=none; R2:ready=complete,errors=none; R3:ready=complete,errors=none |
| C17 | 3-round page巡检 no error | PASS | 3 rounds over 6 pages |
