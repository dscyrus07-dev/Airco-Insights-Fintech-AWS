export type AccountType = 'salaried' | 'business'

export type BankName =
  | 'HDFC Bank'
  | 'ICICI Bank'
  | 'Axis Bank'
  | 'Kotak Bank'
  | 'Canara Bank'
  | 'IDFC First Bank'
  | 'Karnataka Bank'
  | 'Paytm Bank'
  | 'Union Bank of India'
  | 'Bank of Baroda'
  | 'Unknown'
  | 'HSBC Bank'
  | 'SBI'
  | 'Other'

export type ProcessingMode = 'free' | 'hybrid'

export interface UserDetails {
  fullName: string
  accountType: AccountType | ''
  bankName: BankName | ''
  selectedBanks: BankName[]
}

export interface BankStatementFileItem {
  id: string
  bankName: BankName
  file: File
  statementLabel: string
  accountType: AccountType | ''
  pdfPassword?: string
  status?: 'ready' | 'queued' | 'processing' | 'completed' | 'failed'
}

export interface CostEstimate {
  total_transactions: number
  ai_transactions: number
  remaining_as_others: number
  estimated_batches: number
  estimated_claude_calls: number
  estimated_cost_usd: number
  estimated_cost_inr: number
  max_ai_calls: number
  max_ai_transactions: number
  batch_size: number
  rule_engine_classified: number
  rule_engine_unclassified: number
}

export interface ProcessingResult {
  status: 'success' | 'error'
  mode: ProcessingMode
  excel_url: string
  pdf_url: string
  account_summary?: SheetPreview    // Sheet 1 — Summary
  monthly_analysis?: SheetPreview   // Sheet 2 — Monthly Analysis
  weekly_analysis?: SheetPreview    // Sheet 3 — Weekly Analysis
  category_analysis?: SheetPreview  // Sheet 4 — Category Analysis
  bounces_penal?: SheetPreview      // Sheet 5 — Bounces & Penal
  funds_received?: SheetPreview     // Sheet 6 — Funds Received
  funds_remittance?: SheetPreview   // Sheet 7 — Funds Remittance
  raw_transactions?: SheetPreview   // Sheet 8 — Raw Transaction
  source_analysis?: SheetPreview    // Sheet 9 — Source Analysis
  category_outcome?: SheetPreview   // Sheet 10 — Category Outcome
  stats?: {
    total_transactions: number
    rule_engine_classified: number
    ai_classified: number
    others: number
    coverage_percent: number
  }
  ai_usage?: {
    ai_calls: number
    ai_transactions_sent: number
    ai_transactions_classified: number
    estimated_cost_usd: number
    estimated_cost_inr: number
  } | null
}

export interface JobSubmitted {
  job_id: string
  status: string
  message?: string
}

export interface UserUploadHistoryItem {
  job_id: string
  name: string
  display_name?: string
  bank_name?: string
  account_type?: string
  mode?: string
  batch_id?: string | null
  statement_label?: string | null
  status: string
  created_at?: string
  upload_object_key?: string
  total_transactions?: number
  retention_expires_at?: string | null
  retention_days_left?: number | null
  retention_status?: string | null
  deletion_requested_at?: string | null
  deleted_at?: string | null
  deletion_reason?: string | null
  deletion_status?: string | null
  backup_purge_due_at?: string | null
  backup_purge_status?: string | null
}

export interface UserReportHistoryItem {
  job_id: string
  name: string
  display_name?: string
  bank_name?: string
  batch_id?: string | null
  statement_label?: string | null
  created_at?: string
  report_object_key?: string
  retention_expires_at?: string | null
  retention_days_left?: number | null
  retention_status?: string | null
  deletion_requested_at?: string | null
  deleted_at?: string | null
  deletion_reason?: string | null
  deletion_status?: string | null
  backup_purge_due_at?: string | null
  backup_purge_status?: string | null
}

export interface UserBatchBankGroup {
  bank_name: string
  statement_count: number
  processed_count: number
  failed_count: number
  uploads: UserUploadHistoryItem[]
  reports: UserReportHistoryItem[]
}

export interface UserBatchHistoryItem {
  batch_id: string
  created_at?: string | null
  updated_at?: string | null
  display_name?: string | null
  bank_names: string[]
  statement_count: number
  processed_count: number
  failed_count: number
  uploads: UserUploadHistoryItem[]
  reports: UserReportHistoryItem[]
  bank_groups?: UserBatchBankGroup[]
}

export interface ProfileHistoryResponse {
  user: {
    id: string
    email: string
    name: string
    given_name?: string
    family_name?: string
    preferred_username?: string
    roles: string[]
  }
  summary: {
    total_uploads: number
    processed_files: number
    generated_reports: number
    total_batches?: number
    latest_account_type?: string | null
  }
  uploads: UserUploadHistoryItem[]
  reports: UserReportHistoryItem[]
  batches?: UserBatchHistoryItem[]
}

export interface SheetPreview {
  title: string
  headers: string[]
  rows: string[][]
}

export interface SheetData {
  title: string
  headers: string[]
  rows: string[][]
}

export type SelectionRange = {
  start: { row: number; column: number };
  end: { row: number; column: number };
};

export type HistoryEntry = {
  type: 'insert' | 'delete' | 'update';
  data: any;
};

export type SpreadsheetState = {
  sheets: SheetData[];
  activeSheetId: number;
  selection: SelectionRange | null;
  history: HistoryEntry[];
  historyIndex: number; // For undo/redo
  globalDirty: boolean; // For "Save Changes" status
  showFlaggedOnly: boolean;
  filters: Record<number, Record<number, string>>; // sheetId -> columnId -> filter value
  filteredRows: Record<number, number[]>; // sheetId -> array of visible row indices
  editLog: LearningEventRecord[];
};

export interface LearningEventRecord {
  sheet_title?: string
  row_index?: number
  description: string
  category: string
  confidence?: number
  source?: string
  bank_name?: string
  account_type?: string
  recurring_type?: string
  pattern?: string
  metadata?: Record<string, unknown>
}

export type Step = 1 | 2 | 3 | 4 | 5

export interface AppState {
  step: Step
  userDetails: UserDetails
  file: File | null
  mode: ProcessingMode
  apiKey: string
  result: ProcessingResult | null
  error: string | null
}
