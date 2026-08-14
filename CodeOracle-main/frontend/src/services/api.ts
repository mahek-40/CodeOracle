export interface HealthResponse {
  status: string;
  app: string;
  version?: string;
  environment: string;
  gemini_configured?: boolean;
  timestamp: string;
  phase: number;
}

export interface FileStats {
  path: string;
  language: string;
  extension: string;
  lines: number;
  full_path: string;
}

export interface UploadStats {
  root_dir: string;
  total_files: number;
  total_lines: number;
  languages: string[];
  files: FileStats[];
  dependencies_summary?: Record<string, string[]>;
}

export interface JobResponse {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  stage: string;
  source_type: string;
  source_info: string;
  created_at: string;
  updated_at: string;
  stats: UploadStats | null;
  error: string | null;
  stage_error: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  language: string;
  path: string;
  total_lines: number;
  num_functions: number;
  num_classes: number;
  num_imports: number;
  num_exports: number;
  has_parse_error: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  module: string;
  is_relative: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  dependents_map: Record<string, string[]>;
  dependencies_map: Record<string, string[]>;
}

// ─── Explanation Types ────────────────────────────────────────────────────────

export interface SymbolExplanation {
  name: string;
  symbol_type: 'function' | 'class' | 'method';
  file_path: string;
  start_line: number;
  end_line: number;
  summary: string;
  inputs?: string;
  outputs?: string;
  side_effects?: string;
  edge_cases?: string;
  dependencies: string[];
  uncertainty?: string;
}

export interface FileExplanation {
  path: string;
  language: string;
  total_lines: number;
  summary: string;
  purpose?: string;
  key_exports: string[];
  dependencies: string[];
  symbols: SymbolExplanation[];
  uncertainty?: string;
  error?: string;
}

export interface ProjectExplanation {
  overview: string;
  languages: string[];
  total_files: number;
  total_lines: number;
  architecture_summary?: string;
  entry_points: string[];
  files: FileExplanation[];
  partial: boolean;
  error?: string;
}

// ─── Tests Types (Phase 5) ───────────────────────────────────────────────────

export interface GeneratedTestFile {
  path: string;
  filename: string;
  target_file: string;
  language: string;
  content: string;
  num_tests_estimated: number;
  error?: string;
}

export interface TestGenerationResult {
  job_id: string;
  status: 'completed' | 'partial' | 'failed';
  framework: string;
  total_files: number;
  generated_files: GeneratedTestFile[];
  error?: string;
}

export interface TestCaseResult {
  name: string;
  status: 'passed' | 'failed' | 'skipped' | 'error';
  duration_seconds?: number;
  message?: string;
}

export interface TestExecutionResult {
  job_id: string;
  status: 'passed' | 'failed' | 'error' | 'timeout' | 'docker_unavailable' | 'dependency_install_failed';
  stage?: string;
  framework: string;
  sandboxed: boolean;
  exit_code: number;
  duration_ms: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  skipped_tests: number;
  test_cases: TestCaseResult[];
  stdout: string;
  stderr: string;
  install_logs?: string;
  execution_logs?: string;
  error?: string;
  coverage_report?: CoverageReport | null;
  coverage_placeholder: string;
}

export interface JobTestsData {
  job_id: string;
  generation?: TestGenerationResult | null;
  execution?: TestExecutionResult | null;
}

// ─── Coverage Types (Phase 6) ────────────────────────────────────────────────

export interface FileCoverage {
  path: string;
  language: string;
  total_lines: number;
  covered_lines_count: number;
  uncovered_lines_count: number;
  coverage_percent: number;
  covered_lines: number[];
  uncovered_lines: number[];
  uncovered_functions: string[];
}

export interface CoverageReport {
  job_id: string;
  language: string;
  total_lines: number;
  total_covered_lines: number;
  total_uncovered_lines: number;
  overall_coverage_percent: number;
  target_reached: boolean;
  status?: string;
  stage?: string;
  error?: string;
  install_logs?: string;
  execution_logs?: string;
  files: FileCoverage[];
  timestamp: number;
}

export interface CoverageIteration {
  iteration: number;
  test_count: number;
  coverage_percent: number;
  coverage_gain: number;
  new_tests_generated: number;
  target_uncovered_areas: string[];
  duration_ms: number;
  timestamp: number;
}

export interface CoverageImprovementResult {
  job_id: string;
  initial_coverage: number;
  final_coverage: number;
  coverage_gain: number;
  target_reached: boolean;
  status: 'completed' | 'target_reached' | 'max_retries_reached' | 'failed';
  total_iterations: number;
  iterations: CoverageIteration[];
  latest_report?: CoverageReport | null;
  error?: string;
}

export interface JobCoverageData {
  job_id: string;
  report?: CoverageReport | null;
  improvement?: CoverageImprovementResult | null;
}

// ─── Refactoring Types (Phase 7) ─────────────────────────────────────────────

export interface DiffLine {
  orig_line_num?: number | null;
  refactored_line_num?: number | null;
  type: 'same' | 'add' | 'del' | 'mod';
  content: string;
}

export interface FileDiff {
  path: string;
  additions: number;
  deletions: number;
  modifications: number;
  diff_text: string;
  diff_lines: DiffLine[];
}

export interface ModernizationOpportunity {
  category: 'syntax' | 'types' | 'structure' | 'error_handling' | 'performance' | 'imports';
  title: string;
  description: string;
  before_snippet?: string | null;
  after_snippet?: string | null;
}

