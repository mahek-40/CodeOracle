import React, { useState, useMemo } from 'react';
import { ProjectExplanation, FileExplanation, SymbolExplanation } from '../services/api';
import {
  AlertTriangle,
  CheckCircle2,
  FileCode,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  Search,
  X,
  Copy,
  Check,
  Download,
  ChevronsUpDown,
  Sparkles,
} from 'lucide-react';
import { downloadFile } from '../utils/export';

// ─── Markdown-like renderer for Gemini text output ───────────────────────────
function GeminiText({ text, className = '' }: { text: string; className?: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    // Heading: ### or **Heading**
    if (/^#{1,3}\s/.test(line)) {
      const content = line.replace(/^#{1,3}\s/, '');
      elements.push(
        <p key={i} className="text-slate-200 font-semibold text-sm mt-3 mb-1">
          {renderInline(content)}
        </p>
      );
      continue;
    }

    // Bullet
    if (/^\s*[-*]\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-slate-300 text-xs list-disc">
          {renderInline(line.replace(/^\s*[-*]\s/, ''))}
        </li>
      );
      continue;
    }

    // Numbered list
    if (/^\s*\d+\.\s/.test(line)) {
      elements.push(
        <li key={i} className="ml-4 text-slate-300 text-xs list-decimal">
          {renderInline(line.replace(/^\s*\d+\.\s/, ''))}
        </li>
      );
      continue;
    }

    elements.push(
      <p key={i} className="text-slate-300 text-xs leading-relaxed">
        {renderInline(line)}
      </p>
    );
  }

  return <div className={`space-y-0.5 ${className}`}>{elements}</div>;
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="text-slate-100 font-semibold">
        {part}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

// ─── Symbol card ─────────────────────────────────────────────────────────────
function SymbolCard({ sym }: { sym: SymbolExplanation }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const typeColor =
    sym.symbol_type === 'class'
      ? 'text-indigo-400 bg-indigo-950/40 border-indigo-800/40'
      : 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40';

  function copySymbol() {
    navigator.clipboard.writeText(sym.name);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="border border-[#1E293B] rounded-lg overflow-hidden">
      <div className="flex items-center gap-2.5 px-3 py-2 bg-[#0D1420] hover:bg-[#0f1928] transition-colors">
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 flex-1 text-left min-w-0"
        >
          {open ? (
            <ChevronDown size={13} className="text-slate-400 flex-shrink-0" />
          ) : (
            <ChevronRight size={13} className="text-slate-400 flex-shrink-0" />
          )}
          <span
            className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded border ${typeColor} uppercase flex-shrink-0`}
          >
            {sym.symbol_type}
          </span>
          <span className="text-xs text-slate-200 font-mono font-medium truncate">
            {sym.name}
          </span>
          <span className="text-[10px] text-slate-500 font-mono ml-auto flex-shrink-0 pr-2">
            L{sym.start_line}–{sym.end_line}
          </span>
        </button>

        <button
          onClick={copySymbol}
          title="Copy symbol identifier"
          className="text-slate-500 hover:text-slate-200 p-1 rounded transition-colors"
        >
          {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
        </button>
      </div>

      {open && (
        <div className="px-4 py-3 bg-[#0B0F19] space-y-3 border-t border-[#1E293B]">
          {sym.summary ? (
            <GeminiText text={sym.summary} />
          ) : sym.uncertainty ? (
            <p className="text-xs text-amber-400 italic">{sym.uncertainty}</p>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ─── File card ───────────────────────────────────────────────────────────────
function FileCard({ fe, forceOpen }: { fe: FileExplanation; forceOpen?: boolean }) {
  const [open, setOpen] = useState(false);
  const isExpanded = forceOpen !== undefined ? forceOpen : open;
  const hasError = !fe.summary && !fe.symbols.length;

  return (
    <div
      className={`border rounded-xl overflow-hidden transition-all ${
        hasError ? 'border-rose-800/50' : 'border-[#1E293B]'
      }`}
    >
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-[#151C2C] hover:bg-[#1a2235] transition-colors text-left"
      >
        {isExpanded ? (
          <ChevronDown size={14} className="text-slate-400 flex-shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-slate-400 flex-shrink-0" />
        )}
        <FileCode
          size={14}
          className={fe.language === 'python' ? 'text-blue-400' : 'text-amber-400'}
        />
        <span className="text-xs text-slate-200 font-mono truncate">{fe.path}</span>
        <div className="ml-auto flex items-center gap-2 flex-shrink-0">
          <span className="text-[10px] text-slate-500 font-mono">{fe.total_lines}L</span>
          {hasError && <AlertCircle size={13} className="text-rose-400" />}
          {fe.symbols.length > 0 && (
            <span className="text-[10px] text-slate-500 font-mono">
              {fe.symbols.length} symbols
            </span>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-4 py-3 bg-[#0B0F19] space-y-4 border-t border-[#1E293B]">
          {fe.summary ? (
            <GeminiText text={fe.summary} />
          ) : (
            <div className="text-xs text-slate-400 italic">No summary available.</div>
          )}

          {fe.uncertainty && (
            <div className="text-xs text-amber-300 bg-amber-950/20 border border-amber-800/40 rounded p-2.5">
              <strong>Uncertainty:</strong> {fe.uncertainty}
            </div>
          )}

          {fe.symbols.length > 0 && (
            <div>
              <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
                Symbols ({fe.symbols.length})
              </p>
              <div className="space-y-1.5">
                {fe.symbols.map(sym => (
                  <SymbolCard key={sym.name} sym={sym} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main ExplanationView ────────────────────────────────────────────────────
interface ExplanationViewProps {
  explanation: ProjectExplanation | null;
  loading: boolean;
  error: string | null;
  onLoad: () => void;
}

export default function ExplanationView({
  explanation,
  loading,
  error,
  onLoad,
}: ExplanationViewProps) {
  const [search, setSearch] = useState('');
  const [expandAll, setExpandAll] = useState<boolean | undefined>(undefined);

  // Filter files by search term
  const filteredFiles = useMemo(() => {
    if (!explanation?.files) return [];
    if (!search.trim()) return explanation.files;

    const q = search.toLowerCase();
    return explanation.files.filter(
      f =>
        f.path.toLowerCase().includes(q) ||
        f.summary.toLowerCase().includes(q) ||
        f.symbols.some(s => s.name.toLowerCase().includes(q) || s.summary.toLowerCase().includes(q))
    );
  }, [explanation, search]);

  function exportMarkdown() {
    if (!explanation) return;
    let md = `# CodeOracle Intelligence Report\n\n`;
    md += `## Architectural Overview\n\n${explanation.overview || 'N/A'}\n\n`;
    if (explanation.entry_points && explanation.entry_points.length > 0) {
      md += `### Entry Points\n\n${explanation.entry_points.map(e => `- \`${e}\``).join('\n')}\n\n`;
    }
    md += `## File Summaries\n\n`;
    explanation.files.forEach(f => {
      md += `### \`${f.path}\` (${f.language}, ${f.total_lines} lines)\n\n${f.summary}\n\n`;
      if (f.symbols.length > 0) {
        md += `#### Symbols\n\n`;
        f.symbols.forEach(s => {
          md += `- **${s.symbol_type.toUpperCase()} ${s.name}** (Lines ${s.start_line}-${s.end_line}): ${s.summary}\n`;
        });
        md += `\n`;
      }
    });
    downloadFile('codeoracle_explanation_report.md', md, 'text/markdown');
  }

  // Not yet loaded
  if (!explanation && !loading && !error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="text-center space-y-2">
          <div className="h-12 w-12 mx-auto rounded-full bg-cyan-950/40 border border-cyan-800/50 flex items-center justify-center">
            <Sparkles className="h-6 w-6 text-cyan-400" />
          </div>
          <p className="text-slate-200 font-semibold text-sm">
            Generate an AI-powered architectural explanation of this codebase.
          </p>
          <p className="text-slate-500 text-xs font-mono">
            Analyzes hierarchical repository structure, entry points, and symbol semantics.
          </p>
        </div>
        <button
          onClick={onLoad}
          className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white text-xs font-medium px-5 py-2.5 rounded-lg transition-all shadow-lg shadow-cyan-500/20 cursor-pointer"
        >
          <Sparkles className="h-4 w-4" />
          <span>Generate Explanation</span>
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
        <div className="h-8 w-8 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin" />
        <p className="text-sm">Asking Gemini to explain your codebase…</p>
        <p className="text-xs text-slate-500 font-mono">
          Building hierarchical repository, file, and function context.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="flex items-start gap-3 text-rose-300 bg-rose-950/30 border border-rose-800/50 rounded-xl px-5 py-4 max-w-md text-sm">
          <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold mb-1">Explanation failed</p>
            <p className="text-xs text-rose-400/80">{error}</p>
          </div>
        </div>
        <button
          onClick={onLoad}
          className="text-xs text-slate-400 hover:text-white border border-[#1E293B] hover:border-[#2A364F] px-4 py-2 rounded-lg transition-colors cursor-pointer"
        >
          Retry Explanation
        </button>
      </div>
    );
  }

  if (!explanation) return null;

  return (
    <div className="h-full overflow-y-auto px-6 py-5 space-y-6 bg-[#0B0F19]">
      {/* Top Controls: Search, Expand All, Export Markdown */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-2 border-b border-[#1E293B]">
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="flex items-center bg-[#151C2C] border border-[#1E293B] rounded-lg px-3 py-1.5 gap-2 w-full shadow-inner">
            <Search size={13} className="text-slate-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search files and symbols…"
              className="bg-transparent text-xs text-slate-200 outline-none w-full placeholder:text-slate-500 font-mono"
            />
            {search && (
              <button onClick={() => setSearch('')} className="text-slate-400 hover:text-white">
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpandAll(prev => (prev === true ? false : true))}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-[#151C2C] border border-[#1E293B] hover:border-[#2A364F] rounded-lg px-3 py-1.5 transition-colors cursor-pointer font-mono"
          >
            <ChevronsUpDown size={13} />
            <span>{expandAll ? 'Collapse All' : 'Expand All'}</span>
          </button>

          <button
            onClick={exportMarkdown}
            className="flex items-center gap-1.5 text-xs text-cyan-300 hover:text-cyan-200 bg-cyan-950/50 border border-cyan-800/60 hover:border-cyan-700 rounded-lg px-3 py-1.5 transition-colors cursor-pointer font-mono"
          >
            <Download size={13} />
            <span>Export Markdown</span>
          </button>
        </div>
      </div>

      {/* Partial warning */}
      {explanation.partial && (
        <div className="flex items-center gap-2 text-amber-400 text-xs bg-amber-950/20 border border-amber-800/40 rounded-lg px-3 py-2">
          <AlertTriangle size={13} />
          Some files could not be fully explained — results are partial.
        </div>
      )}

      {/* Repository Overview Card */}
      <div className="bg-[#151C2C] border border-[#1E293B] rounded-xl p-5 space-y-3 shadow-lg">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 size={16} className="text-cyan-400" />
          <span className="text-sm font-bold text-white font-mono">Repository Overview</span>
        </div>
        <GeminiText text={explanation.overview || 'N/A'} />

        {explanation.entry_points && explanation.entry_points.length > 0 && (
          <div className="mt-4 pt-3 border-t border-[#1E293B]">
            <p className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
              Primary Entry Points
            </p>
            <div className="flex flex-wrap gap-2">
              {explanation.entry_points.map(ep => (
                <span
                  key={ep}
                  className="text-xs font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-800/50 rounded-lg px-2.5 py-1"
                >
                  ⚡ {ep}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Per-file explanations */}
      {filteredFiles.length > 0 ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-500 uppercase tracking-wider">
            <span>
              File Explanations ({filteredFiles.length}{' '}
              {search ? `of ${explanation.files.length}` : ''})
            </span>
          </div>
          <div className="space-y-2.5">
            {filteredFiles.map(fe => (
              <FileCard key={fe.path} fe={fe} forceOpen={expandAll} />
            ))}
          </div>
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-slate-500 font-mono bg-[#151C2C] border border-[#1E293B] rounded-xl">
          No files match your search query "{search}".
        </div>
      )}
    </div>
  );
}
