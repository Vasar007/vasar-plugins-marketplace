---
type: regex
pattern: '^"""Email texts\."""\n\n\ndef build_subject\(order_id\):\n    """Return the subject line of an order email\."""\n    return "Order " \+ order_id\n(?![\s\S])'
target: { source: file, path: project/notify/email.py }
---