export interface BreakingChangeWarning {
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'signature' | 'api' | 'import_export' | 'return_type' | 'renamed_symbol' | 'configuration' | 'behavior';
  file: string;
  symbol: string;
  explanation: string;
  suggested_mitigation: string;
  affected_dependents: string[];
}

export interface RefactoredFile {
  path: string;
  language: string;
  original_content: string;
  refactored_content: string;
  diff: FileDiff;
  opportunities: ModernizationOpportunity[];
  warnings: BreakingChangeWarning[];
  syntax_valid: boolean;
  error?: string | null;
}

export interface RiskSummary {
  overall_risk: 'low' | 'medium' | 'high' | 'critical';
  critical_warnings_count: number;
  high_warnings_count: number;
  medium_warnings_count: number;
  low_warnings_count: number;
  safety_score: number;
  recommendation: string;
}

export interface ValidationComparison {
  status: 'verified' | 'regressions_detected' | 'validation_failed' | 'skipped';
  original_tests_passed: number;
  original_tests_failed: number;
  refactored_tests_passed: number;
  refactored_tests_failed: number;
  regressions: string[];
  original_coverage_percent?: number | null;
  refactored_coverage_percent?: number | null;
  coverage_delta?: number | null;
  stdout: string;
  stderr: string;
  error?: string | null;
}

export interface RefactorResult {
  job_id: string;
  status: 'completed' | 'partial' | 'failed';
  total_files: number;
  files_modified: number;
  total_additions: number;
  total_deletions: number;
  risk_summary: RiskSummary;
  files: RefactoredFile[];
  all_warnings: BreakingChangeWarning[];
  all_opportunities: ModernizationOpportunity[];
  validation?: ValidationComparison | null;
  error?: string | null;
}

// ─── API Client ───────────────────────────────────────────────────────────────

const RAW_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, '');

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    const msg = detail?.detail?.message || detail?.detail || `Request failed: ${response.status}`;
    throw new Error(msg);
  }
  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/api/health');
}

export async function uploadZip(file: File): Promise<JobResponse> {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch(`${API_BASE_URL}/api/projects/upload`, {
    method: 'POST',
    body: form,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: { message: response.statusText } }));
    throw new Error(detail?.detail?.message || detail?.detail || `Upload failed: ${response.status}`);
  }
  return response.json();
}

export async function ingestGitHub(url: string): Promise<JobResponse> {
  const response = await fetch(`${API_BASE_URL}/api/projects/github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: { message: response.statusText } }));
    throw new Error(detail?.detail?.message || detail?.detail || `GitHub ingestion failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchJobGraph(jobId: string): Promise<GraphData> {
  return apiFetch<GraphData>(`/api/jobs/${jobId}/graph`);
}

export async function fetchJobExplanation(jobId: string): Promise<ProjectExplanation> {
  return apiFetch<ProjectExplanation>(`/api/jobs/${jobId}/explain`);
}

export async function generateJobTests(jobId: string): Promise<TestGenerationResult> {
  return apiFetch<TestGenerationResult>(`/api/jobs/${jobId}/tests/generate`, {
    method: 'POST',
  });
}

export async function runJobTests(jobId: string): Promise<TestExecutionResult> {
  return apiFetch<TestExecutionResult>(`/api/jobs/${jobId}/tests/run`, {
    method: 'POST',
  });
}

export async function fetchJobTests(jobId: string): Promise<JobTestsData> {
  return apiFetch<JobTestsData>(`/api/jobs/${jobId}/tests`);
}

export async function runJobCoverage(jobId: string): Promise<CoverageReport> {
  return apiFetch<CoverageReport>(`/api/jobs/${jobId}/coverage/run`, {
    method: 'POST',
  });
}

export async function improveJobCoverage(jobId: string): Promise<CoverageImprovementResult> {
  return apiFetch<CoverageImprovementResult>(`/api/jobs/${jobId}/coverage/improve`, {
    method: 'POST',
  });
}

export async function fetchJobCoverage(jobId: string): Promise<JobCoverageData> {
  return apiFetch<JobCoverageData>(`/api/jobs/${jobId}/coverage`);
}

export async function generateJobRefactor(jobId: string): Promise<RefactorResult> {
  return apiFetch<RefactorResult>(`/api/jobs/${jobId}/refactor/generate`, {
    method: 'POST',
  });
}

export async function fetchJobRefactor(jobId: string): Promise<RefactorResult> {
  return apiFetch<RefactorResult>(`/api/jobs/${jobId}/refactor`);
}

export async function fetchJobRefactorWarnings(jobId: string): Promise<{ job_id: string; warnings: BreakingChangeWarning[] }> {
  return apiFetch<{ job_id: string; warnings: BreakingChangeWarning[] }>(`/api/jobs/${jobId}/refactor/warnings`);
}

export async function fetchJobRefactorDiffs(jobId: string): Promise<{ job_id: string; diffs: FileDiff[] }> {
  return apiFetch<{ job_id: string; diffs: FileDiff[] }>(`/api/jobs/${jobId}/refactor/diffs`);
}

export async function validateJobRefactor(jobId: string): Promise<ValidationComparison> {
  return apiFetch<ValidationComparison>(`/api/jobs/${jobId}/refactor/validate`, {
    method: 'POST',
  });
}

export async function fetchJobRefactorValidation(jobId: string): Promise<{ job_id: string; validation: ValidationComparison | null }> {
  return apiFetch<{ job_id: string; validation: ValidationComparison | null }>(`/api/jobs/${jobId}/refactor/validate`);
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiFetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
}
