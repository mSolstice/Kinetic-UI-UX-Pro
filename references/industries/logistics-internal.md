# Logistics Internal

## Primary User Goal

Users are trying to route, assign, scan, locate, reconcile, or recover operational work under time pressure, interruptions, device constraints, and real-world movement.

## Trust Requirements

At the moment of decision, show item/order ID, location, route, status freshness, assignee, exception state, scan confidence, next handoff, and whether the action is reversible.

## Error Costs

High-cost mistakes include wrong shipment handoff, misrouted item, missed exception, duplicate scan, stale route, or dispatch instruction sent to the wrong worker.

## Density Expectations

High density. Internal logistics screens need fast scanning, durable labels, compact controls, and visible exception hierarchy. Touch targets still cannot shrink below minimums.

## Motion Budget

Near-zero. Use immediate feedback for scan, assign, fail, and retry. Avoid decorative animation, slow transitions, and anything that delays throughput.

## Style Fit

Suitable: `technical-dense`, `high-contrast-utility`, `data-forward`, `retro-terminal` for command-center contexts only.

Conflicts: `editorial`, `luxury-minimal`, `glass-layered`, `soft-neumorphic`, `playful-rounded`, and `warm-organic` when they reduce operational density or status clarity.

## Often Forgotten States

- Stale GPS or scan data
- Duplicate scan
- Partial route failure
- Offline queue
- Permission-denied reassignment
- Damaged or exception item
- Worker handoff pending
- Device battery or camera unavailable

## Domain-Specific Failure Modes

- Route board shows assignment without data freshness
- Barcode scan succeeds visually but fails server reconciliation
- Exception queue uses color only to show severity
- Driver reassignment lacks confirmation of affected stops
- Offline scan queue has no conflict recovery
- Long package IDs truncate without copy or full-view access
