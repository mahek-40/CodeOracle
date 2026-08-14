import React, { useState, useEffect } from 'react';
import {
  generateJobRefactor,
  fetchJobRefactor,
  validateJobRefactor,
  RefactorResult,
  RefactoredFile,
  ValidationComparison,
} from '../services/api';
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  FileCode,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Copy,
  Check,
  Layers,
  ShieldAlert,
  Terminal,
  Filter,
  CheckSquare,
  Zap,
} from 'lucide-react';

interface RefactoredCodeViewProps {
  jobId: string;
  languages?: string[];
}

export const RefactoredCodeView: React.FC<RefactoredCodeViewProps> = ({
  jobId,
}) => {
  const [generating, setGenerating] = useState(false);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<RefactorResult | null>(null);
  const [validation, setValidation] = useState<ValidationComparison | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<
    'split' | 'unified' | 'warnings' | 'modernizations' | 'validation'
  >('split');
  const [warningFilter, setWarningFilter] = useState<string>('all');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing refactor results if available
  useEffect(() => {
    fetchJobRefactor(jobId)
      .then(data => {
        setResult(data);
        if (data.validation) {
          setValidation(data.validation);
        }
      })
      .catch(() => null);
  }, [jobId]);

  async function handleGenerate() {
    setError(null);
    setGenerating(true);
    try {
      const data = await generateJobRefactor(jobId);
      setResult(data);
      if (data.files.length > 0) {
        setSelectedIndex(0);
      }
      setActiveTab('split');
    } catch (err: any) {
      setError(err.message || 'Failed to generate refactoring proposal.');
    } finally {
      setGenerating(false);
    }
  }

  async function handleValidate() {
    setError(null);
    setValidating(true);
    try {
      const data = await validateJobRefactor(jobId);
      setValidation(data);
      if (result) {
        setResult({ ...result, validation: data });
      }
      setActiveTab('validation');
    } catch (err: any) {
      setError(err.message || 'Failed to execute test validation sandbox.');
    } finally {
      setValidating(false);
    }
  }

  const files = result?.files ?? [];
  const activeFile: RefactoredFile | undefined = files[selectedIndex];
  const allWarnings = result?.all_warnings ?? [];
  const allOpportunities = result?.all_opportunities ?? [];

  const filteredWarnings =
    warningFilter === 'all'
      ? allWarnings
      : allWarnings.filter(w => w.severity === warningFilter);

  function copyRefactoredCode() {
    if (activeFile?.refactored_content) {
      navigator.clipboard.writeText(activeFile.refactored_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const riskBadge = () => {
    const risk = result?.risk_summary.overall_risk;
    if (risk === 'critical') {
      return (
        <span className="px-2.5 py-1 rounded bg-rose-950/70 border border-rose-800 text-rose-300 font-bold text-xs flex items-center gap-1.5 font-mono">
          <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
          <span>CRITICAL RISK</span>
        </span>
      );
    } else if (risk === 'high') {
      return (
        <span className="px-2.5 py-1 rounded bg-amber-950/70 border border-amber-800 text-amber-300 font-bold text-xs flex items-center gap-1.5 font-mono">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
          <span>HIGH RISK</span>
        </span>
      );
    } else if (risk === 'medium') {
      return (
        <span className="px-2.5 py-1 rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300 font-bold text-xs flex items-center gap-1.5 font-mono">
          <AlertTriangle className="h-3.5 w-3.5 text-cyan-400" />
          <span>MEDIUM RISK</span>
        </span>
      );
    }
    return (
      <span className="px-2.5 py-1 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300 font-bold text-xs flex items-center gap-1.5 font-mono">
        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
        <span>LOW RISK</span>
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col bg-[#0B0F19] text-slate-200 overflow-hidden font-sans">
      {/* Top Header & Actions Bar */}
      <div className="px-6 py-3 bg-[#151C2C] border-b border-[#1E293B] flex items-center justify-between gap-4 flex-wrap flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating || validating}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-md shadow-indigo-500/10 transition-all cursor-pointer"
          >
            {generating ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5 text-indigo-200" />
            )}
            <span>
              {generating
                ? 'Modernizing Codebase…'
                : result
                ? 'Regenerate Refactor'
                : 'Generate Modern Refactor'}
            </span>
          </button>

          <button
            onClick={handleValidate}
            disabled={validating || generating || !result}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-medium text-xs px-4 py-2 rounded-lg shadow-md shadow-emerald-500/10 transition-all cursor-pointer"
          >
            {validating ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-200" />
            )}
            <span>
              {validating ? 'Testing Sandbox…' : 'Validate against Test Suite'}
            </span>
          </button>

          {result && riskBadge()}
        </div>

        {/* Safety Guarantee Info */}
        <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
          <span className="text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2.5 py-1 rounded">
            ✓ Non-Destructive (Originals Preserved)
          </span>
          {result && (
            <span>
              Safety Score:{' '}
              <strong className="text-white font-bold">
                {result.risk_summary.safety_score}/100
              </strong>
            </span>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="px-6 py-2.5 bg-rose-950/40 border-b border-rose-900/60 flex items-center gap-3 text-xs text-rose-300">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 text-rose-400" />
          <span className="flex-1">{error}</span>
        </div>
      )}

      {/* Metrics Summary Strip (if results generated) */}
      {result && (
        <div className="px-6 py-2 bg-[#101726] border-b border-[#1E293B] flex items-center gap-4 flex-wrap text-xs font-mono flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Modified Files:</span>
            <span className="text-white font-semibold">
              {result.files_modified} / {result.total_files}
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-slate-700" />

          <div className="flex items-center gap-2">
            <span className="text-emerald-400 font-semibold">
              +{result.total_additions} lines
            </span>
            <span className="text-rose-400 font-semibold">
              -{result.total_deletions} lines
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-slate-700" />

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Breaking Warnings:</span>
            <span
              className={`font-semibold ${
                allWarnings.length > 0 ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {allWarnings.length}
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-slate-700" />

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Modernizations:</span>
            <span className="text-cyan-400 font-semibold">
              {allOpportunities.length} patterns applied
            </span>
          </div>

          {validation && (
            <>
              <div className="h-3.5 w-[1px] bg-slate-700" />
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Validation:</span>
                {validation.status === 'verified' ? (
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> VERIFIED (0 Regressions)
                  </span>
                ) : validation.status === 'regressions_detected' ? (
                  <span className="text-rose-400 font-bold flex items-center gap-1">
                    <XCircle className="h-3.5 w-3.5" /> REGRESSIONS DETECTED ({validation.regressions.length})
                  </span>
                ) : (
                  <span className="text-amber-400 font-semibold">
                    {validation.status.toUpperCase()}
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Main Panel View & Tabs */}
      <div className="px-6 border-b border-[#1E293B] bg-[#151C2C] flex items-center justify-between flex-shrink-0">
        <div className="flex">
          <button
            onClick={() => setActiveTab('split')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'split'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Split View (Original vs Proposed)</span>
          </button>

          <button
            onClick={() => setActiveTab('unified')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'unified'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="h-3.5 w-3.5" />
            <span>Unified Diff</span>
          </button>

          <button
            onClick={() => setActiveTab('warnings')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'warnings'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>Breaking Change Warnings ({allWarnings.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('modernizations')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'modernizations'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Zap className="h-3.5 w-3.5" />
            <span>Modernization Insights ({allOpportunities.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('validation')}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors cursor-pointer ${
              activeTab === 'validation'
                ? 'border-indigo-400 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckSquare className="h-3.5 w-3.5" />
            <span>Test Suite Validation</span>
          </button>
        </div>

        {activeFile && (
          <button
            onClick={copyRefactoredCode}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-[#0B0F19] border border-[#1E293B] rounded px-2.5 py-1 transition-colors cursor-pointer"
          >
            {copied ? (
              <Check className="h-3 w-3 text-emerald-400" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
            <span>{copied ? 'Copied Refactored Code!' : 'Copy Proposed Code'}</span>
          </button>
        )}
      </div>

      {/* Main Content Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Changed Files Selector (for split / unified views) */}
        {(activeTab === 'split' || activeTab === 'unified') && (
          <div className="w-72 border-r border-[#1E293B] bg-[#101726] flex flex-col flex-shrink-0">
            <div className="px-4 py-2.5 border-b border-[#1E293B] flex items-center justify-between text-xs font-semibold text-slate-400">
              <span>Changed Files</span>
              <span className="font-mono text-[11px] text-indigo-400">
                {files.length} files
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {files.map((f, idx) => {
                const isSelected = selectedIndex === idx;
                const fileWarnings = f.warnings.length;

                return (
                  <button
                    key={f.path}
                    onClick={() => setSelectedIndex(idx)}
                    className={`w-full text-left p-2.5 rounded-lg text-xs font-mono transition-all flex flex-col gap-1 border cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-800/60 text-indigo-300'
                        : 'bg-[#151C2C]/50 border-transparent text-slate-300 hover:bg-[#1E293B]/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 truncate">
                        <FileCode className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
                        <span className="font-medium truncate">{f.path}</span>
                      </div>
                      {fileWarnings > 0 && (
                        <span className="bg-amber-950/80 border border-amber-800 text-amber-300 text-[10px] px-1.5 py-0.2 rounded-full font-bold">
                          {fileWarnings} warn
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-500 pl-5.5">
                      <span>
                        +{f.diff.additions} / -{f.diff.deletions}
                      </span>
                      {f.opportunities.length > 0 && (
                        <span className="text-cyan-400">
                          {f.opportunities.length} modernizations
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Right Workspace Panes */}
        <div className="flex-1 overflow-auto p-6 bg-[#0B0F19]">
          {/* 1. Split Diff View */}
          {activeTab === 'split' && (
            <div className="h-full flex flex-col space-y-3">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 bg-[#101726] border border-[#1E293B] rounded-lg px-4 py-2 flex-shrink-0">
                <span className="font-semibold text-white">
                  {activeFile?.path || 'Select a file'}
                </span>
                <div className="flex items-center gap-4">
                  <span className="text-slate-400">
                    Original (Left) vs Proposed Modernized (Right)
                  </span>
                  <span className="text-emerald-400">
                    +{activeFile?.diff.additions ?? 0} lines
                  </span>
                  <span className="text-rose-400">
                    -{activeFile?.diff.deletions ?? 0} lines
                  </span>
                </div>
              </div>

              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-hidden">
                {/* Left: Original Code */}
                <div className="flex flex-col bg-[#070A12] border border-[#1E293B] rounded-xl overflow-hidden shadow-inner">
                  <div className="px-4 py-2 bg-[#101726] border-b border-[#1E293B] text-[11px] font-mono font-semibold text-slate-400">
                    ORIGINAL SOURCE
                  </div>
                  <div className="flex-1 p-4 overflow-auto font-mono text-xs text-slate-300 leading-relaxed">
                    <pre>{activeFile?.original_content || 'No file selected'}</pre>
                  </div>
                </div>

                {/* Right: Proposed Refactored Code */}
                <div className="flex flex-col bg-[#070A12] border border-indigo-900/40 rounded-xl overflow-hidden shadow-inner">
                  <div className="px-4 py-2 bg-indigo-950/30 border-b border-indigo-900/40 text-[11px] font-mono font-semibold text-indigo-300 flex items-center justify-between">
                    <span>PROPOSED MODERNIZED</span>
                    <span className="text-[10px] text-emerald-400 font-normal">
                      ✓ Python 3.10+ / ES2022
                    </span>
                  </div>
                  <div className="flex-1 p-4 overflow-auto font-mono text-xs text-indigo-200 leading-relaxed">
                    <pre>
                      {activeFile?.refactored_content ||
                        (generating
                          ? 'Generating modernization proposal…'
                          : 'Click "Generate Modern Refactor" above.')}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2. Unified Diff View */}
          {activeTab === 'unified' && (
            <div className="h-full flex flex-col space-y-3">
              <div className="font-mono text-xs text-slate-300 bg-[#101726] border border-[#1E293B] rounded-lg px-4 py-2">
                Unified Diff for <strong className="text-white">{activeFile?.path}</strong>
              </div>

              <div className="flex-1 font-mono text-xs bg-[#070A12] border border-[#1E293B] rounded-xl p-4 overflow-auto leading-relaxed shadow-inner">
                {activeFile?.diff.diff_lines && activeFile.diff.diff_lines.length > 0 ? (
                  <div className="space-y-0.5">
                    {activeFile.diff.diff_lines.map((line, idx) => {
                      const isAdd = line.type === 'add';
                      const isDel = line.type === 'del';
                      const isMod = line.type === 'mod';

                      const bg = isAdd
                        ? 'bg-emerald-950/40 text-emerald-300'
                        : isDel
                        ? 'bg-rose-950/40 text-rose-300'
                        : isMod
                        ? 'bg-indigo-950/40 text-indigo-300'
                        : 'text-slate-400';

                      const prefix = isAdd ? '+' : isDel ? '-' : isMod ? '~' : ' ';

                      return (
                        <div key={idx} className={`px-2 py-0.5 rounded ${bg} flex`}>
                          <span className="w-8 text-slate-600 select-none text-[10px]">
                            {line.orig_line_num || ''}
                          </span>
                          <span className="w-8 text-slate-600 select-none text-[10px]">
                            {line.refactored_line_num || ''}
                          </span>
                          <span className="w-4 select-none text-slate-500 font-bold">
                            {prefix}
                          </span>
                          <span className="flex-1 whitespace-pre-wrap">{line.content}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-slate-500 p-4">
                    {activeFile?.diff.diff_text || 'No diff lines to display.'}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 3. Breaking Change Warnings Panel */}
          {activeTab === 'warnings' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <Filter className="h-4 w-4 text-indigo-400" />
                  <span>Filter by Severity:</span>
                </div>
                <div className="flex gap-2">
                  {['all', 'critical', 'high', 'medium', 'low'].map(lvl => (
                    <button
                      key={lvl}
                      onClick={() => setWarningFilter(lvl)}
                      className={`text-xs font-mono uppercase px-3 py-1 rounded border transition-colors cursor-pointer ${
                        warningFilter === lvl
                          ? 'bg-indigo-600 text-white border-indigo-500'
                          : 'bg-[#101726] text-slate-400 border-[#1E293B] hover:text-white'
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {filteredWarnings.length === 0 ? (
                <div className="bg-[#101726] border border-emerald-900/40 rounded-xl p-8 text-center space-y-2">
                  <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
                  <div className="text-sm font-semibold text-white">
                    Zero Breaking Changes Detected
                  </div>
                  <p className="text-xs text-slate-400">
                    All public API contracts, classes, and parameter signatures remain
                    backward-compatible.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredWarnings.map((w, idx) => {
                    const isCrit = w.severity === 'critical';
                    const isHigh = w.severity === 'high';
                    const isMed = w.severity === 'medium';

                    const borderTheme = isCrit
                      ? 'border-rose-900/60 bg-rose-950/20'
                      : isHigh
                      ? 'border-amber-900/60 bg-amber-950/20'
                      : isMed
                      ? 'border-cyan-900/60 bg-cyan-950/20'
                      : 'border-slate-800 bg-slate-900/20';

                    const badgeTheme = isCrit
                      ? 'bg-rose-950 text-rose-300 border-rose-800'
                      : isHigh
                      ? 'bg-amber-950 text-amber-300 border-amber-800'
                      : isMed
                      ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                      : 'bg-slate-900 text-slate-300 border-slate-700';

                    return (
                      <div
                        key={idx}
                        className={`border rounded-xl p-4 space-y-3 ${borderTheme}`}
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border uppercase ${badgeTheme}`}
                            >
                              {w.severity}
                            </span>
                            <span className="text-xs font-mono font-semibold text-white">
                              {w.symbol}
                            </span>
                            <span className="text-xs font-mono text-slate-400">
                              in {w.file}
                            </span>
                          </div>

                          <span className="text-[11px] font-mono text-slate-500 uppercase bg-[#0B0F19] px-2 py-0.5 rounded border border-[#1E293B]">
                            Category: {w.category}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">
                          {w.explanation}
                        </p>

                        <div className="bg-[#0B0F19] border border-[#1E293B] rounded-lg p-3 text-xs space-y-1">
                          <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                            <ShieldCheck className="h-3.5 w-3.5" />
                            <span>Suggested Mitigation</span>
                          </div>
                          <p className="text-slate-300">{w.suggested_mitigation}</p>
                        </div>

                        {w.affected_dependents && w.affected_dependents.length > 0 && (
                          <div className="text-[11px] font-mono text-amber-300">
                            Affected Callers:{' '}
                            <span className="text-slate-300">
                              {w.affected_dependents.join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* 4. Modernization Opportunities Panel */}
          {activeTab === 'modernizations' && (
            <div className="space-y-4">
              <div className="text-xs text-slate-400 font-mono">
                AI Modernization Patterns Applied Across Codebase ({allOpportunities.length} detected)
              </div>

              {allOpportunities.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 font-mono bg-[#101726] border border-[#1E293B] rounded-xl">
                  No explicit modernization patterns detected.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {allOpportunities.map((opp, idx) => (
                    <div
                      key={idx}
                      className="bg-[#101726] border border-[#1E293B] rounded-xl p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white flex items-center gap-2">
                          <Zap className="h-3.5 w-3.5 text-cyan-400" />
                          <span>{opp.title}</span>
                        </span>
                        <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 rounded uppercase">
                          {opp.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {opp.description}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 5. Non-Regression Validation Panel */}
          {activeTab === 'validation' && (
            <div className="space-y-6">
              {!validation ? (
                <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-8 text-center space-y-3">
                  <ShieldCheck className="h-10 w-10 text-indigo-400 mx-auto" />
                  <div className="text-sm font-semibold text-white">
                    Non-Regression Test Validation
                  </div>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Execute the generated unit test suite inside an isolated Docker sandbox against
                    the proposed refactored code to verify semantic safety.
                  </p>
                  <button
                    onClick={handleValidate}
                    disabled={validating || !result}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs px-5 py-2.5 rounded-lg shadow-md shadow-emerald-500/10 transition-all cursor-pointer inline-flex items-center gap-2"
                  >
                    {validating ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <ShieldCheck className="h-4 w-4" />
                    )}
                    <span>
                      {validating ? 'Executing Validation…' : 'Run Validation in Docker Sandbox'}
                    </span>
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Status Banner */}
                  <div
                    className={`rounded-xl p-5 border flex items-center justify-between ${
                      validation.status === 'verified'
                        ? 'bg-emerald-950/30 border-emerald-800 text-emerald-300'
                        : validation.status === 'regressions_detected'
                        ? 'bg-rose-950/30 border-rose-800 text-rose-300'
                        : 'bg-amber-950/30 border-amber-800 text-amber-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {validation.status === 'verified' ? (
                        <CheckCircle2 className="h-6 w-6 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <XCircle className="h-6 w-6 text-rose-400 flex-shrink-0" />
                      )}
                      <div>
                        <div className="text-sm font-bold">
                          {validation.status === 'verified'
                            ? 'Semantic Equivalence Verified'
                            : validation.status === 'regressions_detected'
                            ? 'Regressions Detected in Refactored Code'
                            : 'Validation Incomplete'}
                        </div>
                        <div className="text-xs opacity-80">
                          {validation.status === 'verified'
                            ? 'All generated tests passed against the proposed refactoring with zero regressions.'
                            : `${validation.regressions.length} test failures detected during refactoring execution.`}
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={handleValidate}
                      disabled={validating}
                      className="text-xs bg-[#0B0F19] hover:bg-[#151C2C] border border-[#1E293B] rounded-lg px-3 py-1.5 transition-colors cursor-pointer"
                    >
                      Re-run Validation
                    </button>
                  </div>

                  {/* Test Pass Rate Comparison Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-4 font-mono text-xs">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">
                        Original Test Pass Rate
                      </div>
                      <div className="text-xl font-bold text-white mt-1">
                        {validation.original_tests_passed} passed /{' '}
                        {validation.original_tests_failed} failed
                      </div>
                    </div>

                    <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-4 font-mono text-xs">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">
                        Refactored Test Pass Rate
                      </div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">
                        {validation.refactored_tests_passed} passed /{' '}
                        {validation.refactored_tests_failed} failed
                      </div>
                    </div>

                    <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-4 font-mono text-xs">
                      <div className="text-slate-400 text-[10px] uppercase font-semibold">
                        Coverage Delta
                      </div>
                      <div className="text-xl font-bold text-cyan-400 mt-1">
                        {validation.refactored_coverage_percent !== null &&
                        validation.refactored_coverage_percent !== undefined
                          ? `${validation.refactored_coverage_percent.toFixed(1)}%`
                          : 'Measured'}
                        {validation.coverage_delta !== null &&
                          validation.coverage_delta !== undefined && (
                            <span className="text-xs text-slate-400 ml-2">
                              ({validation.coverage_delta >= 0 ? '+' : ''}
                              {validation.coverage_delta}%)
                            </span>
                          )}
                      </div>
                    </div>
                  </div>

                  {/* Regressions List */}
                  {validation.regressions && validation.regressions.length > 0 && (
                    <div className="bg-rose-950/20 border border-rose-900/60 rounded-xl p-4 space-y-2 font-mono text-xs">
                      <div className="font-semibold text-rose-300 flex items-center gap-2">
                        <XCircle className="h-4 w-4 text-rose-400" />
                        <span>Failing Tests (Regressions):</span>
                      </div>
                      <ul className="list-disc pl-6 space-y-1 text-rose-200">
                        {validation.regressions.map((reg, idx) => (
                          <li key={idx}>{reg}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Sandbox Terminal Logs */}
                  {validation.stdout && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-400 font-mono flex items-center gap-2">
                        <Terminal className="h-4 w-4 text-slate-400" />
                        <span>Docker Sandbox Output</span>
                      </div>
                      <div className="bg-[#070A12] border border-[#1E293B] rounded-xl p-4 font-mono text-xs text-emerald-300 leading-relaxed whitespace-pre-wrap max-h-60 overflow-auto">
                        {validation.stdout}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RefactoredCodeView;
