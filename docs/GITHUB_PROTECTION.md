# GitHub Repository Protection

Repository files clarify rights, but they cannot prevent copying from a public
repository or enforce GitHub account settings. Review these controls in the
repository's GitHub Settings; availability and exact names can vary by plan.

## Access and visibility

- Set the repository to **Private** while source access is restricted or a sale
  is being negotiated. A proprietary license does not hide publicly accessible
  source code.
- Require two-factor authentication for the owner and every collaborator.
- Review collaborators, teams, deploy keys, GitHub Apps, OAuth grants, and
  outside access regularly; remove access that is no longer needed.
- Keep production credentials out of Git. Use Actions/environment secrets,
  minimize who can read them, and rotate any credential that has ever been
  committed or exposed.

## Protect the default branch

Create a branch ruleset for `main` that, where supported:

- Requires pull requests and at least one approval before merging.
- Requires code-owner review (`.github/CODEOWNERS`) and dismisses stale
  approvals after new changes.
- Requires the Python, frontend, and other release-gating CI checks to pass.
- Blocks force pushes and branch deletion, and restricts direct pushes.
- Requires conversation resolution and prevents bypass except for a documented
  emergency process.

A `CODEOWNERS` file only requests review when the repository rules require it;
it does not enable branch protection by itself.

## Security and supply chain

- Enable private vulnerability reporting and publish this `SECURITY.md` policy.
- Enable Dependabot alerts, security updates, and dependency review where
  available. Review new or changed dependency licenses as well as vulnerabilities.
- Enable secret scanning and push protection where available.
- Review GitHub Actions permissions; grant workflows only the minimum token
  permissions they need and pin third-party actions according to your policy.
- Keep backups of the Git repository and critical release artifacts outside the
  same GitHub account. Test restoration periodically.

## Before a public release

Search the complete Git history for secrets and confidential/customer data.
Removing a secret from the latest commit is not enough if it remains in history;
rotate exposed credentials and use GitHub's supported history-remediation process.
Review license files, notices, SBOM output, and repository visibility before
changing the repository to public.
