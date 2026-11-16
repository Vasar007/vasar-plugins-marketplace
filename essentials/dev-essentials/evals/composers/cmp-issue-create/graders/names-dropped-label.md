---
type: regex
pattern: 'performance[^\n]{0,160}(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used|create|created|present|a label|have|has|defined)|skipp|left (?:it )?out|dropp|omitt|ignor|no such|remov(?:ed|ing|al)\b|exclud)|(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used|create|created|present|a label|have|has|defined)|skipp|left (?:it )?out|dropp|omitt|ignor|no such|remov(?:ed|ing|al)\b(?=[^.\n]{0,40}\blabel)|exclud)(?:[^.\n]|\n(?=[ \t]*[-*])){0,40}performance|\blabels?\b[^.\n]{0,30}remov(?:ed|ing|al)\b(?:[^.\n]|\n(?=[ \t]*[-*])){0,40}performance|\bno [`*"]?performance'
flags: i
target: last_message
---
