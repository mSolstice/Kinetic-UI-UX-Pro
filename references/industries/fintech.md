# Fintech

## Primary User Goal

Users are trying to understand, move, approve, reconcile, or recover money under high consequence and often time pressure. They need confidence that figures are current, actions are authorized, and the next step will not create an unintended financial obligation.

## Trust Requirements

At the moment of decision, show amount, currency, account/source, recipient, fees, effective date, settlement timing, data freshness, authorization method, and whether the value is pending, estimated, available, or reconciled. Users should never have to infer whether a number is final.

## Error Costs

Irreversible or high-cost mistakes include sending funds to the wrong recipient, approving the wrong amount, trading before reviewing order type, accepting unexpected fees, closing an account, or relying on stale balances. Concrete failure mode: showing a balance before it has reconciled, then letting the user transfer or trade against it.

## Density Expectations

Medium to high density. Financial screens need comparison and auditability, but primary actions must be isolated from review details. Transaction lists, balances, alerts, and permissions need compact hierarchy rather than marketing spacing.

## Motion Budget

Near-zero to low. Motion should indicate loading, confirmation, reversal windows, and changed values. Avoid count-up animations for money, animated balances, celebratory transfer effects, or transitions that delay review.

## Style Fit

Suitable: `data-forward`, `technical-dense`, `high-contrast-utility`, `swiss-grid`, `luxury-minimal` for premium account surfaces.

Conflicts: `brutalist`, `playful-rounded`, `glass-layered`, `soft-neumorphic`, `retro-terminal` when they obscure seriousness, clarity, or contrast.

## Often Forgotten States

- Pending, available, posted, failed, reversed, disputed, and reconciled states
- Stale market data or delayed balance refresh
- Partial account permission
- Beneficiary verification pending
- Transfer limit exceeded
- Fee changed between quote and submit
- Offline or session-expired recovery after form entry

## Domain-Specific Failure Modes

- Balance shown without last-reconciled timestamp
- Payment confirmation missing recipient account identifier
- Fee disclosed only after final submit
- Decimal or currency switch not visible beside the amount field
- Chart uses color only to indicate loss or gain
- Trade preview omits order type, expiry, or settlement timing

## complianceConsiderations

This is orientation, not legal advice. Requirements vary by jurisdiction and must be verified with qualified legal, compliance, security, and accessibility professionals.

Categories that typically apply include financial disclosure, consumer protection, payments security, identity verification, audit logging, privacy, accessibility, records retention, and incident response.

Questions to ask a qualified professional:

- Which disclosures must be visible before authorization?
- What wording distinguishes available, pending, estimated, and settled funds?
- What authentication, authorization, and audit evidence must be captured?
- What data retention and deletion rules apply to transaction history?
- Which accessibility standards and local consumer-protection rules govern this flow?
