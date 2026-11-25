---
type: regex
pattern: 'orders_count|orders?[ -]count|(?<!\brow )(?<!\brows )\bcount(?:s|ing)?\b[^.\n]{0,25}\borders|number of (?:the |their |a customer.s )?orders|how many orders (?:a|each|the|one|this)(?: given)? customer (?:has|had|placed|places|made|makes)\b|orders?[ -]per[ -]customer[ -](?:total|count|number)|(?:total|count|number)(?: of)? orders per customer'
flags: i
target: { source: file, path: notes/PRs/PR-user-tasks-12-customer-index.md }
---
