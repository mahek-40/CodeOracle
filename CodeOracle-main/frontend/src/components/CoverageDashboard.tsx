import React from 'react';
import {
  CoverageReport,
  CoverageImprovementResult,
  FileCoverage,
} from '../services/api';
import {
  Target,
  Sparkles,
  TrendingUp,
  FileCode,
  CheckCircle2,
  RefreshCw,
  Clock,
  Layers,
  ArrowUpRight,
  AlertTriangle,
  Terminal,
} from 'lucide-react';

interface CoverageDashboardProps {
  jobId: string;
  report: CoverageReport | null;
  improvement: CoverageImprovementResult | null;
  improving: boolean;
  onImproveCoverage: () => void;
  onRefreshCoverage: () => void;
}

export const CoverageDashboard: React.FC<CoverageDashboardProps> = ({
  report,
  improvement,
  improving,
  onImproveCoverage,
  onRefreshCoverage,
}) => {
  const [showLogs, setShowLogs] = React.useState(false);

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-[#101726] border border-[#1E293B] rounded-xl text-center space-y-4 font-mono">
        <div className="h-12 w-12 rounded-full bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-center">
          <Target className="h-6 w-6 text-cyan-400" />
        </div>
        <div className="space-y-1">
          <h3 className="text-base font-bold text-white">No Coverage Data Available Yet</h3>
          <p className="text-xs text-slate-400 max-w-md leading-relaxed">
            Click <strong className="text-cyan-300">"Generate Tests"</strong> or <strong className="text-emerald-300">"Run Tests"</strong> above to author unit tests and measure real line coverage.
          </p>
        </div>
        <button
          onClick={onRefreshCoverage}
          className="flex items-center gap-2 text-xs text-cyan-300 hover:text-white bg-cyan-950/60 border border-cyan-800/60 hover:bg-cyan-900/50 px-4 py-2 rounded-lg transition-colors cursor-pointer"
        >
          <RefreshCw size={13} />
          <span>Measure Coverage</span>
        </button>
      </div>
    );
  }

  const hasCoverageData = (report.files && report.files.length > 0) || (report.total_lines > 0 && report.overall_coverage_percent !== undefined);
  const isFailed = report.status === 'failed' && !hasCoverageData;
  const currentCoverage = report.overall_coverage_percent ?? 0;
  const isTargetMet = !isFailed && currentCoverage >= 60.0;
  const files: FileCoverage[] = report.files ?? [];

  if (isFailed) {
    return (
      <div className="space-y-6">
        <div className="bg-rose-950/30 border border-rose-900/60 rounded-xl p-6 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-rose-900/40 border border-rose-800/60">
                <AlertTriangle className="h-6 w-6 text-rose-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white font-mono">
                  Coverage Unavailable: Execution Failed
                </h3>
                <span className="text-xs font-mono text-rose-300">
                  Failure Stage: <strong className="uppercase">{report?.stage || 'test_execution'}</strong>
                </span>
              </div>
            </div>
            <button
              onClick={onRefreshCoverage}
              className="flex items-center gap-1.5 text-xs text-rose-300 hover:text-white border border-rose-800/60 hover:bg-rose-900/40 rounded-lg px-3 py-1.5 transition-colors cursor-pointer font-mono"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Retry Measurement</span>
            </button>
          </div>

          <div className="bg-[#0B0F19] border border-rose-900/40 rounded-lg p-4 font-mono text-xs text-rose-200">
            <div className="text-slate-400 text-[11px] mb-1 font-semibold">ERROR REASON:</div>
            <p className="whitespace-pre-wrap">{report?.error || 'Test runner did not produce a valid coverage report.'}</p>
          </div>

          {(report?.install_logs || report?.execution_logs) && (
            <div className="space-y-2">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 font-mono transition-colors cursor-pointer"
              >
                <Terminal className="h-3.5 w-3.5" />
                <span>{showLogs ? 'Hide Runner Logs' : 'View Full Terminal Logs'}</span>
              </button>

              {showLogs && (
                <div className="bg-[#080C14] border border-slate-800 rounded-lg p-4 max-h-80 overflow-y-auto font-mono text-[11px] text-slate-300 space-y-3">
                  {report?.install_logs && (
                    <div>
                      <div className="text-cyan-400 font-bold text-[10px] uppercase mb-1">--- Dependency Installation Logs ---</div>
                      <pre className="whitespace-pre-wrap">{report.install_logs}</pre>
                    </div>
                  )}
                  {report?.execution_logs && (
                    <div>
                      <div className="text-indigo-400 font-bold text-[10px] uppercase mb-1">--- Test Execution Logs ---</div>
                      <pre className="whitespace-pre-wrap">{report.execution_logs}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  const coverageColor =
    currentCoverage >= 60
      ? 'text-emerald-400'
      : currentCoverage >= 40
      ? 'text-amber-400'
      : 'text-rose-400';

  const progressBg =
    currentCoverage >= 60
      ? 'bg-emerald-500'
      : currentCoverage >= 40
      ? 'bg-amber-500'
      : 'bg-rose-500';

  return (
    <div className="space-y-6">
      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Main Coverage Gauge */}
        <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Real Line Coverage
            </span>
            <span
              className={`text-[11px] font-mono font-medium px-2.5 py-0.5 rounded-full border ${
                isTargetMet
                  ? 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'
                  : 'bg-amber-950/60 border-amber-800/60 text-amber-300'
              }`}
            >
              {isTargetMet ? '🎯 Target Reached (≥60%)' : '⚠️ Below 60% Target'}
            </span>
          </div>

          <div className="my-4">
            <div className="flex items-baseline gap-2">
              <span className={`text-4xl font-bold font-mono ${coverageColor}`}>
                {currentCoverage.toFixed(1)}%
              </span>
              <span className="text-xs text-slate-500 font-mono">/ 100%</span>
            </div>

            {/* Target 60% Progress Bar */}
            <div className="w-full bg-slate-900 rounded-full h-2 mt-3 relative overflow-hidden border border-slate-800">
              <div
                className={`h-full rounded-full transition-all duration-500 ${progressBg}`}
                style={{ width: `${Math.min(100, currentCoverage)}%` }}
              />
              {/* 60% Marker line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-cyan-400 z-10 opacity-70"
                style={{ left: '60%' }}
                title="60% Target Benchmark"
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-slate-500 mt-1">
              <span>0%</span>
              <span className="text-cyan-400 font-semibold">60% Benchmark</span>
              <span>100%</span>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 font-mono border-t border-[#1E293B] pt-3">
            <span>
              Covered:{' '}
              <strong className="text-emerald-400">
                {report?.total_covered_lines ?? 0}
              </strong>
            </span>
            <span>
              Missing:{' '}
              <strong className="text-rose-400">
                {report?.total_uncovered_lines ?? 0}
              </strong>
            </span>
            <span>
              Total Statements:{' '}
              <strong className="text-white">
                {report?.total_lines ?? 0}
              </strong>
            </span>
          </div>
        </div>

        {/* Coverage Gain & AI Improvement Card */}
        <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Targeted AI Optimization
            </span>
            {improvement && (
              <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/60 text-cyan-300">
                {improvement.total_iterations} Iterations
              </span>
            )}
          </div>

          <div className="my-3 space-y-2">
            {improvement ? (
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <div className="text-xs text-slate-400 font-mono">
                    Baseline: {improvement.initial_coverage.toFixed(1)}% → Final:{' '}
                    {improvement.final_coverage.toFixed(1)}%
                  </div>
                  <div className="text-base font-bold text-emerald-400 font-mono flex items-center gap-1">
                    <ArrowUpRight className="h-4 w-4" />
                    <span>+{improvement.coverage_gain.toFixed(1)}% Gain</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400 leading-relaxed">
                CodeOracle scans uncovered AST function bodies and generates
                iterative targeted unit tests until &gt;60% line coverage is achieved.
              </p>
            )}
          </div>

          <button
            onClick={onImproveCoverage}
            disabled={improving}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-50 text-white font-medium text-xs py-2.5 rounded-lg shadow-md shadow-cyan-600/10 transition-all cursor-pointer"
          >
            {improving ? (
              <RefreshCw className="h-4 w-4 animate-spin text-cyan-200" />
            ) : (
              <Sparkles className="h-4 w-4 text-cyan-200" />
            )}
            <span>
              {improving
                ? 'Targeting Uncovered Areas (Max 3 Retries)…'
                : 'Improve Coverage with AI'}
            </span>
          </button>
        </div>

        {/* Real Tooling Guarantee */}
        <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-5 flex flex-col justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <Target className="h-4 w-4 text-cyan-400" />
            <span>Execution Guarantee</span>
          </div>

          <div className="space-y-2.5 my-3 text-xs text-slate-300">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>100% Real Execution:</strong> Driven by{' '}
                <code className="text-cyan-300 font-mono">coverage.py</code> &amp;{' '}
                <code className="text-cyan-300 font-mono">Vitest</code> in Docker.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Zero Fabrication:</strong> Never simulated or estimated.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Bounded Retries:</strong> Strict max 3 attempts to avoid
                infinite loops.
              </span>
            </div>
          </div>

          <button
            onClick={onRefreshCoverage}
            className="flex items-center justify-center gap-1.5 text-xs text-slate-400 hover:text-white border border-[#1E293B] hover:border-[#2A364F] rounded-lg py-2 transition-colors cursor-pointer"
          >
            <RefreshCw className="h-3 w-3" />
            <span>Re-measure Coverage</span>
          </button>
        </div>
      </div>

      {/* Iteration Timeline (if improvement iterations exist) */}
      {improvement && improvement.iterations && improvement.iterations.length > 0 && (
        <div className="bg-[#101726] border border-[#1E293B] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-cyan-400" />
              <span>Targeted Improvement Progress Timeline</span>
            </span>
            <span className="text-xs font-mono text-emerald-400 font-semibold">
              Final: {improvement.final_coverage.toFixed(1)}% Line Coverage
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 pt-2">
            {improvement.iterations.map(iter => (
              <div
                key={iter.iteration}
                className="bg-[#0B0F19] border border-[#1E293B] rounded-lg p-3 space-y-1.5 font-mono text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 font-semibold">
                    {iter.iteration === 0 ? 'Baseline' : `Iteration #${iter.iteration}`}
                  </span>
                  <span
                    className={`font-bold ${
                      iter.coverage_percent >= 60
                        ? 'text-emerald-400'
                        : 'text-amber-400'
                    }`}
                  >
                    {iter.coverage_percent.toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>
                    {iter.iteration === 0
                      ? 'Initial suite'
                      : `+${iter.new_tests_generated} targeted tests`}
                  </span>
                  {iter.coverage_gain > 0 && (
                    <span className="text-emerald-400 font-semibold">
                      +{iter.coverage_gain.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* File Breakdown Table */}
      <div className="bg-[#101726] border border-[#1E293B] rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#1E293B] flex items-center justify-between">
          <span className="text-xs font-semibold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-cyan-400" />
            <span>Per-File Coverage Breakdown</span>
          </span>
          <span className="text-xs font-mono text-slate-400">
            {files.length} Source Files
          </span>
        </div>

        {files.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 font-mono">
            No source files analyzed yet. Run test generation and execution above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#0B0F19] text-slate-400 uppercase text-[10px] tracking-wider border-b border-[#1E293B]">
                <tr>
                  <th className="px-5 py-3">Source File</th>
                  <th className="px-4 py-3">Coverage</th>
                  <th className="px-4 py-3">Progress</th>
                  <th className="px-4 py-3">Covered / Total</th>
                  <th className="px-5 py-3">Uncovered Line Numbers</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E293B]">
                {files.map(f => {
                  const pct = f.coverage_percent;
                  const tierColor =
                    pct >= 60
                      ? 'text-emerald-400 bg-emerald-950/50 border-emerald-800/40'
                      : pct >= 40
                      ? 'text-amber-400 bg-amber-950/50 border-amber-800/40'
                      : 'text-rose-400 bg-rose-950/50 border-rose-800/40';

                  const barColor =
                    pct >= 60
                      ? 'bg-emerald-500'
                      : pct >= 40
                      ? 'bg-amber-500'
                      : 'bg-rose-500';

                  return (
                    <tr key={f.path} className="hover:bg-[#151C2C]/50 transition-colors">
                      <td className="px-5 py-3 flex items-center gap-2 text-slate-200">
                        <FileCode className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
                        <span className="font-semibold truncate max-w-xs">{f.path}</span>
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded border text-[11px] font-bold ${tierColor}`}
                        >
                          {pct.toFixed(1)}%
                        </span>
                      </td>

                      <td className="px-4 py-3 w-40">
                        <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${barColor}`}
                            style={{ width: `${Math.min(100, pct)}%` }}
                          />
                        </div>
                      </td>

                      <td className="px-4 py-3 text-slate-300">
                        <span className="text-emerald-400 font-medium">
                          {f.covered_lines_count}
                        </span>{' '}
                        / {f.total_lines}
                      </td>

                      <td className="px-5 py-3 text-slate-400">
                        {f.uncovered_lines && f.uncovered_lines.length > 0 ? (
                          <span
                            className="text-rose-300 bg-rose-950/40 border border-rose-900/50 px-2 py-0.5 rounded text-[10px]"
                            title={f.uncovered_lines.join(', ')}
                          >
                            Lines:{' '}
                            {f.uncovered_lines.length > 6
                              ? `${f.uncovered_lines.slice(0, 6).join(', ')}... (+${
                                  f.uncovered_lines.length - 6
                                } more)`
                              : f.uncovered_lines.join(', ')}
                          </span>
                        ) : (
                          <span className="text-emerald-400 text-[11px] font-semibold">
                            ✓ 100% Covered
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default CoverageDashboard;
