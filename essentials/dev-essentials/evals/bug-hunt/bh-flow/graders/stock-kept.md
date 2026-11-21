---
type: regex
pattern: '^"""Stock rules\."""\n\n\ndef full_cases\(units, case_size\):\n    """Return how many full cases a number of units fills\."""\n    # Floor division is correct here: a partial case is not shippable\.\n    return units // case_size\n\n\ndef free_units\(on_hand, reserved\):\n    """Return the units that nobody reserved\. The result is never below zero\."""\n    return max\(on_hand - reserved, 0\)\n(?![\s\S])'
target: { source: file, path: project/inventory/stock.py }
---
