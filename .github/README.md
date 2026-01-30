# About This Directory

This `.github` directory is reserved for GitHub-specific configuration files.

## Common GitHub Files

When you're ready, you can add:

- **workflows/** - GitHub Actions CI/CD pipelines
- **ISSUE_TEMPLATE/** - Issue templates for bug reports, feature requests
- **PULL_REQUEST_TEMPLATE.md** - Template for pull requests
- **dependabot.yml** - Automated dependency updates
- **CODEOWNERS** - Code review ownership

## Not Required

These files are optional and should only be added when needed for your workflow.

Currently, the project uses:
- Google Cloud Build for CI/CD (see `cloudbuild.yaml` in root)
- Manual deployment via scripts (see `deploy-cloud-run.sh`)

If you migrate to GitHub Actions in the future, this is where those workflows would live.
