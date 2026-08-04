# Checkout Flow Spec

## Job
Let a buyer complete a purchase with confidence while handling inventory, address, tax, shipping, and payment changes without surprise.

**Is the request a solution in disguise?**
Yes if it only asks for a payment form. Checkout is cart validation, fulfillment promise, payment authorization, and recovery.

## Actors & context
Returning customer, guest buyer, gift buyer, international buyer, or mobile buyer under time pressure.

## Flow
```
Cart → [review] → shipping address → [delivery options] → payment → [review order] → place order → confirmation
       ↓ failure        ↓ failure            ↓ failure        ↓ failure        ↓ failure       ↓ failure
     fix cart         fix address          choose fallback   recover pay      edit order      recover order
```

| Step | State | User can do | Failure branch | Reverse path |
| --- | --- | --- | --- | --- |
| Cart review | Default/empty/stale/error | Edit quantity, remove items, apply code | Cart empty, item out of stock, stale price | Back to shopping or saved cart |
| Shipping address | Partial/loading/error/success | Enter or choose address | Address validation failure, unsupported region | Back to cart review |
| Delivery options | Loading/partial/error/success | Pick shipping speed or pickup | No delivery method, carrier timeout | Back to address |
| Payment | Partial/loading/error/success | Add card/wallet/store credit | Payment declined mid-flow, 3DS fail, wallet cancel | Back to delivery or choose another method |
| Review order | Stale/partial/success | Confirm totals, items, address, payment | Tax/shipping changed, item stock changed | Back to affected step |
| Place order | Loading/slow/error/success | Submit once | Authorization succeeds but order write fails | Back to review with idempotency status |
| Confirmation | Success/partial/error | See receipt, shipment promise, support route | Confirmation email delayed | Back to account/orders or continue shopping |

## Primary action
Place order.

## States that exist in reality
- [x] Empty: cart has no purchasable items
- [x] Cleared: promo/filter/search removes visible pickup options
- [x] Loading: shipping rates, tax, payment authorization, order write
- [x] Partial: address entered but not validated, payment added but not authorized
- [x] Slow (>5s): carrier rates, fraud check, 3DS challenge
- [x] Error: declined payment, invalid address, failed order creation
- [x] Offline: cannot validate or authorize
- [x] Stale: inventory, price, tax, shipping promise changed
- [x] Overflow: long item names, multiple shipments, many payment methods
- [x] Permission-denied: restricted product, region, or account rule

## Usually missed edge cases
- Payment declined mid-flow
- Cart item going out of stock between steps
- Address validation failure
- Promo code expires before order placement
- Split shipment changes delivery total
- 3DS challenge succeeds but final order write fails
- Guest email mistyped after payment authorization
- Quantity becomes partially fulfillable

## Words
| Element | Copy |
| --- | --- |
| Primary button | Place order |
| Empty state | Your cart is empty. Add items before checking out. |
| Error message | We could not complete checkout. Your payment was not finalized. |
| Success confirmation | Order placed. Your receipt and delivery details are ready. |

## Success signal
The order is created exactly once, payment state is unambiguous, and the buyer receives a receipt plus recovery path for any partial fulfillment.

## Assumptions made without confirmation
Inventory and totals are revalidated before payment and again before order creation. Order submission is idempotent.
