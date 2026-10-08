# Commercial Sale and Transfer Checklist

This checklist is operational guidance, not a sale contract or legal opinion.
Have an intellectual-property lawyer in the relevant jurisdictions review the
chain of title and transaction documents before promising exclusive ownership.

## Establish what can be transferred

- Reconcile the GitHub repository owner, contributors, pull requests, outside
  contractors, employees, and any prior employer or client agreements.
- Obtain signed written assignments or licenses for contributions where needed.
  Git history and repository ownership alone do not prove ownership of every
  copyright or asset.
- Inventory project-created code, documentation, designs, names/logos, domains,
  social accounts, deployment accounts, databases, and release artifacts.
- Separate components that cannot be assigned as project-owned IP, including
  open-source dependencies, the Vazirmatn font under OFL 1.1, hosted services,
  provider APIs, and third-party/customer content. Preserve their terms.
- Generate an SBOM and a license/notice report for the exact release being sold.
  Identify components with attribution, source-disclosure, copyleft, or other
  obligations and have counsel assess them.

## Prepare the transaction

- Use a signed agreement with a precise asset schedule. Define whether the deal
  is an asset sale, an assignment of specified rights, an exclusive license,
  or a share/ownership transaction; these are not interchangeable.
- State the transferred and excluded IP, territory, term, exclusivity, price,
  payment milestones, acceptance criteria, transition support, and treatment of
  liabilities, warranties, and indemnities.
- Confirm contributor assignments and any third-party permissions required for
  the specific rights being promised. Do not promise ownership of third-party
  software or assets.
- Define how customer/personal data will be handled, whether it may lawfully be
  transferred, and what must be deleted or retained. A database backup is not
  automatically a transferable project asset.
- Use a lawyer-approved escrow or staged handover if source code, credentials,
  or payment are exchanged in stages. Never put credentials in the contract or
  source repository.

## Secure handover

- Agree on a cutover date and inventory repositories, branches, tags, release
  artifacts, domains, DNS, hosting, cloud resources, registrars, email/SMS,
  payment gateways, AI providers, analytics, backups, and support channels.
- Transfer accounts through each provider's supported ownership-transfer
  process; do not hand over a personal password. Reissue credentials and rotate
  secrets at cutover.
- Transfer or revoke GitHub organization/repository access, Actions secrets,
  deploy keys, Apps, webhooks, environments, branch rulesets, and billing access.
- Take and verify a final backup; document restoration steps and who retains
  copies. Remove the seller's access only after the agreed acceptance and
  payment conditions are satisfied.
- Record delivery, acceptance, remaining obligations, and the effective date in
  signed documents. Keep an archival copy of the agreement and delivered asset
  inventory.

## Repository-specific items

- Project rights notice: root `LICENSE`.
- Third-party inventory process and font notice: `THIRD_PARTY_NOTICES.md` and
  `app/assets/fonts/LICENSE.txt`.
- Repository security and access checklist: `SECURITY.md` and
  `docs/GITHUB_PROTECTION.md`.
- The GitHub repository URL and commit author are evidence of repository
  administration/history, not conclusive proof of copyright ownership.
