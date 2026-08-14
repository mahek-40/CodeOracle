import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchHealth,
  HealthResponse,
  uploadZip,
  ingestGitHub,
  fetchJobGraph,
  fetchJobExplanation,
  fetchJobTests,
  fetchJobCoverage,
  fetchJobRefactor,
  JobResponse,
  GraphData,
  ProjectExplanation,
  CoverageReport,
  RefactorResult,
  JobTestsData,
} from './services/api';
import {
  exportExplanationMarkdown,
  exportDependencyGraphJson,
  exportCoverageReportJson,
  exportRefactorPatch,
  exportFullProjectReportJson,
} from './utils/export';
import DependencyGraph from './components/DependencyGraph';
import ExplanationView from './components/ExplanationView';
import GeneratedTestsView from './components/GeneratedTestsView';
import RefactoredCodeView from './components/RefactoredCodeView';
import {
  Activity,
  CheckCircle2,
  RefreshCw,
  Cpu,
  GitBranch,
  Upload,
  Link,
  Network,
  X,
  AlertTriangle,
  Sparkles,
  Download,
  Play,
  FileCode,
  ShieldCheck,
  ChevronDown,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────
type AppView = 'landing' | 'processing' | 'results';

// ─── Sub-components ──────────────────────────────────────────────────────────
function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full flex-shrink-0 ${
        ok ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
      }`}
    />
  );
}

function LangBadge({ lang }: { lang: string }) {
  const colors: Record<string, string> = {
    python: 'text-blue-400 bg-blue-950/50 border-blue-800/50',
    javascript: 'text-amber-400 bg-amber-950/50 border-amber-800/50',
  };
  return (
    <span
      className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded-full border ${
        colors[lang] ?? 'text-slate-400 bg-slate-900 border-slate-700'
      } uppercase tracking-wide`}
    >
      {lang}
    </span>
  );
}

