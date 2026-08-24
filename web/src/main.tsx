import { CSSProperties, FormEvent, Fragment, KeyboardEvent, ReactNode, UIEvent, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Anchor,
  ArrowUpDown,
  Bot,
  CalendarDays,
  Check,
  Building2,
  ChevronDown,
  CloudUpload,
  Copy,
  Database,
  FileSearch,
  FileText,
  Globe,
  Layers,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Mic,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Settings2,
  Send,
  Sparkles,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Users,
  Workflow,
  X,
} from "lucide-react";
import "./styles.css";

type Role = "authority" | "tenant";
type User = { user_id: string; username: string; name: string; role: Role; role_title?: string };
type Corpus = {
  documents: number;
  pending_documents?: number;
  processing_documents?: number;
  quarantined_documents?: number;
  failed_documents?: number;
  pages: number;
  chunks: number;
  vectors: number;
  mean_extraction_quality?: number;
  classification_breakdown?: { name: string; count: number }[];
  strategy_breakdown?: { name: string; count: number }[];
};
type TenantTerminologyItem = { count: number; label: string; definition: string };
type TenantTerminology = {
  mapping_records: TenantTerminologyItem;
  applicant_ids: TenantTerminologyItem;
  tenancy_identifiers: TenantTerminologyItem;
  matched_applicant_profiles: TenantTerminologyItem;
  missing_tenancy_identifiers: TenantTerminologyItem;
  orphan_mapping_records: TenantTerminologyItem;
  lifecycle_records: TenantTerminologyItem;
};
type AuthorityMetrics = {
  total_plot_records: string;
  total_land: { sqm: string; hectares: string };
  approved_land: { sqm: string; hectares: string };
  vacant_land: { sqm: string; hectares: string };
  non_vacant_land: { sqm: string; hectares: string };
  registered_land: { sqm: string; hectares: string };
  plot_status_breakdown: { code?: string | null; name: string; count: number; value: number; color: string }[];
  vacancy_breakdown: { code?: string | null; name: string; count: number; value: number; color: string }[];
  land_occupancy_breakdown: { code?: string | null; name: string; count: number; value: number; color: string }[];
  tenancy_record_count: number;
  tenancy_lifecycle_breakdown: { name: string; count: number; color: string }[];
  tenancy_record_status_breakdown: { name: string; count: number; color: string }[];
  lease_type_breakdown: { name: string; count: number; color: string }[];
  tenant_structure_breakdown: { name: string; count: number; color: string }[];
  billing_periodicity_breakdown: { name: string; count: number; color: string }[];
  allotment_breakdown: { name: string; count: number; color: string }[];
  status_definition_source: string;
  vacancy_definition_source: string;
  land_occupancy_definition_source: string;
  tenancy_definition_source: string;
  tenancy_lifecycle_definition_source: string;
  tenant_terminology: TenantTerminology;
  data_quality: {
    mapping_records: number;
    matched_applicants: number;
    orphan_mappings: number;
    missing_contact_person: number;
    missing_purpose: number;
    missing_plot_links: number;
    missing_start_dates: number;
    missing_end_dates: number;
    historical_start_dates: number;
    invalid_start_dates: number;
  };
};
type Document = {
  filename: string;
  pages: number;
  classification: string;
  quality: number;
  chunks: number;
  state?: "indexed" | "processing" | "pending" | "quarantined" | "failed" | string;
  reason?: string | null;
};
type TenantRecord = {
  tenant_id: string;
  tenancy_id: string;
  tenant_name: string;
  contact_person: string;
  tenancy_type: string;
  purpose: string;
  commencement: string;
  status: string;
};
type TenantFilterOptions = {
  statuses: string[];
  lease_types: string[];
  allotment_statuses: string[];
};
type Source = {
  source_id: string;
  title: string;
  filename: string;
  page: number;
  excerpt: string;
  score: number;
  section_title?: string;
  clause_number?: string;
};
type Message = {
  sender: "user" | "assistant";
  content: string;
  sources?: Source[];
  created_at?: string;
};
type ChatSession = {
  chat_session_id: string;
  title: string;
  updated_at: string;
};
type ConversationContextMenu = {
  session: ChatSession;
  x: number;
  y: number;
};
type CorpusState = Corpus & {
  documents_state: { document_id: string; filename: string; pages: number; chunks: number; embeddings: number; state: string; reason?: string | null; indexed: boolean }[];
  invariants?: {
    indexed_documents_without_pages: number;
    indexed_documents_without_chunks: number;
    indexed_pages_without_chunks: number;
    indexed_chunks_without_embeddings: number;
    indexed_chunks_without_page_or_acl_metadata: number;
    indexed_embeddings_with_wrong_dimension: number;
  };
};
type LocalLlmCatalog = { models: string[]; default_model: string };
type Officer = { principal_id: string; name: string; username: string; role: "DO" | "NO" | "HO"; role_title: string };
type ContextOption = { value: string; label: string; available: boolean };
type BillingRuleOption = { value: string; label: string; factor?: number };
type BillingRateOption = { key: string; label: string };
type BillingRules = {
  defaults: { category: string; target_month: number; structure: string; frequency: string; water_tax_included: boolean };
  months: { value: number; label: string }[];
  categories: BillingRuleOption[];
  frequencies: BillingRuleOption[];
  structures: BillingRuleOption[];
  rates: BillingRateOption[];
  max_forecast_months?: number | null;
};
type BillingTenancy = { tenancy_id: string; customer_id: string };
type BillingFormState = {
  tenancy_id: string;
  customer_id: string;
  present_year: string;
  present_month: string;
  target_year: string;
  target_month: string;
  present_amount: string;
  present_cgst: string;
  present_sgst: string;
  area: string;
  billing_frequency: string;
  bill_type: string;
  structure_type: string;
  rates: Record<string, string>;
};
type TenderFormField = { key: string; label: string; type: "number" | "text"; step?: string; required_for?: string[]; source_note?: string };
type TenderPlot = { id: string; label: string; plot_code: string; area_sqm: string; source_status: string };
type TenderChecklist = { key: string; label: string; source_file: string; prefill_fields?: Record<string, string>; items: { key: string; number: string; label: string; source_answer: string; source_remarks: string; answer?: string }[] };
type TenderConfig = { version: number; source_files: Record<string, string>; form_fields: TenderFormField[]; checklists: { key: string; label: string }[]; statuses: Record<string, string>; workflow_notice: string };
type TenderWorkflow = { id: string; status: string; status_label: string; plot_id: string; plot_label: string; source_snapshot: Record<string, string>; checklist: TenderChecklist; fields: Record<string, string | number>; calculation: Record<string, any>; available_actions: { key: string; label: string }[]; events: { at: string; action: string; from?: string | null; to?: string | null; comment?: string }[] };
type AgendaMessage = { message_id: string; sender_name: string; sender_principal: string; recipient_principal?: string; message_type: "OFFICER" | "AI" | "HANDOFF" | "SYSTEM"; content: string; sources: Source[]; created_at: string };
type Agenda = {
  agenda_id: string;
  code: string;
  title: string;
  state: string;
  editing_version: number;
  current_owner_principal: string;
  current_owner_role: "DO" | "NO" | "HO";
  current_owner_name: string;
  assigned_do_name: string;
  assigned_nodal_name: string;
  assigned_hod_name: string;
  is_read_only: boolean;
  updated_at: string;
  messages?: AgendaMessage[];
  context_capsules?: { capsule_id: string; from_principal: string; to_principal: string; state: string; summary: string; version: number; created_at: string; sources?: Source[] }[];
  versions?: { version: number; draft_text: string; created_by_principal: string; created_at: string }[];
};
const base = import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "";
const SIDEBAR_MIN_WIDTH = 180;
const SIDEBAR_DEFAULT_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 340;
const CONVERSATION_MIN_WIDTH = 220;
const CONVERSATION_DEFAULT_WIDTH = 270;
const CONVERSATION_MAX_WIDTH = 420;
const WORKFLOW_SIDE_MIN_WIDTH = 260;
const WORKFLOW_SIDE_DEFAULT_WIDTH = 320;
const WORKFLOW_SIDE_MAX_WIDTH = 420;
function clampWidth(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
function storedWidth(key: string, fallback: number, min: number, max: number): number {
  const stored = window.localStorage.getItem(key);
  if (stored === null) return fallback;
  const value = Number(stored);
  return Number.isFinite(value) ? clampWidth(value, min, max) : fallback;
}
type SplitterOrientation = "vertical" | "horizontal";
type ResizableSplitterProps = {
  orientation: SplitterOrientation;
  value: number;
  min: number;
  max: number;
  defaultValue: number;
  ariaLabel: string;
  className?: string;
  reverse?: boolean;
  onChange: (value: number) => void;
  onCommit?: (value: number) => void;
};
function ResizableSplitter({
  orientation,
  value,
  min,
  max,
  defaultValue,
  ariaLabel,
  className = "",
  reverse = false,
  onChange,
  onCommit,
}: ResizableSplitterProps) {
  const splitterRef = useRef<HTMLDivElement | null>(null);
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const onCommitRef = useRef(onCommit);
  const dragRef = useRef({ pointerId: -1, startCoordinate: 0, startValue: value, orientation, min, max });
  const [resizing, setResizing] = useState(false);
  valueRef.current = value;
  onChangeRef.current = onChange;
  onCommitRef.current = onCommit;
  useEffect(() => {
    if (!resizing) return;
    const handleMove = (event: PointerEvent) => {
      const drag = dragRef.current;
      if (!event.isPrimary || event.pointerId !== drag.pointerId) return;
      event.preventDefault();
      const coordinate = drag.orientation === "vertical" ? event.clientX : event.clientY;
      const delta = reverse ? drag.startCoordinate - coordinate : coordinate - drag.startCoordinate;
      const next = clampWidth(drag.startValue + delta, drag.min, drag.max);
      if (next === valueRef.current) return;
      valueRef.current = next;
      onChangeRef.current(next);
    };
    const finish = (event: PointerEvent) => {
      const drag = dragRef.current;
      if (drag.pointerId !== -1 && event.pointerId !== drag.pointerId) return;
      const splitter = splitterRef.current;
      if (splitter?.hasPointerCapture(event.pointerId)) splitter.releasePointerCapture(event.pointerId);
      onCommitRef.current?.(valueRef.current);
      dragRef.current.pointerId = -1;
      setResizing(false);
    };
    document.body.classList.add("is-resizing-layout");
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
    return () => {
      document.body.classList.remove("is-resizing-layout");
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
    };
  }, [resizing]);
  const commitValue = (next: number) => {
    const clamped = clampWidth(next, min, max);
    valueRef.current = clamped;
    onChangeRef.current(clamped);
    onCommitRef.current?.(clamped);
  };
  const adjustValue = (delta: number) => commitValue(valueRef.current + delta);
  const classNames = ["layout-splitter", orientation, className].filter(Boolean).join(" ");
  return (
    <div
      className={classNames}
      data-resizing={resizing ? "true" : "false"}
      role="separator"
      aria-label={ariaLabel}
      aria-orientation={orientation}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      title="Drag to resize; double-click to reset"
      tabIndex={0}
      ref={splitterRef}
      onPointerDown={(event) => {
        if (!event.isPrimary || event.button !== 0) return;
        event.preventDefault();
        dragRef.current = {
          pointerId: event.pointerId,
          startCoordinate: orientation === "vertical" ? event.clientX : event.clientY,
          startValue: valueRef.current,
          orientation,
          min,
          max,
        };
        event.currentTarget.setPointerCapture?.(event.pointerId);
        setResizing(true);
      }}
      onDoubleClick={() => commitValue(defaultValue)}
      onKeyDown={(event) => {
        const step = event.shiftKey ? 28 : 10;
        const keyboardDirection = reverse && orientation === "vertical" ? -1 : 1;
        if (orientation === "vertical" && event.key === "ArrowLeft") { event.preventDefault(); adjustValue(-step * keyboardDirection); }
        if (orientation === "vertical" && event.key === "ArrowRight") { event.preventDefault(); adjustValue(step * keyboardDirection); }
        if (orientation === "horizontal" && event.key === "ArrowUp") { event.preventDefault(); adjustValue(-step); }
        if (orientation === "horizontal" && event.key === "ArrowDown") { event.preventDefault(); adjustValue(step); }
        if (event.key === "Home") { event.preventDefault(); commitValue(min); }
        if (event.key === "End") { event.preventDefault(); commitValue(max); }
      }}
    >
      <span aria-hidden="true" />
    </div>
  );
}
function personInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0][0] || "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] || "" : "";
  return `${first}${last}`.toUpperCase();
}
type DataStateTone = "loading" | "empty" | "error";
function DataState({
  tone,
  title,
  detail,
  action,
}: {
  tone: DataStateTone;
  title: string;
  detail?: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div className={`data-state ${tone}`} role={tone === "error" ? "alert" : "status"} aria-live="polite">
      <span className="data-state-icon" aria-hidden="true">{tone === "loading" ? <span className="button-spinner" /> : tone === "error" ? <X /> : <FileText />}</span>
      <div><b>{title}</b>{detail && <p>{detail}</p>}</div>
      {action && <button type="button" onClick={action.onClick}>{action.label}</button>}
    </div>
  );
}
function displayName(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).map((part) => {
    const normalized = part.toLowerCase();
    return normalized.length === 1
      ? normalized.toUpperCase()
      : `${normalized[0].toUpperCase()}${normalized.slice(1)}`;
  }).join(" ");
}
function formatChatTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}
function formatWorkflowTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : `${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })} · ${date.toLocaleDateString([], { month: "short", day: "numeric" })}`;
}
function formatEvidenceCreated(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : `Created ${date.toLocaleDateString([], { month: "short", day: "numeric" })} · ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })}`;
}
function agendaStatusLabel(state: string): string {
  const labels: Record<string, string> = {
    DO_DRAFT: "Draft",
    RETURNED_TO_DO: "Returned for Changes",
    SUBMITTED_TO_NO: "Submitted to Nodal",
    SUBMITTED_TO_HO: "Pending HOD Approval",
    APPROVED: "Approved",
    REJECTED: "Rejected",
  };
  return labels[state] || state.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}
