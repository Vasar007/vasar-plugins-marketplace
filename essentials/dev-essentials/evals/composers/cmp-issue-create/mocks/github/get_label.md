---
type: agent
expect:
  owner: example-org
  repo: pager
---

Answer as the GitHub server for the repository example-org/pager. The repository has exactly four labels: bug, documentation, feature, and question. For a call whose name is one of them (ignore case), return the label as JSON with the fields name, color, and description. For any other name, return the JSON {"message": "Not Found", "status": "404"}.
