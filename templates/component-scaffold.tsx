/**
 * Reference scaffold — demonstrates every rule the skill enforces.
 * Copy the patterns, not the markup.
 */
import { useState, useRef, useId, useEffect } from 'react';
import { useReducedMotion, motion } from 'framer-motion';
import './component-scaffold.css';

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Item[] }
  | { status: 'error'; message: string };

export function DataPanel() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const [showSpinner, setShowSpinner] = useState(false);
  const reduced = useReducedMotion();
  const errorId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function load() {
    if (state.status === 'loading') return;      // double-submit blocked at state layer
    abortRef.current?.abort();                    // supersede in-flight
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({ status: 'loading' });              // aria-busy fires NOW
    const t = setTimeout(() => setShowSpinner(true), 200);   // visual only
    const shownAt = Date.now();

    try {
      const data = await fetchItems(ctrl.signal);
      await holdMinimum(shownAt, showSpinner);    // 400ms min once shown
      setState({ status: 'success', data });
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setState({ status: 'error', message: 'We couldn’t load your items. Check your connection and try again.' });
    } finally {
      clearTimeout(t);
      setShowSpinner(false);
    }
  }

  useEffect(() => () => abortRef.current?.abort(), []);

  return (
    <section aria-busy={state.status === 'loading'}>
      {/* live region pre-exists, EMPTY, before any message arrives */}
      <div role="alert" aria-live="polite" className="sr-only" id={errorId}>
        {state.status === 'error' ? state.message : ''}
      </div>

      <button
        ref={triggerRef}
        onClick={load}
        className="btn"
        aria-disabled={state.status === 'loading'}
        data-state={state.status}
      >
        <span className="btn__label">
          {state.status === 'loading' ? 'Loading…' : 'Load items'}
        </span>
      </button>

      {state.status === 'loading' && showSpinner && (
        /* skeleton matches final geometry exactly — no shift on swap */
        <ul className="grid" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i} className="card skeleton" style={{ minHeight: '7.5rem' }} />
          ))}
        </ul>
      )}

      {state.status === 'error' && (
        <div className="card card--error">
          <p>{state.message}</p>
          <button onClick={load}>Try again</button>
        </div>
      )}

      {state.status === 'success' && state.data.length === 0 && (
        /* empty state is onboarding: what belongs here + the action */
        <div className="card card--empty">
          <p>No items yet. Items you save will appear here.</p>
          <button onClick={createFirst}>Create your first item</button>
        </div>
      )}

      {state.status === 'success' && state.data.length > 0 && (
        <ul className="grid">
          {state.data.map(item => (
            <motion.li
              key={item.id}
              layoutId={reduced ? undefined : `card-${item.id}`}
              transition={reduced
                ? { duration: 0.09 }
                : { type: 'spring', stiffness: 300, damping: 30 }}
              className="card"
              style={{ minHeight: '7.5rem' }}   /* min, not fixed — survives expansion */
            >
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </motion.li>
          ))}
        </ul>
      )}
    </section>
  );
}
