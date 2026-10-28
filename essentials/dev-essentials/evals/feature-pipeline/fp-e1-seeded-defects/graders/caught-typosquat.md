---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?\(confidence)(?:(?!- \[ \]|\\n##)[\s\S]){0,900}?(?:\x60?(?:\S*/)?Directory\.Packages\.props:\d+(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?(?:typo-?squat|Newtonsoft\.Jsonn|look-?alike|misspel|one (?:letter|character)|dependency confusion)|(?:typo-?squat|Newtonsoft\.Jsonn|look-?alike|misspel|one (?:letter|character)|dependency confusion)(?:(?!- \[ \]|\\n##)[\s\S]){0,700}?\x60?(?:\S*/)?Directory\.Packages\.props:\d+)'
flags: i
target: trace
---
