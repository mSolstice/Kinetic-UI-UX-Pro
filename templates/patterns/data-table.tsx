import { useMemo, useState } from 'react';
import './data-table.css';

type Row = { id: string; name: string; owner: string; status: 'Ready' | 'Blocked' | 'Draft' };
type TableState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; message: string }
  | { status: 'error'; message: string };

const INITIAL_ROWS: Row[] = [
  { id: 'one', name: 'Checkout refresh', owner: 'Design systems', status: 'Ready' },
  { id: 'two', name: 'Search repair', owner: 'Growth', status: 'Blocked' },
  { id: 'three', name: 'Billing settings', owner: 'Platform', status: 'Draft' },
];

export function DataTablePattern() {
  const [rows, setRows] = useState<Row[]>(INITIAL_ROWS);
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState<keyof Row>('name');
  const [descending, setDescending] = useState(false);
  const [state, setState] = useState<TableState>({ status: 'idle' });
  const [locked, setLocked] = useState(false);

  const filtered = useMemo(() => {
    const match = rows.filter((row) =>
      `${row.name} ${row.owner} ${row.status}`.toLowerCase().includes(query.toLowerCase()),
    );
    return match.sort((a, b) => {
      const result = String(a[sortKey]).localeCompare(String(b[sortKey]));
      return descending ? -result : result;
    });
  }, [descending, query, rows, sortKey]);

  const empty = rows.length === 0;
  const clearedByFilter = !empty && filtered.length === 0;
  const overflow = filtered.length > 2;

  function refresh() {
    if (state.status === 'loading' || locked) return;
    setState({ status: 'loading' });
    window.setTimeout(() => setState({ status: 'success', message: 'Rows refreshed.' }), 0);
  }

  function sortBy(key: keyof Row) {
    setSortKey(key);
    setDescending((current) => (sortKey === key ? !current : false));
  }

  function simulateError() {
    setState({ status: 'error', message: 'Rows could not be refreshed.' });
  }

  return (
    <section
      className="kp-table"
      aria-busy={state.status === 'loading'}
      data-state={empty ? 'empty' : clearedByFilter ? 'cleared-by-filter' : state.status}
      data-overflow={overflow}
    >
      <header className="kp-table__header">
        <div>
          <h2>Project table</h2>
          <p>Sort, filter, empty, filtered-empty, and overflow are intentionally distinct.</p>
        </div>
        <button type="button" className="kp-table__action" aria-disabled={locked} onClick={refresh}>
          {state.status === 'loading' ? 'Refreshing' : 'Refresh'}
        </button>
      </header>

      <label className="kp-table__filter">
        <span>Filter projects</span>
        <input
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
        />
      </label>

      <div className="kp-table__status" aria-live="polite">
        {state.status === 'loading' ? 'Refreshing table rows.' : ''}
        {state.status === 'success' ? state.message : ''}
      </div>
      <div className="kp-table__error" role="alert" aria-live="polite">
        {state.status === 'error' ? state.message : ''}
      </div>

      {empty && (
        <div className="kp-table__empty">
          No projects yet. Create the first project to populate this table.
        </div>
      )}

      {clearedByFilter && (
        <div className="kp-table__empty">
          No rows match this filter. Clear the filter to return to all projects.
          <button type="button" className="kp-table__link" onClick={() => setQuery('')}>
            Clear filter
          </button>
        </div>
      )}

      {!empty && !clearedByFilter && (
        <div className="kp-table__overflow" tabIndex={0} aria-label="Scrollable project table">
          <table>
            <caption>Projects sorted by {sortKey}</caption>
            <thead>
              <tr>
                {(['name', 'owner', 'status'] as Array<keyof Row>).map((key) => (
                  <th key={key} scope="col">
                    <button
                      type="button"
                      className="kp-table__sort"
                      aria-pressed={sortKey === key}
                      onClick={() => sortBy(key)}
                    >
                      {key}
                      {sortKey === key ? (descending ? ' descending' : ' ascending') : ''}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>{row.owner}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <footer className="kp-table__footer">
        <button type="button" className="kp-table__link" onClick={() => setRows([])}>
          Show empty
        </button>
        <button type="button" className="kp-table__link" onClick={() => setRows(INITIAL_ROWS)}>
          Restore rows
        </button>
        <button type="button" className="kp-table__link" onClick={simulateError}>
          Show error
        </button>
        <button type="button" className="kp-table__link" aria-pressed={locked} onClick={() => setLocked((value) => !value)}>
          {locked ? 'Enable refresh' : 'Disable refresh'}
        </button>
      </footer>
    </section>
  );
}
