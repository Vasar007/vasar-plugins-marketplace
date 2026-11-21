---
type: regex
pattern: '^"""Invoice totals\."""\n\n\ndef line_total\(price, quantity\):\n    """Return the total of one invoice line\."""\n    return price \* quantity\n\n\ndef invoice_total\(lines\):\n    """Return the total of all lines of an invoice, in currency units\."""\n    total = sum\(line_total\(line\["price"\], line\["quantity"\]\) for line in lines\)\n    return int\(total\)\n(?![\s\S])'
target: { source: file, path: project/billing/invoice.py }
---
