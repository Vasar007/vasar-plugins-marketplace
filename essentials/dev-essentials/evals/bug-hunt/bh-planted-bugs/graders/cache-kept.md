---
type: regex
pattern: '^"""A cache for stock levels\."""\n\n_cache = \{\}\n\n\ndef stock_level\(sku, warehouse, loader\):\n    """Return the stock level of a sku in one warehouse\. The loader reads it from the database\."""\n    key = sku\n    if key not in _cache:\n        _cache\[key\] = loader\(sku, warehouse\)\n    return _cache\[key\]\n\n\ndef clear\(\):\n    """Empty the cache\."""\n    _cache\.clear\(\)\n(?![\s\S])'
target: { source: file, path: project/inventory/cache.py }
---
