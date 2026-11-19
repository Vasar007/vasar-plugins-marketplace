---
type: regex
match: not_contains
pattern: '\b(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\.Shou[l]d\(\)|Assert\.That\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*(?:[,)]|==)|Assert\.(?:AreEqual|Equal)(?:<\w+>)?\(\s*(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*"|\w+)\s*,\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*[,)]|Assert\.(?:AreEqual|Equal)(?:<\w+>)?\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*,\s*(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*")\s*[,)]|(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*")\s*\.Shou[l]d\(\)\s*\.Be\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\)|Assert\.That\(\s*(?:-?\d[\d_.]*[mMdDfFlL]?|"[^"\n]*")\s*,\s*Is\.EqualTo\(\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\)|\b(\w+)\s*=\s*(?:[\w.]*\.)?(?:FreeShippingThreshold|BaseFee|FeePerKilogram|MaxWeightKilograms|Carrier)\s*\x3b[\s\S]*?\b\1\s*\.Shou[l]d\(\)'
target: { source: file, path: tests/Billing.Domain.Tests/Shipping/ShippingFeeCalculatorTests.cs }
---
