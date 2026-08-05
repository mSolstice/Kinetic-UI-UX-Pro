# Industry Reasoning Packs

Use these packs as reasoning guidance, not rules. They help choose state
coverage, density, motion, trust signals, and compatible visual styles before
building domain-specific UI.

| Industry | Recommended styles | Motion budget | Density | Top-three forgotten states |
| --- | --- | --- | --- | --- |
| Fintech | `data-forward`, `technical-dense`, `high-contrast-utility`, `swiss-grid` | Near-zero to low | Medium to high | Reconciled vs pending balance; fee changed before submit; stale market/account data |
| Healthcare | `high-contrast-utility`, `swiss-grid`, `data-forward`, `warm-organic` | Very low | Medium | Unit confirmation; wrong-patient prevention; partial result availability |
| Ecommerce | `high-contrast-utility`, `playful-rounded`, `warm-organic`, `luxury-minimal`, `editorial` | Low to medium | Variable | Price changed; out-of-stock between steps; payment declined/requires action |
| SaaS B2B | `technical-dense`, `data-forward`, `swiss-grid`, `high-contrast-utility` | Near-zero to low | Medium to high | Workspace switch; unsaved changes; permission-denied action |
| Education | `playful-rounded`, `warm-organic`, `high-contrast-utility`, `data-forward` | Low | Low to high by role | Draft not submitted; deadline/grace period; accommodation or alternate format |
| Government | `high-contrast-utility`, `swiss-grid`, `data-forward` | Near-zero | Medium | Save/resume on shared device; expired session with recovery; missing document checklist |
| Media Publishing | `editorial`, `swiss-grid`, `luxury-minimal`, `warm-organic` | Low to medium | Variable | Updated/corrected article; paywall limit; lost reading position |
| Travel Booking | `high-contrast-utility`, `data-forward`, `warm-organic`, `editorial` | Low | Medium | Inventory expired; price changed; timezone/date mismatch |
| Logistics Internal | `technical-dense`, `high-contrast-utility`, `data-forward` | Near-zero | High | Stale scan/location data; offline queue; duplicate scan |
| Marketplace | `high-contrast-utility`, `playful-rounded`, `warm-organic`, `data-forward` | Low to medium discovery; low payment/dispute | Medium | Verification pending; listing stale; dispute/payment hold state |
