---
type: regex
pattern: 'performance[^\n]{0,160}(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used)|skipp|left (?:it )?out|dropp|omitt|ignor|no such)|(?:(?:not|n.t) (?:exist|found|kept|keep|add|added|apply|applied|available|use|used)|skipp|left (?:it )?out|dropp|omitt|ignor|no such)[^\n]{0,160}performance'
flags: i
target: last_message
---
