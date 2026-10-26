---
type: regex
pattern: 'public string Generate\(int sequence, DateOnly date\)[\s\S]*public bool TryParseSequence\(string value, out int sequence\)'
target: { source: file, path: src/Billing.Domain/Invoices/InvoiceNumberGenerator.cs }
---
