import { useEffect, useId, useMemo, useRef, useState } from 'react';
import './OrdersTable.css';

type LoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Order[]; updatedAt: Date }
  | { status: 'error'; message: string };

type OrderStatus = 'Open' | 'Processing' | 'Shipped' | 'Cancelled';
type PaymentStatus = 'Paid' | 'Pending' | 'Refunded' | 'Failed';
type SortKey = 'placedAt' | 'customer' | 'status' | 'total' | 'payment';
type SortDirection = 'asc' | 'desc';

export type Order = {
  id: string;
  customer: string;
  email: string;
  status: OrderStatus;
  payment: PaymentStatus;
  total: number;
  placedAt: string;
  items: number;
};

type OrdersTableProps = {
  loadOrders?: (signal: AbortSignal) => Promise<Order[]>;
};

const sampleOrders: Order[] = [
  {
    id: 'ORD-1048',
    customer: 'Maya Srinivasan',
    email: 'maya@example.com',
    status: 'Processing',
    payment: 'Paid',
    total: 248.4,
    placedAt: '2026-08-04T09:40:00+05:30',
    items: 3,
  },
  {
    id: 'ORD-1047',
    customer: 'Chris Nguyen',
    email: 'chris@example.com',
    status: 'Open',
    payment: 'Pending',
    total: 89,
    placedAt: '2026-08-04T08:15:00+05:30',
    items: 1,
  },
  {
    id: 'ORD-1046',
    customer: 'Ana Garcia',
    email: 'ana@example.com',
    status: 'Shipped',
    payment: 'Paid',
    total: 452.99,
    placedAt: '2026-08-03T17:20:00+05:30',
    items: 6,
  },
  {
    id: 'ORD-1045',
    customer: 'Jiaying Liu',
    email: 'jiaying@example.com',
    status: 'Cancelled',
    payment: 'Refunded',
    total: 125.5,
    placedAt: '2026-08-03T11:05:00+05:30',
    items: 2,
  },
  {
    id: 'ORD-1044',
    customer: 'Omar Haddad',
    email: 'omar@example.com',
    status: 'Processing',
    payment: 'Failed',
    total: 301.2,
    placedAt: '2026-08-02T19:30:00+05:30',
    items: 4,
  },
  {
    id: 'ORD-1043',
    customer: 'Elena Petrova',
    email: 'elena@example.com',
    status: 'Shipped',
    payment: 'Paid',
    total: 44.75,
    placedAt: '2026-08-02T12:10:00+05:30',
    items: 1,
  },
];

const currency = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

function defaultLoadOrders(signal: AbortSignal) {
  return new Promise<Order[]>((resolve, reject) => {
    const timer = window.setTimeout(() => resolve(sampleOrders), 650);

    signal.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer);
        reject(new DOMException('Request cancelled', 'AbortError'));
      },
      { once: true },
    );
  });
}

