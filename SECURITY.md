# Security Policy

The current source candidate is **v8.0.0**. Only the latest stable release receives
fixes.

Report vulnerabilities privately through GitHub security advisories. Do not open a
public issue containing credentials, personal data, client domains, container or
destination IDs, tracking plans, screenshots, evidence, browser-session details, or run
output.

The runtime redacts credential, cookie, token, session, CSRF, password, and sensitive URL
query fields before canonical evidence is persisted. It stores no screenshots and
packages no run directories. Redaction never upgrades a verdict or substitutes for a
mandatory evidence layer.
