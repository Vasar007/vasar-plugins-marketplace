---
type: regex
pattern: 'performance[^\n]{0,160}(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used|create|created|present|a label)|skipp|left (?:it )?out|dropp|omitt|ignor|no such|remov|exclud)|(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used|create|created|present|a label)|skipp|left (?:it )?out|dropp|omitt|ignor|no such|remov|exclud)[\s\S]{0,40}performance|\bno [`*"]?performance'
flags: i
target: last_message
---
