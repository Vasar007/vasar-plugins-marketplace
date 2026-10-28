---
type: regex
pattern: '(?=[\s\S]*\b212\b)(?=[\s\S]*\b209\b)(?=[\s\S]*test_sparse_files)(?=[\s\S]*test_ipv6_port)(?=[\s\S]*test_ipv6_list)(?=[\s\S]*FreeBSD 14)(?=[\s\S]*(?:4 min(?:utes?)? (?:and )?12|252 s(?:ec(?:onds?)?)?\b))(?=[\s\S]*2 GiB)'
target: { source: file, path: report.md }
arm: both
---
