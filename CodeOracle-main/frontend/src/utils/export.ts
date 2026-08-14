/**
 * Client-Side Export Utilities for CodeOracle
 * Generates and triggers browser downloads for reports, graphs, test suites, and git patches
 * without requiring any server-side database persistence.
 */
import {
  JobResponse,
  GraphData,
  ProjectExplanation,
  CoverageReport,
  RefactorResult,
  JobTestsData,
} from '../services/api';

/**
 * Creates a blob from text and triggers a native browser download.
 */
export function downloadFile(filename: string, content: string, mimeType: string = 'text/plain') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/**
 * Formats ProjectExplanation into a clean, comprehensive Markdown report.
 */
export function exportExplanationMarkdown(
  job: JobResponse,
  explanation: ProjectExplanation | null
) {
  if (!explanation) return;
  const dateStr = new Date().toISOString().split('T')[0];
  const source = job.source_info || job.job_id;

  let md = `# CodeOracle Intelligence Report: ${source}\n\n`;
  md += `**Analysis Date:** ${dateStr}  \n`;
  md += `**Job ID:** \`${job.job_id}\`  \n`;
  md += `**Total Files:** ${job.stats?.total_files ?? 0}  \n`;
  md += `**Total Source Lines:** ${job.stats?.total_lines ?? 0}  \n`;
  md += `**Languages Detected:** ${(job.stats?.languages ?? []).join(', ')}  \n\n`;

  md += `## 1. Repository Architectural Overview\n\n`;
  md += `${explanation.overview || 'No overview available.'}\n\n`;

  if (explanation.entry_points && explanation.entry_points.length > 0) {
    md += `### Primary Entry Points\n\n`;
    explanation.entry_points.forEach(ep => {
      md += `- \`${ep}\`\n`;
    });
    md += `\n`;
  }

  md += `## 2. Module & File Summaries\n\n`;
  (explanation.files || []).forEach(file => {
    md += `### File: \`${file.path}\` (${file.language}, ${file.total_lines} lines)\n\n`;
    md += `**Summary:** ${file.summary || 'N/A'}\n\n`;

    if (file.dependencies && file.dependencies.length > 0) {
      md += `**Dependencies:** ${file.dependencies.join(', ')}  \n`;
    }
    if (file.key_exports && file.key_exports.length > 0) {
      md += `**Key Exports:** ${file.key_exports.join(', ')}  \n`;
    }
    if (file.uncertainty) {
      md += `> ⚠️ **Uncertainty Note:** ${file.uncertainty}\n\n`;
    }

    if (file.symbols && file.symbols.length > 0) {
      md += `#### Functions & Classes in \`${file.path}\`:\n\n`;
      file.symbols.forEach(sym => {
        md += `##### \`${sym.symbol_type.toUpperCase()}\` ${sym.name} (Lines ${sym.start_line}-${sym.end_line})\n`;
        md += `${sym.summary || 'No summary available.'}\n\n`;
      });
    }
    md += `---\n\n`;
  });

  downloadFile(`codeoracle_explanation_${job.job_id.slice(0, 8)}.md`, md, 'text/markdown');
}

/**
 * Exports normalized dependency graph in JSON format.
 */
export function exportDependencyGraphJson(job: JobResponse, graph: GraphData | null) {
  if (!graph) return;
  const payload = {
    job_id: job.job_id,
    source: job.source_info,
    exported_at: new Date().toISOString(),
    graph: graph,
  };
  const jsonStr = JSON.stringify(payload, null, 2);
  downloadFile(`codeoracle_graph_${job.job_id.slice(0, 8)}.json`, jsonStr, 'application/json');
}

/**
 * Exports coverage report with statement metrics in JSON.
 */
export function exportCoverageReportJson(job: JobResponse, coverage: CoverageReport | null) {
  if (!coverage) return;
  const payload = {
    job_id: job.job_id,
    source: job.source_info,
    exported_at: new Date().toISOString(),
    coverage: coverage,
  };
  const jsonStr = JSON.stringify(payload, null, 2);
  downloadFile(`codeoracle_coverage_${job.job_id.slice(0, 8)}.json`, jsonStr, 'application/json');
}

/**
 * Exports unified diff patch file for the refactoring proposal.
 */
export function exportRefactorPatch(job: JobResponse, refactor: RefactorResult | null) {
  if (!refactor) return;
  let patch = `# CodeOracle Modernization Patch\n`;
  patch += `# Project: ${job.source_info || job.job_id}\n`;
  patch += `# Generated: ${new Date().toISOString()}\n`;
  patch += `# Risk Score: ${refactor.risk_summary.safety_score}/100 (${refactor.risk_summary.overall_risk.toUpperCase()} RISK)\n\n`;

  (refactor.files || []).forEach(f => {
    if (f.diff && f.diff.diff_text) {
      patch += `${f.diff.diff_text}\n\n`;
    }
  });

  downloadFile(`codeoracle_refactor_${job.job_id.slice(0, 8)}.patch`, patch, 'text/x-diff');
}

/**
 * Exports a full comprehensive audit summary JSON.
 */
export function exportFullProjectReportJson(
  job: JobResponse,
  explanation: ProjectExplanation | null,
  graph: GraphData | null,
  tests: JobTestsData | null,
  coverage: CoverageReport | null,
  refactor: RefactorResult | null
) {
  const payload = {
    codeoracle_version: '0.1.0',
    export_timestamp: new Date().toISOString(),
    project_metadata: {
      job_id: job.job_id,
      source: job.source_info,
      languages: job.stats?.languages ?? [],
      total_files: job.stats?.total_files ?? 0,
      total_lines: job.stats?.total_lines ?? 0,
    },
    explanation: explanation,
    dependency_graph: graph,
    tests_summary: tests,
    coverage_report: coverage,
    refactor_summary: refactor
      ? {
          status: refactor.status,
          files_modified: refactor.files_modified,
          total_additions: refactor.total_additions,
          total_deletions: refactor.total_deletions,
          risk_summary: refactor.risk_summary,
          warnings_count: refactor.all_warnings.length,
          warnings: refactor.all_warnings,
          modernization_opportunities: refactor.all_opportunities,
          validation: refactor.validation,
        }
      : null,
  };

  const jsonStr = JSON.stringify(payload, null, 2);
  downloadFile(`codeoracle_full_audit_${job.job_id.slice(0, 8)}.json`, jsonStr, 'application/json');
}
