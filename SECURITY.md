# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in `playstealth-cli`, please report it
responsibly:

- Email: `security@sin-clis.dev` (PGP key available on request)
- GitHub: open a private security advisory at
  <https://github.com/SIN-CLIs/playstealth-cli/security/advisories/new>

Do **not** open public issues for security concerns.

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.x     | Yes       |
| < 1.0   | No        |

## Secret Management Policy

`playstealth-cli` never commits live secrets. The repository uses the following
controls:

1. `.env` and `*.env.*` are listed in `.gitignore` and `.dockerignore`. Only
   `.env.example` (placeholder values) is tracked.
2. Recommended runtime injection: [Infisical](https://infisical.com) via
   `playstealth_actions.secret_manager.SecretManager` (project ID + machine
   identity token are the only bootstrap variables that need to live in `.env`).
3. The CI workflow (`.github/workflows/ci.yml`) runs a `security` job that
   greps for hardcoded secrets and verifies `.env.example` only contains
   placeholder values.
4. GitHub App private keys must be provided via the `GITHUB_APP_PRIVATE_KEY`
   environment variable (PEM contents) or stored outside of the repository.
   PEM files in the working tree are ignored by git.

## Historical Disclosure

A NVIDIA AI API key was previously committed in `.env` at commit
[`bb966f8`](https://github.com/SIN-CLIs/playstealth-cli/commit/bb966f8d33f4fdef8df6b8a7f52358f3ecdb2e96)
(see issue #9). Mitigation steps that have been applied:

- The key has been rotated at the provider (NVIDIA NGC / build.nvidia.com).
- `.env` has been removed from the working tree and is ignored going forward.
- `.gitignore` and `.dockerignore` now exclude all `.env*` variants except
  `.env.example`.
- Secret-scanning is now part of CI (`security` job).

If you maintain a fork that still includes the historical commit, run
`git filter-repo` (or `BFG`) to scrub the leaked value from your history and
force-push the cleaned branch.

## Hardening Checklist

Before deploying or contributing, make sure:

- [ ] No live secrets are committed to the repository or its forks.
- [ ] `playstealth_actions.secret_manager` (or equivalent runtime injection)
      is used in production.
- [ ] CI is green, including the `security` job.
- [ ] All operators have read `COMPLIANCE.md` and accept the responsible-use
      policy.
