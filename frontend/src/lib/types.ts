export type Role = "admin" | "reviewer" | "operator" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  department: string;
  organization: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  detected_type: string | null;
  type_label: string | null;
  status: string;
  is_sample: boolean;
  is_seeded: boolean;
  created_at: string;
  has_file: boolean;
  latest_workflow: { id: string; status: string; current_stage: string } | null;
  duplicate_upload_of?: string | null;
}

export interface WorkflowSummary {
  id: string;
  document_id: string;
  filename: string | null;
  status: string;
  current_stage: string;
  document_type: string | null;
  type_label: string | null;
  validation_status: string | null;
  requires_approval: boolean;
  approval_reasons: string[];
  priority: string;
  error: string | null;
  is_seeded: boolean;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface Execution {
  id: string;
  agent: string;
  status: string;
  attempt: number;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  explanation: string;
  error: string | null;
  engine: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
}

export interface Field {
  id: string;
  name: string;
  label: string;
  value: string | null;
  confidence: number;
  status: "ok" | "uncertain" | "missing" | "corrected";
  note: string;
}

export interface Validation {
  id: string;
  rule_code: string;
  rule_type: string;
  field: string | null;
  status: "passed" | "warning" | "failed";
  message: string;
  details: Record<string, unknown>;
}

export interface Action {
  id: string;
  step: number;
  action: string;
  title: string;
  department: string;
  priority: string;
  impact: string;
  requires_approval: boolean;
  reasoning: string;
  status: string;
}

export interface Approval {
  id: string;
  workflow_id: string;
  status: string;
  reasons: string[];
  priority: string;
  reviewer_name: string | null;
  comment: string | null;
  corrections: Record<string, string>;
  created_at: string;
  decided_at: string | null;
}

export interface WorkflowDetail extends WorkflowSummary {
  document: DocumentItem;
  executions: Execution[];
  fields: Field[];
  validations: Validation[];
  actions: Action[];
  approvals: Approval[];
  execution_result: { outcome?: string; actions?: { action: string; status: string; result: string }[] };
}

export interface Anchor {
  id: string;
  audit_event_id: string;
  workflow_id: string | null;
  event_hash: string;
  workflow_id_hash: string;
  event_type: string;
  network: string;
  chain_id: number;
  contract_address: string | null;
  status: "queued" | "submitted" | "confirmed" | "failed" | "not_configured";
  submitted_via: string | null;
  submitter_address: string | null;
  tx_hash: string | null;
  tx_explorer_url: string | null;
  block_number: number | null;
  gas_used: number | null;
  attempts: number;
  last_error: string | null;
  onchain_verified_at: string | null;
  created_at: string | null;
  description?: string | null;
}

export interface AuditEvent {
  id: string;
  sequence: number;
  workflow_id: string | null;
  timestamp: string;
  user_id: string | null;
  actor: string;
  agent: string | null;
  event_type: string;
  description: string;
  payload: Record<string, unknown>;
  previous_hash: string;
  hash: string;
  seeded: boolean;
  anchor: Anchor | null;
}

export interface NetworkInfo {
  name: string;
  rpc_url: string;
  chain_id: number;
  symbol: string;
  explorer: string;
  key: string;
}

export interface SystemStatus {
  app: string;
  demo_mode: boolean;
  llm: { provider: string; model: string | null; configured: boolean };
  database: string;
  storage: string;
  execution: string;
  blockchain: { network: string; chain_id: number; contract_address: string | null; relayer_address: string | null };
  low_confidence_threshold: number;
  max_upload_mb: number;
}
