# CodeOracle — Design System

## Direction
Futuristic developer-tool dashboard: technical, intelligent, trustworthy and clean. Avoid generic AI landing-page aesthetics and excessive gradients.

## Visual System
- Background: near-black/slate
- Surfaces: dark charcoal
- Accent: electric blue/cyan
- Success: green
- Warning: amber
- Error: red
- Text: white/light gray
- Muted: slate gray

## Typography
- Inter for UI.
- JetBrains Mono for code, paths, metrics and identifiers.
- Compact hierarchy; avoid oversized marketing text.

## Input
Show CodeOracle branding, one-line value proposition, ZIP drag/drop, public GitHub URL input, supported languages and 10k-line limit.

## Processing
Show project name, file/line count and pipeline:
`Ingest → Analyze → Explain → Test → Refactor`
Use real stage status; never fake progress percentages.

## Results
Header: project, languages, lines, coverage, warnings.
Tabs:
1. Explanation
2. Dependency Graph
3. Generated Tests
4. Refactored Code

## Explanation
Repository overview, module/file list, function/class details, source references and uncertainty indicators.

## Dependency Graph
Large interactive canvas, zoom/pan, search/filter, clickable nodes and details panel. Reduce clutter for large graphs.

## Generated Tests
Prominent real coverage metric, Monaco test editor, pass/fail results, execution output, uncovered areas and additional-test action.

## Refactored Code
Split-pane diff: Original | Proposed, changed-file list, breaking-change warnings and severity.

## Components
`UploadZone`, `GithubInput`, `ProjectSummary`, `PipelineStatus`, `MetricCard`, `ExplanationPanel`, `DependencyGraph`, `CodeViewer`, `TestResults`, `CoverageBadge`, `WarningPanel`, `DiffViewer`.

## UX
Every loading state explains what is happening. Every error explains recovery. Never hide warnings. Preserve state between tabs. Avoid unnecessary modals. Keep code readable. Provide keyboard focus states and do not rely on color alone.

## Judge-First
Within 15 seconds the judge should understand what CodeOracle does, what is being analyzed, where the graph is, the actual coverage, and what the refactor changed.
