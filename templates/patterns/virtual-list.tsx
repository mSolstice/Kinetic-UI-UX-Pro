import type { CSSProperties } from 'react';
import { useMemo, useState } from 'react';
import './virtual-list.css';

type VirtualItem = { id: string; title: string; detail: string };
type VirtualState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const ROW_ESTIMATE = 48;
const WINDOW_SIZE = 8;
const ITEMS: VirtualItem[] = Array.from({ length: 80 }, (_item, index) => ({
  id: `row-${index}`,
  title: `Result ${index + 1}`,
  detail: 'Reserved row geometry keeps scroll height stable.',
}));

export function VirtualListPattern() {
  const [items, setItems] = useState<VirtualItem[]>(ITEMS);
  const [start, setStart] = useState(0);
  const [state, setState] = useState<VirtualState>({ status: 'idle' });
  const [locked, setLocked] = useState(false);
  const visible = useMemo(() => items.slice(start, start + WINDOW_SIZE), [items, start]);
  const empty = items.length === 0;

  function refresh() {
    if (locked || state.status === 'loading') return;
    setState({ status: 'loading' });
    window.setTimeout(() => setState({ status: 'success', message: 'Visible rows refreshed.' }), 0);
  }

  function fail() {
    setState({ status: 'error', message: 'Rows could not be loaded.' });
  }

  return (
    <section
      className="kp-virtual"
      aria-busy={state.status === 'loading'}
      data-state={empty ? 'empty' : state.status}
      style={{
        '--kp-virtual-count': items.length,
        '--kp-virtual-start': start,
      } as CSSProperties}
    >
      <header className="kp-virtual__header">
        <div>
          <h2>Virtual list</h2>
          <p>The scroll range is reserved before rows render, so CLS remains zero.</p>
        </div>
        <button type="button" className="kp-virtual__button" aria-disabled={locked} onClick={refresh}>
          {state.status === 'loading' ? 'Refreshing' : 'Refresh'}
        </button>
      </header>

      <div className="kp-virtual__status" aria-live="polite">
        {state.status === 'loading' ? 'Refreshing visible rows.' : ''}
        {state.status === 'success' ? state.message : ''}
      </div>
      <div className="kp-virtual__error" role="alert" aria-live="polite">
        {state.status === 'error' ? state.message : ''}
      </div>

      {empty ? (
        <div className="kp-virtual__empty">
          No rows to virtualize. Restore the dataset to preview reserved scrolling.
        </div>
      ) : (
        <div
          className="kp-virtual__viewport"
          tabIndex={0}
          aria-label="Virtualized results"
          onScroll={(event) => {
            const next = Math.floor(event.currentTarget.scrollTop / ROW_ESTIMATE);
            setStart(Math.min(Math.max(next, 0), Math.max(items.length - WINDOW_SIZE, 0)));
          }}
        >
          <div className="kp-virtual__spacer">
            <ul className="kp-virtual__window">
              {visible.map((item) => (
                <li key={item.id} className="kp-virtual__row">
                  <strong>{item.title}</strong>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <footer className="kp-virtual__actions">
        <button type="button" className="kp-virtual__button" onClick={() => setItems([])}>
          Show empty
        </button>
        <button type="button" className="kp-virtual__button" onClick={() => setItems(ITEMS)}>
          Restore rows
        </button>
        <button type="button" className="kp-virtual__button" onClick={fail}>
          Show error
        </button>
        <button type="button" className="kp-virtual__button" aria-pressed={locked} onClick={() => setLocked((value) => !value)}>
          {locked ? 'Enable refresh' : 'Disable refresh'}
        </button>
      </footer>
    </section>
  );
}
