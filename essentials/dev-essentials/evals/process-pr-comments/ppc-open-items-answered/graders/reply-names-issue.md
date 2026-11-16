---
type: regex
pattern: '"tool":"(?:\w*__)?add_reply_to_pull_request_comment"[^\n]{0,1200}?[Tt]racked (?:as|in|by) (?:issue )?[\[*]{0,3}#77\b'
target: mock_calls
---
