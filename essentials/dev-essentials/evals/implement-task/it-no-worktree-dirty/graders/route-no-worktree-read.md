---
type: regex
pattern: '^(?:(?!"command":"(?:[^"\\]|\\.)*?(?:switch(?: +-[\w-]+)*? +(?:-[a-zA-Z]*[cC]|--create|--force-create)|checkout(?: +-[\w-]+)*? +-[a-zA-Z]*[bB]|\bbranch (?!-)(?:[\w.'']|\\")|\bbranch +(?:-[a-zA-Z]*f|--force)\b)|"name":"(?:Edit|Write)"(?![^\n]*"parent_tool_use_id":"toolu_))[\s\S])*?(?:"name":"Read","input":\{"file_path":"|"command":")(?:[^"\\]|\\.)*?work-modes/references(?:[^"\\]|\\.)*?\bno-worktree\.md(?![^\n]*"parent_tool_use_id":"toolu_)'
target: trace
---
