import { createContext, useCallback, useContext, useMemo, useReducer, useRef } from 'react';

type ToastTone = 'success' | 'error' | 'undo';

type Toast = {
  id: string;
  tone: ToastTone;
  title: string;
  message: string;
  action?: {
    label: string;
    onPress: () => void;
  };
  timeoutMs?: number;
};

type ToastState = {
  queue: Toast[];
  archiveStatus: 'idle' | 'archived' | 'restoring' | 'restored';
};

type ToastAction =
  | { type: 'push'; toast: Toast }
  | { type: 'dismiss'; id: string }
  | { type: 'archive' }
  | { type: 'restore-start' }
  | { type: 'restore-complete' };

const ToastContext = createContext<{
  notifySaveSuccess: () => void;
  notifySyncFailure: (retry: () => void) => void;
  archiveWithUndo: () => void;
  dismissToast: (id: string) => void;
} | null>(null);

const initialState: ToastState = {
  queue: [],
  archiveStatus: 'idle',
};

function toastReducer(state: ToastState, action: ToastAction): ToastState {
  switch (action.type) {
    case 'push':
      return {
        ...state,
        queue: [...state.queue.filter(toast => toast.id !== action.toast.id), action.toast].slice(-3),
      };
    case 'dismiss':
      return {
        ...state,
        queue: state.queue.filter(toast => toast.id !== action.id),
      };
    case 'archive':
      return { ...state, archiveStatus: 'archived' };
    case 'restore-start':
      return { ...state, archiveStatus: 'restoring' };
    case 'restore-complete':
      return { ...state, archiveStatus: 'restored' };
    default:
      return state;
  }
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(toastReducer, initialState);
  const timers = useRef(new Map<string, number>());

  const dismissToast = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) window.clearTimeout(timer);
    timers.current.delete(id);
    dispatch({ type: 'dismiss', id });
  }, []);

  const pushToast = useCallback((toast: Toast) => {
    dispatch({ type: 'push', toast });

    if (toast.timeoutMs !== 0) {
      const timeout = window.setTimeout(() => dismissToast(toast.id), toast.timeoutMs ?? 5200);
      timers.current.set(toast.id, timeout);
    }
  }, [dismissToast]);

  const notifySaveSuccess = useCallback(() => {
    pushToast({
      id: 'save-success',
      tone: 'success',
      title: 'Saved',
      message: 'Your changes are up to date.',
    });
  }, [pushToast]);

  const notifySyncFailure = useCallback((retry: () => void) => {
    pushToast({
      id: 'sync-failure',
      tone: 'error',
      title: 'Sync paused',
      message: 'We could not reach the server. Your local work is still here.',
      action: {
        label: 'Try again',
        onPress: retry,
      },
      timeoutMs: 0,
    });
  }, [pushToast]);

  const archiveWithUndo = useCallback(() => {
    dispatch({ type: 'archive' });

    pushToast({
      id: 'archive-undo',
      tone: 'undo',
      title: 'Archived',
      message: 'Project moved out of your active list.',
      action: {
        label: 'Undo',
        onPress: () => {
          dispatch({ type: 'restore-start' });
          window.setTimeout(() => {
            dispatch({ type: 'restore-complete' });
            dismissToast('archive-undo');
            pushToast({
              id: 'archive-restored',
              tone: 'success',
              title: 'Restored',
              message: 'Project returned to your active list.',
            });
          }, 180);
        },
      },
      timeoutMs: 8000,
    });
  }, [dismissToast, pushToast]);

  const value = useMemo(() => ({
    notifySaveSuccess,
    notifySyncFailure,
    archiveWithUndo,
    dismissToast,
  }), [archiveWithUndo, dismissToast, notifySaveSuccess, notifySyncFailure]);

  return (
    <ToastContext.Provider value={value}>
      <section aria-busy={state.archiveStatus === 'restoring'}>
        {children}
      </section>
      <ToastViewport toasts={state.queue} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToasts() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToasts must be used inside ToastProvider');
  }
  return context;
}

export function ToastDemoActions() {
  const { notifySaveSuccess, notifySyncFailure, archiveWithUndo } = useToasts();

  return (
    <div className="toast-demo-actions">
      <button type="button" className="btn" onClick={notifySaveSuccess}>
        Save changes
      </button>
      <button type="button" className="btn btn--secondary" onClick={() => notifySyncFailure(() => {})}>
        Simulate sync failure
      </button>
      <button type="button" className="btn btn--secondary" onClick={archiveWithUndo}>
        Archive project
      </button>
    </div>
  );
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div className="toast-viewport" aria-live="polite" aria-relevant="additions text">
      {toasts.map(toast => (
        <article key={toast.id} className={`toast toast--${toast.tone}`} aria-atomic="true">
          <div className="toast__content">
            <p className="toast__title">{toast.title}</p>
            <p className="toast__message">{toast.message}</p>
          </div>

          {toast.action && (
            <button type="button" className="toast__action" onClick={toast.action.onPress}>
              {toast.action.label}
            </button>
          )}

          <button
            type="button"
            className="toast__close"
            aria-label={`Dismiss ${toast.title}`}
            onClick={() => onDismiss(toast.id)}
          >
            Close
          </button>
        </article>
      ))}
    </div>
  );
}
