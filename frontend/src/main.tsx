import { StrictMode, useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

type Mode = 'LIVE' | 'HISTORICAL_REPLAY' | 'SYNTHETIC_FIXTURE';
type State =
  | { kind: 'loading' }
  | { kind: 'offline' }
  | { kind: 'connected'; mode: Mode; ready: boolean };

const modeLabels: Record<Mode, string> = {
  LIVE: 'Live mode configured · ingestion pending',
  HISTORICAL_REPLAY: 'Historical replay · no data loaded',
  SYNTHETIC_FIXTURE: 'Development fixtures · no live observations',
};

function App() {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const refresh = useCallback(() => setAttempt(value => value + 1), []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    setState({ kind: 'loading' });
    async function check() {
      try {
        const [status, readiness] = await Promise.all([
          fetch('/api/v1/status', { signal: controller.signal }),
          fetch('/health/ready', { signal: controller.signal }),
        ]);
        if (!status.ok) throw new Error('Unavailable');
        const body: unknown = await status.json();
        if (typeof body !== 'object' || body === null || !('data_mode' in body)
          || typeof body.data_mode !== 'string' || !Object.hasOwn(modeLabels, body.data_mode)
          || !('stage' in body) || body.stage !== 'FOUNDATION') {
          throw new Error('Unsupported status contract');
        }
        const health: unknown = await readiness.json();
        const ready = readiness.ok && typeof health === 'object' && health !== null
          && 'status' in health && health.status === 'ok';
        if (active) setState({ kind: 'connected', mode: body.data_mode as Mode, ready });
      } catch {
        // The public message never contains an internal URL or server exception.
        if (active) setState({ kind: 'offline' });
      } finally {
        window.clearTimeout(timeout);
      }
    }
    void check();
    return () => { active = false; controller.abort(); window.clearTimeout(timeout); };
  }, [attempt]);

  return (
    <div className="shell">
      <aside className="rail" aria-label="Project identity">
        <a className="brand" href="/" aria-label="ThermoScope home"><span className="mark">T</span> ThermoScope</a>
        <div className="rail-section">WORKSPACE</div>
        <div className="selected"><span aria-hidden="true">◉</span> Overview</div>
        <p className="rail-note">From thermal observations<br />to inspectable evidence.</p>
        <div className="rail-bottom"><span className="dot" /> Regional pilot<br /><small>Git_Push_Pray · SIH 2026</small></div>
      </aside>
      <main>
        <header><span>THERMAL INTELLIGENCE WORKBENCH</span><span className="tag">Foundation preview</span></header>
        <section className="intro">
          <div className="eyebrow">WORKSPACE OVERVIEW</div>
          <h1>Build the evidence first.</h1>
          <p>Trace satellite observations to their source, compare thermal history, and keep uncertainty visible.</p>
        </section>
        <div className="mode-banner" role="status" aria-live="polite">
          <span className="mode-symbol" aria-hidden="true">◷</span>
          <div><strong>{state.kind === 'connected' ? modeLabels[state.mode] : state.kind === 'loading' ? 'Checking workspace connection…' : 'Workspace API unavailable'}</strong>
            <p>No thermal observations or classification results are available in this foundation build.</p></div>
        </div>
        <section className="status-grid" aria-label="System status">
          <article className="card"><div className="card-title">Application</div><h2>{state.kind === 'connected' ? 'Connected' : state.kind === 'loading' ? 'Checking…' : 'Offline'}</h2><p>{state.kind === 'offline' ? 'Start the local API, then check again.' : 'The interface reports the API’s actual availability.'}</p></article>
          <article className="card"><div className="card-title">Spatial database</div><h2>{state.kind === 'connected' ? state.ready ? 'Ready' : 'Needs attention' : 'Not checked'}</h2><p>{state.kind === 'connected' && !state.ready ? 'Check the database and apply required migrations.' : 'Connection, PostGIS and schema are checked together.'}</p></article>
          <article className="card"><div className="card-title">Classification</div><h2>Not built yet</h2><p>Rules and a trained model require data and evaluation before results appear here.</p></article>
        </section>
        <section className="next-panel">
          <div className="step-number">02</div>
          <div><div className="eyebrow">NEXT BUILD MILESTONE</div><h2>Real satellite observations, on a map.</h2><p>Connect a bounded NASA FIRMS sample, preserve its provenance, and verify that repeated imports do not duplicate observations.</p></div>
        </section>
        <footer><p>Foundation only · No trained model or incident alerts</p><button onClick={refresh} disabled={state.kind === 'loading'}>Check connection <span aria-hidden="true">↻</span></button></footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
