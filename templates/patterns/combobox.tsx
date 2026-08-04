import { useId, useMemo, useState } from 'react';
import './combobox.css';

type ComboState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

type Option = { id: string; label: string; meta?: string; disabled?: boolean };

const OPTIONS: Option[] = [
  { id: 'alpha', label: 'Alpha workspace', meta: 'Recently opened' },
  { id: 'beta', label: 'Beta roadmap', meta: 'Shared with product' },
  { id: 'gamma', label: 'Gamma research', meta: 'Archived' },
];

export function ComboboxPattern() {
  const rootId = useId();
  const listboxId = `${rootId}-listbox`;
  const statusId = `${rootId}-status`;
  const errorId = `${rootId}-error`;
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [disabled, setDisabled] = useState(false);
  const [state, setState] = useState<ComboState>({ status: 'idle' });

  const results = useMemo(() => {
    const next = OPTIONS.filter((option) =>
      option.label.toLowerCase().includes(query.toLowerCase()),
    );
    return query ? next : OPTIONS;
  }, [query]);

  const active = results[activeIndex];
  const activeId = active ? `${rootId}-option-${active.id}` : undefined;
  const empty = results.length === 0;

  function search(value: string) {
    setQuery(value);
    setOpen(true);
    setActiveIndex(0);
    setState({ status: 'loading' });
    window.setTimeout(() => {
      setState(value === 'error'
        ? { status: 'error', message: 'Search is unavailable. Try again.' }
        : { status: 'idle' });
    }, 0);
  }

  function commit(option: Option) {
    if (disabled || option.disabled) return;
    setQuery(option.label);
    setOpen(false);
    setState({ status: 'success', message: `${option.label} selected.` });
  }

  return (
    <section
      className="kp-combobox"
      data-state={empty ? 'empty' : state.status}
      aria-busy={state.status === 'loading'}
    >
      <label className="kp-combobox__label" htmlFor={`${rootId}-input`}>
        Workspace
      </label>
      <div className="kp-combobox__control">
        <input
          id={`${rootId}-input`}
          role="combobox"
          type="search"
          autoComplete="off"
          value={query}
          disabled={disabled}
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={open ? activeId : undefined}
          aria-describedby={`${statusId} ${state.status === 'error' ? errorId : ''}`}
          onChange={(event) => search(event.currentTarget.value)}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === 'ArrowDown') {
              event.preventDefault();
              setOpen(true);
              setActiveIndex((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
            }
            if (event.key === 'ArrowUp') {
              event.preventDefault();
              setActiveIndex((index) => Math.max(index - 1, 0));
            }
            if (event.key === 'Enter' && active) {
              event.preventDefault();
              commit(active);
            }
            if (event.key === 'Escape') setOpen(false);
          }}
        />
        <button
          type="button"
          className="kp-combobox__toggle"
          aria-label={open ? 'Close options' : 'Open options'}
          disabled={disabled}
          onClick={() => setOpen((value) => !value)}
        >
          <span aria-hidden="true">⌄</span>
        </button>
      </div>

      <div id={statusId} className="kp-combobox__status" aria-live="polite">
        {state.status === 'loading' ? 'Searching options.' : ''}
        {state.status === 'success' ? state.message : ''}
      </div>
      <div id={errorId} className="kp-combobox__error" role="alert" aria-live="polite">
        {state.status === 'error' ? state.message : ''}
      </div>

      {open && (
        <ul id={listboxId} role="listbox" className="kp-combobox__list">
          {results.map((option, index) => (
            <li
              id={`${rootId}-option-${option.id}`}
              key={option.id}
              role="option"
              aria-selected={index === activeIndex}
              aria-disabled={option.disabled}
              className="kp-combobox__option"
              onMouseDown={(event) => {
                event.preventDefault();
                commit(option);
              }}
            >
              <span>{option.label}</span>
              {option.meta && <small>{option.meta}</small>}
            </li>
          ))}
          {empty && (
            <li className="kp-combobox__empty">
              No matches. Clear the search or create a new workspace.
            </li>
          )}
        </ul>
      )}

      <button
        type="button"
        className="kp-combobox__disable"
        aria-pressed={disabled}
        onClick={() => setDisabled((value) => !value)}
      >
        {disabled ? 'Enable combobox' : 'Disable combobox'}
      </button>
    </section>
  );
}
