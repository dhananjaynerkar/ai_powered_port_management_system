import { ReactNode, useState } from "react";
import {
  Anchor,
  ArrowRight,
  Bot,
  Building2,
  Check,
  Database,
  FileSearch,
  FileText,
  Layers,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { LanguageSelect } from "../../shared/i18n";

export type LandingCorpus = {
  documents?: number;
  pages?: number;
  chunks?: number;
  vectors?: number;
};

export type PortalRole = "authority" | "tenant";

type LandingHeaderProps = {
  compact?: boolean;
  onRoleEnter: (role: PortalRole) => void;
};

type LandingPageProps = {
  corpus: LandingCorpus | null;
  initialSetup?: boolean;
  onRoleEnter: (role: PortalRole) => void;
};

const modules: { icon: ReactNode; title: string; body: string; meta: string }[] = [
  { icon: <Bot />, title: "AI policy assistant", body: "Ask across indexed port documents and receive page-level evidence with every grounded answer.", meta: "Evidence grounded" },
  { icon: <Users />, title: "Tenant services", body: "Give each tenant the document access and AI support permitted for that identity.", meta: "Role filtered" },
  { icon: <LayoutDashboard />, title: "Authority operations", body: "Review land, applicant-property mappings, corpus health and operational metrics in one workspace.", meta: "Authority portal" },
  { icon: <FileSearch />, title: "Policy repository", body: "Search the local document corpus through semantic and keyword retrieval with source context.", meta: "PostgreSQL + pgvector" },
  { icon: <Workflow />, title: "Governed workflow", body: "Move cited discussions through the DO, Nodal Officer and HOD stages with explicit ownership.", meta: "DO → NO → HO" },
  { icon: <Layers />, title: "Billing & tender", body: "Use source-backed billing forecasts and tender workflows where your role allows them.", meta: "Source-backed" },
];

export function LandingHeader({ compact = false, onRoleEnter }: LandingHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const closeMenu = () => setMenuOpen(false);
  return (
    <header className="landing-header">
      <div className="landing-tricolor" aria-hidden="true" />
      <div className="landing-utility">
        <span>PORT OPERATIONS · LOCAL EVIDENCE</span>
        <LanguageSelect />
      </div>
      <div className="landing-nav-shell">
        <a className="landing-brand" href="#main-content" aria-label="AI PMS home" onClick={closeMenu}>
          <span className="landing-brand-mark"><Anchor aria-hidden="true" /></span>
          <span><small>PORT AUTHORITY</small><b>AI PMS</b></span>
        </a>
        <button type="button" className="landing-menu-toggle" aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>
          {menuOpen ? <X /> : <Menu />}
        </button>
        <nav className={menuOpen ? "landing-links open" : "landing-links"} aria-label="Primary navigation">
          <a href="#platform" onClick={closeMenu}>Platform</a>
          <a href="#assistant-preview" onClick={closeMenu}>AI Assistant</a>
          <a href="#workflow" onClick={closeMenu}>Workflows</a>
          <a href="#trust" onClick={closeMenu}>Security</a>
          <a href="#help" onClick={closeMenu}>Help</a>
          {!compact && <div className="landing-header-actions">
            <button type="button" className="landing-header-tenant" onClick={() => { closeMenu(); onRoleEnter("tenant"); }}>Tenant portal</button>
            <button type="button" className="landing-header-authority" onClick={() => { closeMenu(); onRoleEnter("authority"); }}>Authority portal <ArrowRight aria-hidden="true" /></button>
          </div>}
        </nav>
      </div>
    </header>
  );
}

export function LandingPage({ corpus, initialSetup = false, onRoleEnter }: LandingPageProps) {
  const documents = corpus?.documents ?? null;
  const pages = corpus?.pages ?? null;
  const chunks = corpus?.chunks ?? null;
  return (
    <main id="main-content" className="landing-page">
      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero-inner">
          <div className="landing-hero-copy">
            <span className="landing-eyebrow">AI PMS · PORT OPERATIONS</span>
            <h1 id="landing-title">AI-Powered Port Management System</h1>
            <p className="landing-hero-lede">Search port policies, manage tenant operations and move decisions through governed workflows—powered by local AI with source-backed answers.</p>
            <div className="landing-proof-points" aria-label="Product principles">
              <span><Check aria-hidden="true" />Page-level evidence</span>
              <span><Check aria-hidden="true" />Role-filtered access</span>
              <span><Check aria-hidden="true" />Local AI processing</span>
            </div>
            <div className="landing-role-entry" aria-label="Choose a portal">
              <button type="button" className="landing-role-card" onClick={() => onRoleEnter("authority")}>
                <span className="landing-role-icon authority"><Building2 aria-hidden="true" /></span>
                <span><b>{initialSetup ? "Create authority account" : "Authority portal"}</b><small>Operations, documents, workflow, billing and tender</small></span>
                <ArrowRight aria-hidden="true" />
              </button>
              <button type="button" className="landing-role-card" onClick={() => onRoleEnter("tenant")}>
                <span className="landing-role-icon tenant"><Users aria-hidden="true" /></span>
                <span><b>{initialSetup ? "Create tenant account" : "Tenant portal"}</b><small>Permitted documents and tenant-specific AI support</small></span>
                <ArrowRight aria-hidden="true" />
              </button>
            </div>
          </div>
          <div className="landing-preview-column" id="assistant-preview">
            <div className="landing-preview-label"><span>PRODUCT PREVIEW</span><small>Illustrative · public corpus example</small></div>
            <article className="landing-preview-card" aria-label="Illustrative AI policy assistant preview">
              <header>
                <div className="landing-preview-title"><span className="preview-mark"><Bot aria-hidden="true" /></span><span><b>AI policy assistant</b><small>Local AI · evidence grounded</small></span></div>
                <span className="preview-state"><i />Ready</span>
              </header>
              <div className="preview-query"><small>QUESTION</small><p>What is the lease renewal rule?</p></div>
              <div className="preview-answer"><div className="preview-answer-heading"><span><SparkleMark />Grounded answer</span><small>Example response</small></div><p>Renewal follows the term, notice and approval conditions set out in the applicable port rules. Check the cited clauses before acting.</p><div className="preview-citations"><span><FileText aria-hidden="true" />Port Estate Rules · p.12</span><span><FileText aria-hidden="true" />Lease policy · p.5</span></div></div>
              <footer><span><ShieldCheck aria-hidden="true" />Citation validated</span><span>Authorized documents only</span></footer>
            </article>
            <p className="landing-preview-note">A safe demonstration of the answer flow—not a live tenant record or current decision.</p>
          </div>
        </div>
      </section>

      <section className="landing-evidence-strip" aria-label="Current document corpus evidence">
        <div className="landing-section-width">
          <div className="evidence-strip-intro"><span className="landing-eyebrow">CURRENT CORPUS</span><b>Evidence available to the platform</b><small>Values are read from the document repository when it is available.</small></div>
          <div className="evidence-strip-items">
            <EvidenceMetric icon={<FileText />} value={documents} label="Indexed documents" />
            <EvidenceMetric icon={<Layers />} value={pages} label="Source pages" />
            <EvidenceMetric icon={<Database />} value={chunks} label="Evidence chunks" />
            <div className="evidence-strip-status"><span className="status-dot" /><div><b>Local AI</b><small>Answers remain evidence-grounded</small></div></div>
          </div>
        </div>
      </section>

      <section id="platform" className="landing-section landing-platform" aria-labelledby="platform-title">
        <div className="landing-section-width">
          <div className="landing-section-heading"><span className="landing-eyebrow">PLATFORM MODULES</span><h2 id="platform-title">The operational surface behind every decision</h2><p>One product for official documents, tenant service, governed review and source-backed calculations.</p></div>
          <div className="landing-module-grid">{modules.map((module) => <article className="landing-module" key={module.title}><span className="landing-module-icon">{module.icon}</span><div><span className="landing-module-meta">{module.meta}</span><h3>{module.title}</h3><p>{module.body}</p></div><span className="landing-module-rule" aria-hidden="true" /></article>)}</div>
        </div>
      </section>

      <section id="workflow" className="landing-section landing-workflow" aria-labelledby="workflow-title">
        <div className="landing-section-width landing-workflow-layout">
          <div className="landing-section-heading"><span className="landing-eyebrow">HOW AI PMS WORKS</span><h2 id="workflow-title">Evidence first. Decisions governed.</h2><p>AI can help explore the record. Official action still moves through the accountable workflow.</p></div>
          <div className="landing-flow-panels">
            <article className="landing-flow-card"><header><span className="flow-card-index">01</span><div><b>Answer with evidence</b><small>Private document assistance</small></div></header><div className="landing-flow-line"><FlowNode icon={<FileText />} label="Port documents" /><FlowConnector /><FlowNode icon={<SearchMark />} label="Hybrid search" /><FlowConnector /><FlowNode icon={<ShieldCheck />} label="Authorized evidence" /><FlowConnector /><FlowNode icon={<Bot />} label="Local AI answer" /><FlowConnector /><FlowNode icon={<FileSearch />} label="Page citations" /></div></article>
            <article className="landing-flow-card governance"><header><span className="flow-card-index">02</span><div><b>Move through ownership</b><small>Official agenda governance</small></div></header><div className="governance-flow"><GovernanceStep tone="complete" label="DO" detail="Draft" /><span className="governance-arrow">→</span><GovernanceStep tone="current" label="NO" detail="Review" /><span className="governance-arrow">→</span><GovernanceStep tone="pending" label="HO" detail="Approve / reject" /></div><p className="governance-note">Return for clarification or submit onward; each transition is permission-aware.</p></article>
          </div>
        </div>
      </section>

      <section id="trust" className="landing-section landing-trust" aria-labelledby="trust-title">
        <div className="landing-section-width landing-trust-layout"><div className="trust-stamp"><ShieldCheck aria-hidden="true" /><span>TRUSTED<br />EVIDENCE</span></div><div className="landing-section-heading"><span className="landing-eyebrow">BUILT FOR ACCOUNTABLE OPERATIONS</span><h2 id="trust-title">Useful AI without losing the record.</h2><p>AI PMS keeps the source visible, the access boundary explicit and official workflow actions owned by the right role.</p></div><div className="landing-trust-list"><TrustItem icon={<ShieldCheck />} title="Role-filtered access" body="Only documents permitted for the signed-in identity enter the answer flow." /><TrustItem icon={<FileSearch />} title="Page-level citations" body="Answers point back to source titles and pages so people can review evidence." /><TrustItem icon={<Database />} title="PostgreSQL-backed state" body="Conversations, agendas and operational records stay in the application database." /><TrustItem icon={<Workflow />} title="Controlled ownership" body="DO, Nodal Officer and HOD stages remain distinct and visible." /></div></div>
      </section>

      <section id="help" className="landing-help" aria-labelledby="help-title"><div className="landing-section-width"><div><span className="landing-eyebrow">START WITH YOUR WORKSPACE</span><h2 id="help-title">Choose the portal that matches your role.</h2><p>Use the Authority portal for operational work or the Tenant portal for your permitted records and support.</p></div><div className="landing-help-actions"><button type="button" onClick={() => onRoleEnter("authority")}>Authority portal <ArrowRight aria-hidden="true" /></button><button type="button" onClick={() => onRoleEnter("tenant")}>Tenant portal <ArrowRight aria-hidden="true" /></button></div></div></section>
    </main>
  );
}

function EvidenceMetric({ icon, value, label }: { icon: ReactNode; value: number | null; label: string }) {
  return <div className="evidence-strip-metric"><span>{icon}</span><div><b>{value === null ? "—" : value.toLocaleString()}</b><small>{label}</small></div></div>;
}

function FlowNode({ icon, label }: { icon: ReactNode; label: string }) {
  return <span className="landing-flow-node"><i>{icon}</i><b>{label}</b></span>;
}

function FlowConnector() { return <span className="landing-flow-connector" aria-hidden="true">→</span>; }

function GovernanceStep({ tone, label, detail }: { tone: "complete" | "current" | "pending"; label: string; detail: string }) {
  return <span className={`governance-step ${tone}`}><i>{tone === "complete" ? <Check aria-hidden="true" /> : tone === "current" ? <span className="governance-current-dot" /> : <span className="governance-pending-dot" />}</i><b>{label}</b><small>{detail}</small></span>;
}

function TrustItem({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return <div className="landing-trust-item"><span>{icon}</span><div><b>{title}</b><p>{body}</p></div></div>;
}

function SparkleMark() { return <span className="sparkle-mark" aria-hidden="true">✦</span>; }
function SearchMark() { return <span className="search-mark" aria-hidden="true">⌕</span>; }

export function LandingFooter() {
  return <footer className="landing-footer"><div className="landing-section-width"><div className="landing-footer-brand"><span className="landing-brand-mark"><Anchor aria-hidden="true" /></span><div><b>AI PMS</b><p>AI-Powered Port Management System for port operations, evidence and governed decisions.</p></div></div><nav aria-label="Footer navigation"><div><b>Platform</b><a href="#platform">Modules</a><a href="#assistant-preview">AI assistant</a><a href="#workflow">Workflows</a></div><div><b>Resources</b><a href="#trust">Evidence &amp; access</a><a href="#help">Portal entry</a><span>Local deployment</span></div><div><b>Legal &amp; access</b><span>Privacy policy</span><span>Terms of use</span><span>Accessibility</span></div></nav><div className="landing-footer-bottom"><span>AI PMS · Operational document intelligence</span><span>Use only with authorized access</span></div></div></footer>;
}