function agendaStatusBucket(state: string): "draft" | "pending" | "approved" {
  if (state === "APPROVED") return "approved";
  if (state === "DO_DRAFT" || state === "RETURNED_TO_DO") return "draft";
  return "pending";
}
function workflowStageIndex(state: string): number {
  if (state === "SUBMITTED_TO_NO") return 1;
  if (state === "SUBMITTED_TO_HO") return 2;
  if (state === "APPROVED") return 3;
  return 0;
}
function workflowStageLabel(state: string): string {
  if (state === "SUBMITTED_TO_NO") return "Nodal Officer";
  if (state === "SUBMITTED_TO_HO") return "HOD";
  if (state === "APPROVED") return "Completed";
  return "Data Entry";
}
function renderInlineMarkdown(value: string): ReactNode[] {
  const tokenPattern = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*\*(.+?)\*\*|__(.+?)__|`([^`]+)`|\*([^*\n]+)\*|_([^_\n]+)_)/g;
  const output: ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let token = 0;
  while ((match = tokenPattern.exec(value))) {
    if (match.index > cursor) output.push(value.slice(cursor, match.index));
    if (match[2] && match[3]) output.push(<a key={`link-${token}`} href={match[3]} target="_blank" rel="noreferrer">{match[2]}</a>);
    else if (match[4] || match[5]) output.push(<strong key={`strong-${token}`}>{match[4] || match[5]}</strong>);
    else if (match[6]) output.push(<code key={`code-${token}`}>{match[6]}</code>);
    else if (match[7] || match[8]) output.push(<em key={`em-${token}`}>{match[7] || match[8]}</em>);
    cursor = match.index + match[0].length;
    token += 1;
  }
  if (cursor < value.length) output.push(value.slice(cursor));
  return output;
}
function tableCells(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}
function isTableDivider(line: string): boolean {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}
function renderMarkdown(content: string): ReactNode {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let index = 0;
  let block = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }
    if (/^\s*```/.test(line)) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) codeLines.push(lines[index++]);
      if (index < lines.length) index += 1;
      blocks.push(<pre key={`code-block-${block++}`}><code>{codeLines.join("\n")}</code></pre>);
      continue;
    }
    const heading = line.match(/^\s*(#{1,3})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      const Heading = `h${heading[1].length}` as "h1" | "h2" | "h3";
      blocks.push(<Heading key={`heading-${block++}`}>{renderInlineMarkdown(heading[2])}</Heading>);
      index += 1;
      continue;
    }
    if (index + 1 < lines.length && line.includes("|") && isTableDivider(lines[index + 1])) {
      const headers = tableCells(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) rows.push(tableCells(lines[index++]));
      blocks.push(<table key={`table-${block++}`}><thead><tr>{headers.map((cell, cellIndex) => <th key={cellIndex}>{renderInlineMarkdown(cell)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{renderInlineMarkdown(row[cellIndex] || "")}</td>)}</tr>)}</tbody></table>);
      continue;
    }
    const unordered = line.match(/^\s*[-*+]\s+(.+)/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)/);
    if (unordered || ordered) {
      const items: string[] = [];
      const orderedList = Boolean(ordered);
      while (index < lines.length) {
        const item = lines[index].match(orderedList ? /^\s*\d+[.)]\s+(.+)/ : /^\s*[-*+]\s+(.+)/);
        if (!item) break;
        items.push(item[1]); index += 1;
      }
      const List = orderedList ? "ol" : "ul";
      blocks.push(<List key={`list-${block++}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{renderInlineMarkdown(item)}</li>)}</List>);
      continue;
    }
    if (/^\s*>\s?/.test(line)) {
      const quoteLines: string[] = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) quoteLines.push(lines[index++].replace(/^\s*>\s?/, ""));
      blocks.push(<blockquote key={`quote-${block++}`}>{quoteLines.map((quoteLine, quoteIndex) => <Fragment key={quoteIndex}>{quoteIndex > 0 && <br/>}{renderInlineMarkdown(quoteLine)}</Fragment>)}</blockquote>);
      continue;
    }
    const paragraph: string[] = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^\s*(#{1,3})\s+/.test(lines[index]) && !/^\s*[-*+]\s+/.test(lines[index]) && !/^\s*\d+[.)]\s+/.test(lines[index]) && !/^\s*>\s?/.test(lines[index])) paragraph.push(lines[index++]);
    blocks.push(<p key={`paragraph-${block++}`}>{paragraph.map((paragraphLine, lineIndex) => <Fragment key={lineIndex}>{lineIndex > 0 && <br/>}{renderInlineMarkdown(paragraphLine)}</Fragment>)}</p>);
  }
  return <div className="markdown-content">{blocks}</div>;
}
function CitationList({ sources }: { sources?: Source[] }) {
  const [preview, setPreview] = useState<Source | null>(null);
  const [showAll, setShowAll] = useState(false);
  if (!sources?.length) return null;
  const visible = showAll ? sources : sources.slice(0, 3);
  const hiddenCount = Math.max(0, sources.length - 3);
  return (
    <section className="citation-list" aria-label="Sources">
      <header><b>Sources</b></header>
      <div className="citation-chips">
        {visible.map((source) => (
          <button type="button" className="citation" key={source.source_id} title={source.excerpt} onClick={() => setPreview(source)}>
            <FileText/><b>{source.title || source.filename}</b><span>· p.{source.page}</span>
          </button>
        ))}
        {!showAll && hiddenCount > 0 && <button type="button" className="citation-more" onClick={() => setShowAll(true)}>+{hiddenCount}</button>}
      </div>
      {preview && <aside className="citation-preview" role="dialog" aria-label={`Source preview: ${preview.title || preview.filename}`}>
        <header><div><b>{preview.title || preview.filename}</b><small>{preview.filename} · page {preview.page}</small></div><button type="button" aria-label="Close source preview" onClick={() => setPreview(null)}><X/></button></header>
        <p>{preview.excerpt || "No excerpt is available for this source."}</p>
      </aside>}
    </section>
  );
}
function formatRelativeConversationTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startYesterday = startToday - 86_400_000;
  const value = date.getTime();
  if (value >= startToday) return formatChatTime(timestamp);
  if (value >= startYesterday) return "Yesterday";
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}
function conversationGroup(timestamp: string): "Today" | "Yesterday" | "This week" | "Older" {
  const date = new Date(timestamp);
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const value = date.getTime();
  if (value >= startToday) return "Today";
  if (value >= startToday - 86_400_000) return "Yesterday";
  if (value >= startToday - 7 * 86_400_000) return "This week";
  return "Older";
}

function BillingForecastModal({ chatSessionId, onClose, onComplete }: { chatSessionId: string | null; onClose: () => void; onComplete: (payload: any) => void }) {
  const today = new Date();
  const [rules, setRules] = useState<BillingRules | null>(null);
  const [tenancies, setTenancies] = useState<BillingTenancy[]>([]);
  const [form, setForm] = useState<BillingFormState>({
    tenancy_id: "", customer_id: "", present_year: String(today.getFullYear()), present_month: String(today.getMonth() + 1),
    target_year: String(today.getFullYear() + 1), target_month: "12", present_amount: "", present_cgst: "", present_sgst: "", area: "",
    billing_frequency: "monthly", bill_type: "general", structure_type: "other", rates: {},
  });
  const [loading, setLoading] = useState(true);
  const [prefilling, setPrefilling] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [billingWarnings, setBillingWarnings] = useState<string[]>([]);
  const [billingRateSources, setBillingRateSources] = useState<Record<string, string>>({});
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([api("/api/v1/billing/rules"), api("/api/v1/billing/tenancies")])
      .then(([loadedRules, loadedTenancies]) => {
        if (cancelled) return;
        const defaults = loadedRules.defaults || {};
        setRules(loadedRules);
        setTenancies(loadedTenancies.options || []);
        setForm((current) => ({
          ...current,
          present_month: String(today.getMonth() + 1),
          target_month: String(defaults.target_month || 12),
          billing_frequency: defaults.frequency || current.billing_frequency,
          bill_type: defaults.category || current.bill_type,
          structure_type: defaults.structure || current.structure_type,
        }));
      })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Billing rules are unavailable."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const setField = (name: keyof BillingFormState, value: string) => setForm((current) => ({ ...current, [name]: value }));
  const setRate = (key: string, value: string) => setForm((current) => ({ ...current, rates: { ...current.rates, [key]: value } }));
  const asNumber = (value: string) => value.trim() === "" ? undefined : Number(value);
  const selectTenancy = async (tenancyId: string) => {
    setField("tenancy_id", tenancyId);
    const option = tenancies.find((item) => item.tenancy_id === tenancyId);
    setForm((current) => ({ ...current, tenancy_id: tenancyId, customer_id: option?.customer_id || current.customer_id }));
    if (!tenancyId) return;
    setPrefilling(true); setError(""); setBillingWarnings([]); setBillingRateSources({}); setResult(null);
    try {
      const prefill = await api(`/api/v1/billing/tenancies/${encodeURIComponent(tenancyId)}/prefill`);
      const fields = prefill.fields || {};
      setForm((current) => ({
        ...current,
        tenancy_id: tenancyId,
        customer_id: String(prefill.customer_id || option?.customer_id || current.customer_id || ""),
        present_year: fields.present_year == null ? current.present_year : String(fields.present_year),
        present_month: fields.present_month == null ? current.present_month : String(fields.present_month),
        target_year: fields.target_year == null ? current.target_year : String(fields.target_year),
        target_month: fields.target_month == null ? current.target_month : String(fields.target_month),
        present_amount: fields.present_amount == null ? current.present_amount : String(fields.present_amount),
        present_cgst: fields.present_cgst == null ? current.present_cgst : String(fields.present_cgst),
        present_sgst: fields.present_sgst == null ? current.present_sgst : String(fields.present_sgst),
        area: fields.area == null ? current.area : String(fields.area),
        billing_frequency: fields.billing_frequency || current.billing_frequency,
        bill_type: fields.bill_type || current.bill_type,
        // An unmatched source structure must not be silently converted to the
        // default formula structure. Let the operator choose an explicit rule.
        structure_type: fields.structure_type == null ? "" : String(fields.structure_type),
        rates: Object.fromEntries(Object.entries(prefill.rates || {}).map(([key, value]) => [key, String(value)])),
      }));
      setBillingWarnings(Array.isArray(prefill.warnings) ? prefill.warnings : []);
      setBillingRateSources(prefill.rate_sources && typeof prefill.rate_sources === "object" ? prefill.rate_sources : {});
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load billing values for this tenancy.");
    } finally { setPrefilling(false); }
  };
  const runPrediction = async () => {
    setRunning(true); setError("");
    try {
      const payload = {
        chat_session_id: chatSessionId,
        tenancy_id: form.tenancy_id || undefined,
        customer_id: form.customer_id,
        present_year: asNumber(form.present_year), present_month: asNumber(form.present_month),
        target_year: asNumber(form.target_year), target_month: asNumber(form.target_month),
        present_amount: asNumber(form.present_amount), present_cgst: asNumber(form.present_cgst), present_sgst: asNumber(form.present_sgst), area: asNumber(form.area),
        billing_frequency: form.billing_frequency, bill_type: form.bill_type, structure_type: form.structure_type,
        rates: Object.fromEntries(Object.entries(form.rates).filter(([, value]) => value.trim() !== "").map(([key, value]) => [key, Number(value)])),
        allocated_rate_keys: Object.keys(form.rates).filter((key) => form.rates[key].trim() !== ""),
      };
      const response = await api("/api/v1/billing/predict", { method: "POST", body: JSON.stringify(payload) });
      setResult(response);
      onComplete(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Billing prediction is unavailable.");
    } finally { setRunning(false); }
  };
  const areaMissing = form.area.trim() === "";
  const structureMissing = form.structure_type.trim() === "";
  const requiredInputMissing = !form.target_year || !form.target_month || !form.present_amount || !form.present_cgst || !form.present_sgst || areaMissing || structureMissing;
  const monthOptions = rules?.months || Array.from({ length: 12 }, (_, index) => ({ value: index + 1, label: new Date(2000, index, 1).toLocaleString([], { month: "long" }) }));
  return <div className="billing-forecast-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !running) onClose(); }}>
    <section className="billing-forecast-dialog" role="dialog" aria-modal="true" aria-labelledby="billing-forecast-title">
      <header className="billing-forecast-header"><div><small>FULL BILLING INPUTS</small><h2 id="billing-forecast-title">Billing Forecast Interface</h2><p>Enter the same inputs used by the prediction model. The completed calculation will be added to this chat.</p></div><button type="button" aria-label="Close billing forecast" onClick={onClose} disabled={running}><X/></button></header>
      {loading ? <div className="billing-forecast-loading" role="status"><span className="button-spinner"/>Loading source billing rules…</div> : <>
        <div className="billing-form-grid billing-form-primary">
          <label className="billing-field billing-span-2"><span>Tenancy ID</span><select value={form.tenancy_id} onChange={(event) => void selectTenancy(event.target.value)} disabled={prefilling || running}><option value="">Select a tenancy ID</option>{tenancies.map((item) => <option value={item.tenancy_id} key={item.tenancy_id}>{item.tenancy_id}{item.customer_id ? ` · customer ${item.customer_id}` : ""}</option>)}</select><small>Select a tenancy to load source-backed billing values.</small></label>
          <label className="billing-field"><span>Present year</span><input type="number" min="2000" max="2200" value={form.present_year} onChange={(event) => setField("present_year", event.target.value)} /></label>
          <label className="billing-field"><span>Present month</span><select value={form.present_month} onChange={(event) => setField("present_month", event.target.value)}>{monthOptions.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
          <label className="billing-field"><span>Target year</span><input type="number" min="2000" max="2200" value={form.target_year} onChange={(event) => setField("target_year", event.target.value)} /></label>
          <label className="billing-field"><span>Target month</span><select value={form.target_month} onChange={(event) => setField("target_month", event.target.value)}>{monthOptions.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
        </div>
        <div className="billing-form-grid billing-form-values">
          <label className="billing-field"><span>Present amount</span><input type="number" min="0" step="0.01" placeholder="INR" value={form.present_amount} onChange={(event) => setField("present_amount", event.target.value)} /></label>
          <label className="billing-field"><span>Present CGST</span><input type="number" min="0" step="0.01" placeholder="INR" value={form.present_cgst} onChange={(event) => setField("present_cgst", event.target.value)} /></label>
          <label className="billing-field"><span>Present SGST</span><input type="number" min="0" step="0.01" placeholder="INR" value={form.present_sgst} onChange={(event) => setField("present_sgst", event.target.value)} /></label>
          <label className={`billing-field${areaMissing ? " billing-field-required" : ""}`}><span>Area <b>(required)</b></span><input type="number" min="0" step="0.01" placeholder="sq. m" value={form.area} onChange={(event) => setField("area", event.target.value)} aria-describedby="billing-area-help" />{areaMissing && <small id="billing-area-help">No area was found in the source record. Enter the plot area in sq. m to continue.</small>}</label>
          <label className="billing-field"><span>Billing frequency</span><select value={form.billing_frequency} onChange={(event) => setField("billing_frequency", event.target.value)}>{(rules?.frequencies || []).map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
          <label className="billing-field"><span>Bill type</span><select value={form.bill_type} onChange={(event) => setField("bill_type", event.target.value)}>{(rules?.categories || []).map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
          <label className={`billing-field${structureMissing ? " billing-field-required" : ""}`}><span>Structure <b>(required)</b></span><select value={form.structure_type} onChange={(event) => setField("structure_type", event.target.value)}><option value="">Select a supported structure</option>{(rules?.structures || []).map((item) => <option value={item.value} key={item.value}>{item.label}{item.factor ? ` · ${item.factor}` : ""}</option>)}</select>{structureMissing && <small>Select the applicable formula structure when the source label is not mapped.</small>}</label>
        </div>
        <details className="billing-rates" open><summary>Formula rates (%)</summary><div className="billing-form-grid billing-rate-grid">{(rules?.rates || []).map((rate) => { const source = billingRateSources[rate.key] || "No target-period source value"; const sourceLabel = source.includes("CSV") ? "Customer override" : source.includes("PostgreSQL") ? "Target-period master" : "Unavailable"; return <label className="billing-field" key={rate.key}><span>{rate.label}</span><input type="number" min="0" step="0.01" title={`Source: ${source}`} aria-label={`${rate.label} rate (${source})`} value={form.rates[rate.key] || ""} onChange={(event) => setRate(rate.key, event.target.value)} /><small className="billing-rate-source">{sourceLabel}</small></label>; })}</div></details>
        {billingWarnings.length > 0 && <section className="billing-forecast-notes" role="status" aria-label="Source data notes"><strong>Source data notes</strong><ul>{billingWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></section>}
        {error && <p className="billing-forecast-error" role="alert">{error}</p>}
        {result?.prediction && <div className="billing-forecast-result" role="status"><b>Forecast added to chat</b><strong>INR {Number(result.prediction.final_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong><small>{result.prediction.formula_schedule || "Model forecast with formula layer"}</small></div>}
        <footer className="billing-forecast-actions"><button type="button" className="billing-cancel" onClick={onClose} disabled={running}>Cancel</button><button type="button" className="billing-run" onClick={() => void runPrediction()} disabled={running || prefilling || requiredInputMissing}>{running ? <><span className="button-spinner"/>Running prediction…</> : "Run prediction and add to chat"}</button></footer>
      </>}
    </section>
  </div>;
}

function TenderPublicationModal({ onClose }: { onClose: () => void }) {
  const [config, setConfig] = useState<TenderConfig | null>(null);
  const [plots, setPlots] = useState<TenderPlot[]>([]);
  const [workflows, setWorkflows] = useState<TenderWorkflow[]>([]);
  const [workflow, setWorkflow] = useState<TenderWorkflow | null>(null);
  const [checklist, setChecklist] = useState<TenderChecklist | null>(null);
  const [plotId, setPlotId] = useState("");
  const [checklistKey, setChecklistKey] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState("");
  const [calculation, setCalculation] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const hydrateWorkflow = (item: TenderWorkflow | null) => {
    setWorkflow(item);
    if (!item) {
      setPlotId(""); setChecklistKey(""); setChecklist(null); setFields({}); setAnswers({}); setCalculation(null); setComment("");
      return;
    }
    setPlotId(item.plot_id);
    setChecklistKey(item.checklist.key);
    setChecklist(item.checklist);
    setFields(Object.fromEntries(Object.entries(item.fields || {}).map(([key, value]) => [key, String(value ?? "")])));
    setAnswers(Object.fromEntries((item.checklist.items || []).map((entry) => [entry.key, entry.answer || ""])));
    setCalculation(item.calculation || null);
    setComment("");
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([api("/api/v1/tender/config"), api("/api/v1/tender/plots"), api("/api/v1/tender/workflows")])
      .then(([loadedConfig, loadedPlots, loadedWorkflows]) => {
        if (cancelled) return;
        setConfig(loadedConfig); setPlots(loadedPlots.plots || []); setWorkflows(loadedWorkflows.workflows || []);
      })
      .catch((reason) => { if (!cancelled) setError(reason instanceof Error ? reason.message : "Tender workflow data is unavailable."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const setField = (key: string, value: string) => setFields((current) => ({ ...current, [key]: value }));
  const selectPlot = async (value: string) => {
    setPlotId(value); setError(""); setNotice("");
    if (!value) return;
    try {
      const detail = await api(`/api/v1/tender/plots/${encodeURIComponent(value)}`);
      setFields((current) => ({ ...current, ...(detail.prefill_fields || {}) }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load the selected plot."); }
  };
  const selectChecklist = async (value: string) => {
    setChecklistKey(value); setError(""); setNotice("");
    if (!value) { setChecklist(null); return; }
    try {
      const loaded = await api(`/api/v1/tender/checklists/${encodeURIComponent(value)}`) as TenderChecklist;
      setChecklist(loaded); setAnswers(Object.fromEntries((loaded.items || []).map((entry) => [entry.key, entry.source_answer || ""])));
      setFields((current) => ({ ...current, ...(loaded.prefill_fields || {}) }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load the LAC checklist."); }
  };
  const calculate = async () => {
    setWorking(true); setError(""); setNotice("");
    try { const result = await api("/api/v1/tender/calculate", { method: "POST", body: JSON.stringify({ fields }) }); setCalculation(result); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to calculate the approved financial inputs."); }
    finally { setWorking(false); }
  };
  const createRecord = async () => {
    if (!plotId || !checklistKey) throw new Error("Select an eligible vacant plot and an LAC checklist first.");
    const result = await api("/api/v1/tender/workflows", { method: "POST", body: JSON.stringify({ plot_id: plotId, checklist_key: checklistKey, fields, checklist_answers: answers }) });
    const created = result.workflow as TenderWorkflow;
    setWorkflow(created); setCalculation(created.calculation || null); setWorkflows((current) => [created, ...current]);
    return created;
  };
  const runAction = async (action: { key: string; label: string }) => {
    setWorking(true); setError(""); setNotice("");
    try {
      let current = workflow;
      if (!current) current = await createRecord();
      const result = await api(`/api/v1/tender/workflows/${encodeURIComponent(current.id)}/actions`, { method: "POST", body: JSON.stringify({ action: action.key, fields, checklist_answers: answers, comment }) });
      const updated = result.workflow as TenderWorkflow;
      setWorkflow(updated); setCalculation(updated.calculation || null); setWorkflows((items) => items.map((item) => item.id === updated.id ? updated : item)); setComment(""); setNotice(`${action.label} completed.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Tender workflow action failed."); }
    finally { setWorking(false); }
  };
  const downloadDocument = async (kind: string) => {
    if (!workflow) return;
    setWorking(true); setError("");
    try {
      const response = await fetch(`${base}/api/v1/tender/workflows/${encodeURIComponent(workflow.id)}/documents/${kind}`, { credentials: "include" });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || "Document download failed."); }
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `${kind}-${workflow.id}.pdf`; link.click(); URL.revokeObjectURL(url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Document download failed."); }
    finally { setWorking(false); }
  };

  const requiredFor = (field: TenderFormField) => field.required_for?.some((item) => ["calculate", "submit_lac", "generate_board_note", "generate_tender"].includes(item));
  return <div className="tender-workflow-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !working) onClose(); }}>
    <section className="tender-workflow-dialog" role="dialog" aria-modal="true" aria-labelledby="tender-workflow-title">
      <header className="tender-workflow-header"><div><small>SOURCE-BACKED WORKFLOW</small><h2 id="tender-workflow-title">Tender Publication Workflow</h2><p>Select an eligible vacant plot, complete the LAC evidence, and enter only approved commercial inputs. Missing approvals are never inferred.</p></div><button type="button" aria-label="Close tender workflow" onClick={onClose} disabled={working}><X/></button></header>
      {loading ? <div className="tender-workflow-loading" role="status"><span className="button-spinner"/>Loading source-backed tender data…</div> : <>
        <div className="tender-workflow-toolbar"><label><span>Open saved workflow</span><select value={workflow?.id || ""} onChange={(event) => hydrateWorkflow(workflows.find((item) => item.id === event.target.value) || null)}><option value="">Start a new tender workflow</option>{workflows.map((item) => <option value={item.id} key={item.id}>{item.plot_label} · {item.status_label}</option>)}</select></label><button type="button" onClick={() => hydrateWorkflow(null)} disabled={working}>New workflow</button></div>
        <div className="tender-workflow-source-row"><label><span>Eligible vacant plot</span><select value={plotId} onChange={(event) => void selectPlot(event.target.value)} disabled={working || Boolean(workflow)}><option value="">Select a vacant plot</option>{plots.map((plot) => <option value={plot.id} key={plot.id}>{plot.label}</option>)}</select><small>Source: tender plot export; selection is limited to records marked vacant.</small></label><label><span>LAC checklist</span><select value={checklistKey} onChange={(event) => void selectChecklist(event.target.value)} disabled={working || Boolean(workflow)}><option value="">Select an LAC checklist</option>{(config?.checklists || []).map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}</select><small>{checklist?.source_file || "Checklist evidence is loaded from the copied source files."}</small></label></div>
        <section className="tender-proposal-card"><header><div><h3>Proposal and approved financial inputs</h3><p>Blank values remain blank until an authorised source provides them.</p></div>{workflow && <span className="tender-status-chip">{workflow.status_label}</span>}</header><div className="tender-form-grid">{(config?.form_fields || []).map((field) => <label className="tender-field" key={field.key}><span>{field.label}{requiredFor(field) && <b> (required)</b>}</span><input type={field.type} step={field.step} min={field.type === "number" ? "0" : undefined} value={fields[field.key] || ""} onChange={(event) => setField(field.key, event.target.value)} disabled={working} /><small>{field.source_note || "Enter the approved case value."}</small></label>)}</div></section>
        {checklist && <details className="tender-checklist" open><summary>LAC evidence checklist ({checklist.items.length} items)</summary><div className="tender-checklist-scroll">{checklist.items.map((item) => <label key={item.key}><span><b>{item.number}.</b> {item.label}</span><textarea rows={2} value={answers[item.key] || ""} onChange={(event) => setAnswers((current) => ({ ...current, [item.key]: event.target.value }))} disabled={working}/>{item.source_remarks && <small>Source remark: {item.source_remarks}</small>}</label>)}</div></details>}
        {calculation && <section className={`tender-calculation ${calculation.ready ? "ready" : "pending"}`}><header><h3>Financial calculation</h3><button type="button" onClick={() => void calculate()} disabled={working || !plotId}>{working ? "Calculating…" : "Calculate"}</button></header>{calculation.ready ? <div className="tender-calculation-grid"><span>Developed area<strong>{Number(calculation.developed_area_sqm).toLocaleString(undefined, { maximumFractionDigits: 2 })} sq. m</strong></span><span>Base annual rent<strong>INR {Number(calculation.base_annual_rent).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></span><span>Upfront premium incl. GST<strong>INR {Number(calculation.upfront_premium_including_gst).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></span></div> : <p>Complete: {(calculation.missing_fields || []).join(", ") || "approved financial inputs"}.</p>}</section>}
        {workflow?.source_snapshot && <details className="tender-source-snapshot"><summary>Source snapshot</summary><div>{Object.entries(workflow.source_snapshot).filter(([, value]) => value !== "").slice(0, 12).map(([key, value]) => <span key={key}><b>{key.replaceAll("_", " ")}</b>{value}</span>)}</div></details>}
        {error && <p className="tender-workflow-error" role="alert">{error}</p>}{notice && <p className="tender-workflow-notice" role="status">{notice}</p>}
        <footer className="tender-workflow-actions"><div className="tender-document-actions">{workflow && ["lac", "board-note", "tender"].map((kind) => <button type="button" key={kind} onClick={() => void downloadDocument(kind)} disabled={working}>Download {kind === "board-note" ? "Board Note" : kind.toUpperCase()}</button>)}</div><label className="tender-comment"><span>Action comment</span><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Required when returning a draft for clarification" disabled={working}/></label><div className="tender-transition-actions">{workflow?.available_actions?.map((action) => <button type="button" key={action.key} className={action.key.includes("return") ? "secondary-action" : "primary-action"} disabled={working || (action.key.includes("return") && !comment.trim())} onClick={() => void runAction(action)}>{working && <span className="button-spinner"/>}{action.label}</button>)}{!workflow && <button type="button" className="primary-action" disabled={working || !plotId || !checklistKey} onClick={() => void runAction({ key: "save_draft", label: "Save LAC draft" })}>{working ? "Saving…" : "Create LAC draft"}</button>}</div></footer>
        <small className="tender-workflow-notice-text">{config?.workflow_notice}</small>
      </>}
    </section>
  </div>;
}

const assistantSuggestions = [
  "Summarize lease policy",
  "Explain lease transfer",
  "Show breach rules",
];
const assistantContextOptions: ContextOption[] = [
  { value: "all", label: "All contexts & documents", available: true },
  { value: "billing", label: "Billing Forecast", available: true },
  { value: "tender", label: "Tender Publication Workflow", available: true },
  { value: "board-note", label: "Board Note", available: true },
  { value: "breach", label: "Breach (unavailable)", available: false },
  { value: "chairman-note", label: "Chairman Note (unavailable)", available: false },
  { value: "letter", label: "Letter (unavailable)", available: false },
  { value: "rti", label: "RTI (unavailable)", available: false },
  { value: "sor", label: "SOR (unavailable)", available: false },
  { value: "suit", label: "Suit (unavailable)", available: false },
  { value: "tender-draft", label: "Tender Draft (unavailable)", available: false },
];
function go(path: string) {
  history.pushState({}, "", path);
  dispatchEvent(new Event("popstate"));
}
async function api(path: string, init?: RequestInit): Promise<any> {
  const res = await fetch(base + path, {
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item: any) => item.msg || "Invalid input.").join(" ")
      : body.detail;
    throw new Error(detail || "Request failed.");
  }
  return body;
}

function App() {
  const [path, setPath] = useState(location.pathname);
  const [user, setUser] = useState<User | null>(null);
  const [setup, setSetup] = useState<boolean | null>(null);
  useEffect(() => {
    const change = () => setPath(location.pathname);
    addEventListener("popstate", change);
    api("/api/v1/auth/bootstrap-status")
      .then((x) => setSetup(x.setup_required))
      .catch(() => setSetup(null));
    api("/api/v1/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
    return () => removeEventListener("popstate", change);
  }, []);
  if (setup === null)
    return <div className="loading">Connecting to Port Management System…</div>;
  if (setup && path === "/setup")
    return (
      <Setup
        done={(u) => {
          setUser(u);
          setSetup(false);
          go(
            u.role === "authority"
              ? "/authority/dashboard"
              : "/tenant/dashboard",
          );
        }}
      />
    );
  if (setup && path !== "/")
    return (
      <Login
        initialSetup
        role={path.startsWith("/tenant") ? "tenant" : "authority"}
        done={(u) => {
          setUser(u);
          go(
            u.role === "authority"
              ? "/authority/dashboard"
              : "/tenant/dashboard",
          );
        }}
      />
    );
  if (setup) return <Home initialSetup />;
  if (!user && path === "/") return <Home />;
  if (!user)
    return (
      <Login
        role={path.startsWith("/tenant") ? "tenant" : "authority"}
        done={(u) => {
          setUser(u);
          go(
            u.role === "authority"
              ? "/authority/dashboard"
              : "/tenant/dashboard",
          );
        }}
      />
    );
  return (
    <Dashboard
      user={user}
      path={path}
      logout={async () => {
        await api("/api/v1/auth/logout", { method: "POST" }).catch(() => {});
        setUser(null);
        go("/");
      }}
    />
  );
}

function GovHeader() {
  return (
    <header className="gov-header">
      <div className="tricolor" />
      <div className="gov-top">
        <div />
        <div>
          <Globe size={13} />
          <select aria-label="Language">
            <option>English</option>
          </select>
        </div>
      </div>
      <div className="gov-main">
        <button className="identity" onClick={() => go("/")}>
          <span>PMS</span>
          <div>
            <small>PORT AUTHORITY</small>
            <b>Port Management System</b>
          </div>
        </button>
        <nav>
          <button
            className={location.pathname === "/" ? "active" : ""}
            onClick={() => go("/")}
          >
            Home
          </button>
          <button>About</button>
          <button>Contact</button>
          <button>Help</button>
        </nav>
      </div>
    </header>
  );
}
function Footer() {
  return (
    <footer className="footer">
      <div>
        <section>
          <b title="Port Management System">Port Management System</b>
          <p>
            An enterprise platform for port document intelligence and
            governance.
          </p>
        </section>
        <section>
          <b>Quick Links</b>
          <p>Document Library</p>
          <p>AI Assistant</p>
          <p>About</p>
        </section>
        <section>
          <b>Legal</b>
          <p>Disclaimer</p>
          <p>Privacy Policy</p>
          <p>Terms of Use</p>
          <p>Accessibility</p>
       </section>
      </div>
    </footer>
  );
}
function Home({ initialSetup = false }: { initialSetup?: boolean }) {
  const cards = [
    [
      <Bot />,
      "AI Chat Assistant",
      "Ask questions across indexed policy documents with cited source pages.",
    ],
    [
      <Users />,
      "Tenant Services",
      "Access the document library and evidence-based AI support.",
    ],
    [
      <LayoutDashboard />,
      "Authority Dashboard",
      "Review corpus health and document extraction status.",
    ],
    [
      <FileSearch />,
      "Policy Repository",
      "Search the local PDF corpus using semantic and keyword retrieval.",
    ],
  ];
  const [corpus, setCorpus] = useState<Corpus | null>(null);
  useEffect(() => {
    api("/api/v1/public/corpus")
      .then(setCorpus)
      .catch(() => {});
  }, []);
  const portal = initialSetup ? "/setup" : "/tenant/login";
  const authority = initialSetup ? "/setup" : "/authority/login";
  return (
    <div className="public">
      <GovHeader />
      <section className="home-hero">
        <div>
          <em>● AI Powered</em>
          <h1>AI Powered Port Document Intelligence Assistant</h1>
          <p>
            Secure intelligent assistant for searching indexed port policy
            documents, circulars, tariffs, procedures and acts with Hybrid RAG
            and page-anchored evidence.
          </p>
          <aside>
            <button onClick={() => go(portal)}>
              {initialSetup ? "Create portal account" : "Tenant Portal"}{" "}
              <span>→</span>
            </button>
            <button onClick={() => go(authority)}>
              {initialSetup ? "Initial secure setup" : "Authority Portal"}
            </button>
          </aside>
          <div className="home-stats">
            <article>
              <b>{corpus?.documents ?? "—"}</b>
              <small>Indexed PDFs</small>
            </article>
            <article>
              <b>{corpus?.pages ?? "—"}</b>
              <small>Source Pages</small>
            </article>
          </div>
        </div>
      </section>
      <section className="feature-section">
        <small>PLATFORM MODULES</small>
        <h2>One secure system for port document governance</h2>
        <p>Purpose-built for port authorities, tenants and policy officers.</p>
        <div>
          {cards.map(([icon, title, body], i) => (
            <article key={i}>
              <span>{icon}</span>
              <b>{title}</b>
              <p>{body}</p>
              <i />
            </article>
          ))}
        </div>
      </section>
      <Footer />
    </div>
  );
}

function Setup({ done }: { done: (u: User) => void }) {
  const [form, setForm] = useState({
    display_name: "",
    username: "",
    password: "",
    role: "authority" as Role,
  });
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      done(
        await api("/api/v1/auth/bootstrap", {
          method: "POST",
          body: JSON.stringify(form),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed");
    }
  }
  return (
    <div className="public">
      <GovHeader />
      <main className="login-page">
        <form className="portal-login setup-login" onSubmit={submit}>
          <div className="login-title">
            <span>
              <ShieldCheck />
            </span>
            <div>
              <h1>Initial Portal Account</h1>
              <p>
                <i>●</i> First-use local setup
              </p>
            </div>
          </div>
          <label>
            Display name
            <input
              required
              value={form.display_name}
              onChange={(e) =>
                setForm({ ...form, display_name: e.target.value })
              }
            />
          </label>
          <label>
            Portal role
            <select
              value={form.role}
              onChange={(e) =>
                setForm({ ...form, role: e.target.value as Role })
              }
            >
              <option value="authority">Authority officer</option>
              <option value="tenant">Tenant</option>
            </select>
          </label>
          <label>
            Username
            <input
              required
              minLength={3}
              placeholder="Enter username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </label>
          <label>
            Password
            <input
              required
              minLength={12}
              type="password"
              placeholder="Minimum 12 characters"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button>
            <ShieldCheck />
            Create secure account
          </button>
        </form>
      </main>
      <Footer />
    </div>
  );
}
function Login({
  role,
  done,
  initialSetup = false,
}: {
  role: Role;
  done: (u: User) => void;
  initialSetup?: boolean;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      done(
        await api(
          role === "authority"
            ? "/api/authority/login"
            : "/tenant/api/auth/login",
          { method: "POST", body: JSON.stringify({ username, password }) },
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid credentials.");
    }
  }
  const authority = role === "authority";
  return (
    <div className="public">
      <GovHeader />
      <main className="login-page">
        <form className="portal-login" onSubmit={submit}>
          <div className="login-title">
            <span>{authority ? <Building2 /> : <Anchor />}</span>
            <div>
              <h1>{authority ? "Authority Portal" : "Tenant Portal Login"}</h1>
              <p>
                <i>●</i>{" "}
                {authority
                  ? "Restricted access — Officers only"
                  : "Secure document access"}
              </p>
            </div>
          </div>
          <label>
            Username
            <input
              required
              placeholder={
                authority
                  ? "Enter Officer Username (e.g. do_ND_satya)"
                  : "Enter tenant username"
              }
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              required
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button>
            <ShieldCheck />
            {authority ? "Sign in Securely" : "Secure Login"}
          </button>
          <p className="login-switch">
            {initialSetup ? (
              <>
                First use?{" "}
                <a onClick={() => go("/setup")}>
                  Create initial portal account
                </a>
              </>
            ) : authority ? (
              <>
                Not a Port Officer?{" "}
                <a onClick={() => go("/tenant/login")}>
                  Go to Tenant Login Portal
                </a>
              </>
            ) : (
              <>
                Port authority officer?{" "}
                <a onClick={() => go("/authority/login")}>
                  Go to Authority Portal
                </a>
              </>
            )}
          </p>
        </form>
      </main>
      <Footer />
    </div>
  );
}

function Dashboard({
  user,
  path,
  logout,
}: {
  user: User;
  path: string;
  logout: () => void;
}) {
  const [menu, setMenu] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    return storedWidth("portproject.sidebar-width", SIDEBAR_DEFAULT_WIDTH, SIDEBAR_MIN_WIDTH, SIDEBAR_MAX_WIDTH);
  });
  const sidebarWidthRef = useRef(sidebarWidth);
  const [headerCorpus, setHeaderCorpus] = useState<CorpusState | null>(null);
  const [showCorpusStatus, setShowCorpusStatus] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const tab = path.includes("documents")
    ? "documents"
    : path.includes("ai")
      ? "ai"
      : "overview";
  const authority = user.role === "authority";
  const target = (x: string) =>
    go(authority ? `/authority/${x}` : `/tenant/${x}`);
  const updateSidebarWidth = (value: number, persist = false) => {
    const width = clampWidth(value, SIDEBAR_MIN_WIDTH, SIDEBAR_MAX_WIDTH);
    sidebarWidthRef.current = width;
    setSidebarWidth(width);
    if (persist) window.localStorage.setItem("portproject.sidebar-width", String(width));
  };
  const adjustSidebarWidth = (delta: number) => {
    updateSidebarWidth(sidebarWidthRef.current + delta, true);
  };
  useEffect(() => {
    setShowProfileMenu(false);
    setShowCorpusStatus(false);
    let cancelled = false;
    api("/api/v1/corpus/state")
      .then((state) => { if (!cancelled) setHeaderCorpus(state); })
      .catch(() => { if (!cancelled) setHeaderCorpus(null); });
    return () => { cancelled = true; };
  }, [tab]);
  const pendingDocuments = headerCorpus?.pending_documents || 0;
  const corpusAttention = !headerCorpus ? null : [
    { key: "failed_documents", tone: "failed", label: "failed" },
    { key: "quarantined_documents", tone: "quarantined", label: "quarantined" },
    { key: "processing_documents", tone: "processing", label: "processing" },
    { key: "pending_documents", tone: "pending", label: "pending" },
  ].map((item) => ({ ...item, count: Number(headerCorpus[item.key as keyof Corpus] || 0) })).find((item) => item.count > 0);
  const corpusStatusTone = !headerCorpus ? "unavailable" : corpusAttention?.tone || "ready";
  const corpusStatusLabel = !headerCorpus
    ? "Documents unavailable"
    : corpusAttention
      ? `Documents · ${corpusAttention.count} ${corpusAttention.label}`
      : `Documents ready · ${headerCorpus.documents}`;
  return (
    <div className={`${tab === "ai" ? "app-shell ai-shell" : "app-shell"} reference-shell${authority ? " authority-shell" : " tenant-shell"}`} style={{ "--sidebar-width": `${sidebarWidth}px` } as CSSProperties}>
      <aside className={menu ? "app-sidebar open" : "app-sidebar"}>
        <div className="side-logo">
          <Anchor />
          <b>Port Management System</b>
          <button aria-label="Close navigation menu" onClick={() => setMenu(false)}>
            <X />
          </button>
        </div>
        <nav>
          <button
            className={tab === "overview" ? "chosen" : ""}
            onClick={() => target("dashboard")}
          >
            <LayoutDashboard />
            <span>Dashboard</span>
          </button>
          <button
            className={tab === "documents" ? "chosen" : ""}
            onClick={() => target("documents")}
          >
            <Users />
            <span>{authority ? "Tenants" : "Document Library"}</span>
          </button>
          <button
            className={tab === "ai" ? "chosen" : ""}
            onClick={() => target(authority ? "ai-chat" : "ai-support")}
          >
            <Bot />
            <span>AI Assistant</span>
          </button>
        </nav>
        <div className="side-account-actions">
          <span className="profile-avatar side-profile-avatar" aria-label={user.name} title={displayName(user.name)}>{personInitials(user.name)}</span>
          <button className="side-logout" onClick={logout}>
            <LogOut />
            Logout
          </button>
        </div>
        <ResizableSplitter
          orientation="vertical"
          value={sidebarWidth}
          min={SIDEBAR_MIN_WIDTH}
          max={SIDEBAR_MAX_WIDTH}
          defaultValue={SIDEBAR_DEFAULT_WIDTH}
          ariaLabel="Resize navigation sidebar"
          className="shell-splitter"
          onChange={updateSidebarWidth}
          onCommit={(value) => updateSidebarWidth(value, true)}
        />
      </aside>
      <section className="app-content">
        <header className="app-top">
          <button className="menu" aria-label="Open navigation menu" onClick={() => setMenu(true)}>
            <Menu />
          </button>
          {tab === "ai" ? (
            <div className="page-shell-title ai-page-title">
              <h1>AI Assistant &amp; Workflow</h1>
              <p>Ask trusted-document questions and manage official agendas</p>
            </div>
          ) : tab === "overview" ? (
            <div className="page-shell-title dashboard-page-title">
              <h1>Dashboard</h1>
              <p>Land and applicant-property overview</p>
            </div>
          ) : (
            <div className="page-shell-title tenant-page-title">
              <h1>{authority ? "Tenants" : "Document Library"}</h1>
              <p>{authority ? "Search and review applicant-property mapping records" : "Browse indexed port documents and extraction status"}</p>
            </div>
          )}
          <div className="app-top-right">
            <div className={`corpus-status-control ${corpusStatusTone}`}>
              <button type="button" className="corpus-status-button" aria-expanded={showCorpusStatus} onClick={() => setShowCorpusStatus((value) => !value)}><ShieldCheck/><span>{corpusStatusLabel}</span><ChevronDown/></button>
              {showCorpusStatus && <section className="corpus-status-popover" role="dialog" aria-label="Document corpus status">
                <header><div><b>Document corpus</b><small>{corpusStatusTone === "ready" ? "Answers are grounded in indexed documents." : corpusStatusTone === "quarantined" ? "Some documents need extraction review." : corpusStatusTone === "failed" ? "Some documents failed processing." : corpusStatusTone === "processing" ? "Some documents are still processing." : corpusStatusTone === "pending" ? "Some documents are awaiting processing." : "Document status is unavailable."}</small></div><button type="button" aria-label="Close document status" onClick={() => setShowCorpusStatus(false)}><X/></button></header>
                {headerCorpus ? <dl><div><dt>Indexed</dt><dd>{headerCorpus.documents.toLocaleString()}</dd></div><div><dt>Chunks</dt><dd>{headerCorpus.chunks.toLocaleString()}</dd></div><div><dt>Embeddings</dt><dd>{headerCorpus.vectors.toLocaleString()}</dd></div><div><dt>Processing</dt><dd>{(headerCorpus.processing_documents || 0).toLocaleString()}</dd></div><div><dt>Pending</dt><dd>{pendingDocuments.toLocaleString()}</dd></div><div><dt>Quarantined</dt><dd>{(headerCorpus.quarantined_documents || 0).toLocaleString()}</dd></div><div><dt>Failed</dt><dd>{(headerCorpus.failed_documents || 0).toLocaleString()}</dd></div></dl> : <p className="corpus-status-empty">Unable to load live document status.</p>}
                <button type="button" className="corpus-manage-button" onClick={() => { setShowCorpusStatus(false); target("documents"); }}><CloudUpload/>Manage documents</button>
              </section>}
            </div>
            <div className="app-top-user">
              <button
                type="button"
                className="profile-trigger"
                aria-haspopup="menu"
                aria-expanded={showProfileMenu}
                onClick={() => setShowProfileMenu((value) => !value)}
              >
                <span className="profile-copy"><b>{displayName(user.name)}</b><small>{user.role_title || (authority ? "Authority Officer" : "Data Entry Operator")}</small></span>
                <span className="profile-secure-dot" title="Secure session" aria-label="Secure session" />
                <ChevronDown aria-hidden="true" />
              </button>
              {showProfileMenu && <div className="profile-menu" role="menu">
                <div className="profile-menu-heading"><b>{displayName(user.name)}</b><small>{user.role_title || (authority ? "Authority Officer" : "Data Entry Operator")}</small></div>
                <div className="profile-menu-secure"><span className="profile-secure-dot" aria-hidden="true" />Secure session</div>
                <div className="profile-menu-divider" />
                <button type="button" role="menuitem" onClick={() => { setShowProfileMenu(false); logout(); }}><LogOut />Logout</button>
              </div>}
            </div>
          </div>
        </header>
        <main id="main-content" className={`page-content page-${tab}`}>
          {tab === "overview" ? (
            <Overview authority={authority} />
          ) : tab === "documents" ? (
            <Documents authority={authority} />
          ) : (
            <Assistant user={user} />
          )}
        </main>
      </section>
    </div>
  );
}
function Overview({ authority }: { authority: boolean }) {
  const [data, setData] = useState<AuthorityMetrics | null>(null);
  const [corpus, setCorpus] = useState<Corpus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const request = authority ? api("/api/authority/dashboard/metrics").then((value) => { if (!cancelled) setData(value); }) : api("/api/v1/corpus").then((value) => { if (!cancelled) setCorpus(value); });
    request.catch(() => { if (!cancelled) setError(authority ? "Unable to load land metrics." : "Unable to load document metrics."); }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [authority, reloadKey]);
  if (!authority) {
    if (loading) return <section className="data-state-page"><DataState tone="loading" title="Loading document metrics" detail="Retrieving the current indexed corpus." /></section>;
    if (error || !corpus) return <section className="data-state-page"><DataState tone="error" title="Unable to load document metrics." detail="The document summary could not be retrieved. Try again." action={{ label: "Retry", onClick: () => setReloadKey((value) => value + 1) }} /></section>;
    const cards = [
      [
        "INDEXED PDFs",
        corpus?.documents,
        "Live document records",
        <FileText />,
      ],
      [
        "SOURCE PAGES",
        corpus?.pages,
        "Extracted from indexed PDFs",
        <Layers />,
      ],
      [
        "SEARCHABLE CHUNKS",
        corpus?.chunks,
        "Hybrid retrieval passages",
        <Database />,
      ],
      [
        "PGVECTOR EMBEDDINGS",
        corpus?.vectors,
        "Configured dense vectors",
        <Database />,
      ],
    ];
    return <>
      <section className="page-intro compact-intro"><div><span className="eyebrow">Document intelligence</span><h2>Corpus overview</h2><p>Current ingestion and retrieval capacity for your authenticated document workspace.</p></div></section>
      <section className="kpis tenant-kpis">
        {cards.map(([label, value, sub, icon], i) => (
          <article key={i}>
            <div><small>{label}</small><span>{icon}</span></div><b>{value ?? "—"}</b><p>{sub}</p>
          </article>
        ))}
      </section>
    </>;
  }
  if (loading) return <section className="data-state-page"><DataState tone="loading" title="Loading land metrics" detail="Retrieving live operational metrics from the PMS database." /></section>;
  if (error || !data) return <section className="data-state-page"><DataState tone="error" title="Unable to load land metrics." detail="The dashboard metrics could not be retrieved. Try again." action={{ label: "Retry", onClick: () => setReloadKey((value) => value + 1) }} /></section>;
  const kpis = [
    [
      "TOTAL PLOT RECORDS",
      data?.total_plot_records,
      "From public.plot",
      <Layers />,
    ],
    [
      "TOTAL LAND AREA",
      data?.total_land.sqm,
      `Equivalent to ${data?.total_land.hectares ?? "—"}`,
      <Layers />,
    ],
    [
      "APPROVED LAND (A)",
      data?.approved_land.sqm,
      `${data?.approved_land.hectares ?? "—"} · public.plot.status`,
      <Building2 />,
    ],
    [
      "VACANT LAND (is_vacant)",
      data?.vacant_land.sqm,
      `${data?.vacant_land.hectares ?? "—"} · explicit vacancy flag`,
      <Layers />,
    ],
    [
      "REGISTERED LAND (RG - REGISTERED)",
      data?.registered_land.sqm,
      `${data?.registered_land.hectares ?? "—"} · public.plot.status`,
      <FileSearch />,
    ],
  ];
  return (
    <>
      <section className="page-intro dashboard-intro"><div><span className="eyebrow">Authority operations</span><h2>Land and applicant-property overview</h2><p>Live distribution across plot status, explicit vacancy, and applicant-property mapping records.</p></div><span className="data-note">Updated from PMS database</span></section>
      <section className="kpis">
        {kpis.map(([label, value, sub, icon], i) => (
          <article key={i}>
            <div>
              <small>{label}</small>
              <span>{icon}</span>
            </div>
            <b>{value ?? "—"}</b>
            <p>{sub}</p>
          </article>
        ))}
      </section>
      <section className="charts">
        <Chart
          title="Plot status distribution"
          subtitle={`${data?.total_plot_records ?? "—"} · labels from public.m_property_status`}
          entries={data?.plot_status_breakdown ?? []}
        />
        <Donut
          title="Plot status and vacancy classification"
          subtitle="Source-derived view: status RG first, then public.plot.is_vacant"
          centerValue={data?.total_land.hectares ?? "—"}
          centerLabel="Total"
          entries={data?.land_occupancy_breakdown ?? []}
        />
        <Chart
          title="Derived tenure classification"
          subtitle={`${data?.tenant_terminology?.lifecycle_records.count.toLocaleString() ?? "—"} ${data?.tenant_terminology?.lifecycle_records.label.toLowerCase() ?? "derived tenure classifications"}; not an active-tenancy status`}
          entries={data?.tenancy_lifecycle_breakdown ?? []}
        />
        <Chart
          title="Lease / tenancy type"
          subtitle="Source values from public.applicant_property_mapping.tenancy_type"
          entries={data?.lease_type_breakdown ?? []}
        />
        <Chart
          title="Tenant structure"
          subtitle="Separate dimension · public.applicant_property_mapping.tenant_type"
          entries={data?.tenant_structure_breakdown ?? []}
        />
        <Chart
          title="Billing periodicity"
          subtitle="Separate dimension · public.applicant_property_mapping.bill_periodicity"
          entries={data?.billing_periodicity_breakdown ?? []}
        />
      </section>
      {data?.tenant_terminology && <p className="data-quality-note">
        Terminology: {data.tenant_terminology.mapping_records.count.toLocaleString()} applicant-property mapping records · {data.tenant_terminology.tenancy_identifiers.count.toLocaleString()} tenancy identifiers · {data.tenant_terminology.applicant_ids.count.toLocaleString()} applicant IDs represented. These are different concepts; lifecycle is derived from tenancy type, not a canonical active-tenancy count.
      </p>}
      {data?.data_quality && <p className="data-quality-note">
        Data quality: {data.data_quality.orphan_mappings.toLocaleString()} mapping records are not linked to an applicant, {data.data_quality.missing_plot_links.toLocaleString()} have no plot link, {data.data_quality.historical_start_dates.toLocaleString()} have historical start dates, and {data.data_quality.invalid_start_dates.toLocaleString()} have invalid start dates.
      </p>}
    </>
  );
}
function Chart({
  title,
  subtitle,
  entries,
}: {
  title: string;
  subtitle: string;
  entries: { name: string; count: number; color: string }[];
}) {
  const max = Math.max(1, ...entries.map((x) => x.count));
  const scale = Math.ceil(max / 800) * 800;
  const plotLeft = 45;
  const plotRight = 488;
  const slotWidth = (plotRight - plotLeft) / Math.max(entries.length, 1);
  const barWidth = Math.min(42, Math.max(12, slotWidth * 0.72));
  return (
    <article className="chart">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <svg
        className="live-bars"
        viewBox="0 0 500 220"
        role="img"
        aria-label={title}
      >
        {[0, 1, 2, 3, 4].map((i) => {
          const y = 18 + i * 40;
          return (
            <g key={i}>
              <line x1="38" x2="488" y1={y} y2={y} />
              <text x="4" y={y + 4}>
                {Math.round((scale * (4 - i)) / 4)}
              </text>
            </g>
          );
        })}
        {entries.map((x, i) => {
          const width = barWidth;
          const xPos = plotLeft + i * slotWidth + (slotWidth - width) / 2;
          const height = (x.count / scale) * 160;
          const label = x.name.length > 10 ? `${x.name.slice(0, 9)}…` : x.name;
          const labelX = xPos + width / 2;
          const rotateLabels = entries.length > 8;
          return (
            <g key={x.name}>
              <title>{`${x.name}: ${x.count.toLocaleString()}`}</title>
              <rect
                x={xPos}
                y={178 - height}
                width={width}
                height={height}
                rx="3"
                fill={x.color}
              />
              <text
                className="chart-axis-label"
                x={labelX}
                y="202"
                textAnchor={rotateLabels ? "end" : "middle"}
                transform={rotateLabels ? `rotate(-38 ${labelX} 202)` : undefined}
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
    </article>
  );
}
function Donut({
  title,
  subtitle,
  centerValue,
  centerLabel,
  entries,
}: {
  title: string;
  subtitle: string;
  centerValue: string;
  centerLabel: string;
  entries: { name: string; value: number; color: string }[];
}) {
  const total = entries.reduce((sum, x) => sum + x.value, 0);
  let cursor = 0;
  const stops = entries
    .map((x) => {
      const start = (cursor / Math.max(total, 1)) * 360;
      cursor += x.value;
      return `${x.color} ${start}deg ${(cursor / Math.max(total, 1)) * 360}deg`;
    })
    .join(", ");
  return (
    <article className="chart donut-card">
      <h2>{title}</h2>
      <p>{subtitle}</p>
      <div className="donut" role="img" aria-label={`${title}: ${entries.map((entry) => `${entry.name} ${entry.value.toFixed(2)} hectares`).join(", ")}`} tabIndex={0} style={{ background: `conic-gradient(${stops})` }}>
        <span>
          <b>{centerValue}</b>
          <small>{centerLabel}</small>
        </span>
      </div>
      <div className="legend">
        {entries.map((x) => (
          <span key={x.name}>
            <i className="dot" style={{ background: x.color }} />
            <strong>{x.name}</strong>
            <small>{x.value.toFixed(2)} ha · {total ? `${((x.value / total) * 100).toFixed(1)}%` : "0.0%"}</small>
          </span>
        ))}
      </div>
    </article>
  );
}
function tenantCell(value: string | null | undefined): string {
  const text = String(value ?? "").trim();
  return !text || text === "Not provided" || text === "Not linked" ? "—" : text;
}
function tenantOptionLabel(value: string): string {
  if (value.toLowerCase() === "fifteen monthly") return "15-Monthly";
  if (value.toLowerCase() === "exipred lease") return "Expired Lease";
  return value;
}
function paginationItems(page: number, pages: number): Array<number | "ellipsis"> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const values = new Set([1, 2, page - 1, page, page + 1, pages - 1, pages]);
  const ordered = Array.from(values).filter((value) => value >= 1 && value <= pages).sort((a, b) => a - b);
  const items: Array<number | "ellipsis"> = [];
  ordered.forEach((value, index) => {
    if (index > 0 && value - ordered[index - 1] > 1) items.push("ellipsis");
    items.push(value);
  });
  return items;
}
function Documents({ authority }: { authority: boolean }) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [tenants, setTenants] = useState<TenantRecord[]>([]);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [leaseTypeFilter, setLeaseTypeFilter] = useState("");
  const [allotmentFilter, setAllotmentFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [tenantFilters, setTenantFilters] = useState<TenantFilterOptions>({ statuses: [], lease_types: [], allotment_statuses: [] });
  const [tenantTerminology, setTenantTerminology] = useState<TenantTerminology | null>(null);
  const [tenantLoading, setTenantLoading] = useState(false);
  const [tenantError, setTenantError] = useState("");
  const [tenantReloadKey, setTenantReloadKey] = useState(0);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentsError, setDocumentsError] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [customPageSize, setCustomPageSize] = useState("25");
  const [pageInput, setPageInput] = useState("1");
  const [sortBy, setSortBy] = useState("tenant_id");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  useEffect(() => {
    if (authority) {
      setTenantLoading(true);
      setTenantError("");
      api(
        `/api/authority/tenants?query=${encodeURIComponent(filter)}&status=${encodeURIComponent(statusFilter)}&lease_type=${encodeURIComponent(leaseTypeFilter)}&allotment_status=${encodeURIComponent(allotmentFilter)}&date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}&page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_direction=${sortDirection}`,
      ).then((x) => {
        setTenants(x.tenants);
        setTotal(x.total);
        setPages(x.pages ?? Math.max(1, Math.ceil(x.total / pageSize)));
        setPage(x.page ?? page);
        setPageInput(String(x.page ?? page));
        setTenantFilters(x.filters ?? { statuses: [], lease_types: [], allotment_statuses: [] });
        setTenantTerminology(x.tenant_terminology ?? null);
      }).catch(() => {
        setTenantError("Unable to load tenant records.");
        setTenants([]);
      }).finally(() => setTenantLoading(false));
    } else {
      setDocumentsLoading(true);
      setDocumentsError("");
      api("/api/v1/documents").then((x) => setDocs(x.documents)).catch(() => { setDocumentsError("Unable to load indexed documents."); setDocs([]); }).finally(() => setDocumentsLoading(false));
    }
  }, [authority, filter, statusFilter, leaseTypeFilter, allotmentFilter, dateFrom, dateTo, page, pageSize, sortBy, sortDirection, tenantReloadKey]);
  if (authority) {
    const resetPage = () => {
      setPage(1);
      setPageInput("1");
    };
    const commitPageSize = (value: string) => {
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) return;
      const next = Math.min(100, Math.max(1, parsed));
      setCustomPageSize(String(next));
      setPageSize(next);
      resetPage();
    };
    const goToPage = (nextPage: number) => {
      const target = Math.min(Math.max(nextPage, 1), pages);
      setPage(target);
      setPageInput(String(target));
    };
    const sort = (column: string) => {
      setSortDirection((direction) => (sortBy === column && direction === "asc" ? "desc" : "asc"));
      setSortBy(column);
      resetPage();
    };
    const heading = (label: string, column: string) => (
      <button className="tenant-sort" onClick={() => sort(column)} aria-label={`Sort by ${label}`} aria-sort={sortBy === column ? (sortDirection === "asc" ? "ascending" : "descending") : "none"}>
        {label} <ArrowUpDown className={sortBy === column ? "active-sort" : ""} />
      </button>
    );
    return (
      <section className="registry">
        <header className="tenant-registry-header">
          <div className="registry-heading">
            <h2>
              <Users />
              Applicant-property mapping records
            </h2>
            <small>{total.toLocaleString()} {tenantTerminology?.mapping_records.label.toLowerCase() ?? "applicant-property mapping records"}</small>
          </div>
        </header>
        <div className="tenant-filters" role="search" aria-label="Applicant-property mapping record filters">
          <label className="tenant-search">
            <Search />
            <input
              placeholder="Search applicants, organizations, or tenancy IDs..."
              aria-label="Search applicants, organizations, or tenancy IDs"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                resetPage();
              }}
            />
          </label>
          <label className="tenant-select-control">
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); resetPage(); }}>
              <option value="">All statuses</option>
              {tenantFilters.statuses.map((value) => <option key={value} value={value}>{tenantOptionLabel(value)}</option>)}
            </select>
            <ChevronDown />
          </label>
          <label className="tenant-select-control">
            <span>Lease type</span>
            <select value={leaseTypeFilter} onChange={(e) => { setLeaseTypeFilter(e.target.value); resetPage(); }}>
              <option value="">All lease types</option>
              {tenantFilters.lease_types.map((value) => <option key={value} value={value}>{tenantOptionLabel(value)}</option>)}
            </select>
            <ChevronDown />
          </label>
          <label className="tenant-select-control">
            <span>Allotment</span>
            <select value={allotmentFilter} onChange={(e) => { setAllotmentFilter(e.target.value); resetPage(); }}>
              <option value="">All allotments</option>
              {tenantFilters.allotment_statuses.map((value) => <option key={value} value={value}>{tenantOptionLabel(value)}</option>)}
            </select>
            <ChevronDown />
          </label>
          <div className="tenant-date-range">
            <span>Date range</span>
            <input type="date" aria-label="Start date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); resetPage(); }} />
            <span aria-hidden="true">to</span>
            <input type="date" aria-label="End date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); resetPage(); }} />
          </div>
          <label className="tenant-page-size">
            <span>Rows</span>
            <input
              type="number"
              min="1"
              max="100"
              step="1"
              aria-label="Custom rows per page, from 1 to 100"
              value={customPageSize}
              onChange={(e) => setCustomPageSize(e.target.value.replace(/\D/g, "").slice(0, 3))}
              onBlur={() => commitPageSize(customPageSize)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); commitPageSize(customPageSize); } }}
            />
          </label>
        </div>
        {tenantError && <DataState tone="error" title="Unable to load tenant records." detail="The tenant table could not be retrieved. Try again." action={{ label: "Retry", onClick: () => setTenantReloadKey((value) => value + 1) }} />}
          <div className="tenant-table" role="table" aria-label="Applicant-property mapping records">
            <div className="tenant-row headings" role="row">
              <span role="columnheader">{heading("TENANCY IDENTIFIER", "tenancy_id")}</span>
              <span role="columnheader">{heading("APPLICANT ID", "tenant_id")}</span>
              <span role="columnheader">{heading("APPLICANT / ORGANIZATION", "tenant_name")}</span>
              <span role="columnheader">{heading("CONTACT PERSON", "contact_person")}</span>
              <span role="columnheader">{heading("TENANCY TYPE", "tenancy_type")}</span>
              <span role="columnheader">{heading("PURPOSE", "purpose")}</span>
              <span role="columnheader">{heading("COMMENCEMENT", "commencement")}</span>
              <span role="columnheader">{heading("RECORD STATUS", "status")}</span>
          </div>
          {tenantLoading ? <DataState tone="loading" title="Loading tenant records" detail="Retrieving the latest filtered page." /> : tenants.map((t) => (
            <div className="tenant-row" role="row" key={`${t.tenant_id}-${t.tenancy_id}`}>
              <span role="cell">
                <b>{tenantCell(t.tenancy_id)}</b>
              </span>
              <span role="cell"><b>{tenantCell(t.tenant_id)}</b></span>
              <span role="cell">{tenantCell(t.tenant_name)}</span>
              <span role="cell">{tenantCell(t.contact_person)}</span>
              <span role="cell">{tenantCell(t.tenancy_type)}</span>
              <span role="cell">{tenantCell(t.purpose)}</span>
              <span role="cell">{tenantCell(t.commencement)}</span>
              <span role="cell">
                <i>{tenantCell(t.status)}</i>
              </span>
            </div>
          ))}
          {!tenantLoading && !tenantError && !tenants.length && <DataState tone="empty" title="No tenants match these filters." detail="Try clearing a filter or broadening the search." />}
        </div>
        <footer className="tenant-footer">
          <span>Showing {tenants.length ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} {tenantTerminology?.mapping_records.label.toLowerCase() ?? "applicant-property mapping records"}</span>
          <div className="tenant-pagination">
            <button disabled={page === 1 || tenantLoading} onClick={() => goToPage(page - 1)}>‹ Previous</button>
            <nav aria-label="Applicant-property mapping record pages">
              {paginationItems(page, pages).map((item, index) => item === "ellipsis" ? <span key={`ellipsis-${index}`} aria-hidden="true">…</span> : <button key={item} className={item === page ? "active" : ""} aria-current={item === page ? "page" : undefined} onClick={() => goToPage(item)}>{item}</button>)}
            </nav>
            <button disabled={page === pages || tenantLoading} onClick={() => goToPage(page + 1)}>Next ›</button>
            <label className="tenant-page-jump">Page <input aria-label="Page number" inputMode="numeric" value={pageInput} onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ""))} onKeyDown={(e) => { if (e.key === "Enter") goToPage(Number(pageInput) || 1); }} /> of {pages}</label>
          </div>
        </footer>
      </section>
    );
  }
  const filtered = docs.filter(
    (d) =>
      d.filename.toLowerCase().includes(filter.toLowerCase()) ||
      d.classification.toLowerCase().includes(filter.toLowerCase()),
  );
  const rows = filtered.slice((page - 1) * 10, page * 10);
  const documentPages = Math.max(1, Math.ceil(filtered.length / 10));
  return (
    <section className="registry">
      <header>
        <h2>
          <Users />
          Registered Port Documents
        </h2>
        <label>
          <Search />
          <input
            placeholder="Search by filename or classification"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setPage(1);
            }}
          />
        </label>
      </header>
      <div className="doc-table" role="table" aria-label="Registered port documents">
        <div className="doc-row headings" role="row">
          <span role="columnheader">DOCUMENT</span>
          <span role="columnheader">CLASSIFICATION</span>
          <span role="columnheader">PAGES</span>
          <span role="columnheader">CHUNKS</span>
        <span role="columnheader">QUALITY</span>
        <span role="columnheader">INGESTION STATE</span>
        </div>
        {documentsLoading ? <DataState tone="loading" title="Loading indexed documents" detail="Retrieving document and extraction details." /> : documentsError ? <DataState tone="error" title="Unable to load indexed documents." detail="The document list could not be retrieved. Refresh and try again." /> : rows.map((d) => (
          <div className="doc-row" role="row" key={d.filename}>
            <span role="cell">
              <b>{d.filename}</b>
            </span>
            <span role="cell">{d.classification.replaceAll("_", " ")}</span>
            <span role="cell">{d.pages}</span>
            <span role="cell">{d.chunks}</span>
            <span role="cell">
              <i>{d.quality}%</i>
            </span>
            <span role="cell"><i className={`document-state ${d.state || "pending"}`} title={d.reason || undefined}>{d.state || "pending"}</i></span>
          </div>
        ))}
        {!documentsLoading && !documentsError && !rows.length && <DataState tone="empty" title="No documents match this search." detail="Try a different filename or classification." />}
      </div>
      <footer>
        Showing {rows.length ? (page - 1) * 10 + 1 : 0} to{" "}
        {Math.min(page * 10, filtered.length)} of {filtered.length} documents{" "}
        <div>
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            Page {page} of {documentPages}
          </span>
          <button disabled={page === documentPages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      </footer>
    </section>
  );
}
function Assistant({ user }: { user: User }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [corpusState, setCorpusState] = useState<CorpusState | null>(null);
  const [ragReady, setRagReady] = useState(false);
  const [agendas, setAgendas] = useState<Agenda[]>([]);
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [handoffTarget, setHandoffTarget] = useState("");
  const [handoffNote, setHandoffNote] = useState("");
  const [agendaQuery, setAgendaQuery] = useState("");
  const [agendaFilter, setAgendaFilter] = useState<"all" | "draft" | "pending" | "approved">("all");
  const [agendaLoading, setAgendaLoading] = useState(false);
  const [agendaDraft, setAgendaDraft] = useState("");
  const [draftEditing, setDraftEditing] = useState(false);
  const [pendingTransition, setPendingTransition] = useState<{ action: string; label: string; question: string } | null>(null);
  const [showDraft, setShowDraft] = useState(false);
  const [showWorkflowDetails, setShowWorkflowDetails] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [conversationQuery, setConversationQuery] = useState("");
  const [conversationFilter, setConversationFilter] = useState<"all" | "today" | "week">("all");
  const [localLlmCatalog, setLocalLlmCatalog] = useState<LocalLlmCatalog>({ models: [], default_model: "" });
  const [llmModel, setLlmModel] = useState("");
  const [selectedContext, setSelectedContext] = useState("all");
  const [tab, setTab] = useState<"assistant" | "workflow">("assistant");
  const [showDocuments, setShowDocuments] = useState(false);
  const [showBillingForecast, setShowBillingForecast] = useState(false);
  const [showTenderPublication, setShowTenderPublication] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [showConversationDrawer, setShowConversationDrawer] = useState(false);
  const [showComposerSettings, setShowComposerSettings] = useState(false);
  const [conversationContextMenu, setConversationContextMenu] = useState<ConversationContextMenu | null>(null);
  const [pendingDelete, setPendingDelete] = useState<ChatSession | null>(null);
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null);
  const [conversationWidth, setConversationWidth] = useState(() => {
    return storedWidth("portproject.conversation-width", CONVERSATION_DEFAULT_WIDTH, CONVERSATION_MIN_WIDTH, CONVERSATION_MAX_WIDTH);
  });
  const conversationWidthRef = useRef(conversationWidth);
  const [workflowSideWidth, setWorkflowSideWidth] = useState(() => {
    return storedWidth("portproject.workflow-side-width", WORKFLOW_SIDE_DEFAULT_WIDTH, WORKFLOW_SIDE_MIN_WIDTH, WORKFLOW_SIDE_MAX_WIDTH);
  });
  const workflowSideWidthRef = useRef(workflowSideWidth);
  const [busy, setBusy] = useState(false);
  const [queryBusy, setQueryBusy] = useState(false);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [workspaceError, setWorkspaceError] = useState("");
  const [isAtLatest, setIsAtLatest] = useState(true);
  const requestController = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const composerInputRef = useRef<HTMLTextAreaElement | null>(null);
  const assistantGridRef = useRef<HTMLDivElement | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState<{ message: string; tone: "error" | "success" } | null>(null);
  const toastTimer = useRef<number | null>(null);
  const showToast = (message: string, tone: "error" | "success" = "error") => {
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
    setToast({ message, tone });
    toastTimer.current = window.setTimeout(() => {
      setToast(null);
      toastTimer.current = null;
    }, 4000);
  };
  useEffect(() => () => {
    if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
  }, []);
  const conversationMaxWidth = () => {
    const grid = assistantGridRef.current;
    if (!grid) return CONVERSATION_MAX_WIDTH;
    const availableWidth = grid.getBoundingClientRect().width;
    return availableWidth ? Math.max(CONVERSATION_MIN_WIDTH, Math.min(CONVERSATION_MAX_WIDTH, availableWidth - 320)) : CONVERSATION_MAX_WIDTH;
  };
  const updateConversationWidth = (value: number, persist = false) => {
    const width = clampWidth(value, CONVERSATION_MIN_WIDTH, conversationMaxWidth());
    conversationWidthRef.current = width;
    setConversationWidth(width);
    if (persist) window.localStorage.setItem("portproject.conversation-width", String(width));
  };
  const workflowSideMaxWidth = () => {
    const grid = assistantGridRef.current;
    if (!grid) return WORKFLOW_SIDE_MAX_WIDTH;
    const availableWidth = grid.getBoundingClientRect().width;
    const maxAvailable = availableWidth - conversationWidthRef.current - 340;
    return Math.max(WORKFLOW_SIDE_MIN_WIDTH, Math.min(WORKFLOW_SIDE_MAX_WIDTH, maxAvailable));
  };
  const updateWorkflowSideWidth = (value: number, persist = false) => {
    const width = clampWidth(value, WORKFLOW_SIDE_MIN_WIDTH, workflowSideMaxWidth());
    workflowSideWidthRef.current = width;
    setWorkflowSideWidth(width);
    if (persist) window.localStorage.setItem("portproject.workflow-side-width", String(width));
  };
  useEffect(() => {
    const handleResize = () => {
      updateConversationWidth(conversationWidthRef.current, true);
      updateWorkflowSideWidth(workflowSideWidthRef.current, true);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);
  const adjustConversationWidth = (delta: number) => {
    updateConversationWidth(conversationWidthRef.current + delta, true);
  };
  async function load() {
    setWorkspaceLoading(true);
    setWorkspaceError("");
    try {
      const requests: Promise<any>[] = [api("/api/v1/chat/sessions"), api("/api/v1/corpus/state"), api("/api/v1/local-llms").catch(() => ({ models: [], default_model: "" }))];
      if (user.role === "authority") requests.push(api("/api/v1/workflow/agendas"), api("/api/v1/workflow/officers"));
      const [chat, corpus, models, workflow, directory] = await Promise.all(requests);
      setSessions(chat.sessions);
      setCorpusState(corpus);
      setDocuments(corpus.documents_state.map((item: any) => ({ filename: item.filename, pages: item.pages, chunks: item.chunks, classification: item.state, quality: item.embeddings === item.chunks ? 100 : 0, state: item.state, reason: item.reason })));
      setLocalLlmCatalog(models);
      setLlmModel((current) => current && models.models.includes(current) ? current : models.default_model);
      if (workflow) {
        setAgendas(workflow.agendas);
        if (agenda && !workflow.agendas.some((item: Agenda) => item.agenda_id === agenda.agenda_id)) {
          setAgenda(null);
          setShowDraft(false);
          setShowWorkflowDetails(false);
          setPendingTransition(null);
        }
      }
      if (directory) setOfficers(directory.officers);
      const readiness = await fetch(base + "/health/ready", { credentials: "include" }).then(async (response) => ({ ok: response.ok, body: await response.json().catch(() => ({})) })).catch(() => ({ ok: false, body: {} }));
      setRagReady(readiness.ok && readiness.body.rag_ready === true);
    } catch (loadError) {
      setWorkspaceError("AI Assistant is temporarily unavailable.");
      throw loadError;
    } finally {
      setWorkspaceLoading(false);
    }
  }
  useEffect(() => {
    let cancelled = false;
    let readinessTimer: number | undefined;
    const refreshReadiness = async () => {
      const readiness = await fetch(base + "/health/ready", { credentials: "include" })
        .then(async (response) => ({ ok: response.ok, body: await response.json().catch(() => ({})) }))
        .catch(() => ({ ok: false, body: {} }));
      if (cancelled) return;
      const ready = readiness.ok && readiness.body.rag_ready === true;
      setRagReady(ready);
      if (ready && readinessTimer !== undefined) window.clearInterval(readinessTimer);
    };
    load().catch(() => setError("AI Assistant is temporarily unavailable."));
    readinessTimer = window.setInterval(() => { void refreshReadiness(); }, 10000);
    return () => {
      cancelled = true;
      if (readinessTimer !== undefined) window.clearInterval(readinessTimer);
    };
  }, []);
  useEffect(() => {
    if (isAtLatest && tab === "assistant") messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, queryBusy, tab, isAtLatest]);
  useEffect(() => {
    const input = composerInputRef.current;
    if (!input) return;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 96)}px`;
  }, [question]);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(""), 4000);
    return () => window.clearTimeout(timeout);
  }, [notice]);
  useEffect(() => {
    setShowConversationDrawer(false);
    setShowComposerSettings(false);
  }, [tab]);
  useEffect(() => {
    if (!conversationContextMenu) return;
    const closeMenu = () => setConversationContextMenu(null);
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") closeMenu();
    };
    document.addEventListener("pointerdown", closeMenu);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    return () => {
      document.removeEventListener("pointerdown", closeMenu);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
    };
  }, [conversationContextMenu]);
  async function choose(id: string) {
    setConversationContextMenu(null);
    const data = await api(`/api/v1/chat/sessions/${id}`);
    setActive(id); setMessages(data.messages); setTab("assistant"); setIsAtLatest(true); setNotice("");
  }
  async function newChat() {
    setConversationContextMenu(null);
    const x = await api("/api/v1/chat/sessions", { method: "POST" });
    await load(); setActive(x.chat_session_id); setMessages([]); setTab("assistant"); setIsAtLatest(true); setNotice("");
  }
  async function copyConversationId(id: string) {
    setConversationContextMenu(null);
    if (!navigator.clipboard) {
      setError("Clipboard access is unavailable in this browser.");
      return;
    }
    try {
      await navigator.clipboard.writeText(id);
      setError("");
      setNotice("Conversation ID copied.");
    } catch {
      setError("Unable to copy the conversation ID.");
    }
  }
  async function deleteConversation(session: ChatSession) {
    setDeletingConversationId(session.chat_session_id);
    setError(""); setNotice("");
    try {
      await api(`/api/v1/chat/sessions/${session.chat_session_id}`, { method: "DELETE" });
      if (active === session.chat_session_id) {
        setActive(null);
        setMessages([]);
      }
      setPendingDelete(null);
      await load();
      setNotice("Conversation deleted.");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unable to delete this conversation.";
      if (/linked to workflow records|cannot be deleted/i.test(message)) {
        setError("");
        showToast("This conversation is linked to workflow records and cannot be deleted.");
      } else {
        setError("Unable to delete this conversation.");
      }
    } finally {
      setDeletingConversationId(null);
    }
  }
  async function manageDocuments() {
    setShowDocuments((value) => !value);
  }
  function openBillingForecast() {
    if (tab !== "assistant") setTab("assistant");
    setSelectedContext("billing");
    setShowBillingForecast(true);
    setError("");
  }
  function openTenderPublication() {
    if (tab !== "assistant") setTab("assistant");
    setSelectedContext("tender");
    setShowTenderPublication(true);
    setError("");
  }
  function completeBillingForecast(payload: any) {
    const request = payload.prediction?.request || {};
    const forecastQuestion = `Billing forecast for ${request.tenancy_id || request.customer_id || "manual input"}`;
    const now = new Date().toISOString();
    setActive(payload.chat_session_id || active);
    setMessages((current) => [
      ...current,
      { sender: "user", content: forecastQuestion, created_at: payload.user_created_at || now },
      { sender: "assistant", content: payload.summary || "Billing forecast completed.", sources: [], created_at: payload.assistant_created_at || now },
    ]);
    setSelectedContext("all");
    setShowBillingForecast(false);
    setNotice("Billing forecast added to the conversation.");
    void load().catch(() => undefined);
  }
  async function forwardAgenda() {
    if (!active) { setError("Start a conversation and ask a document question before creating an agenda."); return; }
    setBusy(true); setError("");
    try {
      const result = await api("/api/v1/workflow/agendas", { method: "POST", body: JSON.stringify({ chat_session_id: active }) });
      await load(); await chooseAgenda(result.agenda.agenda_id); setNotice(`Official agenda created: ${result.agenda.code}`); setTab("workflow");
    } catch { setError("Unable to create an agenda right now."); }
    finally { setBusy(false); }
  }
  async function chooseAgenda(id: string) {
    setAgendaLoading(true); setError("");
    try {
      const result = await api(`/api/v1/workflow/agendas/${id}`);
      setAgenda(result.agenda); setAgendaDraft(result.agenda.versions?.[0]?.draft_text || ""); setDraftEditing(false); setPendingTransition(null); setTab("workflow"); setShowWorkflowDetails(false); setNotice(""); setHandoffTarget(""); setHandoffNote("");
    } catch {
      setAgenda(null); setShowDraft(false); setShowWorkflowDetails(false); setPendingTransition(null); setError("This agenda could not be loaded.");
    } finally {
      setAgendaLoading(false);
    }
  }
  async function saveAgendaDraft() {
    if (!agenda) return;
    setBusy(true); setError("");
    try {
      await api(`/api/v1/workflow/agendas/${agenda.agenda_id}/revisions`, { method: "POST", body: JSON.stringify({ draft_text: agendaDraft }) });
      await chooseAgenda(agenda.agenda_id); setNotice("Official draft revision saved.");
    } catch { setError("Unable to save the agenda revision."); }
    finally { setBusy(false); }
  }
  async function transition(action: string) {
    if (!agenda) return;
    setBusy(true); setError("");
    try {
      await api(`/api/v1/workflow/agendas/${agenda.agenda_id}/transition`, { method: "POST", body: JSON.stringify({ action, target_principal: handoffTarget || null, note: handoffNote.trim() }) });
      await load(); await chooseAgenda(agenda.agenda_id);
      const transitionMessages: Record<string, string> = { submit_to_nodal: "Agenda submitted to Nodal Officer.", submit_to_hod: "Agenda submitted for HOD approval.", approve: "Agenda approved.", reject: "Agenda rejected.", return_to_do: "Agenda returned to Data Entry." };
      setNotice(transitionMessages[action] || "Agenda ownership and state updated.");
    } catch { setError("The agenda update could not be completed."); }
    finally { setBusy(false); }
  }
  function requestTransition(action: string, label: string, question = `Submit agenda to ${label}?`) {
    setPendingTransition({ action, label, question });
  }
  async function confirmTransition() {
    if (!pendingTransition) return;
    const action = pendingTransition.action;
    setPendingTransition(null);
    await transition(action);
  }
  function stopRequest() {
    if (!requestController.current) return;
    requestController.current.abort();
    requestController.current = null;
    setQueryBusy(false);
    setBusy(false);
    setNotice("Request stopped.");
  }
  async function send(e: FormEvent) {
    e.preventDefault(); if (!question.trim()) return;
    const q = question;
    const controller = new AbortController();
    requestController.current = controller;
    setQuestion(""); setBusy(true); setQueryBusy(true); setError(""); setNotice("");
    try {
      if (tab === "workflow" && agenda) {
        await api(`/api/v1/workflow/agendas/${agenda.agenda_id}/query`, { method: "POST", body: JSON.stringify({ question: q, llm_model: llmModel || undefined }), signal: controller.signal });
        await chooseAgenda(agenda.agenda_id);
      } else {
        const sentAt = new Date().toISOString();
        setMessages((m) => [...m, { sender: "user", content: q, created_at: sentAt }]);
        const r = await api("/api/v1/policy/query", { method: "POST", body: JSON.stringify({ question: q, chat_session_id: active, llm_model: llmModel || undefined }), signal: controller.signal });
        setActive(r.chat_session_id); setMessages((m) => [...m, { sender: "assistant", content: r.answer, sources: r.sources, created_at: r.assistant_created_at || new Date().toISOString() }]); await load();
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") setNotice("Request stopped.");
      else setError("AI Assistant is temporarily unavailable. Please try again.");
    } finally {
      if (requestController.current === controller) requestController.current = null;
      setQueryBusy(false); setBusy(false);
    }
  }
  const nextRole = agenda?.state === "DO_DRAFT" || agenda?.state === "RETURNED_TO_DO" ? "NO" : agenda?.state === "SUBMITTED_TO_NO" ? "HO" : null;
  const eligibleOfficers = officers.filter((officer) => officer.role === nextRole);
  const workflowMessages = agenda?.messages || [];
  const filteredAgendas = agendas.filter((item) => {
    const query = agendaQuery.trim().toLowerCase();
    const matchesQuery = !query || item.code.toLowerCase().includes(query) || item.title.toLowerCase().includes(query);
    const matchesFilter = agendaFilter === "all" || agendaStatusBucket(item.state) === agendaFilter;
    return matchesQuery && matchesFilter;
  });
  const hasCitedRagAnswer = messages.some((message) => message.sender === "assistant" && Boolean(message.sources?.length));
  const activeSession = sessions.find((session) => session.chat_session_id === active);
  const latestAssistantMessage = [...messages].reverse().find((message) => message.sender === "assistant");
  const filteredSessions = sessions.filter((session) => {
    const matchesQuery = session.title.toLowerCase().includes(conversationQuery.trim().toLowerCase());
    const group = conversationGroup(session.updated_at);
    const matchesFilter = conversationFilter === "all" || (conversationFilter === "today" ? group === "Today" : group === "Today" || group === "Yesterday" || group === "This week");
    return matchesQuery && matchesFilter;
  });
  const sessionGroups = (["Today", "Yesterday", "This week", "Older"] as const).map((label) => ({
    label,
    sessions: filteredSessions.filter((session) => conversationGroup(session.updated_at) === label),
  })).filter((group) => group.sessions.length);
  const canCreateAgenda = user.role === "authority" && !busy && Boolean(active) && hasCitedRagAnswer;
  const requiresHandoffTarget = agenda?.state === "DO_DRAFT" || agenda?.state === "RETURNED_TO_DO" || agenda?.state === "SUBMITTED_TO_NO";
  const handoffDisabledReason = agenda?.is_read_only
    ? `Handoff actions are locked while active owner is ${agenda.current_owner_name}.`
    : !nextRole && agenda
      ? `No handoff is available while this agenda is ${agendaStatusLabel(agenda.state).toLowerCase()}.`
      : requiresHandoffTarget && !eligibleOfficers.length
        ? `No eligible ${nextRole === "NO" ? "Nodal Officer" : "Head of Department"} is available.`
      : requiresHandoffTarget && !handoffTarget
        ? `Select a ${nextRole === "NO" ? "Nodal Officer" : "Head of Department"} to continue.`
        : "";
  const handoffExplanation = requiresHandoffTarget && agenda
    ? `This will send ${agenda.code} from ${workflowStageLabel(agenda.state)} to the selected ${nextRole === "NO" ? "Nodal Officer" : "Head of Department"}.`
    : "";
  const composerDisabledReason = agenda?.is_read_only
      ? "This agenda is view-only for your role."
    : !ragReady
      ? "Document search is still preparing."
      : "";
  const agendaDisabledReason = busy
    ? "Wait for the current document answer to finish."
    : !active
      ? "Start a conversation first."
      : !hasCitedRagAnswer
        ? "Ask a document question and wait for its cited answer before creating an agenda."
        : "Create an official agenda from this cited conversation.";
  const copyResponse = async (content: string) => {
    await navigator.clipboard?.writeText(content);
    setNotice("Response copied.");
  };
  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!queryBusy && ragReady && question.trim()) event.currentTarget.form?.requestSubmit();
    }
  };
  const handleMessageScroll = (event: UIEvent<HTMLDivElement>) => {
    const element = event.currentTarget;
    setIsAtLatest(element.scrollHeight - element.scrollTop - element.clientHeight < 72);
  };
  return <section className="ai-workspace enterprise-ai-workspace">
    {toast && <div className={`app-toast ${toast.tone}`} role="alert" aria-live="assertive">{toast.message}</div>}
    <div className="ai-tabs">
      <button className={tab === "assistant" ? "selected" : ""} onClick={() => setTab("assistant")}><Sparkles/>AI Assistant</button>
      {user.role === "authority" && <button className={tab === "workflow" ? "selected" : ""} onClick={() => setTab("workflow")}><Workflow/>Workflow {agendas.length ? `(${agendas.length})` : ""}</button>}
      <aside><button type="button" className="conversation-drawer-toggle" aria-expanded={showConversationDrawer} onClick={() => setShowConversationDrawer((value) => !value)}><Menu/>{tab === "assistant" ? "Conversations" : "Agendas"}</button>{tab === "assistant" ? <button type="button" onClick={newChat}><Plus/>New chat</button> : <button type="button" className="workflow-private-shortcut" onClick={() => setTab("assistant")}><Sparkles/>Ask AI privately</button>}</aside>
    </div>
    <div ref={assistantGridRef} className={`${tab === "workflow" ? `assistant-grid workflow-grid${agenda ? " has-details" : ""}` : "assistant-grid"}${showConversationDrawer ? " conversation-drawer-open" : ""}`} style={{ "--conversation-width": `${conversationWidth}px`, "--workflow-side-width": `${workflowSideWidth}px` } as CSSProperties}>
      <aside className={tab === "workflow" ? "conversations agenda-list" : "conversations"}>
        {tab === "assistant" ? <>
          <div className="conversation-heading"><div><h3>Conversations</h3><small>{sessions.length} saved conversation{sessions.length === 1 ? "" : "s"}</small></div><button onClick={newChat} aria-label="Start a new conversation"><Plus/></button></div>
          <label className="conversation-search"><Search/><input value={conversationQuery} onChange={(event) => setConversationQuery(event.target.value)} placeholder="Search conversations…" /></label>
          <div className="conversation-filters" role="group" aria-label="Conversation date filter"><button className={conversationFilter === "all" ? "selected" : ""} onClick={() => setConversationFilter("all")}>All</button><button className={conversationFilter === "today" ? "selected" : ""} onClick={() => setConversationFilter("today")}>Today</button><button className={conversationFilter === "week" ? "selected" : ""} onClick={() => setConversationFilter("week")}>This week</button></div>
          <div className="conversation-scroll">
            {workspaceError ? <DataState tone="error" title="AI Assistant is temporarily unavailable." detail="Your conversations could not be loaded. Try again." action={{ label: "Retry", onClick: () => void load().catch(() => undefined) }} /> : workspaceLoading ? <div className="conversation-skeleton" aria-label="Loading conversations"><span/><span/><span/></div> : sessionGroups.length ? sessionGroups.map((group) => <section className="conversation-group" key={group.label}><small>{group.label}</small>{group.sessions.map((session) => <button className={active === session.chat_session_id ? "current conversation-item" : "conversation-item"} onClick={() => void choose(session.chat_session_id).catch(() => setError("Unable to open this conversation."))} onContextMenu={(event) => { event.preventDefault(); const menuWidth = 224; const menuHeight = 148; setConversationContextMenu({ session, x: Math.max(8, Math.min(event.clientX, window.innerWidth - menuWidth - 8)), y: Math.max(8, Math.min(event.clientY, window.innerHeight - menuHeight - 8)) }); }} key={session.chat_session_id}><MessageSquare/><span><b>{session.title}</b></span><time>{formatRelativeConversationTime(session.updated_at)}</time></button>)}</section>) : <p>{sessions.length ? "No conversations match this filter." : "Start a conversation to create a saved thread."}</p>}
          </div>
          <button className="manage-documents" onClick={manageDocuments}><CloudUpload/>Manage documents</button>
        </> : <>
          <div className="agenda-list-heading"><small>Official agendas</small><b>{agendas.length}</b></div>
          <label className="agenda-search"><Search/><input value={agendaQuery} onChange={(event) => setAgendaQuery(event.target.value)} placeholder="Search agendas…" /></label>
          <div className="agenda-filters" role="group" aria-label="Agenda status filter">
            {(["all", "draft", "pending", "approved"] as const).map((filter) => <button type="button" className={agendaFilter === filter ? "selected" : ""} onClick={() => setAgendaFilter(filter)} key={filter}>{filter === "all" ? "All" : filter[0].toUpperCase() + filter.slice(1)}</button>)}
          </div>
          <div className="agenda-scroll">
            {workspaceError ? <DataState tone="error" title="This agenda could not be loaded." detail="The workflow list is temporarily unavailable. Try again." action={{ label: "Retry", onClick: () => void load().catch(() => undefined) }} /> : workspaceLoading ? <div className="agenda-skeleton" aria-label="Loading agendas"><span/><span/><span/></div> : filteredAgendas.length ? filteredAgendas.map((item) => <button className={agenda?.agenda_id === item.agenda_id ? "current agenda-card" : "agenda-card"} onClick={() => void chooseAgenda(item.agenda_id)} key={item.agenda_id}><span className="agenda-card-main"><b>{item.code}</b><strong>{item.title}</strong></span><span className={`agenda-status-chip ${agendaStatusBucket(item.state)}`}>{agendaStatusLabel(item.state)}</span><time>{formatWorkflowTime(item.updated_at)}</time></button>) : <p>{agendas.length ? "No agendas match this filter." : "No agenda is assigned to your role."}</p>}
          </div>
         </>}
         <ResizableSplitter
           orientation="vertical"
           value={conversationWidth}
           min={CONVERSATION_MIN_WIDTH}
           max={conversationMaxWidth()}
           defaultValue={CONVERSATION_DEFAULT_WIDTH}
           ariaLabel="Resize conversation list"
           className="conversation-splitter"
           onChange={updateConversationWidth}
           onCommit={(value) => updateConversationWidth(value, true)}
         />
       </aside>
       <section className="chat-box">
        <header className={tab === "workflow" ? "chat-header workflow-header" : "chat-header"}>
          {tab === "workflow" && agenda ? <>
            <div className="workflow-agenda-heading"><div className="workflow-agenda-title"><b>{agenda.code}</b><span className={`agenda-status-chip ${agendaStatusBucket(agenda.state)}`}>{agendaStatusLabel(agenda.state)}</span></div><h2>{agenda.title}</h2><span>Version {agenda.editing_version} · Updated {formatWorkflowTime(agenda.updated_at)}</span></div>
            <div className="workflow-header-actions"><button type="button" className="draft-control" onClick={() => setShowDraft((value) => !value)}><FileText/>View official draft · v{agenda.editing_version}</button><button type="button" className="workflow-details-toggle" aria-expanded={showWorkflowDetails} onClick={() => setShowWorkflowDetails((value) => !value)}><FileText/>Details &amp; handoff</button></div>
          </> : <><div><b>{tab === "assistant" ? activeSession?.title || "New conversation" : "Agenda workflow"}</b><span>{tab === "assistant" ? activeSession ? `Updated ${formatRelativeConversationTime(activeSession.updated_at)}` : "Ask about indexed port documents." : "Select an agenda to view its workflow and messages."}</span></div>{tab === "assistant" && <div className="chat-header-actions"><button type="button" className="chat-actions-trigger" aria-expanded={showActions} aria-controls="assistant-actions" onClick={() => setShowActions((value) => !value)}><MoreHorizontal/>Actions</button></div>}</>}
        </header>
        {showDocuments && <div className="document-popover"><b>Corpus documents</b><button onClick={() => setShowDocuments(false)}>Close</button>{documents.map((doc) => <span key={doc.filename}>{doc.filename} · {doc.state || "pending"} · {doc.pages} pages · {doc.chunks} chunks{doc.reason ? ` · ${doc.reason}` : ""}</span>)}</div>}
        {tab === "assistant" && showActions && <aside id="assistant-actions" className="quick-actions-drawer" aria-label="Quick actions">
          <header><div><b>Quick actions</b><span>Actions for this conversation</span></div><button type="button" aria-label="Close actions" onClick={() => setShowActions(false)}><X/></button></header>
          {user.role === "authority" && <section><button className="quick-primary" disabled={!canCreateAgenda} title={agendaDisabledReason} onClick={forwardAgenda}><CalendarDays/>Create agenda</button><p>{agendaDisabledReason}</p></section>}
          <section><button className="quick-secondary" disabled={!latestAssistantMessage} onClick={() => latestAssistantMessage && void copyResponse(latestAssistantMessage.content)}><Copy/>Copy latest answer</button><p>{latestAssistantMessage ? "Copy the most recent grounded response." : "Ask a document question to create an answer."}</p></section>
          <details className="conversation-details">
            <summary>Conversation details</summary>
            <section className="quick-fact"><small>Answer model</small><b>{llmModel || localLlmCatalog.default_model || "Unavailable"}</b></section>
            <section className="quick-fact"><small>Indexed documents</small><b>{corpusState ? `${corpusState.documents} documents` : "Loading…"}</b></section>
            <section className="quick-fact"><small>Latest sources</small><b>{latestAssistantMessage?.sources?.length ? `${latestAssistantMessage.sources.length} citations` : "No sources yet"}</b></section>
          </details>
        </aside>}
        {tab === "workflow" ? agendaLoading ? <div className="workflow-state workflow-loading" role="status"><span className="button-spinner"/><b>Loading agenda</b><p>Retrieving workflow details and messages.</p></div> : agenda ? <>
          <section className="workflow-summary" aria-label="Agenda workflow progress">
            <div className="workflow-stepper">
              {[
                { key: "do", label: "Data Entry", name: agenda.assigned_do_name },
                { key: "nodal", label: "Nodal Officer", name: agenda.assigned_nodal_name },
                { key: "hod", label: "HOD", name: agenda.assigned_hod_name },
              ].map((step, index, steps) => {
                const stage = workflowStageIndex(agenda.state);
                const status: "completed" | "current" | "pending" = agenda.state === "APPROVED" || index < stage ? "completed" : index === stage ? "current" : "pending";
                const statusLabel = status === "completed" ? "Completed" : status === "current" ? "Current" : "Pending";
                const assignee = step.name && !/^pending assignment$/i.test(step.name.trim()) ? step.name : "Pending assignment";
                return <div className="workflow-step-wrap" key={step.key}><div className={`workflow-step ${status}`} aria-current={status === "current" ? "step" : undefined} title={`${step.label}: ${statusLabel}`}><span className="workflow-step-icon" aria-hidden="true">{status === "completed" ? <Check/> : <span className={`workflow-step-marker ${status}`}/>}</span><span><b>{step.label}</b><small>{assignee}</small><em className="workflow-step-status">{statusLabel}</em></span></div>{index < steps.length - 1 && <i className={status === "completed" ? "completed" : ""} aria-hidden="true"/>}</div>;
              })}
            </div>
            <div className={agenda.is_read_only ? "ownership-status locked" : "ownership-status"}><ShieldCheck/><span><b>● Active owner: {agenda.current_owner_name}</b><small>{agenda.is_read_only ? "Review-only access." : "You can edit this draft and perform the next authorized handoff."}</small></span><strong>Current stage: {workflowStageLabel(agenda.state)} · Step {Math.min(workflowStageIndex(agenda.state) + 1, 3)} of 3</strong></div>
            <div className="ai-evidence-status"><Sparkles/><span>Supporting document evidence is available for cited questions.</span></div>
          </section>
          {agenda.context_capsules?.length ? <div className="workflow-document-toolbar"><span>Evidence ({agenda.context_capsules.length})</span><small>Agenda evidence snapshots</small></div> : null}
          {showDraft && <div className="agenda-draft"><header><div><b>Official draft · v{agenda.editing_version}</b><span>{agenda.is_read_only ? "View-only draft" : draftEditing ? "Editing is enabled for your role." : "Review the current official draft."}</span></div>{!agenda.is_read_only && <button type="button" className="draft-edit-toggle" onClick={() => setDraftEditing((value) => !value)}>{draftEditing ? "Stop editing" : "Edit draft"}</button>}</header><textarea readOnly={!draftEditing || agenda.is_read_only} disabled={agenda.is_read_only} value={agendaDraft} onChange={(e) => setAgendaDraft(e.target.value)} /><footer>{!agenda.is_read_only && draftEditing && <button disabled={busy || !agendaDraft.trim()} onClick={saveAgendaDraft}>Save v{agenda.editing_version + 1}</button>}</footer></div>}
          <div className="workflow-messages">
            {agenda.context_capsules?.map((capsule) => <details className="workflow-evidence-item" key={capsule.capsule_id}><summary><span className="workflow-avatar system-avatar"><FileText/></span><span><b>Agenda evidence snapshot · v{capsule.version}</b><small>{formatEvidenceCreated(capsule.created_at)}</small></span><ChevronDown/></summary><div className="workflow-evidence-details"><p>{capsule.summary}</p><small>Workflow state: {agendaStatusLabel(capsule.state)}</small><CitationList sources={capsule.sources}/></div></details>)}
            {workflowMessages.map((message) => <article className={message.message_type.toLowerCase()} key={message.message_id}><header><div className="workflow-sender"><span className={`workflow-avatar ${message.message_type === "AI" ? "system-avatar" : "human-avatar"}`}>{message.message_type === "AI" ? <Sparkles/> : personInitials(message.sender_name)}</span><span><b>{message.message_type === "AI" ? "Port RAG AI Assistant" : message.sender_name}</b><small>{message.message_type === "AI" ? "Grounded response" : message.message_type.replaceAll("_", " ")}</small></span></div><time title={message.created_at}>{formatWorkflowTime(message.created_at)}</time></header>{message.message_type === "AI" ? renderMarkdown(message.content) : <p>{message.content}</p>}<CitationList sources={message.sources}/>{message.message_type === "AI" && <div className="response-actions" aria-label="Response actions"><button type="button" onClick={() => void copyResponse(message.content)}><Copy/>Copy</button><button type="button" aria-label="Helpful answer" onClick={() => setNotice("Thanks for the feedback.")}><ThumbsUp/></button><button type="button" aria-label="Unhelpful answer" onClick={() => setNotice("Thanks for the feedback.")}><ThumbsDown/></button></div>}</article>)}
            {queryBusy && <div className="workflow-ai-thinking" role="status" aria-live="polite"><span className="workflow-avatar system-avatar"><Sparkles/></span><div><b>Port RAG AI Assistant</b><p>Reviewing supporting documents and preparing a response…</p><span className="thinking-dots" aria-hidden="true"><i/><i/><i/></span></div></div>}
            {!workflowMessages.length && !agenda.context_capsules?.length && !queryBusy && <div className="thread-empty"><Sparkles/><b>No discussion yet</b><span>Ask AI about this agenda or continue the workflow by assigning it to the next authorized officer.</span></div>}
          </div>
          {agenda.is_read_only ? <div className="workflow-readonly-state" role="status"><ShieldCheck/><div><b>Read-only thread</b><span>This agenda is currently owned by {agenda.current_owner_name}.</span><small>You can review the discussion and cited evidence.</small></div></div> : <><form className="workflow-composer" onSubmit={send}><button type="button" onClick={manageDocuments} aria-label="Manage documents"><Paperclip/></button><input disabled={workspaceLoading} placeholder="Ask AI about this agenda…" value={question} onChange={(e) => setQuestion(e.target.value)}/><button type={queryBusy ? "button" : "submit"} className={queryBusy ? "stop-query" : ""} onClick={queryBusy ? stopRequest : undefined} disabled={queryBusy ? false : !ragReady || !question.trim()}>{queryBusy ? <><span className="stop-icon" aria-hidden="true"/>Stop</> : <><Send/>Ask AI</>}</button></form>{composerDisabledReason && !queryBusy && <small className="workflow-composer-help">{composerDisabledReason}</small>}</>}
        </> : <div className="assistant-welcome workflow-state">{error ? <DataState tone="error" title="This agenda could not be loaded." detail="Select another agenda or try again." /> : <><small>OFFICIAL WORKFLOW</small><p>Select an agenda from the left, or promote an evidence-based private conversation.</p></>}</div> : <>
          <div className="messages" onScroll={handleMessageScroll}>
            {workspaceLoading && <div className="message-skeleton" aria-label="Loading conversation"><span/><span/><span/></div>}
            {!workspaceLoading && workspaceError && <DataState tone="error" title="AI Assistant is temporarily unavailable." detail="Your workspace could not be loaded. Try again from the conversation panel." />}
            {!workspaceLoading && !workspaceError && !messages.length && <div className="assistant-welcome enterprise-empty-state"><div className="empty-icon"><Sparkles/></div><div><small>PORT RAG AI ASSISTANT</small><h2>Ask about trusted port documents</h2><p>{corpusState?.documents ? "Search indexed policies, rules and documents, get cited answers, and create an agenda." : "The indexed corpus is empty. Add documents before asking a policy question."}</p></div></div>}
            {messages.map((message, index) => <article className={message.sender} key={`${message.created_at || "message"}-${index}`}><div className="message-meta">{message.sender === "assistant" ? <><span className="message-avatar assistant-avatar" aria-hidden="true"><Sparkles/></span><b>Port RAG AI Assistant</b></> : <span className="message-avatar user-avatar" aria-label={user.name} title={user.name}>{personInitials(user.name)}</span>}{message.created_at && <time dateTime={message.created_at}>{formatChatTime(message.created_at)}</time>}</div>{message.sender === "assistant" ? renderMarkdown(message.content) : <p>{message.content}</p>}<CitationList sources={message.sources}/>{message.sender === "assistant" && <div className="response-actions" aria-label="Response actions"><button type="button" onClick={() => void copyResponse(message.content)}><Copy/>Copy</button><button type="button" aria-label="Helpful answer" onClick={() => setNotice("Thanks for the feedback.")}><ThumbsUp/></button><button type="button" aria-label="Unhelpful answer" onClick={() => setNotice("Thanks for the feedback." )}><ThumbsDown/></button></div>}</article>)}
            {queryBusy && <div className="assistant-thinking" role="status" aria-live="polite"><span className="message-avatar assistant-avatar" aria-hidden="true"><Sparkles/></span><div><b>Port RAG AI Assistant</b><p>Searching indexed documents…</p><p>Generating a grounded answer…</p><span className="thinking-dots" aria-hidden="true"><i/><i/><i/></span></div></div>}
            <div ref={messagesEndRef}/>
            {!isAtLatest && messages.length > 0 && <button className="jump-latest" type="button" onClick={() => { setIsAtLatest(true); messagesEndRef.current?.scrollIntoView({ block: "end" }); }}>↓ Jump to latest</button>}
          </div>
          <div className="suggested-prompts composer-suggestions">{assistantSuggestions.slice(0, 3).map((suggestion) => <button type="button" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}</div>
          <form className="chat-composer" onSubmit={send}>
            <div className="composer-input-row"><textarea ref={composerInputRef} disabled={workspaceLoading} rows={1} onKeyDown={handleComposerKeyDown} placeholder="Ask about port policies or documents…" value={question} onChange={(event) => setQuestion(event.target.value)}/></div>
            <div className="composer-controls-row">
              <div className="composer-tools"><button type="button" onClick={manageDocuments} aria-label="Manage documents"><Paperclip/></button><button type="button" aria-label="Voice input is not enabled" title="Voice input is not enabled"><Mic/></button></div>
              <div className="composer-settings">
                <button type="button" className="composer-settings-toggle" aria-expanded={showComposerSettings} aria-label="Composer settings" onClick={() => setShowComposerSettings((value) => !value)}><Settings2/><span>Settings</span></button>
                <div className={`composer-settings-controls${showComposerSettings ? " open" : ""}`}>
                  <label className="model-select" title={llmModel || "Local answer model unavailable"}><select aria-label="Local answer model" disabled={!localLlmCatalog.models.length || busy} value={llmModel} onChange={(event) => setLlmModel(event.target.value)}>{localLlmCatalog.models.length ? localLlmCatalog.models.map((model) => <option value={model} key={model}>{model}</option>) : <option>Local models unavailable</option>}</select><ChevronDown/></label>
                  <label className="context-select" title="Choose a document context"><select aria-label="Document context" value={selectedContext} onChange={(event) => { const value = event.target.value; setSelectedContext(value); if (value === "billing") openBillingForecast(); if (value === "tender") openTenderPublication(); }}>{assistantContextOptions.map((option) => <option value={option.value} disabled={!option.available} key={option.value}>{option.label}</option>)}</select><ChevronDown/></label>
                </div>
              </div>
              <button type={queryBusy ? "button" : "submit"} className={queryBusy ? "stop-query" : ""} onClick={queryBusy ? stopRequest : undefined} disabled={queryBusy ? false : !ragReady || !question.trim()}>{queryBusy ? <><span className="stop-icon" aria-hidden="true"/>Stop</> : <><Send/>Ask AI</>}</button>
            </div>
          </form><small className="grounding-note"><ShieldCheck/> Answers are grounded in the indexed corpus and include available citations.</small>
        </>}
        {(error || notice) && <p className={error ? "error" : "notice"}>{error || notice}</p>}
       </section>
       {tab === "workflow" && agenda && <ResizableSplitter
         orientation="vertical"
         value={workflowSideWidth}
         min={WORKFLOW_SIDE_MIN_WIDTH}
         max={workflowSideMaxWidth()}
         defaultValue={WORKFLOW_SIDE_DEFAULT_WIDTH}
         ariaLabel="Resize agenda summary panel"
         className="workflow-details-splitter"
         reverse
         onChange={updateWorkflowSideWidth}
         onCommit={(value) => updateWorkflowSideWidth(value, true)}
       />}
      {tab === "workflow" && agenda && <aside className={`workflow-side-panel${showWorkflowDetails ? " open" : ""}`} aria-label="Agenda summary and handoff">
        <header className="workflow-side-header"><div><small>Agenda summary</small></div><button type="button" aria-label="Close agenda details" onClick={() => setShowWorkflowDetails(false)}><X/></button></header>
        <dl className="workflow-facts">
          <div><dt>Owner</dt><dd>{agenda.current_owner_name}</dd></div>
          <div><dt>Stage</dt><dd>{workflowStageLabel(agenda.state)}</dd></div>
          <div><dt>Version</dt><dd>v{agenda.editing_version}</dd></div>
          <div><dt>Status</dt><dd><span className={`agenda-status-chip ${agendaStatusBucket(agenda.state)}`}>{agendaStatusLabel(agenda.state)}</span></dd></div>
        </dl>
        <section className="handoff-panel"><header><div><b>Next handoff</b><small>{nextRole ? "Send this agenda to the next authorized workflow stage." : "No further handoff is available."}</small></div></header>{!agenda.is_read_only && requiresHandoffTarget && <><label className="handoff-select"><span>Assign to</span><select disabled={!eligibleOfficers.length || busy} value={handoffTarget} onChange={(e) => setHandoffTarget(e.target.value)}><option value="">Select {nextRole === "NO" ? "Nodal Officer" : "Head of Department"}</option>{eligibleOfficers.map((officer) => <option value={officer.principal_id} key={officer.principal_id}>{officer.name} ({officer.role_title})</option>)}</select></label><label className="handoff-note"><span>Note (optional)</span><textarea value={handoffNote} onChange={(e) => setHandoffNote(e.target.value)} placeholder="Add instructions or context for the next owner…" rows={2}/></label><p className="handoff-summary">{handoffExplanation}</p></>}{handoffDisabledReason && (agenda.is_read_only || requiresHandoffTarget) && <p className="handoff-help">{handoffDisabledReason}</p>}<div className="handoff-actions">{agenda.state === "DO_DRAFT" || agenda.state === "RETURNED_TO_DO" ? <button type="button" disabled={agenda.is_read_only || !handoffTarget || !eligibleOfficers.length || busy} onClick={() => requestTransition("submit_to_nodal", "Nodal Officer")}>Submit to Nodal</button> : agenda.state === "SUBMITTED_TO_NO" && !agenda.is_read_only ? <><button type="button" className="secondary-action" onClick={() => requestTransition("return_to_do", "Data Entry")}>Return to DO</button><button type="button" disabled={!handoffTarget || !eligibleOfficers.length || busy} onClick={() => requestTransition("submit_to_hod", "HOD")}>Submit to HOD</button></> : agenda.state === "SUBMITTED_TO_HO" && !agenda.is_read_only ? <><button type="button" className="secondary-action" onClick={() => requestTransition("return_to_do", "Data Entry")}>Return to DO</button><button type="button" className="danger-action" onClick={() => requestTransition("reject", "Data Entry", "Reject agenda?")}>Reject</button><button type="button" onClick={() => requestTransition("approve", "HOD", "Approve agenda?")}>Approve</button></> : <span>{agenda.is_read_only ? `Handoff actions are locked while active owner is ${agenda.current_owner_name}.` : `Agenda is ${agendaStatusLabel(agenda.state)}.`}</span>}</div></section>
        {pendingTransition && <div className="handoff-confirmation" role="dialog" aria-modal="true" aria-labelledby="handoff-confirm-title"><div className="handoff-confirm-card"><h3 id="handoff-confirm-title">{pendingTransition.question}</h3><p><b>{agenda.code}</b> will move from {workflowStageLabel(agenda.state)} to {pendingTransition.label}.</p><div><button type="button" className="secondary-action" onClick={() => setPendingTransition(null)}>Cancel</button><button type="button" onClick={() => void confirmTransition()}>{pendingTransition.action === "approve" ? "Approve" : pendingTransition.action === "reject" ? "Reject" : "Submit"}</button></div></div></div>}
      </aside>}
    </div>
    {conversationContextMenu && <div className="conversation-context-menu" role="menu" aria-label={`Actions for ${conversationContextMenu.session.title}`} style={{ left: conversationContextMenu.x, top: conversationContextMenu.y }} onPointerDown={(event) => event.stopPropagation()}>
      <div className="conversation-context-title">Conversation actions</div>
      <button type="button" role="menuitem" onClick={() => void choose(conversationContextMenu.session.chat_session_id).catch(() => setError("Unable to open this conversation."))}><MessageSquare/>Open conversation</button>
      <button type="button" role="menuitem" onClick={() => void copyConversationId(conversationContextMenu.session.chat_session_id)}><Copy/>Copy conversation ID</button>
      <div className="conversation-context-divider" />
      <button type="button" role="menuitem" className="conversation-context-danger" disabled={queryBusy && active === conversationContextMenu.session.chat_session_id} title={queryBusy && active === conversationContextMenu.session.chat_session_id ? "Wait for the current answer to finish." : "Delete this private conversation"} onClick={() => { const session = conversationContextMenu.session; setConversationContextMenu(null); setPendingDelete(session); }}><Trash2/>Delete conversation</button>
      <button type="button" role="menuitem" onClick={() => void newChat()}><Plus/>New conversation</button>
    </div>}
    {pendingDelete && <div className="conversation-delete-backdrop" role="presentation" onMouseDown={() => deletingConversationId === null && setPendingDelete(null)}>
      <section className="conversation-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="conversation-delete-title" onMouseDown={(event) => event.stopPropagation()}>
        <div className="conversation-delete-icon" aria-hidden="true"><Trash2/></div>
        <div>
          <h2 id="conversation-delete-title">Delete conversation?</h2>
          <p><b>{pendingDelete.title}</b> and all of its messages will be permanently removed. Conversations linked to workflow records are protected.</p>
        </div>
        <footer>
          <button type="button" className="conversation-delete-cancel" disabled={deletingConversationId !== null} onClick={() => setPendingDelete(null)}>Cancel</button>
          <button type="button" className="conversation-delete-confirm" disabled={deletingConversationId !== null} onClick={() => void deleteConversation(pendingDelete)}>{deletingConversationId ? "Deleting…" : "Delete conversation"}</button>
        </footer>
      </section>
    </div>}
    {showBillingForecast && <BillingForecastModal chatSessionId={active} onClose={() => { setShowBillingForecast(false); setSelectedContext("all"); }} onComplete={completeBillingForecast} />}
    {showTenderPublication && <TenderPublicationModal onClose={() => { setShowTenderPublication(false); setSelectedContext("all"); }} />}
  </section>;
}
createRoot(document.getElementById("root")!).render(<App />);
