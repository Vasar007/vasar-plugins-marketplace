# Example PR Descriptions

Step 5 of `SKILL.md` points here. Each example follows the structure and the length limits of `SKILL.md`.

## Example Output (Small Change)

**With a spec or a plan (here a change of the spec framework):**

```markdown
## What

Implements the spec change `order-discount-limits`. A discount can no longer exceed the order total.

## Why

A discount above the order total made the total negative, and the payment step rejected the order.

## Changes

- **DiscountCalculator**: Limit check against the order total
- **DiscountPolicy**: Validation rules for discount ranges

## Testing

Unit and integration tests cover multi-currency edge cases. Not run in this session.
```

Length: about 450 characters.

**Without a spec or a plan:**

```markdown
## What

Adds discount validation, so that a discount cannot exceed the order total.

## Why

Orders with a large discount got a negative total. The validation stops them before the payment step.

## Changes

- **DiscountCalculator**: Added a limit check against the order total
- **DiscountPolicy**: Added validation rules for discount ranges

## Testing

Unit tests cover the edge cases, and integration tests cover multi-currency orders. Not run in this session.
```

Length: about 470 characters.

## Example Output (UI Change)

The input gives no image and no video:

```markdown
## What

Adds a toggle for compact rows to the settings page.

## Why

Users with long lists asked to see more rows on one screen.

## Changes

- **Settings page**: a toggle for compact rows
- **List styles**: a compact row height, with a short slide when the height changes

## UI changes

- **Settings page**: a new toggle "Compact rows" under Display.
- **Order list**: with the toggle on, each row is shorter, and the list slides to the new height.

Not confirmed: images of the settings page and the order list before and after the change, and a short video of the slide.

## Testing

The diff changes no test. Not run in this session.
```

Length: about 640 characters.

## Example Output (Larger Change)

```markdown
## What
Moves order processing to async state transitions, with an event-driven design for the order lifecycle.

## Why
The synchronous flow held the request thread during payment, and a failed step lost the order state. Now the thread is free, and a failed order recovers from its events.

## Changes
- **OrderProcessor**: Async state machine with retry logic and dead-letter queue
- **PaymentCoordinator**: Event sourcing for audit trail and recovery
- **WebApi Controllers**: Updated to return 202 Accepted for long-running operations
- **Configuration**: Added circuit breaker and timeout settings
- **Persistence**: Added event store container with TTL policies

## Testing
Integration tests simulate a failure at each stage, and a load test sends 1000 concurrent orders. Not run in this session.

## Notes
Breaking change: Order status polling now uses an event subscription model. Update clients to use webhooks.
```

Length: about 920 characters.
