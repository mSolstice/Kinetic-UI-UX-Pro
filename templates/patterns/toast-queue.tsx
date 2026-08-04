import { useMemo, useState } from 'react';
import './toast-queue.css';

type ToastTone = 'success' | 'error' | 'info';
type Toast = { id: string; tone: ToastTone; message: string };
type ToastState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const MAX_VISIBLE = 3;

export function ToastQueuePattern() {
  const [queue, setQueue] = useState<Toast[]>([]);
  const [state, setState] = useState<ToastState>({ status: 'idle' });
  const [locked, setLocked] = useState(false);
  const visible = useMemo(() => queue.slice(0, MAX_VISIBLE), [queue]);
  const waiting = Math.max(queue.length - MAX_VISIBLE, 0);
  const empty = queue.length === 0;

  function addToast(tone: ToastTone) {
    if (locked) return;
    setState({ status: 'loading' });
    window.setTimeout(() => {
      const id = `${tone}-${Date.now()}`;
      setQueue((current) => [...current, { id, tone, message: `${tone} toast queued.` }]);
      setState({ status: 'success', message: 'Toast added.' });
    }, 0);
  }

  function removeToast(id: string) {
    setQueue((current) => current.filter((toast) => toast.id !== id));
  }

  function failToast() {
    setState({ status: 'error', message: 'Toast service is unavailable.' });
  }

  return (
    <section
      className="kp-toast-demo"
      aria-busy={state.status === 'loading'}
      data-state={empty ? 'empty' : state.status}
    >
      <header className="kp-toast-demo__header">
        <h2>Toast queue</h2>
        <p>Shows at most {MAX_VISIBLE} concurrent toasts. Extra messages wait their turn.</p>
      </header>

      <div className="kp-toast-demo__actions">
        <button type="button" className="kp-toast-demo__button" aria-disabled={locked} onClick={() => addToast('info')}>
          {state.status === 'loading' ? 'Queuing' : 'Add info'}
        </button>
        <button type="button" className="kp-toast-demo__button" aria-disabled={locked} onClick={() => addToast('success')}>
          Add success
        </button>
        <button type="button" className="kp-toast-demo__button" aria-disabled={locked} onClick={failToast}>
          Show error
        </button>
        <button type="button" className="kp-toast-demo__button" aria-pressed={locked} onClick={() => setLocked((value) => !value)}>
          {locked ? 'Enable queue' : 'Disable queue'}
        </button>
      </div>

      <div className="kp-toast-demo__status" aria-live="polite" role="status">
        {state.status === 'loading' ? 'Adding toast.' : ''}
        {state.status === 'success' ? state.message : ''}
        {state.status === 'error' ? state.message : ''}
      </div>

      {empty && (
        <div className="kp-toast-demo__empty">
          No notifications. Queue a toast to preview placement, dismissal, and polite announcement.
        </div>
      )}

      <ol className="kp-toast-stack" aria-label="Notifications">
        {visible.map((toast) => (
          <li key={toast.id} className="kp-toast" data-tone={toast.tone}>
            <div>
              <strong>{toast.tone}</strong>
              <p>{toast.message}</p>
            </div>
            <button type="button" className="kp-toast__close" onClick={() => removeToast(toast.id)}>
              Dismiss
            </button>
          </li>
        ))}
      </ol>

      {waiting > 0 && (
        <p className="kp-toast-demo__waiting">
          {waiting} toast{waiting === 1 ? '' : 's'} waiting for an open slot.
        </p>
      )}
    </section>
  );
}
