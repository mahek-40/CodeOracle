import React, { useState, useEffect } from 'react';
import {
  generateJobTests,
  runJobTests,
  fetchJobTests,
  runJobCoverage,
  improveJobCoverage,
  fetchJobCoverage,
  TestGenerationResult,
  TestExecutionResult,
  GeneratedTestFile,
  CoverageReport,
  CoverageImprovementResult,
} from '../services/api';
import CoverageDashboard from './CoverageDashboard';
import {
  Play,
  Sparkles,
  Shield,
  CheckCircle2,
  XCircle,
  Clock,
  FileCode,
  Terminal,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  AlertCircle,
  Target,
} from 'lucide-react';

interface GeneratedTestsViewProps {
  jobId: string;
  languages?: string[];
}

export const GeneratedTestsView: React.FC<GeneratedTestsViewProps> = ({
  jobId,
  languages = [],
}) => {
  const [generating, setGenerating] = useState(false);
  const [running, setRunning] = useState(false);
  const [improvingCoverage, setImprovingCoverage] = useState(false);
  const [generation, setGeneration] = useState<TestGenerationResult | null>(null);
  const [execution, setExecution] = useState<TestExecutionResult | null>(null);
  const [coverageReport, setCoverageReport] = useState<CoverageReport | null>(null);
  const [coverageImprovement, setCoverageImprovement] =
    useState<CoverageImprovementResult | null>(null);

  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<
    'coverage' | 'code' | 'stdout' | 'stderr' | 'cases' | 'install_logs'
  >('coverage');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing test & coverage data if available
  useEffect(() => {
    fetchJobTests(jobId)
      .then(data => {
        if (data.generation) setGeneration(data.generation);
        if (data.execution) {
          setExecution(data.execution);
          if (data.execution.coverage_report) {
            setCoverageReport(data.execution.coverage_report);
          }
        }
      })
      .catch(() => null);

    fetchJobCoverage(jobId)
      .then(data => {
        if (data.report) setCoverageReport(data.report);
        if (data.improvement) setCoverageImprovement(data.improvement);
      })
      .catch(() => null);
  }, [jobId]);

  async function handleGenerate() {
    setError(null);
    setGenerating(true);
    try {
      const result = await generateJobTests(jobId);
      setGeneration(result);
      if (result.generated_files.length > 0) {
        setSelectedIndex(0);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate test suite.');
    } finally {
      setGenerating(false);
    }
  }

  async function handleRun() {
    setError(null);
    setRunning(true);
    try {
      const result = await runJobTests(jobId);
      setExecution(result);
      if (result.coverage_report) {
        setCoverageReport(result.coverage_report);
      }
      if (result.stdout || result.test_cases.length > 0) {
        setActiveTab('coverage');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to execute tests in Docker sandbox.');
    } finally {
      setRunning(false);
    }
  }

  async function handleImproveCoverage() {
    setError(null);
    setImprovingCoverage(true);
    try {
      const result = await improveJobCoverage(jobId);
      setCoverageImprovement(result);
      if (result.latest_report) {
        setCoverageReport(result.latest_report);
      }
      // Refresh test files list
      const testsData = await fetchJobTests(jobId);
      if (testsData.generation) setGeneration(testsData.generation);
      setActiveTab('coverage');
    } catch (err: any) {
      setError(err.message || 'Coverage improvement workflow failed.');
    } finally {
      setImprovingCoverage(false);
    }
  }

  async function handleRefreshCoverage() {
    setError(null);
    try {
      const report = await runJobCoverage(jobId);
      setCoverageReport(report);
    } catch (err: any) {
      setError(err.message || 'Failed to re-measure coverage.');
    }
  }

  const files = generation?.generated_files ?? [];
  const activeFile: GeneratedTestFile | undefined = files[selectedIndex];

  function copyCode() {
    if (activeFile?.content) {
      navigator.clipboard.writeText(activeFile.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="h-full flex flex-col bg-[#0B0F19] text-slate-200 overflow-hidden font-sans">
      {/* Action and Control Header */}
      <div className="px-6 py-3 bg-[#151C2C] border-b border-[#1E293B] flex items-center justify-between gap-4 flex-wrap flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating || improvingCoverage}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-md shadow-cyan-500/10 transition-all cursor-pointer"
          >
            {generating ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5 text-cyan-200" />
            )}
            <span>
              {generating
                ? 'Generating Tests…'
                : files.length > 0
                ? 'Regenerate Tests'
                : 'Generate Tests'}
            </span>
          </button>

          <button
            onClick={handleRun}
            disabled={running || improvingCoverage || files.length === 0}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-md shadow-emerald-500/10 transition-all cursor-pointer"
          >
            {running ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 text-emerald-200" />
            )}
            <span>{running ? 'Running in Sandbox…' : 'Run in Sandbox'}</span>
          </button>

          <button
            onClick={handleImproveCoverage}
            disabled={improvingCoverage || running}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-md shadow-indigo-500/10 transition-all cursor-pointer"
          >
            {improvingCoverage ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Target className="h-3.5 w-3.5 text-indigo-200" />
            )}
            <span>
              {improvingCoverage ? 'Improving Coverage…' : 'Target >60% Coverage'}
            </span>
          </button>

          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#0B0F19] border border-[#1E293B] text-cyan-400 uppercase">
            Framework:{' '}
            {generation?.framework ||
              (languages.includes('javascript') ? 'vitest' : 'pytest')}
          </span>
        </div>

        {/* Security & Sandbox Badge */}
        <div className="flex items-center gap-2 bg-[#0B0F19]/80 border border-emerald-900/40 rounded-lg px-3 py-1 text-xs text-emerald-400 font-mono">
          <Shield className="h-3.5 w-3.5 text-emerald-400" />
          <span>Docker Sandbox (network: none · 512MB RAM · 1 CPU)</span>
        </div>
      </div>

      {/* Error & Warning Alert Banner */}
      {error && (
        <div className="px-6 py-2.5 bg-rose-950/40 border-b border-rose-900/60 flex items-center gap-3 text-xs text-rose-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-400" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {execution?.status === 'docker_unavailable' && (
        <div className="px-6 py-2.5 bg-amber-950/40 border-b border-amber-900/60 flex items-center gap-3 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 text-amber-400" />
          <span className="flex-1">
            <strong>Docker Sandbox Unavailable:</strong>{' '}
            {execution.error ||
              'Untrusted code cannot run without Docker isolation.'}
          </span>
        </div>
      )}

      {/* Execution & Coverage Summary Bar */}
      {execution && (
        <div className="px-6 py-2.5 bg-[#101726] border-b border-[#1E293B] flex items-center gap-4 flex-wrap text-xs font-mono flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Tests:</span>
            {execution.status === 'passed' && (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> PASSED
              </span>
            )}
            {execution.status === 'failed' && (
              <span className="text-rose-400 font-semibold flex items-center gap-1">
                <XCircle className="h-3.5 w-3.5" /> FAILED
              </span>
            )}
            {execution.status === 'dependency_install_failed' && (
              <span className="text-rose-400 font-semibold flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5" /> DEPENDENCY INSTALL FAILED
              </span>
            )}
            {execution.status === 'timeout' && (
              <span className="text-amber-400 font-semibold flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" /> TIMEOUT
              </span>
            )}
            {execution.status === 'docker_unavailable' && (
              <span className="text-amber-400 font-semibold">UNAVAILABLE</span>
            )}
          </div>

          <div className="h-3.5 w-[1px] bg-slate-700" />

          <div className="flex items-center gap-3">
            <span className="text-slate-300">
              Total: <strong className="text-white">{execution.total_tests}</strong>
            </span>
            <span className="text-emerald-400">
              Passed: <strong>{execution.passed_tests}</strong>
            </span>
            {execution.failed_tests > 0 && (
              <span className="text-rose-400">
                Failed: <strong>{execution.failed_tests}</strong>
              </span>
            )}
          </div>

          <div className="h-3.5 w-[1px] bg-slate-700" />

          {/* Real Coverage Metric */}
          {coverageReport && (
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Line Coverage:</span>
              <span
                className={`font-bold ${
                  coverageReport.overall_coverage_percent >= 60
                    ? 'text-emerald-400'
                    : 'text-amber-400'
                }`}
              >
                {coverageReport.overall_coverage_percent.toFixed(1)}%
              </span>
              {coverageReport.target_reached && (
                <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.2 rounded font-semibold">
                  TARGET MET
                </span>
              )}
            </div>
          )}

          <div className="ml-auto flex items-center gap-3 text-slate-400">
            <span>
              Duration:{' '}
              <strong className="text-cyan-400">{execution.duration_ms}ms</strong>
            </span>
            <span>
              Exit Code:{' '}
              <strong
                className={
                  execution.exit_code === 0
                    ? 'text-emerald-400'
                    : 'text-rose-400'
                }
              >
                {execution.exit_code}
              </strong>
            </span>
          </div>
        </div>
      )}

      {/* Main Workspace Tabs Header */}
      <div className="px-6 border-b border-[#1E293B] bg-[#151C2C] flex items-center justify-between flex-shrink-0">
        <div className="flex">
          <button
            onClick={() => setActiveTab('coverage')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'coverage'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Target className="h-3.5 w-3.5" />
            <span>Coverage Dashboard</span>
          </button>

          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'code'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="h-3.5 w-3.5" />
            <span>Generated Tests ({files.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('stdout')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'stdout'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>Terminal Logs (stdout)</span>
          </button>

          {execution?.stderr && (
            <button
              onClick={() => setActiveTab('stderr')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                activeTab === 'stderr'
                  ? 'border-rose-400 text-rose-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
              <span>Error Output (stderr)</span>
            </button>
          )}

          {execution?.install_logs && (
            <button
              onClick={() => setActiveTab('install_logs')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                activeTab === 'install_logs'
                  ? 'border-indigo-400 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>Dependency Logs</span>
            </button>
          )}

          {execution?.test_cases && execution.test_cases.length > 0 && (
            <button
              onClick={() => setActiveTab('cases')}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
                activeTab === 'cases'
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Test Cases ({execution.test_cases.length})</span>
            </button>
          )}
        </div>

        {activeTab === 'code' && activeFile && (
          <button
            onClick={copyCode}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-[#0B0F19] border border-[#1E293B] rounded px-2.5 py-1 transition-colors cursor-pointer"
          >
            {copied ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
            <span>{copied ? 'Copied!' : 'Copy Code'}</span>
          </button>
        )}
      </div>

      {/* Main Workspace Split Pane */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'coverage' && (
          <CoverageDashboard
            jobId={jobId}
            report={coverageReport}
            improvement={coverageImprovement}
            improving={improvingCoverage}
            onImproveCoverage={handleImproveCoverage}
            onRefreshCoverage={handleRefreshCoverage}
          />
        )}

        {activeTab === 'code' && (
          <div className="h-full flex overflow-hidden border border-[#1E293B] rounded-xl">
            {/* Left file selector */}
            <div className="w-72 border-r border-[#1E293B] bg-[#101726] flex flex-col flex-shrink-0">
              <div className="px-4 py-2.5 border-b border-[#1E293B] text-xs font-semibold text-slate-400">
                Generated Test Files
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {files.map((f, idx) => (
                  <button
                    key={f.path}
                    onClick={() => setSelectedIndex(idx)}
                    className={`w-full text-left p-2.5 rounded-lg text-xs font-mono transition-all flex flex-col gap-1 border cursor-pointer ${
                      selectedIndex === idx
                        ? 'bg-cyan-950/40 border-cyan-800/60 text-cyan-300'
                        : 'bg-[#151C2C]/50 border-transparent text-slate-300 hover:bg-[#1E293B]/60'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <FileCode className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                      <span className="font-medium truncate">{f.filename}</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pl-5.5">
                      <span>for {f.target_file}</span>
                      {f.num_tests_estimated > 0 && (
                        <span className="text-emerald-400 font-semibold">
                          {f.num_tests_estimated} tests
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Right code content */}
            <div className="flex-1 bg-[#070A12] p-4 overflow-auto font-mono text-xs text-slate-200 leading-relaxed">
              {activeFile ? (
                <pre>{activeFile.content}</pre>
              ) : (
                <div className="text-slate-500 p-4">No test files generated yet.</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'stdout' && (
          <div className="font-mono text-xs text-emerald-300 bg-[#070A12] border border-[#1E293B] rounded-xl p-5 leading-relaxed overflow-auto whitespace-pre-wrap shadow-inner h-full">
            {execution?.stdout ||
              (running
                ? 'Executing tests in Docker sandbox…'
                : 'No execution output yet. Click "Run in Sandbox" above.')}
          </div>
        )}

        {activeTab === 'stderr' && (
          <div className="font-mono text-xs text-rose-300 bg-[#070A12] border border-rose-950/60 rounded-xl p-5 leading-relaxed overflow-auto whitespace-pre-wrap shadow-inner h-full">
            {execution?.stderr || 'No standard error output.'}
          </div>
        )}

        {activeTab === 'install_logs' && (
          <div className="font-mono text-xs text-indigo-300 bg-[#070A12] border border-indigo-950/60 rounded-xl p-5 leading-relaxed overflow-auto whitespace-pre-wrap shadow-inner h-full">
            {execution?.install_logs || 'No dependency installation logs available.'}
          </div>
        )}

        {activeTab === 'cases' && execution && (
          <div className="space-y-2 font-mono text-xs">
            {execution.test_cases.map((tc, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-[#101726] border border-[#1E293B] rounded-lg"
              >
                <div className="flex items-center gap-2.5">
                  {tc.status === 'passed' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                  ) : tc.status === 'failed' ? (
                    <XCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
                  ) : (
                    <Clock className="h-4 w-4 text-amber-400 flex-shrink-0" />
                  )}
                  <span className="text-slate-200 truncate">{tc.name}</span>
                </div>
                <span
                  className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded ${
                    tc.status === 'passed'
                      ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40'
                      : tc.status === 'failed'
                      ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                      : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
                  }`}
                >
                  {tc.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GeneratedTestsView;
