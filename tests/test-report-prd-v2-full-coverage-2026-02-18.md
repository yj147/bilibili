# PRD v2 Full Coverage Report

Generated: 2026-02-18 19:11:44

| Metric | Value |
|---|---|
| Total Cases | 69 |
| Passed | 69 |
| Failed | 0 |

## Case Results

| Case | Result | Mode | Detail |
|---|---|---|---|
| TC-F-001 | PASS | live | status=200 |
| TC-F-002 | PASS | live | status=200 |
| TC-F-003 | PASS | live | status=200 |
| TC-F-004 | PASS | live | status=200 |
| TC-F-005 | PASS | live | status=200, body={'created': 2, 'skipped': 0, 'total': 2} |
| TC-F-006 | PASS | live | status=200 |
| TC-F-007 | PASS | live | check-all already live |
| TC-F-008 | PASS | live | status=200 |
| TC-F-009 | PASS | live | status=200 |
| TC-F-010 | PASS | live | status=200 |
| TC-F-011 | PASS | live | status=200, body={'message': 'Created 2 targets', 'count': 2} |
| TC-F-012 | PASS | live | status=200 |
| TC-F-013 | PASS | live | status=200 |
| TC-F-014 | PASS | live | status=200 |
| TC-F-015 | PASS | live | first=202 |
| TC-F-016 | PASS | simulated | batch queue also validated by multi-account simulation |
| TC-F-017 | PASS | live | status=(200,200) |
| TC-F-018 | PASS | simulated | mocked scan success |
| TC-F-019 | PASS | live | status=200 |
| TC-F-020 | PASS | live | status=200 |
| TC-F-021 | PASS | live | status=200 |
| TC-F-022 | PASS | live | status=200 |
| TC-F-023 | PASS | live | status=200 |
| TC-F-024 | PASS | live | status=200 |
| TC-F-025 | PASS | live | status=(200,200) |
| TC-F-026 | PASS | live | status=200 |
| TC-F-027 | PASS | live | status=200 |
| TC-F-028 | PASS | live | status=200 |
| TC-F-029 | PASS | live | status=200 |
| TC-F-030 | PASS | live | status=200 |
| TC-F-031 | PASS | live | status=(200,200) |
| TC-F-032 | PASS | live | status=(200,200) |
| TC-F-033 | PASS | live | ws auth connect with token |
| TC-F-034 | PASS | live | msgs=3 |
| TC-F-035 | PASS | live | status=(200,200) |
| TC-E-001 | PASS | live | status=400 |
| TC-E-002 | PASS | live | status=422 |
| TC-E-003 | PASS | live | status=422 |
| TC-E-004 | PASS | live | status=422 |
| TC-E-005 | PASS | live | status=422 |
| TC-E-006 | PASS | live | status=400 |
| TC-E-007 | PASS | live | status=422 |
| TC-E-008 | PASS | live | status=422 |
| TC-E-009 | PASS | live | status=422 |
| TC-E-010 | PASS | live | status=200, body={'message': 'Auto-reply feature is already enabled (standalone mode)'} |
| TC-E-011 | PASS | live | status=400 |
| TC-E-012 | PASS | live | status=400 |
| TC-ERR-001 | PASS | live | status=404 |
| TC-ERR-002 | PASS | live | duplicate claim checked in live |
| TC-ERR-003 | PASS | live | status=400 |
| TC-ERR-004 | PASS | live | status=404 |
| TC-ERR-005 | PASS | live | status=(404,404,404,404) |
| TC-ERR-006 | PASS | live | status=404 |
| TC-ERR-007 | PASS | live | status=401 |
| TC-ERR-008 | PASS | live | invalid ws token rejected |
| TC-ERR-009 | PASS | live | status=404 |
| TC-ERR-010 | PASS | live | second=409, body={'error': True, 'code': 409, 'detail': 'Health check already in progress'} |
| TC-ST-001 | PASS | simulated | status=completed |
| TC-ST-002 | PASS | simulated | status=failed, retry=1 |
| TC-ST-003 | PASS | simulated | claim=(True,False) |
| TC-ST-004 | PASS | live | status=(200,200) |
| TC-ST-005 | PASS | live | toggle-cycle |
| TC-ST-006 | PASS | simulated | before=2.0 after=4.0 |
| TC-ST-007 | PASS | live | msgs=3 |
| TC-ST-008 | PASS | live | check-all accepted after completion |
| TC-RISK-001 | PASS | simulated | waits=[0.9994235729973298] |
| TC-RISK-002 | PASS | simulated | attempts=2, sleeps=[0.9955781259923242, 90.0] |
| TC-RISK-003 | PASS | simulated | reason=4 |
| TC-RISK-004 | PASS | simulated | non-finite rejected |

## Section-6 Multi-Account Evidence (Simulated)

- Scenario 1 (fairness/randomized order): covered in simulated run (shuffle observed).
- Scenario 2 (batch semaphore=5): covered in simulated run (max concurrency asserted <=5).
- Scenario 3 (retry + early success): covered in simulated run (stops after success account).
- Scenario 4 (cookie health on active/expiring accounts): covered in simulated run.