export function OrdersTable({ loadOrders = defaultLoadOrders }: OrdersTableProps) {
  const [state, setState] = useState<LoadState>({ status: 'idle' });
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'all' | OrderStatus>('all');
  const [payment, setPayment] = useState<'all' | PaymentStatus>('all');
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'placedAt',
    direction: 'desc',
  });

  const messageId = useId();
  const searchId = useId();
  const statusId = useId();
  const paymentId = useId();
  const abortRef = useRef<AbortController | null>(null);

  async function load() {
    if (state.status === 'loading') return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ status: 'loading' });

    try {
      const data = await loadOrders(controller.signal);
      setState({ status: 'success', data, updatedAt: new Date() });
    } catch (error) {
      if (controller.signal.aborted) return;
      setState({
        status: 'error',
        message: 'We could not load orders. Check the connection and try again.',
      });
    }
  }

  useEffect(() => {
    void load();
    return () => abortRef.current?.abort();
  }, []);

  const filtersActive = query.trim() !== '' || status !== 'all' || payment !== 'all';
  const orders = state.status === 'success' ? state.data : [];

  const filteredOrders = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return orders
      .filter((order) => {
        const matchesQuery =
          normalizedQuery === '' ||
          order.id.toLowerCase().includes(normalizedQuery) ||
          order.customer.toLowerCase().includes(normalizedQuery) ||
          order.email.toLowerCase().includes(normalizedQuery);
        const matchesStatus = status === 'all' || order.status === status;
        const matchesPayment = payment === 'all' || order.payment === payment;

        return matchesQuery && matchesStatus && matchesPayment;
      })
      .sort((a, b) => {
        const direction = sort.direction === 'asc' ? 1 : -1;
        return compareOrders(a, b, sort.key) * direction;
      });
  }, [orders, payment, query, sort, status]);

  function resetFilters() {
    setQuery('');
    setStatus('all');
    setPayment('all');
  }

  function updateSort(key: SortKey) {
    setSort((current) => ({
      key,
      direction: current.key === key && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  }

  return (
    <section className="orders-shell" aria-busy={state.status === 'loading'}>
      <div id={messageId} className="orders-sr" role="alert" aria-live="polite">
        {state.status === 'error' ? state.message : ''}
      </div>

      <header className="orders-header">
        <div>
          <p className="orders-kicker">Orders</p>
          <h2>Recent orders</h2>
        </div>
        <button className="orders-button orders-button--secondary" type="button" onClick={load}>
          {state.status === 'loading' ? 'Loading' : 'Reload'}
        </button>
      </header>

      {state.status === 'error' && (
        <div className="orders-error" aria-describedby={messageId}>
          <div>
            <h3>Orders did not load</h3>
            <p>{state.message}</p>
          </div>
          <button className="orders-button" type="button" onClick={load}>
            Try again
          </button>
        </div>
      )}

      {state.status === 'loading' && <OrdersTableSkeleton />}

      {state.status === 'success' && (
        <>
          <div className="orders-toolbar" aria-label="Order filters">
            <div className="orders-field orders-field--search">
              <label htmlFor={searchId}>Search</label>
              <input
                id={searchId}
                type="search"
                value={query}
                autoComplete="off"
                onChange={(event) => setQuery(event.target.value)}
              />
            </div>
            <div className="orders-field">
              <label htmlFor={statusId}>Status</label>
              <select
                id={statusId}
                value={status}
                onChange={(event) => setStatus(event.target.value as 'all' | OrderStatus)}
              >
                <option value="all">All statuses</option>
                <option value="Open">Open</option>
                <option value="Processing">Processing</option>
                <option value="Shipped">Shipped</option>
                <option value="Cancelled">Cancelled</option>
              </select>
            </div>
            <div className="orders-field">
              <label htmlFor={paymentId}>Payment</label>
              <select
                id={paymentId}
                value={payment}
                onChange={(event) => setPayment(event.target.value as 'all' | PaymentStatus)}
              >
                <option value="all">All payments</option>
                <option value="Paid">Paid</option>
                <option value="Pending">Pending</option>
                <option value="Refunded">Refunded</option>
                <option value="Failed">Failed</option>
              </select>
            </div>
            <button
              className="orders-button orders-button--secondary"
              type="button"
              aria-disabled={!filtersActive}
              onClick={filtersActive ? resetFilters : undefined}
            >
              Reset filters
            </button>
          </div>

          <div className="orders-summary" aria-live="polite">
            <span>
              {filteredOrders.length} of {orders.length} orders
            </span>
            <span>
              Updated <time dateTime={state.updatedAt.toISOString()}>{dateFormatter.format(state.updatedAt)}</time>
            </span>
          </div>

          {orders.length === 0 && (
            <div className="orders-empty">
              <h3>No orders yet</h3>
              <p>New orders will appear here once customers check out.</p>
            </div>
          )}

          {orders.length > 0 && filteredOrders.length === 0 && (
            <div className="orders-empty">
              <h3>No matching orders</h3>
              <p>Adjust the filters or reset them to see the full order list.</p>
              <button className="orders-button" type="button" onClick={resetFilters}>
                Reset filters
              </button>
            </div>
          )}

          {filteredOrders.length > 0 && (
            <div className="orders-table-wrap">
              <table className="orders-table">
                <caption>Recent order list</caption>
                <thead>
                  <tr>
                    <SortableHeader label="Order" sortKey="placedAt" sort={sort} onSort={updateSort} />
                    <SortableHeader label="Customer" sortKey="customer" sort={sort} onSort={updateSort} />
                    <SortableHeader label="Status" sortKey="status" sort={sort} onSort={updateSort} />
                    <SortableHeader label="Payment" sortKey="payment" sort={sort} onSort={updateSort} />
                    <SortableHeader label="Total" sortKey="total" sort={sort} onSort={updateSort} align="end" />
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id}>
                      <td>
                        <strong>{order.id}</strong>
                        <span>{dateFormatter.format(new Date(order.placedAt))}</span>
                      </td>
                      <td>
                        <strong>{order.customer}</strong>
                        <span>{order.email}</span>
                      </td>
                      <td>
                        <span className="orders-pill" data-tone={statusTone(order.status)}>
                          {order.status}
                        </span>
                      </td>
                      <td>
                        <span className="orders-pill" data-tone={paymentTone(order.payment)}>
                          {order.payment}
                        </span>
                      </td>
                      <td className="orders-total">
                        <strong>{currency.format(order.total)}</strong>
                        <span>
                          {order.items} {order.items === 1 ? 'item' : 'items'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function SortableHeader({
  label,
  sortKey,
  sort,
  align,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  sort: { key: SortKey; direction: SortDirection };
  align?: 'end';
  onSort: (key: SortKey) => void;
}) {
  const active = sort.key === sortKey;

  return (
    <th aria-sort={active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
      <button
        className="orders-sort"
        data-active={active}
        data-direction={active ? sort.direction : undefined}
        data-align={align}
        type="button"
        onClick={() => onSort(sortKey)}
      >
        <span>{label}</span>
        <span className="orders-sort-indicator" aria-hidden="true">
          {active ? (sort.direction === 'asc' ? 'Asc' : 'Desc') : 'Sort'}
        </span>
      </button>
    </th>
  );
}

function OrdersTableSkeleton() {
  return (
    <div className="orders-table-wrap" aria-hidden="true">
      <div className="orders-skeleton-bar" />
      <table className="orders-table orders-table--skeleton">
        <tbody>
          {Array.from({ length: 6 }).map((_, index) => (
            <tr key={index}>
              <td />
              <td />
              <td />
              <td />
              <td />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function compareOrders(a: Order, b: Order, key: SortKey) {
  if (key === 'placedAt') return Date.parse(a.placedAt) - Date.parse(b.placedAt);
  if (key === 'total') return a.total - b.total;
  if (key === 'customer') return a.customer.localeCompare(b.customer);
  if (key === 'status') return a.status.localeCompare(b.status);
  return a.payment.localeCompare(b.payment);
}

function statusTone(status: OrderStatus) {
  if (status === 'Shipped') return 'success';
  if (status === 'Cancelled') return 'danger';
  if (status === 'Processing') return 'info';
  return 'neutral';
}

function paymentTone(payment: PaymentStatus) {
  if (payment === 'Paid') return 'success';
  if (payment === 'Failed') return 'danger';
  if (payment === 'Pending') return 'warning';
  return 'neutral';
}
