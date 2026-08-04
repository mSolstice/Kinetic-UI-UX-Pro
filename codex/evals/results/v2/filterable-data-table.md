Using Kinetic UI UX Pro.

References loaded:
- references/ux-foundations.md
- references/interaction-states.md
- references/i18n-and-input.md

Scripts run:
- scripts/ast_audit.py examples/orders-table/OrdersTable.tsx

Designed a filterable orders table with search, status filters, sortable columns, retry after failed loading, overflow handling for long values, and a cleared-by-filter state that offers reset filters instead of pretending the table is truly empty.

### Kinetic UI UX Pro Verification Receipt
- **Job & primary action:** Find the right order quickly; primary action is refine/search orders.
- **States implemented:** loading, error, success, empty, cleared-by-filter.
- **Programmatic signalling:** `aria-busy`, table sort state, and polite status text.
- **i18n & input:** long order names wrap; dates and amounts use locale-aware formatting.
