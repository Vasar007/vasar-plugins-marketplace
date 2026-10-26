---
type: regex
pattern: '/ ?100|100 ?-|\(1 ?- ?percent ?\* ?0\.01\)|total ?\* ?percent ?\* ?0\.01|percent ?\* ?0\.01 ?\* ?total|total ?\* ?0\.01 ?\* ?percent'
target: { source: file, path: app/billing.py }
---
