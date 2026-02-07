// Account types
export interface Account {
  id: number;
  name: string;
  uid: number | null;
  sessdata: string;
  bili_jct: string;
  buvid3: string;
  group_tag: string;
  is_active: boolean;
  last_check_at: string | null;
  status: string;
  created_at: string;
}

export interface AccountCreate {
  name: string;
  sessdata: string;
  bili_jct: string;
  buvid3?: string;
  group_tag?: string;
}

export interface AccountStatus {
  id: number;
  name: string;
  status: string;
  is_valid: boolean;
  uid: number | null;
}

// Target types
export type TargetType = 'video' | 'comment' | 'user';
export type TargetStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Target {
  id: number;
  type: TargetType;
  identifier: string;
  aid: number | null;
  reason_id: number | null;
  reason_text: string | null;
  status: TargetStatus;
  retry_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface TargetListResponse {
  items: Target[];
  total: number;
  page: number;
  page_size: number;
}

// Report types
export interface ReportLog {
  id: number;
  target_id: number;
  account_id: number | null;
  account_name: string | null;
  action: string;
  request_data: Record<string, unknown> | null;
  response_data: Record<string, unknown> | null;
  success: boolean;
  error_message: string | null;
  executed_at: string;
}

// AutoReply types
export interface AutoReplyConfig {
  id: number;
  keyword: string | null;
  response: string;
  priority: number;
  is_active: boolean;
}

export interface AutoReplyStatus {
  is_running: boolean;
  active_accounts: number;
}

// Scheduler types
export interface ScheduledTask {
  id: number;
  name: string;
  task_type: string;
  cron_expression: string | null;
  interval_seconds: number | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  config_json: Record<string, unknown> | null;
}
