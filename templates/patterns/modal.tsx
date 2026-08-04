import { useEffect, useId, useRef, useState } from 'react';
import './modal.css';

type ModalState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

export function ModalPattern() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const openerRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descId = useId();
  const errorId = useId();
  const [state, setState] = useState<ModalState>({ status: 'idle' });
  const [items, setItems] = useState<string[]>([]);
  const [locked, setLocked] = useState(false);

  function openDialog() {
    dialogRef.current?.showModal();
  }

  function closeDialog() {
    dialogRef.current?.close();
    openerRef.current?.focus();
  }

  function save() {
    if (state.status === 'loading' || locked) return;
    setState({ status: 'loading' });
    window.setTimeout(() => {
      setItems(['Saved invite']);
      setState({ status: 'success', message: 'Invite saved.' });
    }, 0);
  }

  function simulateError() {
    setState({ status: 'error', message: 'We could not save this invite. Try again.' });
  }

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const onClose = () => openerRef.current?.focus();
    dialog.addEventListener('close', onClose);
    return () => dialog.removeEventListener('close', onClose);
  }, []);

  return (
    <section className="kp-modal-shell" aria-busy={state.status === 'loading'}>
      <button ref={openerRef} type="button" className="kp-modal-open" onClick={openDialog}>
        Open invite modal
      </button>

      <dialog
        ref={dialogRef}
        className="kp-modal"
        aria-labelledby={titleId}
        aria-describedby={descId}
        data-state={items.length === 0 ? 'empty' : state.status}
      >
        <div className="kp-modal__surface">
          <header className="kp-modal__header">
            <h2 id={titleId}>Invite reviewer</h2>
            <button type="button" className="kp-modal__close" aria-label="Close" onClick={closeDialog}>
              ×
            </button>
          </header>

          <p id={descId}>
            Share a focused review request. Empty, loading, success, and error states stay in this dialog.
          </p>

          <div id={errorId} className="kp-modal__alert" role="alert" aria-live="polite">
            {state.status === 'error' ? state.message : ''}
          </div>
          <div className="kp-modal__status" aria-live="polite">
            {state.status === 'loading' ? 'Saving invite.' : ''}
            {state.status === 'success' ? state.message : ''}
          </div>

          {items.length === 0 ? (
            <div className="kp-modal__empty">
              No reviewers added yet. Add the first reviewer before sending.
            </div>
          ) : (
            <ul className="kp-modal__list">
              {items.map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}

          <footer className="kp-modal__actions">
            <button type="button" className="kp-modal__secondary" onClick={simulateError}>
              Show error
            </button>
            <button
              type="button"
              className="kp-modal__secondary"
              aria-pressed={locked}
              onClick={() => setLocked((value) => !value)}
            >
              {locked ? 'Enable save' : 'Disable save'}
            </button>
            <button
              type="button"
              className="kp-modal__primary"
              aria-disabled={state.status === 'loading' || locked}
              aria-describedby={state.status === 'error' ? errorId : undefined}
              onClick={save}
            >
              {state.status === 'loading' ? 'Saving' : 'Save invite'}
            </button>
          </footer>
        </div>
      </dialog>
    </section>
  );
}
