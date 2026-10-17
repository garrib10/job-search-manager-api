# Security Policy

## Supported versions

Only the latest release on the `main` branch is supported. It is the version deployed at
https://job-search-manager-api-production.up.railway.app. Fixes are not backported to older releases.

## Reporting a vulnerability

**Please do not report security issues in public GitHub issues, pull requests, or discussions.**

Report privately through GitHub's private vulnerability reporting:

1. Go to the repository's [**Security** tab](https://github.com/garrib10/job-search-manager-api/security).
2. Click **Report a vulnerability**, or go directly to the
   [new advisory form](https://github.com/garrib10/job-search-manager-api/security/advisories/new).
3. Describe the issue, the affected endpoint or file, steps to reproduce, and the impact you expect.

## What to expect

This is a personal project maintained by one person, so response times are best effort:

- **Acknowledgement:** within 7 days.
- **Assessment:** within 14 days, including whether the report is accepted and how severe it is.
- **Fix:** depends on severity. Accepted issues are fixed on `develop`, released to `main`, and credited in the
  advisory unless you prefer to stay anonymous.

## Scope

**In scope**

- The API source code in this repository (`app/`).
- The deployed API at https://job-search-manager-api-production.up.railway.app.
- The GitHub Actions workflows in `.github/workflows/`.

**Out of scope**

- Vulnerabilities in third-party dependencies that have no exploitable path in this project. Please report those
  upstream; Dependabot tracks published advisories here.
- Denial-of-service, load, or volume testing against the deployed API.
- Findings from automated scanners without a demonstrated impact.
- Social engineering, and issues with GitHub or Railway themselves.

**Known limitation (please don't report)**

All authenticated users currently share the same companies, applications, and interviews. Every resource endpoint
requires login, but records are not yet owned by a user. Per-user ownership is planned for v0.2.0.

## Testing guidelines

- Only use accounts you created yourself, and do not access, modify, or delete data you did not create.
- Do not run automated scanners or high-volume requests against the deployed API.
- Stop and report as soon as you confirm an issue; do not keep exploiting it.
