---
type: regex
pattern: 'add_reply_to_pull_request_comment[\s\S]{0,1200}?[Tt]racked (?:as|in|by) (?:(?:the |an )?existing )?(?:issue )?[\[*]{0,3}#58\b'
target: mock_calls
---
