import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  AlertTriangle,
  BarChart3,
  Check,
  ChevronRight,
  Database,
  FileSearch,
  Filter,
  Gauge,
  MessageCircle,
  Play,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  X
} from 'lucide-react';
import './styles.css';

const API = '';

const tabs = [
  { id: 'overview', label: 'Home', icon: Gauge },
  { id: 'copilot', label: 'Ask AI', icon: MessageCircle },
  { id: 'documents', label: 'Reports', icon: FileSearch },
  { id: 'review', label: 'Review', icon: ShieldCheck },
  { id: 'matrix', label: 'Compare', icon: BarChart3 },
  { id: 'controls', label: 'Settings', icon: Settings }
];

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [dashboard, setDashboard] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [detail, setDetail] = useState(null);
  const [runDetails, setRunDetails] = useState([]);
  const [query, setQuery] = useState('');
  const [sector, setSector] = useState('All');
  const [chatDraft, setChatDraft] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      answer: 'Ask me what needs attention, which company has the biggest cost exposure, or what a specific report says. I use the reports in this workspace first, and can use general AI when configured.',
      sources: [],
      suggestions: ['Which company has the biggest fuel cost?', 'Which reports need a closer look?', 'Explain this product simply']
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function refresh(preferredRun = selectedRun) {
    setError('');
    const data = await request('/api/dashboard');
    setDashboard(data);
    const latestId = preferredRun || data.runs?.[0]?.id;
    if (latestId) {
      setSelectedRun(latestId);
      setDetail(await request(`/api/runs/${latestId}`));
    } else {
      setDetail(null);
    }
    const details = await Promise.all((data.runs || []).slice(0, 30).map((run) => request(`/api/runs/${run.id}`)));
    setRunDetails(details);
  }

  async function runAction(action) {
    setLoading(true);
    setError('');
    try {
      if (action === 'seed') await request('/api/seed', { method: 'POST', body: JSON.stringify({ reset: true }) });
      if (action === 'analyze') await request('/api/analyze', { method: 'POST', body: JSON.stringify({ mode: 'regex' }) });
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function chooseRun(runId, tab = 'documents') {
    setSelectedRun(runId);
    setActiveTab(tab);
    setDetail(await request(`/api/runs/${runId}`));
  }

  async function reviewEvidence(evidenceId, decision) {
    setLoading(true);
    try {
      await request(`/api/evidence/${evidenceId}/review`, {
        method: 'PUT',
        body: JSON.stringify({ decision, note: decision === 'accepted' ? 'Checked in analyst console.' : 'Needs analyst follow-up.' })
      });
      if (selectedRun) setDetail(await request(`/api/runs/${selectedRun}`));
      const data = await request('/api/dashboard');
      setDashboard(data);
      const details = await Promise.all((data.runs || []).slice(0, 30).map((run) => request(`/api/runs/${run.id}`)));
      setRunDetails(details);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function askCopilot(message = chatDraft) {
    const prompt = message.trim();
    if (!prompt) return;
    setChatDraft('');
    setChatLoading(true);
    setChatMessages((items) => [...items, { role: 'user', answer: prompt, sources: [], suggestions: [] }]);
    try {
      const response = await request('/api/chat', { method: 'POST', body: JSON.stringify({ message: prompt }) });
      setChatMessages((items) => [...items, { role: 'assistant', ...response }]);
    } catch (err) {
      setChatMessages((items) => [...items, { role: 'assistant', answer: err.message, sources: [], suggestions: [] }]);
    } finally {
      setChatLoading(false);
    }
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  const documents = dashboard?.documents || [];
  const runs = dashboard?.runs || [];
  const flags = dashboard?.flags || [];
  const sectors = useMemo(() => ['All', ...Array.from(new Set(documents.map((doc) => doc.sector))).sort()], [documents]);
  const filteredDocuments = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return documents.filter((doc) => {
      const matchesQuery = !needle || `${doc.company} ${doc.sector} ${doc.doc_key}`.toLowerCase().includes(needle);
      const matchesSector = sector === 'All' || doc.sector === sector;
      return matchesQuery && matchesSector;
    });
  }, [documents, query, sector]);
  const peerRows = useMemo(() => buildPeerRows(runDetails), [runDetails]);
  const reviewRows = useMemo(() => buildReviewRows(runDetails), [runDetails]);

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <strong>FilingLens</strong>
            <span>Company reports, clarified</span>
          </div>
        </div>
        <nav>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} className={activeTab === tab.id ? 'navItem active' : 'navItem'} onClick={() => setActiveTab(tab.id)}>
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className="sidebarMeta">
          <span>Mode</span>
          <strong>AI-assisted clarity</strong>
          <small>Finds what was explained, what was skipped, and what needs a human look.</small>
        </div>
      </aside>

      <main className="product">
        <Topbar
          query={query}
          setQuery={setQuery}
          sector={sector}
          setSector={setSector}
          sectors={sectors}
          loading={loading}
          onSeed={() => runAction('seed')}
          onAnalyze={() => runAction('analyze')}
          onRefresh={() => refresh()}
        />

        {error && <div className="notice danger"><AlertTriangle size={16} /> {error}</div>}

        {activeTab === 'overview' && (
          <Overview
            counts={dashboard?.counts}
            runs={runs}
            flags={flags}
            peerRows={peerRows}
            onOpenRun={chooseRun}
            chatMessages={chatMessages}
            chatDraft={chatDraft}
            setChatDraft={setChatDraft}
            chatLoading={chatLoading}
            onAsk={askCopilot}
          />
        )}

        {activeTab === 'copilot' && (
          <CopilotWorkspace
            messages={chatMessages}
            draft={chatDraft}
            setDraft={setChatDraft}
            loading={chatLoading}
            onAsk={askCopilot}
            onOpenRun={chooseRun}
          />
        )}

        {activeTab === 'documents' && (
          <DocumentsWorkspace
            documents={filteredDocuments}
            runs={runs}
            selectedRun={selectedRun}
            detail={detail}
            onOpenRun={chooseRun}
            onReview={reviewEvidence}
          />
        )}

        {activeTab === 'review' && (
          <ReviewQueue
            rows={reviewRows}
            flags={flags}
            onOpenRun={chooseRun}
            onReview={reviewEvidence}
          />
        )}

        {activeTab === 'matrix' && <PeerMatrix rows={peerRows} onOpenRun={chooseRun} />}

        {activeTab === 'controls' && (
          <Controls loading={loading} onSeed={() => runAction('seed')} onAnalyze={() => runAction('analyze')} />
        )}
      </main>
    </div>
  );
}

