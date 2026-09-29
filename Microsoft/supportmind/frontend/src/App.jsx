import { useEffect, useState } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'supportmind_token';
const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/customers', label: 'Customers' },
  { to: '/tickets', label: 'Tickets' },
  { to: '/agent', label: 'AI Agent' },
  { to: '/memory', label: 'Memory' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/demo', label: 'Demo Mode' }
];

async function api(path, options = {}) {
  const { auth = true, ...fetchOptions } = options;
  const token = localStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      ...(fetchOptions.body ? { 'Content-Type': 'application/json' } : {}),
      ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
      ...fetchOptions.headers
    }
  });
  if (response.status === 401 && auth) {
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event('supportmind:unauthorized'));
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status}).`);
    error.payload = data;
    error.status = response.status;
    throw error;
  }
  return data;
}

function date(value) {
  return value ? new Date(value).toLocaleString() : 'Not available';
}

function ErrorNotice({ children }) {
  return <div className="notice error-notice" role="alert">{children}</div>;
}

function EmptyState({ children }) {
  return <div className="empty-state">{children}</div>;
}

function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(localStorage.getItem(TOKEN_KEY)));
  useEffect(() => {
    const expire = () => setAuthenticated(false);
    window.addEventListener('supportmind:unauthorized', expire);
    return () => window.removeEventListener('supportmind:unauthorized', expire);
  }, []);

  if (!authenticated) return <LoginPage onLogin={() => setAuthenticated(true)} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block"><div className="brand-icon">S</div><div><div className="brand-name">SupportMind</div><div className="brand-tag">Support that remembers</div></div></div>
        <nav className="nav-list">{navItems.map((item) => <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>{item.label}</NavLink>)}</nav>
      </aside>
      <main className="main-panel">
        <div className="topbar"><span className="muted">Customer support workspace</span><button className="quiet-button" onClick={() => { localStorage.removeItem(TOKEN_KEY); setAuthenticated(false); }}>Sign out</button></div>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/tickets" element={<TicketsPage />} />
          <Route path="/agent" element={<AgentPage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/demo" element={<DemoPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await api('/api/auth/login', { method: 'POST', auth: false, body: JSON.stringify({ email, password }) });
      localStorage.setItem(TOKEN_KEY, result.access_token);
      onLogin();
    } catch (err) {
      setError(err.message || 'Unable to sign in. Check that the backend is available.');
    } finally {
      setLoading(false);
    }
  }
  return <main className="login-shell"><form className="login-panel" onSubmit={submit}><div className="brand-icon">S</div><p className="eyebrow">SUPPORTMIND</p><h1>Sign in to your workspace</h1><label>Email<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error && <ErrorNotice>{error}</ErrorNotice>}<button className="primary-button" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button></form></main>;
}

function useInitialData(loader, fallback = 'Could not load data.') {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    loader().then((value) => { if (active) setData(value); }).catch((err) => { if (active) setError(err.message || fallback); });
    return () => { active = false; };
  }, []);
  return { data, error };
}

function PageHeading({ eyebrow, children, action }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{children}</h1></div>{action}</div>;
}

function StatCard({ title, value }) {
  return <div className="stat-card"><div className="stat-title">{title}</div><div className="stat-value">{value ?? 'No data'}</div></div>;
}

function DashboardPage() {
  const { data, error } = useInitialData(() => Promise.all([api('/api/analytics/dashboard'), api('/api/tickets'), api('/api/customers')]), 'Dashboard data is unavailable.');
  if (error) return <div className="page"><PageHeading eyebrow="OVERVIEW">Dashboard</PageHeading><ErrorNotice>{error}</ErrorNotice></div>;
  if (!data) return <div className="page"><PageHeading eyebrow="OVERVIEW">Dashboard</PageHeading><p className="muted">Loading workspace data...</p></div>;
  const [metrics, tickets, customers] = data;
  const customerNames = new Map(customers.map((customer) => [customer.id, customer.name]));
  const stats = [['Customers', metrics.total_customers], ['Active customers', metrics.active_customers], ['Tickets', metrics.total_tickets], ['Open tickets', metrics.open_tickets], ['Resolved tickets', metrics.resolved_tickets], ['Memory events', metrics.total_memory_events], ['Hindsight retained', metrics.hindsight_retention_count], ['Hindsight retrievals', metrics.hindsight_retrieval_count]];
  return <div className="page"><PageHeading eyebrow="OVERVIEW">Dashboard</PageHeading><div className="stats-grid">{stats.map(([title, value]) => <StatCard key={title} title={title} value={value} />)}</div><section className="panel"><h2>Recent tickets</h2>{tickets.length ? <div className="table-wrap"><table><thead><tr><th>Ticket</th><th>Customer</th><th>Status</th><th>Created</th></tr></thead><tbody>{tickets.slice(0, 6).map((ticket) => <tr key={ticket.id}><td>{ticket.title}</td><td>{customerNames.get(ticket.customer_id) || 'Unknown customer'}</td><td>{ticket.status}</td><td>{date(ticket.created_at)}</td></tr>)}</tbody></table></div> : <EmptyState>No ticket data available yet.</EmptyState>}</section></div>;
}

function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [selectedId, setSelectedId] = useState('');
  const [detail, setDetail] = useState(null);
  const [memory, setMemory] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api('/api/customers'), api('/api/tickets')]).then(([customerRows, ticketRows]) => { setCustomers(customerRows); setTickets(ticketRows); if (customerRows[0]) setSelectedId(String(customerRows[0].id)); }).catch((err) => setError(err.message || 'Customer data is unavailable.')).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!selectedId) { setDetail(null); setMemory(null); return undefined; }
    let active = true;
    const customerTickets = tickets.filter((ticket) => ticket.customer_id === Number(selectedId));
    Promise.all([api(`/api/customers/${selectedId}`), api(`/api/customers/${selectedId}/memory`), Promise.all(customerTickets.slice(0, 4).map((ticket) => api(`/api/tickets/${ticket.id}/messages`)))]).then(([profile, memories, messageGroups]) => {
      if (!active) return;
      setDetail({ ...profile, tickets: customerTickets });
      setMemory(memories);
      setInteractions(messageGroups.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5));
    }).catch((err) => { if (active) setError(err.message || 'Customer details are unavailable.'); });
    return () => { active = false; };
  }, [selectedId, tickets]);
  if (loading) return <div className="page"><PageHeading eyebrow="ACCOUNTS">Customers</PageHeading><p className="muted">Loading customers...</p></div>;
  return <div className="page"><PageHeading eyebrow="ACCOUNTS" action={<label className="field-label">Customer<select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}><option value="">Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label>}>Customers</PageHeading>{error && <ErrorNotice>{error}</ErrorNotice>}{!customers.length && !error && <EmptyState>No customers are available.</EmptyState>}{customers.length > 0 && <section className="panel table-panel"><div className="table-wrap"><table><thead><tr><th>Customer</th><th>Company</th><th>External ID</th><th>Tickets</th><th>Open</th><th>Last interaction</th><th>Status</th></tr></thead><tbody>{customers.map((customer) => { const customerTickets = tickets.filter((ticket) => ticket.customer_id === customer.id); return <tr key={customer.id} className={String(customer.id) === selectedId ? 'selected-row' : ''} onClick={() => setSelectedId(String(customer.id))}><td><button className="text-button">{customer.name}</button></td><td>{customer.company || 'Not provided'}</td><td>{customer.external_customer_id}</td><td>{customerTickets.length}</td><td>{customerTickets.filter((ticket) => ticket.status === 'OPEN').length}</td><td>{date(customer.last_interaction_at)}</td><td>{customer.status}</td></tr>; })}</tbody></table></div></section>}{detail && <><section className="panel profile-panel"><p className="eyebrow">CUSTOMER PROFILE</p><h2>{detail.name}</h2><dl className="profile-grid"><div><dt>Company</dt><dd>{detail.company || 'Not provided'}</dd></div><div><dt>External ID</dt><dd>{detail.external_customer_id}</dd></div><div><dt>Email</dt><dd>{detail.email || 'Not provided'}</dd></div><div><dt>Phone</dt><dd>{detail.phone || 'Not provided'}</dd></div><div><dt>Status</dt><dd>{detail.status}</dd></div><div><dt>Last interaction</dt><dd>{date(detail.last_interaction_at)}</dd></div></dl></section><div className="panel-grid"><section className="panel"><h2>Ticket history <span className="count">{detail.tickets.length}</span></h2>{detail.tickets.length ? <ul className="list">{detail.tickets.map((ticket) => <li key={ticket.id}><strong>#{ticket.id} · {ticket.title}</strong><span className="muted">{ticket.category} · {ticket.priority} · {ticket.status}</span></li>)}</ul> : <EmptyState>No tickets for this customer.</EmptyState>}</section><section className="panel"><h2>Hindsight memories</h2>{memory?.hindsight_available ? <><p className="muted">{memory.memory_count} memories retrieved from Hindsight Cloud</p>{memory.memories.map((item, index) => <p className="memory-summary" key={item.id || index}>{item.summary}</p>)}{!memory.memory_count && <EmptyState>No relevant Hindsight memories found.</EmptyState>}</> : <p className="muted">Hindsight memory is temporarily unavailable; no historical memories are shown.</p>}</section></div><section className="panel"><h2>Latest interactions</h2>{interactions.length ? <ul className="list">{interactions.map((item) => <li key={item.id}><span><strong>{item.sender_type}</strong> · {date(item.created_at)}</span><span>{item.content}</span></li>)}</ul> : <EmptyState>No saved interactions yet.</EmptyState>}</section></>}</div>;
}

function TicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [selectedId, setSelectedId] = useState('');
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memory, setMemory] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([api('/api/tickets'), api('/api/customers')]).then(([rows, customerRows]) => { setTickets(rows); setCustomers(customerRows); if (rows[0]) setSelectedId(String(rows[0].id)); }).catch((err) => setError(err.message || 'Tickets are unavailable.')).finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (!selectedId) { setSelected(null); setMessages([]); setMemory(null); return undefined; }
    let active = true;
    const ticket = tickets.find((item) => item.id === Number(selectedId));
    Promise.all([api(`/api/tickets/${selectedId}`), api(`/api/tickets/${selectedId}/messages`), ticket ? api(`/api/customers/${ticket.customer_id}/memory?query=${encodeURIComponent(ticket.title)}`) : Promise.resolve(null)]).then(([ticketData, messageData, memoryData]) => { if (active) { setSelected(ticketData); setMessages(messageData); setMemory(memoryData); } }).catch((err) => { if (active) setError(err.message || 'Ticket details are unavailable.'); });
    return () => { active = false; };
  }, [selectedId, tickets]);
  async function updateStatus(status) {
    if (!selected) return;
    setSaving(true);
    setError('');
    try {
      const updated = await api(`/api/tickets/${selected.id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
      setSelected(updated);
      setTickets((rows) => rows.map((ticket) => ticket.id === updated.id ? updated : ticket));
    } catch (err) { setError(err.message || 'Ticket status could not be updated.'); }
    finally { setSaving(false); }
  }
  const visible = tickets.filter((ticket) => filter === 'ALL' || ticket.status === filter);
  const customerNames = new Map(customers.map((customer) => [customer.id, customer.name]));
  if (loading) return <div className="page"><PageHeading eyebrow="WORK QUEUE">Tickets</PageHeading><p className="muted">Loading tickets...</p></div>;
  return <div className="page"><PageHeading eyebrow="WORK QUEUE" action={<label className="field-label">Status<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="ALL">All</option><option value="OPEN">Open</option><option value="PENDING">Pending</option><option value="RESOLVED">Resolved</option></select></label>}>Tickets</PageHeading>{error && <ErrorNotice>{error}</ErrorNotice>}{!tickets.length && <EmptyState>No tickets are available.</EmptyState>}<section className="panel table-panel"><div className="table-wrap"><table><thead><tr><th>Ticket</th><th>Customer</th><th>Category</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead><tbody>{visible.map((ticket) => <tr key={ticket.id} className={String(ticket.id) === selectedId ? 'selected-row' : ''} onClick={() => setSelectedId(String(ticket.id))}><td><button className="text-button">#{ticket.id} · {ticket.title}</button></td><td>{customerNames.get(ticket.customer_id) || 'Unknown customer'}</td><td>{ticket.category}</td><td>{ticket.priority}</td><td>{ticket.status}</td><td>{date(ticket.created_at)}</td></tr>)}</tbody></table></div>{tickets.length > 0 && !visible.length && <EmptyState>No tickets match this status.</EmptyState>}</section>{selected && <div className="panel-grid detail-grid"><section className="panel"><div className="ticket-header"><div><p className="eyebrow">TICKET #{selected.id}</p><h2>{selected.title}</h2><p className="muted">{customerNames.get(selected.customer_id) || 'Unknown customer'} · {selected.category} · {selected.priority}</p></div><label className="field-label">Status<select disabled={saving} value={selected.status} onChange={(event) => updateStatus(event.target.value)}><option value="OPEN">Open</option><option value="PENDING">Pending</option><option value="RESOLVED">Resolved</option></select></label></div><p className="muted detail-date">Created {date(selected.created_at)} · Updated {date(selected.updated_at)}</p><h3>Conversation</h3>{messages.length ? <div className="conversation-list">{messages.map((message) => <article className="conversation-item" key={message.id}><div><strong>{message.sender_type}</strong><time>{date(message.created_at)}</time></div><p>{message.content}</p></article>)}</div> : <EmptyState>No messages on this ticket.</EmptyState>}</section><section className="panel"><h2>Related memory context</h2>{memory?.hindsight_available ? <>{memory.memories.map((item, index) => <article className="memory-summary" key={item.id || index}>{item.summary}</article>)}{!memory.memory_count && <EmptyState>No related memories retrieved.</EmptyState>}</> : <p className="muted">Hindsight memory is temporarily unavailable for this customer.</p>}</section></div>}</div>;
}

function AgentPage() {
  const [customers, setCustomers] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [customerId, setCustomerId] = useState('');
  const [ticketId, setTicketId] = useState('');
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [memory, setMemory] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => { api('/api/customers').then((rows) => { setCustomers(rows); if (rows[0]) setCustomerId(String(rows[0].id)); }).catch((err) => setError(err.message || 'Customer list is unavailable.')); }, []);
  useEffect(() => {
    if (!customerId) { setTickets([]); setTicketId(''); return; }
    api(`/api/tickets?customer_id=${customerId}`).then(setTickets).catch((err) => setError(err.message || 'Ticket list is unavailable.'));
    setTicketId(''); setMessages([]); setMemory(null);
  }, [customerId]);
  useEffect(() => { if (ticketId) api(`/api/tickets/${ticketId}/messages`).then(setMessages).catch((err) => setError(err.message || 'Conversation history is unavailable.')); else setMessages([]); }, [ticketId]);
  async function send() {
    const content = draft.trim();
    if (!customerId || !content || loading) return;
    setLoading(true); setError(''); setMemory(null);
    try {
      const result = await api('/api/agent/chat', { method: 'POST', body: JSON.stringify({ customer_id: Number(customerId), ticket_id: ticketId ? Number(ticketId) : null, message: content }) });
      setDraft('');
      setTicketId(String(result.ticket_id));
      const ticket = await api(`/api/tickets/${result.ticket_id}`);
      setTickets((rows) => [ticket, ...rows.filter((row) => row.id !== ticket.id)]);
      setMessages(await api(`/api/tickets/${result.ticket_id}/messages`));
      setMemory(result);
    } catch (err) {
      setError(err.message || 'The agent could not complete this request.');
      const status = err.payload?.memory_status;
      if (status) setMemory({ memory_available: status.available, memory_used: status.used, memory_count: status.count, memory_references: status.references || [], memory_retained: status.retained });
    }
    finally { setLoading(false); }
  }
  return <div className="page"><PageHeading eyebrow="ASSISTED SUPPORT">AI Support Agent</PageHeading><div className="selector-row"><label className="field-label">Customer<select value={customerId} onChange={(event) => setCustomerId(event.target.value)}><option value="">Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label><label className="field-label">Ticket<select value={ticketId} onChange={(event) => setTicketId(event.target.value)}><option value="">New conversation</option>{tickets.map((ticket) => <option key={ticket.id} value={ticket.id}>#{ticket.id} · {ticket.title}</option>)}</select></label></div>{error && <ErrorNotice>{error}</ErrorNotice>}<div className="chat-box">{messages.map((message) => <article key={message.id} className={`chat-message ${message.sender_type === 'CUSTOMER' ? 'customer' : 'agent'}`}><small>{message.sender_type} · {date(message.created_at)}</small><p>{message.content}</p></article>)}{!messages.length && <EmptyState>Choose a customer and start a support conversation.</EmptyState>}</div>{memory && <section className="panel memory-status"><h2>Hindsight status</h2><p>Memory used: <strong>{memory.memory_available ? (memory.memory_used ? 'Yes' : 'No') : 'Unavailable'}</strong></p><p>Memories recalled: <strong>{memory.memory_count}</strong></p><p>Memory retained: <strong>{memory.memory_retained ? 'Yes' : 'No'}</strong></p>{(memory.memory_references || []).map((reference, index) => <p className="memory-summary" key={index}>{reference}</p>)}{!memory.memory_available && <p className="muted">Hindsight memory is temporarily unavailable. The conversation can continue, but historical memory could not be retrieved.</p>}</section>}<div className="chat-input-row"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(); } }} placeholder="Describe the customer's support issue..." rows="2"/><button className="primary-button" disabled={loading || !customerId || !draft.trim()} onClick={send}>{loading ? 'Sending...' : 'Send'}</button></div></div>;
}

function MemoryPage() {
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState('');
  const [query, setQuery] = useState('');
  const [memories, setMemories] = useState([]);
  const [summary, setSummary] = useState('');
  const [available, setAvailable] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => { api('/api/customers').then((rows) => { setCustomers(rows); if (rows[0]) setCustomerId(String(rows[0].id)); }).catch((err) => setError(err.message || 'Customer list is unavailable.')); }, []);
  async function search(action) {
    if (!customerId || !query.trim() || loading) return;
    setLoading(true); setError(''); setSummary('');
    try {
      const result = await api(`/api/memory/${customerId}/${action}`, { method: 'POST', body: JSON.stringify({ query }) });
      setMemories(result.memories || []); setAvailable(Boolean(result.hindsight_available)); setSummary(result.summary || '');
    } catch (err) { setError(err.message || 'Unable to retrieve customer memories.'); }
    finally { setLoading(false); }
  }
  return <div className="page"><PageHeading eyebrow="PERSISTENT CONTEXT">Memory Inspector</PageHeading><p className="muted">Memory results are retrieved from Hindsight Cloud for the selected customer.</p><section className="panel"><div className="selector-row"><label className="field-label">Customer<select value={customerId} onChange={(event) => { setCustomerId(event.target.value); setMemories([]); setSummary(''); setAvailable(null); }}><option value="">Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label></div><div className="chat-input-row"><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') search('recall'); }} placeholder="Search this customer's history..."/><button className="primary-button" onClick={() => search('recall')} disabled={loading || !customerId || !query.trim()}>{loading ? 'Searching...' : 'Recall'}</button><button className="secondary-button" onClick={() => search('reflect')} disabled={loading || !customerId || !query.trim()}>Reflect</button></div></section>{error && <ErrorNotice>{error}</ErrorNotice>}{loading && <p className="muted">Contacting Hindsight Cloud...</p>}{available === false && <ErrorNotice>Hindsight memory is temporarily unavailable. No local fallback is presented as Hindsight data.</ErrorNotice>}{summary && <section className="panel"><h2>Customer memory summary</h2><p className="memory-summary">{summary}</p></section>}{available === true && <section className="panel"><h2>Retrieved from Hindsight Cloud <span className="count">{memories.length}</span></h2>{memories.length ? <div className="memory-grid">{memories.map((item, index) => <article className="memory-card" key={item.id || index}><div className="memory-meta"><span className="badge info">{item.type || 'Memory'}</span>{item.relevance != null && <span className="badge neutral">Relevance {item.relevance}</span>}</div><p>{item.summary}</p>{item.source && <small className="muted">Source: {item.source}</small>}{item.date && <small className="muted">Date: {date(item.date)}</small>}</article>)}</div> : <EmptyState>No relevant memories were returned by Hindsight Cloud.</EmptyState>}</section>}{available === null && !loading && !error && <EmptyState>Select a customer and query to inspect persistent memory.</EmptyState>}</div>;
}

function AnalyticsPage() {
  const { data, error } = useInitialData(() => api('/api/analytics/dashboard'), 'Analytics data is unavailable.');
  if (error) return <div className="page"><PageHeading eyebrow="MEASUREMENT">Analytics</PageHeading><ErrorNotice>{error}</ErrorNotice></div>;
  if (!data) return <div className="page"><PageHeading eyebrow="MEASUREMENT">Analytics</PageHeading><p className="muted">Loading analytics...</p></div>;
  const stats = [['Customers', data.total_customers], ['Tickets', data.total_tickets], ['Agent interactions', data.agent_interactions], ['Average tickets per customer', data.average_tickets_per_customer], ['Memory events', data.total_memory_events], ['Hindsight retentions', data.hindsight_retention_count], ['Hindsight retrievals', data.hindsight_retrieval_count], ['Resolved tickets', data.resolved_tickets]];
  const groups = [['Tickets by status', data.tickets_by_status], ['Tickets by priority', data.tickets_by_priority]];
  return <div className="page"><PageHeading eyebrow="MEASUREMENT">Analytics</PageHeading><div className="stats-grid">{stats.map(([title, value]) => <StatCard key={title} title={title} value={value ?? 'No data'} />)}</div><div className="panel-grid">{groups.map(([title, values]) => <section className="panel" key={title}><h2>{title}</h2>{Object.keys(values || {}).length ? <ul className="metric-list">{Object.entries(values).map(([key, value]) => <li key={key}><span>{key}</span><strong>{value}</strong></li>)}</ul> : <EmptyState>No ticket data available yet.</EmptyState>}</section>)}</div><section className="panel"><h2>Tickets over time</h2>{data.tickets_over_time?.length ? <ul className="metric-list">{data.tickets_over_time.map((item) => <li key={item.month}><span>{item.month}</span><strong>{item.count}</strong></li>)}</ul> : <EmptyState>No ticket data available yet.</EmptyState>}</section></div>;
}

function DemoPage() {
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState('');
  const [tickets, setTickets] = useState([]);
  const [ticketId, setTicketId] = useState('');
  const [draft, setDraft] = useState('');
  const [baseline, setBaseline] = useState(null);
  const [hindsightResult, setHindsightResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => { api('/api/customers').then((rows) => { setCustomers(rows); const preferred = rows.find((customer) => customer.name.toLowerCase() === 'rahul kumar'); setCustomerId(String((preferred || rows[0])?.id || '')); }).catch((err) => setError(err.message || 'Customer list is unavailable.')); }, []);
  useEffect(() => { if (!customerId) { setTickets([]); setTicketId(''); return; } api(`/api/tickets?customer_id=${customerId}`).then(setTickets).catch((err) => setError(err.message || 'Ticket list is unavailable.')); }, [customerId]);
  async function run(useMemory) {
    if (!customerId || !draft.trim() || loading) return;
    setLoading(true); setError('');
    try {
      const result = await api('/api/agent/chat', { method: 'POST', body: JSON.stringify({ customer_id: Number(customerId), ticket_id: ticketId ? Number(ticketId) : null, message: draft.trim(), use_memory: useMemory }) });
      if (result.ticket_id) setTicketId(String(result.ticket_id));
      if (result.ticket_id) {
        const ticket = await api(`/api/tickets/${result.ticket_id}`);
        setTickets((rows) => [ticket, ...rows.filter((row) => row.id !== ticket.id)]);
      }
      if (useMemory) setHindsightResult(result); else setBaseline(result);
    } catch (err) {
      setError(err.message || 'The live agent demonstration failed.');
      const status = err.payload?.memory_status;
      if (useMemory && status) setHindsightResult({ message: '', memory_available: status.available, memory_used: status.used, memory_count: status.count, memory_references: status.references || [], memory_retained: status.retained });
    }
    finally { setLoading(false); }
  }
  function reset() { setBaseline(null); setHindsightResult(null); setDraft(''); setTicketId(''); }
  return <div className="page"><PageHeading eyebrow="LIVE WALKTHROUGH">Hindsight Demo</PageHeading><section className="panel"><div className="selector-row"><label className="field-label">Customer<select value={customerId} onChange={(event) => { setCustomerId(event.target.value); reset(); }}><option value="">Select customer</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}</select></label><label className="field-label">Existing ticket (optional)<select value={ticketId} onChange={(event) => setTicketId(event.target.value)}><option value="">Start a new interaction</option>{tickets.map((ticket) => <option key={ticket.id} value={ticket.id}>#{ticket.id} · {ticket.title}</option>)}</select></label></div><div className="chat-input-row"><textarea rows="2" value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Describe a support issue for this customer..."/><button className="secondary-button" disabled={loading || !customerId || !draft.trim()} onClick={() => run(false)}>{loading ? 'Working...' : 'Run without memory'}</button><button className="primary-button" disabled={loading || !customerId || !draft.trim()} onClick={() => run(true)}>Ask with Hindsight</button></div>{error && <ErrorNotice>{error}</ErrorNotice>}<button className="quiet-button" onClick={reset}>Start a new comparison</button></section><div className="demo-grid"><section className="demo-card"><h2>WITHOUT MEMORY</h2><p className="muted">This request explicitly omits Hindsight recall.</p>{baseline ? <><p className="demo-response">{baseline.message}</p><p className="muted">Memory used: No · Memories recalled: 0</p><p className="muted">Hindsight retention: {baseline.memory_retained ? 'confirmed' : 'not confirmed'}</p></> : <EmptyState>Run the first agent interaction without historical memory.</EmptyState>}</section><section className="demo-card highlight"><h2>WITH HINDSIGHT MEMORY</h2><p className="muted">The agent response and recalled items come from the live backend flow.</p>{hindsightResult ? <><p className="demo-response">{hindsightResult.message}</p><p>Memory used: {hindsightResult.memory_available ? (hindsightResult.memory_used ? 'Yes' : 'No relevant match') : 'Unavailable'}</p><p>Memories recalled: {hindsightResult.memory_count}</p><p>Memory retained: {hindsightResult.memory_retained ? 'Yes' : 'Not confirmed'}</p>{hindsightResult.memory_references?.map((item, index) => <article className="memory-summary" key={index}>{item}</article>)}{!hindsightResult.memory_available && <ErrorNotice>Hindsight is unavailable; this response did not use historical memory.</ErrorNotice>}</> : <EmptyState>Ask a related question to run an actual Hindsight recall.</EmptyState>}</section></div></div>;
}

export default App;