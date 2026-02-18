# UI Automation Checklist (2026-02-18, agent-browser full)

Baseline: `tests/prd-test-cases-v2.md`

| ID | Check | Status | Detail |
|---|---|---|---|
| C01 | backend/frontend health | PASS | backend=200,frontend=200 |
| C02 | frontend proxy health | PASS | proxy_status=200 |
| C03 | dashboard page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C04 | dashboard filters/search interaction | PASS | dashboard filters/search interacted |
| C05 | dashboard refresh interaction | PASS | dashboard refresh clicked |
| C06 | accounts page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C07 | accounts manual import | PASS | created_account=ui_full_1771412931_acc |
| C08 | accounts edit account | PASS | edited_account=ui_full_1771412931_acc_edit |
| C09 | accounts single check action | PASS | checked_account_id=1 |
| C10 | accounts check-all action | PASS | check-all submitted |
| C11 | accounts refresh cookie action | PASS | refresh_cookie_account_id=1 |
| C12 | accounts refresh list action | PASS | accounts refresh list clicked |
| C13 | accounts qr modal open/close | PASS | qr modal open/close |
| C14 | accounts delete account action | PASS | deleted_account_id=2 |
| C15 | targets page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C16 | targets add single target | PASS | single_target=BVui_full_1771412931_single |
| C17 | targets batch import mixed delimiters | PASS | batch_ids=BVui_full_1771412931_batch_1,BVui_full_1771412931_batch_2,BVui_full_1771412931_batch_3,BVui_full_1771412931_batch_4,BVui_full_1771412931_batch_5 |
| C18 | targets edit target | PASS | edited_target_id=1 |
| C19 | targets execute single action | PASS | execute_target_id=1 |
| C20 | targets select-all toggle action | PASS | selected_all=6,selected_none=0 |
| C21 | targets execute-all action | PASS | execute-all submitted |
| C22 | targets bulk-delete completed action | PASS | bulk_deleted_completed_target_id=7 |
| C23 | targets bulk-delete failed action | PASS | bulk_deleted_failed_target_id=8 |
| C24 | targets scan-comments submit action | PASS | scan_bvid=BVui_full_1771412931_scan |
| C25 | targets delete target action | PASS | deleted_target_id=9 |
| C26 | autoreply page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C27 | autoreply create rule | PASS | rule_keyword=ui_full_1771412931_kw |
| C28 | autoreply search interaction | PASS | search_visible=ui_full_1771412931_kw |
| C29 | autoreply toggle rule | PASS | rule_id=1,before=True |
| C30 | autoreply edit rule | PASS | rule_id=1,keyword=ui_full_1771412931_kw_edit |
| C31 | autoreply save default reply | PASS | default reply saved |
| C32 | autoreply service toggle and restore | PASS | restored_to=False |
| C33 | autoreply delete rule | PASS | deleted_rule_id=1 |
| C34 | scheduler page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C35 | scheduler create interval task | PASS | task_name=ui_full_1771412931_task |
| C36 | scheduler toggle interval task | PASS | task_id=3,before=True |
| C37 | scheduler edit task name | PASS | task_id=3,name=ui_full_1771412931_task_edit |
| C38 | scheduler edit config_json path | PASS | task_id=3,cron=*/15 * * * * |
| C39 | scheduler create cron task | PASS | cron_task_name=ui_full_1771412931_task_cron |
| C40 | scheduler delete cron task | PASS | deleted_cron_task_id=4 |
| C41 | scheduler delete interval task | PASS | deleted_task_id=3 |
| C42 | config page health | PASS | title=Bili-Sentinel \| B站管理助手,ready=complete,errors=none |
| C43 | config save range/switch/select/number fields | PASS | config batch fields saved |