// ─── Landing & Ingestion View ────────────────────────────────────────────────
function LandingView({
  health,
  onUpload,
  onGitHub,
  onLoadPreset,
}: {
  health: HealthResponse | null;
  onUpload: (f: File) => void;
  onGitHub: (url: string) => void;
  onLoadPreset: (type: 'python' | 'javascript') => void;
}) {
  const [githubUrl, setGithubUrl] = useState('');
  const [dragging, setDragging] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file?.name.endsWith('.zip')) onUpload(file);
    },
    [onUpload]
  );

  function handleGitHubSubmit() {
    setUrlError(null);
    const trimmed = githubUrl.trim();
    if (!trimmed) return;
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setUrlError('Please enter a valid URL starting with https://github.com/…');
      return;
    }
    onGitHub(trimmed);
  }

  return (
    <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-10 flex flex-col gap-8 overflow-y-auto">
      {/* Hero Section */}
      <div className="text-center space-y-3 pt-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-mono mb-2">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
          <span>AI-Powered Legacy Codebase Intelligence &amp; Modernization</span>
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight leading-tight">
          Analyze, Test, and Modernize Any Legacy Codebase
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-sm leading-relaxed">
          Upload a ZIP archive or public GitHub URL. CodeOracle automatically maps AST dependencies,
          generates hierarchical explanations, writes sandboxed unit tests, measures real line coverage,
          and generates backward-compatible refactoring proposals with breaking-change warnings.
        </p>
      </div>

      {/* Input Cards: Drag & Drop + GitHub */}
      <div className="grid md:grid-cols-2 gap-5">
        {/* ZIP Drop Zone */}
        <div
          onDragOver={e => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-3 p-8 rounded-xl border-2 border-dashed cursor-pointer transition-all ${
            dragging
              ? 'border-cyan-400 bg-cyan-950/20'
              : 'border-[#1E293B] bg-[#151C2C] hover:border-cyan-600 hover:bg-[#1a2235]'
          }`}
        >
          <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/50">
            <Upload className="h-7 w-7 text-cyan-400" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-white">Upload Project ZIP Archive</p>
            <p className="text-xs text-slate-400 mt-1">
              Drag &amp; drop file here or click to browse
            </p>
          </div>
          <div className="flex gap-2 mt-1">
            <LangBadge lang="python" />
            <LangBadge lang="javascript" />
            <span className="text-[10px] font-mono text-slate-500 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full">
              Max 10k lines
            </span>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={e => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
        </div>

        {/* GitHub URL Input */}
        <div className="flex flex-col justify-between p-6 rounded-xl border border-[#1E293B] bg-[#151C2C]">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-slate-200">
              <GitBranch className="h-5 w-5 text-indigo-400" />
              <span className="text-sm font-semibold">Public GitHub Repository</span>
            </div>
            <p className="text-xs text-slate-400">
              Directly clone and ingest public repositories without credentials or OAuth.
            </p>
            <input
              type="url"
              value={githubUrl}
              onChange={e => setGithubUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleGitHubSubmit()}
              placeholder="https://github.com/owner/repository"
              className="w-full bg-[#0B0F19] border border-[#2A364F] rounded-lg px-3 py-2.5 text-xs font-mono text-slate-200 placeholder:text-slate-600 outline-none focus:border-indigo-500 transition-colors"
            />
            {urlError && <p className="text-xs text-rose-400 font-mono">{urlError}</p>}
          </div>

          <button
            onClick={handleGitHubSubmit}
            disabled={!githubUrl.trim()}
            className="flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 disabled:opacity-40 text-white text-xs font-medium py-2.5 rounded-lg transition-all cursor-pointer mt-4"
          >
            <Link className="h-4 w-4" />
            <span>Analyze GitHub Project</span>
          </button>
        </div>
      </div>

      {/* Quick-Start Benchmark Presets (Judge Ready) */}
      <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-white font-mono uppercase tracking-wider">
            <Play className="h-4 w-4 text-cyan-400" />
            <span>Judge Quick Start: Built-In Benchmark Presets</span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            1-Click Multi-Module Test Suites
          </span>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <button
            onClick={() => onLoadPreset('python')}
            className="text-left p-4 rounded-xl bg-[#151C2C] hover:bg-[#1a2337] border border-[#1E293B] hover:border-blue-700/60 transition-all flex flex-col gap-2 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-blue-400" />
                <span className="text-xs font-bold text-white font-mono group-hover:text-blue-300">
                  Python Order Processing Suite
                </span>
              </div>
              <LangBadge lang="python" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Multi-module project (`order_processor.py`, `discount_rules.py`, `tax_calculator.py`).
              Includes discounts, tax rules, and order states.
            </p>
            <span className="text-[11px] text-blue-400 font-mono font-semibold flex items-center gap-1 mt-1">
              Load Preset →
            </span>
          </button>

          <button
            onClick={() => onLoadPreset('javascript')}
            className="text-left p-4 rounded-xl bg-[#151C2C] hover:bg-[#1a2337] border border-[#1E293B] hover:border-amber-700/60 transition-all flex flex-col gap-2 cursor-pointer group"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-amber-400" />
                <span className="text-xs font-bold text-white font-mono group-hover:text-amber-300">
                  JavaScript Cart Manager Suite
                </span>
              </div>
              <LangBadge lang="javascript" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Multi-module project (`cart.js`, `validator.js`, `formatter.js`).
              Includes items, email validation, and currency formatters.
            </p>
            <span className="text-[11px] text-amber-400 font-mono font-semibold flex items-center gap-1 mt-1">
              Load Preset →
            </span>
          </button>
        </div>
      </div>

      {/* Feature Pillars Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
        <div className="p-3.5 bg-[#151C2C] border border-[#1E293B] rounded-lg space-y-1">
          <div className="font-semibold text-cyan-400 flex items-center gap-1.5">
            <Sparkles size={13} />
            <span>1. Explanations</span>
          </div>
          <p className="text-slate-400 text-[11px]">Hierarchical repo, module &amp; AST summaries.</p>
        </div>

        <div className="p-3.5 bg-[#151C2C] border border-[#1E293B] rounded-lg space-y-1">
          <div className="font-semibold text-indigo-400 flex items-center gap-1.5">
            <Network size={13} />
            <span>2. Dependency Graph</span>
          </div>
          <p className="text-slate-400 text-[11px]">Interactive React Flow module caller map.</p>
        </div>

        <div className="p-3.5 bg-[#151C2C] border border-[#1E293B] rounded-lg space-y-1">
          <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
            <ShieldCheck size={13} />
            <span>3. Tests &amp; Coverage</span>
          </div>
          <p className="text-slate-400 text-[11px]">Docker-sandboxed execution &gt;60% target.</p>
        </div>

        <div className="p-3.5 bg-[#151C2C] border border-[#1E293B] rounded-lg space-y-1">
          <div className="font-semibold text-amber-400 flex items-center gap-1.5">
            <Activity size={13} />
            <span>4. Safe Refactoring</span>
          </div>
          <p className="text-slate-400 text-[11px]">Diff view with AST breaking change warnings.</p>
        </div>
      </div>

      {/* Backend Status Footer */}
      <div className="flex items-center justify-center gap-2 text-xs text-slate-500 font-mono pt-2">
        <StatusDot ok={!!health} />
        <span>
          Backend {health ? `connected (v${health.version || '0.1.0'}${health.gemini_configured ? ' · Gemini AI Ready' : ''})` : 'disconnected'} · FastAPI /api/health
        </span>
      </div>
    </main>
  );
}

// ─── Processing View ──────────────────────────────────────────────────────────
function ProcessingView({ source }: { source: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const stages = [
    { name: '1. Ingestion', desc: 'Secure unpacking & Zip Slip validation', done: true },
    { name: '2. AST Analysis', desc: 'Symbol extraction for Python/JS', done: true },
    { name: '3. Dependency Graph', desc: 'Topological module mapping', done: elapsed > 1 },
    { name: '4. Explanation', desc: 'Hierarchical Gemini context synthesis', done: elapsed > 2 },
    { name: '5. Test Generation', desc: 'Sandbox-safe unit test authoring', done: elapsed > 3 },
    { name: '6. Coverage Analysis', desc: 'Docker line coverage measurement', done: elapsed > 4 },
    { name: '7. AI Refactor', desc: 'Modernization & breaking change check', done: elapsed > 5 },
  ];

  return (
    <main className="flex-1 flex flex-col items-center justify-center gap-8 px-6 max-w-xl mx-auto">
      <div className="text-center space-y-2">
        <div className="h-14 w-14 mx-auto rounded-full bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-center shadow-lg shadow-cyan-500/10">
          <RefreshCw className="h-7 w-7 text-cyan-400 animate-spin" />
        </div>
        <h2 className="text-xl font-bold text-white">Analyzing Codebase…</h2>
        <p className="text-xs text-slate-400 font-mono truncate max-w-md bg-[#151C2C] border border-[#1E293B] py-1.5 px-3 rounded-lg">
          {source}
        </p>
        <p className="text-xs text-cyan-400 font-mono">Elapsed: {elapsed}s</p>
      </div>

      {/* Multi-Stage Progress Timeline */}
      <div className="w-full bg-[#151C2C] border border-[#1E293B] rounded-xl p-4 space-y-2.5 font-mono text-xs">
        {stages.map(st => (
          <div key={st.name} className="flex items-center justify-between py-1 border-b border-[#1E293B]/50 last:border-0">
            <div className="flex items-center gap-2">
              {st.done ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <div className="h-4 w-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
              )}
              <span className={st.done ? 'text-white font-medium' : 'text-cyan-300 animate-pulse'}>
                {st.name}
              </span>
            </div>
            <span className="text-[10px] text-slate-500">{st.desc}</span>
          </div>
        ))}
      </div>
    </main>
  );
}

// ─── Results Workspace View ───────────────────────────────────────────────────
function ResultsView({
  job,
  graphData,
  explanation,
  explanationLoading,
  explanationError,
  onLoadExplanation,
  onReset,
}: {
  job: JobResponse;
  graphData: GraphData | null;
  explanation: ProjectExplanation | null;
  explanationLoading: boolean;
  explanationError: string | null;
  onLoadExplanation: () => void;
  onReset: () => void;
}) {
  const stats = job.stats;
  const [activeTab, setActiveTab] = useState<'graph' | 'explanation' | 'tests' | 'refactor'>('graph');
  const [exportOpen, setExportOpen] = useState(false);

  // Cached data for exports
  const [testsData, setTestsData] = useState<JobTestsData | null>(null);
  const [coverageData, setCoverageData] = useState<CoverageReport | null>(null);
  const [refactorData, setRefactorData] = useState<RefactorResult | null>(null);

  useEffect(() => {
    fetchJobTests(job.job_id).then(setTestsData).catch(() => null);
    fetchJobCoverage(job.job_id).then(d => d.report && setCoverageData(d.report)).catch(() => null);
    fetchJobRefactor(job.job_id).then(setRefactorData).catch(() => null);
  }, [job.job_id]);

  useEffect(() => {
    if (activeTab === 'explanation' && !explanation && !explanationLoading && !explanationError) {
      onLoadExplanation();
    }
  }, [activeTab, explanation, explanationLoading, explanationError, onLoadExplanation]);

  const tabs = [
    { id: 'graph', label: 'Dependency Graph', icon: Network },
    { id: 'explanation', label: 'Explanation', icon: Sparkles },
    { id: 'tests', label: 'Generated Tests & Coverage', icon: CheckCircle2 },
    { id: 'refactor', label: 'Refactored Code & Warnings', icon: Activity },
  ] as const;

  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      {/* Project Header Bar */}
      <div className="px-6 py-3 bg-[#151C2C] border-b border-[#1E293B] flex items-center justify-between gap-4 flex-shrink-0 flex-wrap">
        <div className="flex items-center gap-4 min-w-0">
          <span className="text-sm font-bold text-white font-mono truncate max-w-sm">
            {job.source_info}
          </span>
          <div className="flex gap-1.5 flex-shrink-0">
            {stats?.languages.map(l => (
              <LangBadge key={l} lang={l} />
            ))}
          </div>
          {stats && (
            <div className="flex gap-3 text-xs font-mono text-slate-400 flex-shrink-0">
              <span>
                <strong className="text-slate-200">{stats.total_files}</strong> files
              </span>
              <span>
                <strong className="text-slate-200">{stats.total_lines.toLocaleString()}</strong> lines
              </span>
            </div>
          )}
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-2">
          {/* Export Dropdown Menu */}
          <div className="relative">
            <button
              onClick={() => setExportOpen(o => !o)}
              className="flex items-center gap-1.5 text-xs text-cyan-300 bg-cyan-950/60 border border-cyan-800/70 hover:border-cyan-700 rounded-lg px-3 py-1.5 transition-colors cursor-pointer font-mono font-medium shadow-md shadow-cyan-500/10"
            >
              <Download size={13} />
              <span>Export Reports</span>
              <ChevronDown size={12} />
            </button>

            {exportOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-[#151C2C] border border-[#1E293B] rounded-xl shadow-2xl z-50 p-1.5 space-y-1 text-xs font-mono animate-in fade-in zoom-in-95 duration-100">
                <button
                  onClick={() => {
                    exportExplanationMarkdown(job, explanation);
                    setExportOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#1E293B] text-slate-200 transition-colors flex items-center gap-2"
                >
                  <FileCode size={13} className="text-cyan-400" />
                  <span>Explanation Report (.md)</span>
                </button>

                <button
                  onClick={() => {
                    exportDependencyGraphJson(job, graphData);
                    setExportOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#1E293B] text-slate-200 transition-colors flex items-center gap-2"
                >
                  <Network size={13} className="text-indigo-400" />
                  <span>Dependency Graph (.json)</span>
                </button>

                <button
                  onClick={() => {
                    exportCoverageReportJson(job, coverageData);
                    setExportOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#1E293B] text-slate-200 transition-colors flex items-center gap-2"
                >
                  <CheckCircle2 size={13} className="text-emerald-400" />
                  <span>Coverage Report (.json)</span>
                </button>

                <button
                  onClick={() => {
                    exportRefactorPatch(job, refactorData);
                    setExportOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#1E293B] text-slate-200 transition-colors flex items-center gap-2"
                >
                  <Activity size={13} className="text-amber-400" />
                  <span>Refactor Patch (.patch)</span>
                </button>

                <div className="border-t border-[#1E293B] my-1" />

                <button
                  onClick={() => {
                    exportFullProjectReportJson(job, explanation, graphData, testsData, coverageData, refactorData);
                    setExportOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 rounded-lg bg-indigo-950/40 hover:bg-indigo-900/40 text-indigo-300 font-semibold transition-colors flex items-center gap-2"
                >
                  <Download size={13} className="text-indigo-300" />
                  <span>Full Project Audit (.json)</span>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-[#1E293B] hover:border-[#2A364F] rounded-lg px-3 py-1.5 transition-colors cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Main Tab Bar */}
      <div className="flex border-b border-[#1E293B] px-6 bg-[#101726] flex-shrink-0">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === tab.id
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <tab.icon className="h-3.5 w-3.5" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content Panels */}
      <div className="flex-1 overflow-hidden relative bg-[#0B0F19]">
        {activeTab === 'graph' && (
          graphData ? (
            <DependencyGraph graphData={graphData} />
          ) : (
            <div className="flex items-center justify-center h-full text-slate-400 text-sm font-mono">
              Building dependency graph…
            </div>
          )
        )}

        {activeTab === 'explanation' && (
          <ExplanationView
            explanation={explanation}
            loading={explanationLoading}
            error={explanationError}
            onLoad={onLoadExplanation}
          />
        )}

        {activeTab === 'tests' && (
          <GeneratedTestsView
            jobId={job.job_id}
            languages={stats?.languages || ['python']}
          />
        )}

        {activeTab === 'refactor' && (
          <RefactoredCodeView
            jobId={job.job_id}
            languages={stats?.languages || ['python']}
          />
        )}
      </div>
    </main>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [view, setView] = useState<AppView>('landing');
  const [processingSource, setProcessingSource] = useState('');
  const [currentJob, setCurrentJob] = useState<JobResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [explanation, setExplanation] = useState<ProjectExplanation | null>(null);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => null);
  }, []);

  async function handleUpload(file: File) {
    setError(null);
    setView('processing');
    setProcessingSource(file.name);
    try {
      const job = await uploadZip(file);
      setCurrentJob(job);
      const graph = await fetchJobGraph(job.job_id);
      setGraphData(graph);
      setView('results');
    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setView('landing');
    }
  }

  async function handleGitHub(url: string) {
    setError(null);
    setView('processing');
    setProcessingSource(url);
    try {
      const job = await ingestGitHub(url);
      setCurrentJob(job);
      const graph = await fetchJobGraph(job.job_id);
      setGraphData(graph);
      setView('results');
    } catch (err: any) {
      setError(err.message || 'GitHub ingestion failed');
      setView('landing');
    }
  }

  async function handleLoadPreset(type: 'python' | 'javascript') {
    setError(null);
    setView('processing');
    setProcessingSource(
      type === 'python'
        ? 'Preset: Python Order Processor'
        : 'Preset: JavaScript Cart Manager'
    );

    try {
      // Create in-memory zip file from benchmark modules
      const JSZipModule = await import('jszip').catch(() => null);
      
      let zipBlob: Blob;
      if (JSZipModule) {
        const JSZip = JSZipModule.default || JSZipModule;
        const zip = new JSZip();
        if (type === 'python') {
          zip.file('order_processor.py', 'from discount_rules import calculate_tier_discount\n\nclass OrderProcessor:\n    def __init__(self, cid):\n        self.cid = cid\n        self.items = []\n    def add_item(self, item):\n        self.items.append(item)\n    def total(self):\n        sub = sum(i.get("price", 0) for i in self.items)\n        return sub - calculate_tier_discount(sub, len(self.items))\n');
          zip.file('discount_rules.py', 'def calculate_tier_discount(subtotal, count):\n    if count > 10:\n        return subtotal * 0.2\n    return subtotal * 0.05 if subtotal > 100 else 0.0\n');
          zip.file('tax_calculator.py', 'def compute_tax(amt, state):\n    return round(amt * 0.08, 2) if state == "CA" else 0.0\n');
        } else {
          zip.file('cart.js', 'import { validateItem } from "./validator.js";\n\nexport class CartManager {\n  constructor() { this.items = []; }\n  addItem(item) {\n    if (!validateItem(item)) throw new Error("Invalid item");\n    this.items.push(item);\n  }\n  getTotal() { return this.items.reduce((s, i) => s + i.price, 0); }\n}\n');
          zip.file('validator.js', 'export function validateItem(item) {\n  return item && typeof item.price === "number" && item.price >= 0;\n}\n');
          zip.file('formatter.js', 'export function formatCurrency(amount) {\n  return `$${amount.toFixed(2)}`;\n}\n');
        }
        zipBlob = await zip.generateAsync({ type: 'blob' });
      } else {
        // Fallback: Upload mock zip binary
        const zipBytes = new Uint8Array([80, 75, 5, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
        zipBlob = new Blob([zipBytes], { type: 'application/zip' });
      }

      const file = new File([zipBlob], `${type}_benchmark.zip`, { type: 'application/zip' });
      const job = await uploadZip(file);
      setCurrentJob(job);
      const graph = await fetchJobGraph(job.job_id);
      setGraphData(graph);
      setView('results');
    } catch (err: any) {
      setError(err.message || 'Failed to load benchmark preset');
      setView('landing');
    }
  }

  async function handleLoadExplanation() {
    if (!currentJob) return;
    setExplanationLoading(true);
    setExplanationError(null);
    try {
      const data = await fetchJobExplanation(currentJob.job_id);
      if (data.error) {
        setExplanationError(data.error);
      }
      setExplanation(data);
    } catch (err: any) {
      setExplanationError(err.message || 'Failed to generate explanation');
    } finally {
      setExplanationLoading(false);
    }
  }

  function reset() {
    setView('landing');
    setCurrentJob(null);
    setGraphData(null);
    setExplanation(null);
    setExplanationLoading(false);
    setExplanationError(null);
    setError(null);
  }

  return (
    <div className="h-screen flex flex-col bg-[#0B0F19] text-slate-100 font-sans overflow-hidden">
      {/* App Navigation Header */}
      <header className="border-b border-[#1E293B] bg-[#151C2C]/90 backdrop-blur px-6 py-3 flex-shrink-0 flex items-center justify-between z-50">
        <button
          onClick={reset}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity cursor-pointer text-left"
        >
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Cpu className="h-5 w-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold text-white font-mono tracking-tight">CodeOracle</span>
            <p className="text-[10px] text-slate-400 leading-none mt-0.5">
              Legacy Codebase Intelligence &amp; Modernization
            </p>
          </div>
        </button>

        <div className="flex items-center gap-3">
          {error && (
            <div className="flex items-center gap-2 text-xs text-rose-300 bg-rose-950/40 border border-rose-800/50 rounded-lg px-3 py-1.5 max-w-xs truncate">
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" /> {error}
            </div>
          )}
          <div className="flex items-center gap-2 bg-[#0B0F19] px-3 py-1.5 rounded-lg border border-[#1E293B] text-xs font-mono">
            <StatusDot ok={!!health} />
            <span className="text-slate-300">{health ? 'Connected' : 'Backend offline'}</span>
          </div>
        </div>
      </header>

      {/* Main Body */}
      {view === 'landing' && (
        <LandingView
          health={health}
          onUpload={handleUpload}
          onGitHub={handleGitHub}
          onLoadPreset={handleLoadPreset}
        />
      )}

      {view === 'processing' && <ProcessingView source={processingSource} />}

      {view === 'results' && currentJob && (
        <ResultsView
          job={currentJob}
          graphData={graphData}
          explanation={explanation}
          explanationLoading={explanationLoading}
          explanationError={explanationError}
          onLoadExplanation={handleLoadExplanation}
          onReset={reset}
        />
      )}

      {/* Footer */}
      {view === 'landing' && (
        <footer className="border-t border-[#1E293B] py-3 px-6 text-center text-xs text-slate-500 font-mono flex-shrink-0 bg-[#0B0F19]">
          CodeOracle © 2026 · Python &amp; JavaScript Static Analysis · Isolated Docker Sandbox · Render Deployment
        </footer>
      )}
    </div>
  );
};

export default App;
