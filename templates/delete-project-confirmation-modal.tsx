import { useEffect, useId, useRef, useState } from 'react';

type DeleteState =
  | { status: 'idle' }
  | { status: 'deleting' }
  | { status: 'error'; message: string };

type DeleteProjectConfirmationModalProps = {
  open: boolean;
  projectName: string;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => Promise<void> | void;
  confirmLabel?: string;
  cancelLabel?: string;
  title?: string;
};

export function DeleteProjectConfirmationModal({
  open,
  projectName,
  onOpenChange,
  onConfirm,
  confirmLabel = 'Delete project',
  cancelLabel = 'Cancel',
  title = 'Delete saved project?',
}: DeleteProjectConfirmationModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const descriptionId = useId();
  const errorId = useId();
  const [state, setState] = useState<DeleteState>({ status: 'idle' });

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      returnFocusRef.current = document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
      setState({ status: 'idle' });
      if (!dialog.open) dialog.showModal();
      return;
    }

    if (dialog.open) dialog.close();
  }, [open]);

  function restoreFocus() {
    returnFocusRef.current?.focus();
    returnFocusRef.current = null;
  }

  function requestClose() {
    if (state.status === 'deleting') return;
    onOpenChange(false);
  }

  async function handleDelete() {
    if (state.status === 'deleting') return;

    setState({ status: 'deleting' });

    try {
      await onConfirm();
      onOpenChange(false);
    } catch {
      setState({
        status: 'error',
        message: 'We could not delete this project. Check your connection and try again.',
      });
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="delete-project-modal"
      aria-labelledby={titleId}
      aria-describedby={`${descriptionId} ${errorId}`}
      aria-busy={state.status === 'deleting'}
      onCancel={(event) => {
        if (state.status === 'deleting') event.preventDefault();
        else requestClose();
      }}
      onClose={restoreFocus}
      onClick={(event) => {
        if (event.target === event.currentTarget) requestClose();
      }}
    >
      <div className="delete-project-modal__panel">
        <div aria-hidden="true" className="delete-project-modal__icon">
          !
        </div>

        <div className="delete-project-modal__content">
          <h2 id={titleId}>{title}</h2>
          <p id={descriptionId}>
            This will permanently delete <strong>{projectName}</strong>. This action cannot be undone.
          </p>

          <div role="alert" aria-live="polite" id={errorId} className="delete-project-modal__error">
            {state.status === 'error' ? state.message : ''}
          </div>
        </div>

        <div className="delete-project-modal__actions">
          <button
            type="button"
            className="delete-project-modal__button delete-project-modal__button--secondary"
            onClick={requestClose}
            aria-disabled={state.status === 'deleting'}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className="delete-project-modal__button delete-project-modal__button--danger"
            onClick={handleDelete}
            aria-disabled={state.status === 'deleting'}
          >
            {state.status === 'deleting' ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
