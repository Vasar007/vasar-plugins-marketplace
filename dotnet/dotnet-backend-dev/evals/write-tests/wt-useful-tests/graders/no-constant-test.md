---
type: regex
match: not_contains
pattern: '\b(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\.Shou[l]d\(\)|Assert\.That\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*[,)]|Assert\.(?:AreEqual|Equal)\(\s*(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*"|\w+)\s*,\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\)|Assert\.(?:AreEqual|Equal)\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*,\s*(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*")\s*\)|(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*")\s*\.Shou[l]d\(\)\s*\.Be\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\)'
target: { source: file, path: tests/Billing.Domain.Tests/Shipping/ShippingFeeCalculatorTests.cs }
---
