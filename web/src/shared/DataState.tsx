import { FileText, X } from "lucide-react";

export type DataStateTone = "loading" | "empty" | "error";

export function DataState({
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
      <span className="data-state-icon" aria-hidden="true">{tone === "loading" ? <span className="data-state-skeleton" /> : tone === "error" ? <X /> : <FileText />}</span>
      <div><b>{title}</b>{detail && <p>{detail}</p>}</div>
      {action && <button type="button" onClick={action.onClick}>{action.label}</button>}
    </div>
  );
}
