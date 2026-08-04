import { useId, useMemo, useRef, useState } from 'react';
import './command-palette.css';

type Command = { id: string; label: string; group: string; disabled?: boolean };
type PaletteState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const COMMANDS: Command[] = [
  { id: 'new', label: 'Create project', group: 'Project' },
  { id: 'invite', label: 'Invite teammate', group: 'Team' },
  { id: 'billing', label: 'Open billing', group: 'Settings' },
  { id: 'archive', label: 'Archive workspace', group: 'Admin', disabled: true },
];

export function CommandPalettePattern() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const openerRef = useRef<HTMLButtonElement>(null);
  const rootId = useId();
  const listboxId = `${rootId}-commands`;
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [state, setState] = useState<PaletteState>({ status: 'idle' });
  const [locked, setLocked] = useState(false);
  const commands = useMemo(() => COMMANDS.filter((command) =>
    command.label.toLowerCase().includes(query.toLowerCase()),
  ), [query]);
  const active = commands[activeIndex];
  const empty = commands.length === 0;

  function close() {
    dialogRef.current?.close();
    openerRef.current?.focus();
  }

  function run(command: Command) {
    if (locked || command.disabled) return;
    setState({ status: 'loading' });
    window.setTimeout(() => {
      setState({ status: 'success', message: `${command.label} ran.` });
      close();
    }, 0);
  }

  function simulateError() {
    setState({ status: 'error', message: 'Command failed. Try another action.' });
  }

  return (
    <section className="kp-command-shell" aria-busy={state.status === 'loading'}>
      <button ref={openerRef} type="button" className="kp-command-open" onClick={() => dialogRef.current?.showModal()}>
        Open command palette
      </button>
      <dialog
        ref={dialogRef}
        className="kp-command"
        aria-labelledby={`${rootId}-title`}
        data-state={empty ? 'empty' : state.status}
      >
        <div className="kp-command__panel">
          <header className="kp-command__header">
            <h2 id={`${rootId}-title`}>Command palette</h2>
            <button type="button" className="kp-command__close" onClick={close}>
              Close
            </button>
          </header>

          <label className="kp-command__search">
            <span>Search commands</span>
            <input
              type="search"
              autoComplete="off"
              value={query}
              role="combobox"
              aria-expanded="true"
              aria-controls={listboxId}
              aria-activedescendant={active ? `${rootId}-${active.id}` : undefined}
              onChange={(event) => {
                setQuery(event.currentTarget.value);
                setActiveIndex(0);
              }}
              onKeyDown={(event) => {
                if (event.key === 'ArrowDown') {
                  event.preventDefault();
                  setActiveIndex((index) => Math.min(index + 1, Math.max(commands.length - 1, 0)));
                }
                if (event.key === 'ArrowUp') {
                  event.preventDefault();
                  setActiveIndex((index) => Math.max(index - 1, 0));
                }
                if (event.key === 'Enter' && active) {
                  event.preventDefault();
                  run(active);
                }
                if (event.key === 'Escape') close();
              }}
            />
          </label>

          <div className="kp-command__status" aria-live="polite">
            {state.status === 'loading' ? 'Running command.' : ''}
            {state.status === 'success' ? state.message : ''}
          </div>
          <div className="kp-command__error" role="alert" aria-live="polite">
            {state.status === 'error' ? state.message : ''}
          </div>

          <ul id={listboxId} role="listbox" className="kp-command__list">
            {commands.map((command, index) => (
              <li
                id={`${rootId}-${command.id}`}
                key={command.id}
                role="option"
                aria-selected={index === activeIndex}
                aria-disabled={command.disabled}
                className="kp-command__item"
                onMouseDown={(event) => {
                  event.preventDefault();
                  run(command);
                }}
              >
                <span>{command.label}</span>
                <small>{command.group}</small>
              </li>
            ))}
          </ul>

          {empty && <p className="kp-command__empty">No commands match. Clear the search to browse all commands.</p>}

          <footer className="kp-command__footer">
            <button type="button" className="kp-command__secondary" onClick={simulateError}>
              Show error
            </button>
            <button type="button" className="kp-command__secondary" aria-pressed={locked} onClick={() => setLocked((value) => !value)}>
              {locked ? 'Enable commands' : 'Disable commands'}
            </button>
          </footer>
        </div>
      </dialog>
    </section>
  );
}
