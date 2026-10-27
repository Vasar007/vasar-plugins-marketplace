---
description: Probe of the eval-only dependency copy. It shows whether a case loads dev-essentials from the .deps folder that compare_versions.py makes with --extra-dep.
tags: [probe]
plugins: ["../../..", "../../../.deps/dev-essentials"]
allowed_tools: [Skill, Read]
---

List the name of each skill in your listing that has a plugin prefix, with the prefix. Do not invoke a skill.
