---
type: agent
expect:
  owner: example-org
  repo: pager
---

Answer as the GitHub server for the repository example-org/pager. Issue 77 is the issue that the earlier issue_write call created. Its id is 9077, its state is open, and its html_url is `https://github.com/example-org/pager/issues/77`. Its title, body, and labels are the ones of that issue_write call. For the method get on issue 77, return the issue as JSON. Give it the fields number, id, title, body, state, labels (a list of objects with a name), and html_url. For the method get_parent, and for another issue number, return the JSON {"message": "Not Found", "status": "404"}.
