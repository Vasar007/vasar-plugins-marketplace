---
type: regex
pattern: '\nFREE_SHIPPING_THRESHOLD\s=\s50\.0\n[\s\S]*\nBASE_FEE\s=\s4\.90\n[\s\S]*\nFEE_PER_KILOGRAM\s=\s1\.20\n[\s\S]*\nMAX_WEIGHT_KILOGRAMS\s=\s30\n[\s\S]*\n\s+if\s+order_total\s+>=\s+FREE_SHIPPING_THRESHOLD:\s+return\s+0\.0\s+return\s+round\(BASE_FEE\s\+\sFEE_PER_KILOGRAM\s\*\s\(weight_kilograms\s-\s1\),\s2\)\n'
target: { source: file, path: app/shipping.py }
---