function Topbar({ query, setQuery, sector, setSector, sectors, loading, onSeed, onAnalyze, onRefresh }) {
  return (
    <header className="topbar">
      <div>
        <h1>FilingLens</h1>
        <p>Read company risk disclosures in plain English, with every answer tied back to the report.</p>
      </div>
      <div className="topbarControls">
        <label className="searchBox">
          <Search size={16} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search company, sector, report" />
        </label>
        <label className="selectBox">
          <Filter size={16} />
          <select value={sector} onChange={(event) => setSector(event.target.value)}>
            {sectors.map((item) => <option key={item}>{item}</option>)}
          </select>
        </label>
        <button className="primaryAction" onClick={onAnalyze} disabled={loading}><Play size={16} /> Check reports</button>
        <button className="iconAction" onClick={onSeed} disabled={loading} title="Seed demo"><Database size={17} /></button>
        <button className="iconAction" onClick={onRefresh} disabled={loading} title="Refresh"><RefreshCw size={17} /></button>
      </div>
    </header>
  );
}

function Overview({ counts, runs, flags, peerRows, onOpenRun, chatMessages, chatDraft, setChatDraft, chatLoading, onAsk }) {
  const highFlags = flags.filter((flag) => flag.severity === 'high');
  const staleRows = peerRows.filter((row) => row.stale);
  const missingSensitivity = flags.filter((flag) => flag.flag === 'MISSING_FUEL_SENSITIVITY');
  const topExposure = [...peerRows].sort((a, b) => (b.fuelShare || 0) - (a.fuelShare || 0)).slice(0, 5);

  return (
    <div className="tabStack">
      <section className="productHero">
        <div>
          <span className="eyebrow"><Sparkles size={15} /> AI-assisted report review</span>
          <h2>Know what the report really says.</h2>
          <p>
            FilingLens reads company filings, highlights unclear risk explanations, and lets anyone ask simple questions without digging through pages of finance language.
          </p>
        </div>
        <div className="heroBrief">
          <strong>{missingSensitivity.length} reports need a closer look</strong>
          <span>{staleRows.length} old report and {flags.filter((flag) => flag.flag === 'PROMPT_INJECTION_TEXT').length} unusual source-text warning.</span>
        </div>
      </section>
      <MetricGrid
        items={[
          ['Companies', counts?.companies ?? 0, 'In this workspace'],
          ['Reports', counts?.runs ?? 0, 'Ready to review'],
          ['Needs attention', counts?.highFlags ?? 0, 'Important items'],
          ['Review items', counts?.openEvidence ?? 0, 'Still unchecked']
        ]}
      />
      <section className="overviewGrid">
        <Panel title="What Needs Attention" action={`${highFlags.length} important`}>
          <div className="attentionIntro">
            <strong>Start here.</strong>
            <span>These are not predictions or advice. They are places where the report may be unclear, old, or inconsistent.</span>
          </div>
          <div className="riskTiles calm">
            <RiskTile label="Report skips price impact" value={missingSensitivity.length} tone="high" />
            <RiskTile label="Report may be old" value={staleRows.length} tone="medium" />
            <RiskTile label="Unusual source text" value={flags.filter((flag) => flag.flag === 'PROMPT_INJECTION_TEXT').length} tone="high" />
          </div>
          <FlagList flags={highFlags.slice(0, 3)} onOpenRun={onOpenRun} compact />
        </Panel>
        <CopilotPanel
          messages={chatMessages}
          draft={chatDraft}
          setDraft={setChatDraft}
          loading={chatLoading}
          onAsk={onAsk}
          onOpenRun={onOpenRun}
        />
      </section>
      <section className="overviewGrid">
        <Panel title="Suggested Next Steps" action="guided workflow">
          <div className="workflowList">
            <WorkflowCard title="Check skipped explanations" detail="Open reports where costs look meaningful but price impact is not clearly explained." count={missingSensitivity.length} />
            <WorkflowCard title="Refresh old reports" detail="Look again when the report date is too far before the market move." count={staleRows.length} />
            <WorkflowCard title="Resolve conflicting numbers" detail="Compare the quoted pages before trusting a number." count={flags.filter((flag) => flag.flag.includes('AMBIGUOUS')).length} />
          </div>
        </Panel>
        <Panel title="Biggest Fuel or Import Cost" action="share of revenue">
          <div className="barList">
            {topExposure.map((row) => (
              <button key={row.runId} className="barRow" onClick={() => onOpenRun(row.runId, 'documents')}>
                <span>{row.company}</span>
                <div><i style={{ width: `${Math.min(row.fuelShare || 0, 45) * 2}%` }} /></div>
                <strong>{formatPct(row.fuelShare)}</strong>
              </button>
            ))}
          </div>
        </Panel>
      </section>
      <Panel title="Recent Reports" action="quick access">
        <RunTable runs={runs.slice(0, 6)} onOpenRun={onOpenRun} />
      </Panel>
    </div>
  );
}

