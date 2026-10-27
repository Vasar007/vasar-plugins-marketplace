---
type: regex
pattern: 'public\sstring\sGenerate\(int\ssequence,\sDateOnly\sdate\)\s+\{\s+if\s\(sequence\s<=\s0\)\s+\{\s+throw\snew\sArgumentOutOfRangeException\(nameof\(sequence\),\s"The\ssequence\smust\sbe\spositive\."\)\x3b\s+\}\s+return\s\$"\{Prefix\}-\{date\.Year:D4\}-\{sequence:D6\}"\x3b\s+\}\s+///\s<summary>\s+///\sReads\sthe\ssequence\snumber\sof\san\sinvoice\snumber\.\sReturns\sfalse\sif\sthe\stext\shas\sanother\sformat\.\s+///\s</summary>\s+public\sbool\sTryParseSequence\(string\svalue,\sout\sint\ssequence\)\s+\{\s+sequence\s=\s0\x3b\s+var\sparts\s=\svalue\.Split\(\x27-\x27\)\x3b\s+return\sparts\.Length\s==\s3\s+&&\sparts\[0\]\s==\sPrefix\s+&&\sint\.TryParse\(parts\[2\],\sout\ssequence\)\s+&&\ssequence\s>\s0\x3b\s+\}\s+\}'
target: { source: file, path: src/Billing.Domain/Invoices/InvoiceNumberGenerator.cs }
---
