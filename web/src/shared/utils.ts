export function clampWidth(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function storedWidth(key: string, fallback: number, min: number, max: number): number {
  const stored = window.localStorage.getItem(key);
  if (stored === null) return fallback;
  const value = Number(stored);
  return Number.isFinite(value) ? clampWidth(value, min, max) : fallback;
}

export function personInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0][0] || "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] || "" : "";
  return `${first}${last}`.toUpperCase();
}

export function displayName(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).map((part) => {
    const normalized = part.toLowerCase();
    return normalized.length === 1
      ? normalized.toUpperCase()
      : `${normalized[0].toUpperCase()}${normalized.slice(1)}`;
  }).join(" ");
}

export function formatChatTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function formatWorkflowTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : `${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })} · ${date.toLocaleDateString([], { month: "short", day: "numeric" })}`;
}

export function formatEvidenceCreated(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? "" : `Created ${date.toLocaleDateString([], { month: "short", day: "numeric" })} · ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })}`;
}

export function agendaStatusLabel(state: string): string {
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

export function agendaStatusBucket(state: string): "draft" | "pending" | "approved" {
  if (state === "APPROVED") return "approved";
  if (state === "DO_DRAFT" || state === "RETURNED_TO_DO") return "draft";
  return "pending";
}

export function workflowStageIndex(state: string): number {
  if (state === "SUBMITTED_TO_NO") return 1;
  if (state === "SUBMITTED_TO_HO") return 2;
  if (state === "APPROVED") return 3;
  return 0;
}

export function workflowStageLabel(state: string): string {
  if (state === "SUBMITTED_TO_NO") return "Nodal Officer";
  if (state === "SUBMITTED_TO_HO") return "HOD";
  if (state === "APPROVED") return "Completed";
  return "Data Entry";
}

export function formatRelativeConversationTime(timestamp: string): string {
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

export function conversationGroup(timestamp: string): "Today" | "Yesterday" | "This week" | "Older" {
  const date = new Date(timestamp);
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const value = date.getTime();
  if (value >= startToday) return "Today";
  if (value >= startToday - 86_400_000) return "Yesterday";
  if (value >= startToday - 7 * 86_400_000) return "This week";
  return "Older";
}

export function tenantCell(value: string | null | undefined): string {
  const text = String(value ?? "").trim();
  return !text || text === "Not provided" || text === "Not linked" ? "—" : text;
}

export function tenantOptionLabel(value: string): string {
  if (value.toLowerCase() === "fifteen monthly") return "15-Monthly";
  if (value.toLowerCase() === "exipred lease") return "Expired Lease";
  return value;
}

export function paginationItems(page: number, pages: number): Array<number | "ellipsis"> {
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