function CopilotWorkspace({ messages, draft, setDraft, loading, onAsk, onOpenRun }) {
  return (
    <section className="copilotWorkspace">
      <CopilotPanel
        messages={messages}
        draft={draft}
        setDraft={setDraft}
        loading={loading}
        onAsk={onAsk}
        onOpenRun={onOpenRun}
        expanded
      />
      <Panel title="Try Asking" action="starter prompts">
        <div className="promptGrid">
          {[
            'Which company has the biggest fuel cost?',
            'Which reports need a closer look?',
            'Explain this product simply',
            'Summarize SecureFiling in simple words',
            'What unusual source text exists?',
            'Compare ImportMart with peers'
          ].map((prompt) => (
            <button key={prompt} onClick={() => onAsk(prompt)}>{prompt}</button>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function CopilotPanel({ messages, draft, setDraft, loading, onAsk, onOpenRun, expanded = false }) {
  const latestSuggestions = [...messages].reverse().find((item) => item.suggestions?.length)?.suggestions || [];
  return (
    <section className={expanded ? 'copilotPanel expanded' : 'copilotPanel'}>
      <header className="copilotHeader">
        <div>
          <span className="eyebrow"><MessageCircle size={14} /> Disclosure Copilot</span>
          <h2>Ask in plain English</h2>
        </div>
        <Badge tone="ok">Source-aware</Badge>
      </header>
      <div className="chatStream">
        {messages.map((message, index) => (
          <article key={index} className={message.role === 'user' ? 'chatBubble user' : 'chatBubble assistant'}>
            {message.role === 'assistant' && <span className="chatMode">{message.mode === 'ai' ? 'AI answer' : 'From reports'}</span>}
            <p>{message.answer}</p>
            {Boolean(message.sources?.length) && (
              <div className="sourceChips">
                {message.sources.slice(0, 4).map((source, sourceIndex) => (
                  <button key={`${source.run_id}-${sourceIndex}`} onClick={() => onOpenRun(source.run_id, 'documents')}>
                    {source.company}
                  </button>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
      {Boolean(latestSuggestions.length) && (
        <div className="suggestions">
          {latestSuggestions.slice(0, 3).map((item) => (
            <button key={item} onClick={() => onAsk(item)}>{item}</button>
          ))}
        </div>
      )}
      <form className="chatInput" onSubmit={(event) => { event.preventDefault(); onAsk(); }}>
        <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask: what should I look at first?" />
        <button disabled={loading || !draft.trim()}><Send size={16} /></button>
      </form>
    </section>
  );
}

function WorkflowCard({ title, detail, count }) {
  return (
    <article className="workflowCard">
      <span>{count}</span>
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}

function DocumentsWorkspace({ documents, selectedRun, detail, onOpenRun, onReview }) {
  const activeFlags = detail?.flags?.filter((flag) => flag.flag !== 'REVIEW_NOTE') || [];
  return (
    <section className="documentGrid simplified">
      <Panel title="Reports" action={`${documents.length} companies`}>
        <div className="panelNote">Choose a company. The page shows the useful summary first and keeps source detail lower down.</div>
        <div className="documentRows compact">
          {documents.map((doc) => (
            <button key={doc.id} className={doc.latest_run_id === selectedRun ? 'documentRow active' : 'documentRow'} onClick={() => doc.latest_run_id && onOpenRun(doc.latest_run_id, 'documents')}>
              <div>
                <strong>{doc.company}</strong>
                <span>{doc.sector}</span>
              </div>
              <ChevronRight size={16} />
            </button>
          ))}
        </div>
      </Panel>
      <section className="documentMain">
        <RunSummary detail={detail} />
        <ReportSnapshot detail={detail} />
        <EvidenceLedger detail={detail} onReview={onReview} />
        <SourceViewer detail={detail} />
      </section>
      <Panel title="At a Glance" action="summary">
        <div className="quickStats">
          <MiniStat label="Items to review" value={activeFlags.length} />
          <MiniStat label="Answers found" value={(detail?.evidence || []).filter((row) => row.status === 'DISCLOSED').length} />
        </div>
        <div className="sideGuidance">
          <strong>How to read this</strong>
          <span>Start with the plain-English summary. Open evidence only when you want to see the exact wording behind an answer.</span>
          <strong>Best next action</strong>
          <span>{activeFlags.length ? 'Review the highlighted items before sharing this report.' : 'This report looks clear based on the available evidence.'}</span>
        </div>
      </Panel>
    </section>
  );
}

function ReviewQueue({ rows, flags, onOpenRun, onReview }) {
  const highFlags = flags.filter((flag) => flag.severity === 'high');
  const pending = rows.filter((row) => row.review_status === 'pending');
  const missing = pending.filter((row) => row.status !== 'DISCLOSED');
  const needsHuman = pending.filter((row) => row.status === 'REVIEW' || row.status === 'AMBIGUOUS');
  return (
    <section className="reviewGrid simplified">
      <Panel title="Review Inbox" action={`${pending.length} items`}>
        <div className="reviewHero">
          <div>
            <span>Start with the clearest decisions</span>
            <strong>{missing.length} missing or unclear answers</strong>
            <p>Accept what looks right, mark follow-up for anything uncertain, and reject noisy evidence.</p>
          </div>
          <div className="quickStats vertical">
            <MiniStat label="Important" value={highFlags.length} />
            <MiniStat label="Needs human" value={needsHuman.length} />
          </div>
        </div>
        <div className="reviewRows">
          {pending.slice(0, 10).map((row) => (
            <article key={row.id} className="reviewRow focused">
              <div>
                <span>{row.company}</span>
                <strong>{labelField(row.field)}</strong>
                <p>{simpleStatus(row.status)} - {row.value_text || 'No clear answer found'}</p>
                {row.quote && <small>{row.quote}</small>}
              </div>
              <div className="rowActions">
                <button title="Accept" onClick={() => onReview(row.id, 'accepted')}><Check size={15} /></button>
                <button title="Follow up" onClick={() => onReview(row.id, 'needs_followup')}><AlertTriangle size={15} /></button>
                <button title="Reject" onClick={() => onReview(row.id, 'rejected')}><X size={15} /></button>
              </div>
            </article>
          ))}
        </div>
      </Panel>
      <Panel title="Why Items Were Flagged" action={`${highFlags.length} important`}>
        <FlagList flags={highFlags.slice(0, 8)} onOpenRun={onOpenRun} />
      </Panel>
    </section>
  );
}

function PeerMatrix({ rows, onOpenRun }) {
  const sorted = [...rows].sort((a, b) => (b.fuelShare || 0) - (a.fuelShare || 0));
  const top = sorted[0];
  return (
    <Panel title="Company Comparison" action={`${rows.length} companies`}>
      <div className="compareHero">
        <div>
          <span>Simple peer view</span>
          <strong>{top ? `${top.company} has the largest visible cost exposure` : 'No comparison yet'}</strong>
          <p>This view compares what the reports disclose. It is not advice or a prediction.</p>
        </div>
        <div className="quickStats vertical">
          <MiniStat label="Companies" value={rows.length} />
          <MiniStat label="Flagged" value={rows.filter((row) => row.flags.length).length} />
        </div>
      </div>
      <div className="compareCards">
        {sorted.map((row) => (
          <button key={row.runId} className="compareCard" onClick={() => onOpenRun(row.runId, 'documents')}>
            <div className="compareCardTop">
              <div>
                <strong>{row.company}</strong>
                <span>{row.sector}</span>
              </div>
              {row.flags.length ? <Badge tone="warn">{row.flags.length} item{row.flags.length > 1 ? 's' : ''}</Badge> : <Badge tone="ok">Clear</Badge>}
            </div>
            <div className="exposureBar">
              <span style={{ width: `${Math.min(row.fuelShare || 0, 45) * 2}%` }} />
            </div>
            <div className="compareFacts">
              <span><b>{formatPct(row.fuelShare)}</b> cost size</span>
              <span><b>{formatValue(row.fxExposure, 'crore')}</b> currency exposure</span>
              <span><b>{row.fuelSensitivity === null ? 'Missing' : 'Explained'}</b> fuel impact</span>
            </div>
            <FlagPills flags={row.flags} />
          </button>
        ))}
      </div>
    </Panel>
  );
}

function Controls({ loading, onSeed, onAnalyze }) {
  return (
    <section className="controlsGrid">
      <Panel title="Workspace Controls" action="local prototype">
        <div className="controlRows">
          <ControlRow title="Load demo reports" detail="Adds sample companies and reports so the product has something to check." action={<button onClick={onSeed} disabled={loading}><Database size={16} /> Load</button>} />
          <ControlRow title="Check all reports" detail="Finds quoted facts, missing explanations, old reports, and items that need review." action={<button onClick={onAnalyze} disabled={loading}><Play size={16} /> Check</button>} />
        </div>
      </Panel>
      <Panel title="How The AI Is Kept Honest" action="simple version">
        <div className="boundary">
          <div><strong>Find</strong><span>The system looks for useful report passages.</span></div>
          <div><strong>Check</strong><span>Every number must link back to exact text.</span></div>
          <div><strong>Flag</strong><span>Unclear, old, or conflicting items are highlighted.</span></div>
          <div><strong>Review</strong><span>A human accepts, rejects, or follows up.</span></div>
        </div>
      </Panel>
    </section>
  );
}

function ReportSnapshot({ detail }) {
  if (!detail) return null;
  const byField = Object.fromEntries((detail.evidence || []).map((row) => [row.field, row]));
  const flags = (detail.flags || []).filter((flag) => flag.flag !== 'REVIEW_NOTE');
  const fuelCost = byField.fuel_cost_crore;
  const fuelImpact = byField.fuel_sensitivity_impact_crore;
  const fxExposure = byField.fx_net_exposure_crore;
  const headline = flags.length
    ? `${flags.length} thing${flags.length > 1 ? 's' : ''} to check before trusting this report`
    : 'No major issues found in this report';
  return (
    <Panel title="Plain-English Summary" action="start here">
      <div className="snapshotHero">
        <div>
          <span>{detail.run.sector} report</span>
          <strong>{headline}</strong>
          <p>{summarySentence(detail)}</p>
        </div>
        <Badge tone={flags.length ? 'warn' : 'ok'}>{flags.length ? 'Needs a look' : 'Looks clear'}</Badge>
      </div>
      <div className="snapshotGrid">
        <SnapshotCard label="Cost mentioned" value={formatEvidenceValue(fuelCost)} detail={fuelCost?.quote || 'No source text captured.'} />
        <SnapshotCard label="Price impact explained" value={fuelImpact?.status === 'DISCLOSED' ? formatEvidenceValue(fuelImpact) : 'Not clearly explained'} detail={fuelImpact?.quote || 'The report did not give a clean price-impact number.'} />
        <SnapshotCard label="Currency exposure" value={formatEvidenceValue(fxExposure)} detail={fxExposure?.quote || 'No currency exposure passage found.'} />
      </div>
    </Panel>
  );
}

function SnapshotCard({ label, value, detail }) {
  return (
    <article className="snapshotCard">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function RunSummary({ detail }) {
  if (!detail) return <Empty title="No report selected" text="Choose a company to see what the report says." />;
  const run = detail.run;
  const flags = detail.flags || [];
  return (
    <section className="runSummary">
      <div>
        <h2>{run.company}</h2>
        <p>{run.sector}</p>
      </div>
      <div className="summaryBadges">
        {Boolean(run.review_required) && <Badge tone="warn">Needs review</Badge>}
        {Boolean(run.stale) && <Badge tone="warn">May be old</Badge>}
        {flags.some((flag) => flag.severity === 'high') ? <Badge tone="danger">Important item</Badge> : <Badge tone="ok">Looks clear</Badge>}
      </div>
    </section>
  );
}

function EvidenceLedger({ detail, onReview }) {
  if (!detail) return null;
  const rows = detail.evidence || [];
  return (
    <Panel title="Evidence" action="source-backed">
      <div className="evidenceCards">
        {rows.map((row) => (
          <article key={row.id} className={row.status === 'DISCLOSED' ? 'evidenceCard' : 'evidenceCard needsReview'}>
            <div className="evidenceCardTop">
              <div>
                <span>{labelField(row.field)}</span>
                <strong>{formatEvidenceValue(row)}</strong>
              </div>
              <Status value={row.status} />
            </div>
            <p>{row.quote || row.verifier_note || 'No clear supporting text was found for this answer.'}</p>
            <div className="evidenceFooter">
              <span>{row.page_number ? 'Source cited' : 'No source cited'}</span>
              <div className="rowActions">
                <button title="Accept" onClick={() => onReview(row.id, 'accepted')}><Check size={14} /></button>
                <button title="Follow up" onClick={() => onReview(row.id, 'needs_followup')}><AlertTriangle size={14} /></button>
                <button title="Reject" onClick={() => onReview(row.id, 'rejected')}><X size={14} /></button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function SourceViewer({ detail }) {
  if (!detail) return null;
  const citedPages = new Set((detail.evidence || []).filter((row) => row.page_number).map((row) => row.page_number));
  const pages = (detail.pages || []).filter((page) => citedPages.has(page.page_number));
  if (!pages.length) return null;
  return (
    <Panel title="Source Excerpts" action="optional detail">
      <div className="sourceGrid">
        {pages.map((page) => (
          <article key={page.page_number} className={citedPages.has(page.page_number) ? 'sourcePage cited' : 'sourcePage'}>
            <strong>Source excerpt</strong>
            <p>{page.text}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function MetricGrid({ items }) {
  return (
    <section className="metricGrid">
      {items.map(([label, value, sub]) => (
        <div className="metric" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
          <small>{sub}</small>
        </div>
      ))}
    </section>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="miniStat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <header className="panelHeader">
        <h2>{title}</h2>
        {action && <span>{action}</span>}
      </header>
      {children}
    </section>
  );
}

function RiskTile({ label, value, tone }) {
  return (
    <div className={`riskTile ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RunTable({ runs, onOpenRun }) {
  if (!runs.length) return <Empty title="No reports" text="Load demo data to populate the workspace." />;
  return (
    <div className="recentCards">
      {runs.map((run) => (
        <button key={run.id} className="recentCard" onClick={() => onOpenRun(run.id, 'documents')}>
          <div>
            <strong>{run.company}</strong>
            <span>{run.sector}</span>
          </div>
          {run.review_required ? <Badge tone="warn">Needs review</Badge> : <Badge tone="ok">Looks clear</Badge>}
        </button>
      ))}
    </div>
  );
}

function FlagList({ flags, onOpenRun, compact = false }) {
  if (!flags.length) return <Empty title="No flags" text="No high-priority flags in the current run set." />;
  return (
    <div className={compact ? 'flagList compact' : 'flagList'}>
      {flags.map((flag) => (
        <button key={flag.id} className={`flagRow ${flag.severity}`} onClick={() => onOpenRun(flag.run_id, 'documents')}>
          <div>
            <strong>{simpleFlag(flag.flag)}</strong>
            <span>{flag.company}</span>
            {flag.note && <p>{flag.note}</p>}
          </div>
          <ChevronRight size={15} />
        </button>
      ))}
    </div>
  );
}

function FlagPills({ flags }) {
  if (!flags.length) return <span className="muted">None</span>;
  return (
    <div className="flagPills">
      {flags.slice(0, 3).map((flag) => <span key={flag}>{simpleFlag(flag)}</span>)}
      {flags.length > 3 && <span>+{flags.length - 3}</span>}
    </div>
  );
}

function ControlRow({ title, detail, action }) {
  return (
    <div className="controlRow">
      <div>
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>
      {action}
    </div>
  );
}

function Badge({ tone, children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function Status({ value }) {
  const tone = value === 'DISCLOSED' ? 'ok' : value === 'NOT_DISCLOSED' ? 'missing' : 'warn';
  return <span className={`status ${tone}`}>{simpleStatus(value)}</span>;
}

function Empty({ title, text }) {
  return (
    <div className="empty">
      <ShieldCheck size={17} />
      <div>
        <strong>{title}</strong>
        <span>{text}</span>
      </div>
    </div>
  );
}

function buildPeerRows(details) {
  return details.map((detail) => {
    const byField = Object.fromEntries((detail.evidence || []).map((row) => [row.field, row]));
    return {
      runId: detail.run.id,
      company: detail.run.company,
      sector: detail.run.sector,
      stale: Boolean(detail.run.stale),
      fuelShare: detail.run.fuel_cost_share_revenue_pct,
      fuelSensitivity: num(byField.fuel_sensitivity_impact_crore),
      fxExposure: num(byField.fx_net_exposure_crore),
      fxSensitivity: num(byField.fx_sensitivity_impact_crore),
      hedgeRatio: num(byField.hedge_ratio_pct),
      flags: (detail.flags || []).filter((flag) => flag.flag !== 'REVIEW_NOTE').map((flag) => flag.flag)
    };
  });
}

function buildReviewRows(details) {
  return details.flatMap((detail) => (detail.evidence || [])
    .filter((row) => row.status !== 'DISCLOSED' || row.review_status !== 'accepted')
    .map((row) => ({
      ...row,
      company: detail.run.company,
      sector: detail.run.sector,
      runId: detail.run.id
    })));
}

function num(row) {
  if (!row || row.numeric_value === null || row.numeric_value === undefined) return null;
  return Number(row.numeric_value);
}

function formatPct(value) {
  if (value === null || value === undefined) return 'n/a';
  return `${Number(value).toFixed(1)}%`;
}

function formatValue(value, unit) {
  if (value === null || value === undefined) return 'Not disclosed';
  if (unit === '%') return `${Number(value).toFixed(0)}%`;
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
}

function formatEvidenceValue(row) {
  if (!row || !row.value_text) return 'Not disclosed';
  return `${row.value_text}${row.unit ? ` ${row.unit}` : ''}`;
}

function summarySentence(detail) {
  const byField = Object.fromEntries((detail.evidence || []).map((row) => [row.field, row]));
  const fuelCost = formatEvidenceValue(byField.fuel_cost_crore);
  const fuelImpact = byField.fuel_sensitivity_impact_crore?.status === 'DISCLOSED';
  const fxImpact = byField.fx_sensitivity_impact_crore?.status === 'DISCLOSED';
  const parts = [`It mentions ${fuelCost} of fuel or import cost`];
  parts.push(fuelImpact ? 'explains fuel-price impact' : 'does not clearly explain fuel-price impact');
  parts.push(fxImpact ? 'and explains currency impact.' : 'and leaves currency impact unclear.');
  return parts.join(', ');
}

function labelField(field) {
  const labels = {
    fuel_cost_crore: 'Fuel/import cost',
    fuel_sensitivity_impact_crore: 'Fuel price impact',
    fx_net_exposure_crore: 'Currency exposure',
    fx_sensitivity_impact_crore: 'Currency impact',
    hedge_ratio_pct: 'Hedged amount',
    fuel_sensitivity_present: 'Fuel impact explained',
    fx_sensitivity_present: 'Currency impact explained',
    pass_through_present: 'Can pass cost to customers',
    prompt_injection_detected: 'Unusual source instructions'
  };
  return labels[field] || field.replaceAll('_', ' ');
}

function simpleFlag(flag) {
  const labels = {
    MISSING_FUEL_SENSITIVITY: 'Missing fuel-price explanation',
    PROMPT_INJECTION_TEXT: 'Unusual source text',
    AMBIGUOUS_DISCLOSURE: 'Conflicting numbers',
    AMBIGUOUS_FX_SENSITIVITY_IMPACT_CRORE: 'Conflicting currency-impact numbers',
    STALE_DISCLOSURE: 'Old report',
    REVIEW_NOTE: 'Review note'
  };
  return labels[flag] || flag.replaceAll('_', ' ').toLowerCase();
}

function simpleStatus(value) {
  const labels = {
    DISCLOSED: 'Found',
    NOT_DISCLOSED: 'Not found',
    REVIEW: 'Needs review',
    AMBIGUOUS: 'Unclear',
    PARTIAL: 'Partial',
    NOT_FOUND: 'Not found'
  };
  return labels[value] || value;
}

createRoot(document.getElementById('root')).render(<App />);
