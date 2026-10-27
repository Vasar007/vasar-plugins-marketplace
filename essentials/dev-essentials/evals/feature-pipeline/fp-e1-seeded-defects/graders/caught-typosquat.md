---
type: regex
pattern: '- \[ \](?=(?:(?!- \[ \])[\s\S]){0,900}?\(confidence)(?:(?!- \[ \])[\s\S]){0,900}?(?:\x60?(?:\S*/)?Directory\.Packages\.props:\d+(?:(?!- \[ \])[\s\S]){0,700}?(?:typo-?squat|Newtonsoft\.Jsonn|look-?alike|misspel|one (?:letter|character)|dependency confusion)|(?:typo-?squat|Newtonsoft\.Jsonn|look-?alike|misspel|one (?:letter|character)|dependency confusion)(?:(?!- \[ \])[\s\S]){0,700}?\x60?(?:\S*/)?Directory\.Packages\.props:\d+)'
flags: i
target: trace
---
