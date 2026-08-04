import { KeyboardEvent, useEffect, useId, useRef, useState } from 'react';
import './customer-search-combobox.css';

export type Customer = {
  id: string;
  name: string;
  email: string;
};

type SearchState =
  | { status: 'idle' }
  | { status: 'loading'; query: string }
  | { status: 'success'; query: string; data: Customer[] }
  | { status: 'error'; query: string; message: string };

type CustomerSearchComboboxProps = {
  label?: string;
  minQueryLength?: number;
  selectedCustomer?: Customer | null;
  searchCustomers: (query: string, signal: AbortSignal) => Promise<Customer[]>;
  onCustomerSelect: (customer: Customer) => void;
};

const NETWORK_ERROR_MESSAGE =
  'We could not search customers. Check your connection and try again.';

export function CustomerSearchCombobox({
  label = 'Find customer',
  minQueryLength = 2,
  selectedCustomer = null,
  searchCustomers,
  onCustomerSelect,
}: CustomerSearchComboboxProps) {
  const [query, setQuery] = useState(selectedCustomer?.name ?? '');
  const [state, setState] = useState<SearchState>({ status: 'idle' });
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [showLoading, setShowLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const spinnerShownAtRef = useRef<number | null>(null);

  const inputId = useId();
  const listboxId = useId();
  const helperId = useId();
  const statusId = useId();
  const errorId = useId();

  const customers = state.status === 'success' ? state.data : [];
  const activeCustomer = activeIndex >= 0 ? customers[activeIndex] : null;
  const activeDescendant = activeCustomer
    ? `${listboxId}-option-${activeCustomer.id}`
    : undefined;
  const isLoading = state.status === 'loading';
  const hasError = state.status === 'error';
  const trimmedQuery = query.trim();
  const canSearch = trimmedQuery.length >= minQueryLength;

  useEffect(() => {
    setQuery(selectedCustomer?.name ?? '');
  }, [selectedCustomer?.id, selectedCustomer?.name]);

  useEffect(() => {
    if (!canSearch) {
      abortRef.current?.abort();
      setState({ status: 'idle' });
      setIsOpen(false);
      setActiveIndex(-1);
      setShowLoading(false);
      return;
    }

    const debounce = window.setTimeout(() => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const requestQuery = trimmedQuery;
      let spinnerDelay: number | undefined;

      setState({ status: 'loading', query: requestQuery });
      setIsOpen(true);
      setActiveIndex(-1);
      spinnerDelay = window.setTimeout(() => {
        spinnerShownAtRef.current = Date.now();
        setShowLoading(true);
      }, 200);

      searchCustomers(requestQuery, controller.signal)
        .then(async (data) => {
          await holdLoadingMinimum(spinnerShownAtRef.current);
          if (controller.signal.aborted) return;
          setState({ status: 'success', query: requestQuery, data });
          setIsOpen(true);
          setActiveIndex(data.length > 0 ? 0 : -1);
        })
        .catch(async () => {
          await holdLoadingMinimum(spinnerShownAtRef.current);
          if (controller.signal.aborted) return;
          setState({
            status: 'error',
            query: requestQuery,
            message: NETWORK_ERROR_MESSAGE,
          });
          setIsOpen(true);
          setActiveIndex(-1);
        })
        .finally(() => {
          window.clearTimeout(spinnerDelay);
          if (!controller.signal.aborted) {
            spinnerShownAtRef.current = null;
            setShowLoading(false);
          }
        });
    }, 250);

    return () => {
      window.clearTimeout(debounce);
    };
  }, [canSearch, minQueryLength, searchCustomers, trimmedQuery]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  useEffect(() => {
    function closeOnOutsidePointer(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
        setActiveIndex(-1);
      }
    }

    document.addEventListener('pointerdown', closeOnOutsidePointer);
    return () => document.removeEventListener('pointerdown', closeOnOutsidePointer);
  }, []);

  function selectCustomer(customer: Customer) {
    abortRef.current?.abort();
    setQuery(customer.name);
    setState({ status: 'success', query: customer.name, data: [customer] });
    setIsOpen(false);
    setActiveIndex(-1);
    setShowLoading(false);
    onCustomerSelect(customer);
    inputRef.current?.focus();
  }

  function retrySearch() {
    const current = query.trim();
    if (current.length < minQueryLength) return;
    setQuery(`${current} `);
    window.requestAnimationFrame(() => setQuery(current));
    inputRef.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setIsOpen(true);
      if (customers.length > 0) {
        setActiveIndex((index) => (index + 1) % customers.length);
      }
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setIsOpen(true);
      if (customers.length > 0) {
        setActiveIndex((index) =>
          index <= 0 ? customers.length - 1 : index - 1,
        );
      }
    }

    if (event.key === 'Enter' && activeCustomer) {
      event.preventDefault();
      selectCustomer(activeCustomer);
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      setIsOpen(false);
      setActiveIndex(-1);
    }
  }

  return (
    <section
      className="customer-combobox"
      aria-busy={isLoading}
      ref={rootRef}
    >
      <div className="customer-combobox__field">
        <label className="customer-combobox__label" htmlFor={inputId}>
          {label}
        </label>
        <div className="customer-combobox__control">
          <input
            ref={inputRef}
            id={inputId}
            className="customer-combobox__input"
            type="search"
            role="combobox"
            autoComplete="off"
            spellCheck={false}
            value={query}
            aria-autocomplete="list"
            aria-controls={listboxId}
            aria-describedby={`${helperId} ${statusId} ${hasError ? errorId : ''}`}
            aria-expanded={isOpen}
            aria-invalid={hasError}
            aria-activedescendant={activeDescendant}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => {
              if (state.status === 'success' || state.status === 'error') {
                setIsOpen(true);
              }
            }}
            onKeyDown={handleKeyDown}
          />
          {showLoading && (
            <span
              className="customer-combobox__spinner"
              aria-hidden="true"
            />
          )}
        </div>
        <p className="customer-combobox__help" id={helperId}>
          Search by customer name or email.
        </p>
      </div>

      <div className="customer-combobox__status" aria-live="polite" id={statusId}>
        {statusMessage(state, minQueryLength)}
      </div>

      <div className="customer-combobox__error" role="alert" id={errorId}>
        {hasError ? state.message : ''}
      </div>

      {isOpen && canSearch && (
        <div
          className="customer-combobox__popover"
          id={listboxId}
          role="listbox"
          aria-label="Customers"
        >
          {isLoading && showLoading && (
            <div className="customer-combobox__loading" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          )}

          {state.status === 'success' && state.data.length === 0 && (
            <div className="customer-combobox__empty">
              No customers match this search.
            </div>
          )}

          {state.status === 'error' && (
            <div className="customer-combobox__failure">
              <p>{state.message}</p>
              <button type="button" onClick={retrySearch}>
                Try again
              </button>
            </div>
          )}

          {state.status === 'success' &&
            state.data.map((customer, index) => (
              <button
                type="button"
                className="customer-combobox__option"
                id={`${listboxId}-option-${customer.id}`}
                role="option"
                aria-selected={index === activeIndex}
                key={customer.id}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectCustomer(customer)}
              >
                <span className="customer-combobox__name">{customer.name}</span>
                <span className="customer-combobox__email">{customer.email}</span>
              </button>
            ))}
        </div>
      )}
    </section>
  );
}

function statusMessage(state: SearchState, minQueryLength: number) {
  if (state.status === 'idle') {
    return `Enter at least ${minQueryLength} characters to search.`;
  }

  if (state.status === 'loading') {
    return `Searching customers for ${state.query}.`;
  }

  if (state.status === 'error') {
    return '';
  }

  if (state.data.length === 0) {
    return `No customers found for ${state.query}.`;
  }

  return `${state.data.length} customer${state.data.length === 1 ? '' : 's'} found.`;
}

function holdLoadingMinimum(spinnerShownAt: number | null) {
  if (!spinnerShownAt) return Promise.resolve();

  const elapsed = Date.now() - spinnerShownAt;
  const remaining = Math.max(0, 400 - elapsed);

  return new Promise((resolve) => {
    window.setTimeout(resolve, remaining);
  });
}
