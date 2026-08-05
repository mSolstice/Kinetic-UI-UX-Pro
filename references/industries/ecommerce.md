# Ecommerce

## Primary User Goal

Users are trying to evaluate, choose, pay for, receive, return, or get support for a product while balancing price, trust, urgency, and risk. They need confidence that the offer is real and the final cost is stable.

## Trust Requirements

At the moment of decision, show product identity, variant, quantity, price, tax, fees, discount, shipping cost, delivery estimate, return policy, stock status, payment security cue, and final total.

## Error Costs

High-cost mistakes include ordering the wrong variant, paying an unexpected total, missing return restrictions, shipping to the wrong address, or buying an out-of-stock item. Concrete failure mode: a total that changes after the payment step.

## Density Expectations

Variable density. Product discovery can be spacious; comparison, cart, checkout, and order management need compact clarity with totals and constraints visible near the action.

## Motion Budget

Low to medium. Use motion for cart add, step progression, loading, and confirmation only when it does not hide totals. Avoid motion that creates pressure or obscures price changes.

## Style Fit

Suitable: `high-contrast-utility`, `playful-rounded`, `warm-organic`, `luxury-minimal`, `editorial` depending on brand and product.

Conflicts: `technical-dense` for consumer browsing, `retro-terminal`, `brutalist` for trust-sensitive checkout, and `glass-layered` where totals or legal text sit over variable backgrounds.

## Often Forgotten States

- Variant unavailable
- Price changed since item was added
- Cart item out of stock between steps
- Discount removed or ineligible
- Address validation failed
- Payment pending, declined, or requires action
- Partial shipment and split delivery
- Return window expired

## Domain-Specific Failure Modes

- Final total changes after payment method entry
- Product card hides unavailable sizes until checkout
- Free-shipping threshold ignores taxes or discounts
- Return policy is inaccessible at purchase decision
- Saved address is stale but used silently
- Checkout loses cart after session expiry
