# HACS Compatibility Auditor Rules

Community rules repository for [HACS Compatibility Auditor](https://github.com/RmG152/hacs-compatibility-auditor).

## What is this?

The HACS Compatibility Auditor integration analyzes HACS repositories looking for potential incompatibilities with Home Assistant. However, it can sometimes generate **false positives** (marking something as incompatible when it works) or **false negatives** (failing to detect a real incompatibility).

This repository centralizes **reviewed community rules** that the integration consumes to improve its accuracy:

| Rule | Purpose |
|------|---------|
| **Whitelist** | Repos that the algorithm incorrectly flags but are compatible |
| **Blacklist** | Incompatible repos that the algorithm doesn't detect on its own |
| **False Positives** | Specific issues that should be ignored in the analysis |
| **Label Overrides** | Adjust label weights per repository |
| **Keyword Overrides** | Adjust keyword weights per repository |

## How to contribute

Open an issue using the corresponding template:

- [Suggest Whitelist](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=whitelist_request.yml) — to report a false positive
- [Suggest Blacklist](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=blacklist_request.yml) — to report an undetected incompatibility
- [Report False Positive](https://github.com/RmG152/hacs-compatibility-auditor-rules/issues/new?template=false_positive_report.yml) — to ignore a specific issue

A workflow will automatically review your request and create a Pull Request. A maintainer will review and approve the changes.

## Structure

```
rules/
├── whitelist.yaml            # Compatible repos (override false positives)
├── blacklist.yaml            # Incompatible repos (override false negatives)
├── false_positives.yaml      # Specific issues to ignore
├── label_overrides.yaml      # Label weight overrides
└── keyword_overrides.yaml    # Keyword weight overrides
index.json                    # Auto-generated manifest
```

## Rule Format

### Whitelist / Blacklist

```yaml
repositories:
  - full_name: "owner/repo"
    reason: "Reason for inclusion"
    ha_version: ">=2026.1.0"    # Optional, "*" = all
    added: "2026-05-14"
    issue: "https://github.com/.../issues/1"
```

### False Positives

```yaml
issues:
  - full_name: "owner/repo"
    issue_number: 123
    reason: "Issue resolved but label was not cleaned up"
    added: "2026-05-14"
    issue: "https://github.com/.../issues/2"
```

### Label / Keyword Overrides

```yaml
overrides:
  - full_name: "owner/repo"
    labels:
      "breaking": 0         # Ignore this label
      "incompatible": 5     # Reduce weight
```

## License

MIT
