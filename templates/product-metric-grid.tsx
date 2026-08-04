import { useMemo } from 'react';

type TrendDirection = 'up' | 'down' | 'flat';

type MetricValue =
  | { kind: 'number'; value: number; unit?: string; maximumFractionDigits?: number }
  | { kind: 'currency'; value: number; currency: string; maximumFractionDigits?: number }
  | { kind: 'percent'; value: number; maximumFractionDigits?: number }
  | { kind: 'empty'; message: string; actionLabel?: string; onAction?: () => void };

type ProductMetric = {
  id: string;
  label: string;
  description?: string;
  value: MetricValue;
  trend?: {
    direction: TrendDirection;
    label: string;
  };
};

type MetricGridState =
  | { status: 'loading'; skeletonCount?: number }
  | { status: 'success'; metrics: ProductMetric[] }
  | { status: 'error'; message: string; onRetry: () => void };

type ProductMetricGridProps = {
  state: MetricGridState;
  locale?: string;
  title?: string;
  emptyTitle?: string;
  emptyMessage?: string;
  emptyActionLabel?: string;
  onCreateMetric?: () => void;
};

const trendGlyph: Record<TrendDirection, string> = {
  up: '+',
  down: '-',
  flat: '=',
};

export function ProductMetricGrid({
  state,
  locale = navigator.language,
  title = 'Product metrics',
  emptyTitle = 'No metrics configured',
  emptyMessage = 'Choose the product signals this team reviews most often.',
  emptyActionLabel = 'Add metric',
  onCreateMetric,
}: ProductMetricGridProps) {
  const formatter = useMemo(() => createMetricFormatter(locale), [locale]);
  const loadingCount = state.status === 'loading' ? state.skeletonCount ?? 6 : 0;
  const isEmpty = state.status === 'success' && state.metrics.length === 0;

  return (
    <section className="metric-panel" aria-busy={state.status === 'loading'}>
      <div className="metric-panel__header">
        <h2>{title}</h2>
        {onCreateMetric && (
          <button
            className="metric-panel__action"
            type="button"
            onClick={onCreateMetric}
            aria-disabled={state.status === 'loading'}
          >
            {emptyActionLabel}
          </button>
        )}
      </div>

      <div className="sr-only" role="status" aria-live="polite">
        {state.status === 'loading' ? 'Loading product metrics.' : ''}
        {state.status === 'error' ? state.message : ''}
      </div>

      {state.status === 'loading' && (
        <ul className="metric-grid" aria-hidden="true">
          {Array.from({ length: loadingCount }).map((_, index) => (
            <li className="metric-card metric-card--skeleton" key={index}>
              <span className="metric-card__label-skeleton" />
              <span className="metric-card__value-skeleton" />
              <span className="metric-card__meta-skeleton" />
            </li>
          ))}
        </ul>
      )}

      {state.status === 'error' && (
        <div className="metric-empty" role="alert">
          <h3>Metrics could not be loaded</h3>
          <p>{state.message}</p>
          <button className="metric-panel__action" type="button" onClick={state.onRetry}>
            Try again
          </button>
        </div>
      )}

      {isEmpty && (
        <div className="metric-empty">
          <h3>{emptyTitle}</h3>
          <p>{emptyMessage}</p>
          {onCreateMetric && (
            <button className="metric-panel__action" type="button" onClick={onCreateMetric}>
              {emptyActionLabel}
            </button>
          )}
        </div>
      )}

      {state.status === 'success' && state.metrics.length > 0 && (
        <ul className="metric-grid">
          {state.metrics.map((metric) => (
            <MetricCard key={metric.id} metric={metric} formatter={formatter} />
          ))}
        </ul>
      )}
    </section>
  );
}

function MetricCard({
  metric,
  formatter,
}: {
  metric: ProductMetric;
  formatter: ReturnType<typeof createMetricFormatter>;
}) {
  const isMetricEmpty = metric.value.kind === 'empty';

  return (
    <li className={isMetricEmpty ? 'metric-card metric-card--empty' : 'metric-card'}>
      <div className="metric-card__topline">
        <h3>{metric.label}</h3>
        {metric.trend && !isMetricEmpty && (
          <span className={`metric-card__trend metric-card__trend--${metric.trend.direction}`}>
            <span aria-hidden="true">{trendGlyph[metric.trend.direction]}</span>
            {metric.trend.label}
          </span>
        )}
      </div>

      {isMetricEmpty ? (
        <div className="metric-card__empty-body">
          <p>{metric.value.message}</p>
          {metric.value.onAction && metric.value.actionLabel && (
            <button className="metric-card__link" type="button" onClick={metric.value.onAction}>
              {metric.value.actionLabel}
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="metric-card__value">{formatter(metric.value)}</p>
          {metric.description && <p className="metric-card__description">{metric.description}</p>}
        </>
      )}
    </li>
  );
}

function createMetricFormatter(locale: string) {
  return (value: Exclude<MetricValue, { kind: 'empty' }>) => {
    const maximumFractionDigits = value.maximumFractionDigits ?? 1;

    if (value.kind === 'currency') {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: value.currency,
        maximumFractionDigits,
      }).format(value.value);
    }

    if (value.kind === 'percent') {
      return new Intl.NumberFormat(locale, {
        style: 'percent',
        maximumFractionDigits,
      }).format(value.value);
    }

    const formatted = new Intl.NumberFormat(locale, {
      maximumFractionDigits,
    }).format(value.value);

    return value.unit ? `${formatted} ${value.unit}` : formatted;
  };
}

export const productMetricExample: ProductMetric[] = [
  {
    id: 'activation',
    label: 'New-user activation after assisted setup completion',
    value: { kind: 'percent', value: 0.428 },
    trend: { direction: 'up', label: '6.2% vs last week' },
    description: 'Users who reached their first successful product action.',
  },
  {
    id: 'localized-retention',
    label: 'Kundenbindungsrate fur lokalisierte Produktvarianten',
    value: { kind: 'percent', value: 0.781 },
    trend: { direction: 'flat', label: 'steady' },
    description: 'German label pressure test without destructive truncation.',
  },
  {
    id: 'empty-quality',
    label: 'Post-launch qualitative sentiment by market segment',
    value: {
      kind: 'empty',
      message: 'No survey responses have been connected for this metric.',
      actionLabel: 'Connect source',
    },
  },
];
