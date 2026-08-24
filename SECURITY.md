# Security Policy

The current source candidate is **v6.0.1**. Its stable release requires the sanitized
live Playwright/Tag Assistant pilot described in the repository release checks. Only the
latest stable release receives fixes.

Report vulnerabilities privately through GitHub security advisories. Do not
open a public issue containing credentials, personal data, client domains,
container/destination IDs, tracking plans, screenshots, evidence files,
browser-session details, or run output.

All evidence persistence must pass through the central privacy/redaction gate. Raw
sensitive material belongs only in explicit quarantine and cannot be loaded into
verdicts or reports. The runtime does not persist screenshots. Machine provenance and
passing statuses remain code-path controlled; agent notes cannot fabricate observations
or upgrade a deterministic result.
