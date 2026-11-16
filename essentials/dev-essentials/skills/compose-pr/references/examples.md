# Example PR Descriptions

Step 5 of `SKILL.md` points here. Each example follows the structure and the length limits of `SKILL.md`.

## Example Output (Small Change)

**With a spec or a plan (here an OpenSpec change):**

```markdown
## Changes

Implements the OpenSpec change `order-discount-limits`. Added validation to prevent discounts that exceed the order total.

## Modified Components

- **DiscountCalculator**: Limit check against the order total
- **DiscountPolicy**: Validation rules for discount ranges

## Testing

Unit and integration tests cover multi-currency edge cases.
```

Length: about 350 characters.

**Without a spec or a plan:**

```markdown
## Changes

Added discount validation to prevent discounts that exceed the order total.

## Modified Components

- **DiscountCalculator**: Added a limit check against the order total
- **DiscountPolicy**: Added validation rules for discount ranges

## Testing

Unit tests cover edge cases; integration tests verify multi-currency scenarios.
```

Length: about 340 characters.

## Example Output (Larger Change)

```markdown
## Changes
Refactored order processing to support async state transitions and improve error handling. Introduced an event-driven design for the order lifecycle.

## Modified Components
- **OrderProcessor**: Async state machine with retry logic and dead-letter queue
- **PaymentCoordinator**: Event sourcing for audit trail and recovery
- **WebApi Controllers**: Updated to return 202 Accepted for long-running operations
- **Configuration**: Added circuit breaker and timeout settings
- **Persistence**: Added event store container with TTL policies

## Testing
Integration tests simulate failures at each stage. Load tests verify 1000 concurrent orders.

## Notes
Breaking change: Order status polling now uses an event subscription model. Update clients to use webhooks.
```

Length: about 770 characters.
