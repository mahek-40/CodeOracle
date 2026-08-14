import React, { useCallback, useEffect, useState, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  NodeTypes,
  Handle,
  Position,
  NodeProps,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { GraphData, GraphNode as GNode, GraphEdge as GEdge } from '../services/api';
import {
  FileCode,
  AlertTriangle,
  Search,
  X,
  ArrowRight,
  GitCommit,
} from 'lucide-react';

// --- Custom Node Component ---
const langColor: Record<string, string> = {
  python: '#3B82F6',
  javascript: '#F59E0B',
};

function FileNode({ data }: NodeProps) {
  const color = langColor[data.language] || '#6B7280';
  const isSelected = data.isSelected;
  const isUpstream = data.isUpstream;
  const isDownstream = data.isDownstream;

  let borderColor = `${color}60`;
  let ringStyle = '';

  if (isSelected) {
    borderColor = '#06B6D4';
    ringStyle = 'ring-2 ring-cyan-400 shadow-lg shadow-cyan-500/20';
  } else if (isUpstream) {
    borderColor = '#38BDF8';
    ringStyle = 'ring-2 ring-sky-400/80 shadow-md shadow-sky-500/15';
  } else if (isDownstream) {
    borderColor = '#F59E0B';
    ringStyle = 'ring-2 ring-amber-400/80 shadow-md shadow-amber-500/15';
  }

  return (
    <div
      style={{ borderColor }}
      className={`bg-[#151C2C] border-2 rounded-lg px-3 py-2.5 min-w-[150px] max-w-[220px] cursor-pointer transition-all ${ringStyle}`}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#334155', border: 'none' }}
      />
      <div className="flex items-center gap-2 mb-1.5">
        <FileCode size={13} style={{ color }} className="flex-shrink-0" />
        <span className="text-[11px] font-semibold text-white truncate font-mono leading-tight">
          {data.label}
        </span>
        {data.has_parse_error && (
          <AlertTriangle size={11} className="text-amber-400 flex-shrink-0" />
        )}
      </div>

      <div className="flex items-center justify-between gap-1 mt-1">
        <span
          style={{ background: `${color}20`, color }}
          className="text-[9px] rounded px-1.5 py-0.5 font-mono font-medium uppercase tracking-wide"
        >
          {data.language}
        </span>
        <span className="text-[9px] text-slate-400 font-mono">
          {data.total_lines}L
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#334155', border: 'none' }}
      />
    </div>
  );
}

const nodeTypes: NodeTypes = { file: FileNode };

// --- Topological / Level Layout ---
function layoutNodes(gnodes: GNode[], gedges: GEdge[]): Node[] {
  const idSet = new Set(gnodes.map(n => n.id));
  const depCount: Record<string, number> = {};
  gnodes.forEach(n => {
    depCount[n.id] = 0;
  });
  gedges.forEach(e => {
    if (idSet.has(e.target)) depCount[e.target] = (depCount[e.target] || 0) + 1;
  });

  const levels: Record<string, number> = {};
  const queue = gnodes.filter(n => depCount[n.id] === 0).map(n => n.id);
  queue.forEach(id => {
    levels[id] = 0;
  });

  let i = 0;
  while (i < queue.length) {
    const curr = queue[i++];
    const outEdges = gedges.filter(e => e.source === curr);
    outEdges.forEach(e => {
      if (idSet.has(e.target)) {
        levels[e.target] = Math.max(levels[e.target] || 0, (levels[curr] || 0) + 1);
        queue.push(e.target);
      }
    });
  }
  gnodes.forEach(n => {
    if (!(n.id in levels)) levels[n.id] = 0;
  });

  const byLevel: Record<number, string[]> = {};
  Object.entries(levels).forEach(([id, lv]) => {
    byLevel[lv] = byLevel[lv] || [];
    byLevel[lv].push(id);
  });

  const NODE_W = 240,
    NODE_H = 110;
  const positions: Record<string, { x: number; y: number }> = {};
  Object.entries(byLevel).forEach(([lvStr, ids]) => {
    const lv = Number(lvStr);
    ids.forEach((id, idx) => {
      positions[id] = { x: lv * NODE_W, y: idx * NODE_H };
    });
  });

  return gnodes.map(gn => ({
    id: gn.id,
    type: 'file',
    position: positions[gn.id] || { x: 0, y: 0 },
    data: { ...gn, isSelected: false, isUpstream: false, isDownstream: false },
  }));
}

function toRFEdges(
  gedges: GEdge[],
  selectedId: string | null,
  upstreamIds: Set<string>,
  downstreamIds: Set<string>
): Edge[] {
  return gedges.map(e => {
    const isFocused =
      selectedId &&
      ((e.source === selectedId && upstreamIds.has(e.target)) ||
        (e.target === selectedId && downstreamIds.has(e.source)));

    let stroke = '#334155';
    let strokeWidth = 1.5;
    let animated = e.is_relative;

    if (isFocused) {
      stroke = e.source === selectedId ? '#38BDF8' : '#F59E0B';
      strokeWidth = 2.5;
      animated = true;
    }

    return {
      id: e.id,
      source: e.source,
      target: e.target,
      animated,
      style: { stroke, strokeWidth },
      labelStyle: { fill: '#64748B', fontSize: 10, fontFamily: 'monospace' },
      label: e.module.length < 20 ? e.module : `…${e.module.slice(-15)}`,
    };
  });
}

// --- Detail Side Drawer ---
function NodeDetail({
  node,
  graphData,
  onClose,
  onSelectNode,
}: {
  node: GNode;
  graphData: GraphData;
  onClose: () => void;
  onSelectNode: (id: string) => void;
}) {
  const deps = graphData.dependencies_map[node.id] || [];
  const dependents = graphData.dependents_map[node.id] || [];

  return (
    <div className="w-80 bg-[#151C2C] border border-[#1E293B] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-right-4 duration-200">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1E293B] bg-[#101726]">
        <div className="flex items-center gap-2 truncate">
          <FileCode
            size={14}
            style={{ color: langColor[node.language] || '#94A3B8' }}
          />
          <span className="text-xs font-bold text-white font-mono truncate">
            {node.label}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      <div className="px-4 py-3 space-y-4 overflow-y-auto text-xs font-mono text-slate-300 max-h-[calc(100vh-220px)]">
        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-y-2 bg-[#0B0F19] p-3 rounded-lg border border-[#1E293B]">
          <span className="text-slate-500">Language</span>
          <span className="text-white uppercase">{node.language}</span>

          <span className="text-slate-500">Total Lines</span>
          <span className="text-cyan-400 font-semibold">{node.total_lines}</span>

          <span className="text-slate-500">Functions</span>
          <span className="text-slate-200">{node.num_functions}</span>

          <span className="text-slate-500">Classes</span>
          <span className="text-slate-200">{node.num_classes}</span>

          <span className="text-slate-500">Imports</span>
          <span className="text-slate-200">{node.num_imports}</span>

          <span className="text-slate-500">Exports</span>
          <span className="text-slate-200">{node.num_exports}</span>
        </div>

        {node.has_parse_error && (
          <div className="flex items-center gap-1.5 text-amber-400 bg-amber-950/30 border border-amber-800/40 rounded px-2.5 py-2">
            <AlertTriangle size={13} />
            <span>Parse error detected in this file</span>
          </div>
        )}

        {/* Upstream Dependencies */}
        <div>
          <div className="text-slate-400 mb-1.5 font-semibold flex items-center justify-between">
            <span className="flex items-center gap-1 text-sky-400">
              <ArrowRight size={12} /> Upstream Dependencies
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
              {deps.length}
            </span>
          </div>
          {deps.length === 0 ? (
            <div className="text-slate-600 italic text-[11px]">
              No internal dependencies
            </div>
          ) : (
            <ul className="space-y-1">
              {deps.map(d => (
                <li key={d}>
                  <button
                    onClick={() => onSelectNode(d)}
                    className="w-full text-left text-sky-300 hover:text-sky-200 hover:bg-sky-950/40 px-2 py-1 rounded transition-colors truncate block"
                  >
                    → {d}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Downstream Dependents */}
        <div>
          <div className="text-slate-400 mb-1.5 font-semibold flex items-center justify-between">
            <span className="flex items-center gap-1 text-amber-400">
              <GitCommit size={12} /> Downstream Callers
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
              {dependents.length}
            </span>
          </div>
          {dependents.length === 0 ? (
            <div className="text-slate-600 italic text-[11px]">
              No callers (potential entry point or standalone)
            </div>
          ) : (
            <ul className="space-y-1">
              {dependents.map(d => (
                <li key={d}>
                  <button
                    onClick={() => onSelectNode(d)}
                    className="w-full text-left text-amber-300 hover:text-amber-200 hover:bg-amber-950/40 px-2 py-1 rounded transition-colors truncate block"
                  >
                    ← {d}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Main DependencyGraph Component ---
interface DependencyGraphProps {
  graphData: GraphData;
}

export default function DependencyGraph({ graphData }: DependencyGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [langFilter, setLangFilter] = useState<'all' | 'python' | 'javascript'>('all');

  // Compute upstream dependencies and downstream callers for selected node
  const { upstreamSet, downstreamSet } = useMemo(() => {
    const up = new Set<string>();
    const down = new Set<string>();

    if (selectedNodeId) {
      // Upstream = targets of outgoing edges from selectedNodeId
      const directDeps = graphData.dependencies_map[selectedNodeId] || [];
      directDeps.forEach(d => up.add(d));

      // Downstream = sources of incoming edges to selectedNodeId
      const directCallers = graphData.dependents_map[selectedNodeId] || [];
      directCallers.forEach(c => down.add(c));
    }

    return { upstreamSet: up, downstreamSet: down };
  }, [selectedNodeId, graphData]);

  // Initial layout
  useEffect(() => {
    const initialNodes = layoutNodes(graphData.nodes, graphData.edges);
    setNodes(initialNodes);
    setSelectedNodeId(null);
  }, [graphData, setNodes]);

  // Update edges when selection changes
  useEffect(() => {
    const updatedEdges = toRFEdges(
      graphData.edges,
      selectedNodeId,
      upstreamSet,
      downstreamSet
    );
    setEdges(updatedEdges);
  }, [graphData, selectedNodeId, upstreamSet, downstreamSet, setEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(prev => (prev === node.id ? null : node.id));
  }, []);

  const handleSelectFromDrawer = useCallback((id: string) => {
    setSelectedNodeId(id);
  }, []);

  // Filter nodes based on search and language filter
  const displayedNodes = useMemo(() => {
    return nodes.map(n => {
      const gnode = graphData.nodes.find(gn => gn.id === n.id);
      const matchesSearch =
        !search ||
        n.id.toLowerCase().includes(search.toLowerCase()) ||
        (gnode && gnode.label.toLowerCase().includes(search.toLowerCase()));

      const matchesLang =
        langFilter === 'all' || (gnode && gnode.language === langFilter);

      const isSelected = n.id === selectedNodeId;
      const isUpstream = upstreamSet.has(n.id);
      const isDownstream = downstreamSet.has(n.id);

      const isDimmed =
        (selectedNodeId &&
          !isSelected &&
          !isUpstream &&
          !isDownstream) ||
        !matchesSearch ||
        !matchesLang;

      return {
        ...n,
        style: isDimmed ? { opacity: 0.2 } : { opacity: 1 },
        data: {
          ...n.data,
          isSelected,
          isUpstream,
          isDownstream,
        },
      };
    });
  }, [nodes, search, langFilter, selectedNodeId, upstreamSet, downstreamSet, graphData]);

  const selectedNodeObj = selectedNodeId
    ? graphData.nodes.find(n => n.id === selectedNodeId)
    : null;

  return (
    <div className="relative w-full h-full flex bg-[#0B0F19] overflow-hidden">
      {/* Top Search & Filter Bar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 flex-wrap">
        {/* Search */}
        <div className="flex items-center bg-[#151C2C] border border-[#1E293B] rounded-lg px-3 py-1.5 gap-2 shadow-lg">
          <Search size={13} className="text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filter modules…"
            className="bg-transparent text-xs text-slate-200 outline-none w-36 placeholder:text-slate-500 font-mono"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="text-slate-400 hover:text-white"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Language Filter */}
        <div className="flex bg-[#151C2C] border border-[#1E293B] rounded-lg p-0.5 shadow-lg">
          {(['all', 'python', 'javascript'] as const).map(lang => (
            <button
              key={lang}
              onClick={() => setLangFilter(lang)}
              className={`px-2.5 py-1 rounded text-xs font-mono uppercase transition-colors cursor-pointer ${
                langFilter === lang
                  ? 'bg-cyan-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>

        {/* Stats Chip */}
        <div className="bg-[#151C2C] border border-[#1E293B] rounded-lg px-3 py-1.5 text-xs font-mono text-slate-400 shadow-lg">
          {graphData.total_nodes} nodes · {graphData.total_edges} edges
        </div>

        {/* Selection Indicator */}
        {selectedNodeId && (
          <div className="bg-cyan-950/80 border border-cyan-800 text-cyan-300 text-xs font-mono px-3 py-1.5 rounded-lg flex items-center gap-2 shadow-lg">
            <span>
              Focus: <strong>{selectedNodeId}</strong> ({upstreamSet.size} deps,{' '}
              {downstreamSet.size} callers)
            </span>
            <button
              onClick={() => setSelectedNodeId(null)}
              className="hover:text-white"
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1 w-full h-full">
        <ReactFlow
          nodes={displayedNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          minZoom={0.2}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1E293B" gap={20} />
          <Controls className="bg-[#151C2C] border border-[#1E293B] rounded-lg text-slate-300 fill-slate-300" />
          <MiniMap
            nodeColor={n => langColor[(n.data as any)?.language] || '#334155'}
            maskColor="#0B0F1980"
            className="!bg-[#151C2C] !border-[#1E293B] rounded-lg overflow-hidden shadow-xl"
          />
        </ReactFlow>
      </div>

      {/* Node Detail Side Panel */}
      {selectedNodeObj && (
        <div className="absolute top-3 right-3 z-20">
          <NodeDetail
            node={selectedNodeObj}
            graphData={graphData}
            onClose={() => setSelectedNodeId(null)}
            onSelectNode={handleSelectFromDrawer}
          />
        </div>
      )}
    </div>
  );
}
