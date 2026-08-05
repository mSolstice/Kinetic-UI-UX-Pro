# Travel Booking

## Primary User Goal

Users are trying to compare, reserve, change, or cancel time-sensitive travel inventory while coordinating money, identity, documents, people, and uncertainty.

## Trust Requirements

At the moment of decision, show traveler identity, dates, time zone, route/location, fare/rate rules, taxes/fees, cancellation policy, baggage or amenity limits, inventory hold time, and final total.

## Error Costs

High-cost mistakes include booking wrong date, wrong passenger, wrong location, non-refundable fare, missing document requirement, or total change after payment review.

## Density Expectations

Medium density. Search results need comparison; checkout needs clear staged confirmation. Mobile must expose critical constraints without burying them in accordions.

## Motion Budget

Low. Use motion for search loading, step progression, and map/list orientation. Avoid large animations that delay booking or hide time-sensitive inventory changes.

## Style Fit

Suitable: `high-contrast-utility`, `data-forward`, `warm-organic`, `editorial`, `playful-rounded` for discovery.

Conflicts: `luxury-minimal` when it hides restrictions, `glass-layered` over maps without solid text surfaces, `brutalist`, `retro-terminal`, and `soft-neumorphic` for checkout.

## Often Forgotten States

- Inventory expired during review
- Price changed since search
- Timezone difference
- Passport/visa or ID requirement
- Split booking or partial availability
- Payment requires extra verification
- Cancellation window and refund status
- Offline itinerary access

## Domain-Specific Failure Modes

- Calendar selects local date but itinerary uses destination timezone
- Hotel room policy hides taxes or resort fees until payment
- Flight fare changes after passenger details are entered
- Cancellation rule is not visible beside final confirmation
- Search result remains selectable after inventory expires
- Passenger name field does not match document-name constraints
