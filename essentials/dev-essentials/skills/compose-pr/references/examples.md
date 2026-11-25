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

Unit and integration tests cover multi-currency edge cases.
```

Length: about 430 characters.

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

Unit tests cover the edge cases, and integration tests cover multi-currency orders.
```

Length: about 440 characters.

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
Integration tests simulate failures at each stage, and load tests verify 1000 concurrent orders.

## Notes
Breaking change: Order status polling now uses an event subscription model. Update clients to use webhooks.
```

Length: about 890 characters.
