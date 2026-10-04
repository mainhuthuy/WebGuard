# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within WebGuard, please report it responsibly.

### How to Report

1. **DO NOT** create a public GitHub issue for security vulnerabilities.
2. Send an email to [your-email@example.com] with the subject line: `[SECURITY] WebGuard Vulnerability Report`.
3. Include the following information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment:** Within 48 hours of receiving the report.
- **Assessment:** Within 1 week of acknowledgment.
- **Fix & Disclosure:** Patches will be released as soon as possible after validation.

### Scope

This security policy applies to:
- The WebGuard scanner engine and its modules
- The FastAPI backend API
- The React frontend dashboard
- Docker configurations and deployment scripts

### Out of Scope

- Vulnerabilities in third-party dependencies (please report these to the respective maintainers)
- Social engineering attacks
- Issues in the demo/landing page that do not affect the core scanner

## AI Explain (BYOK) Data Handling

The optional "Explain with AI" feature lets a user paste their own API key for a third-party AI
provider (Google, Groq, OpenRouter, OpenAI or Anthropic). That key is:
- Stored **only in the user's own browser** (`localStorage`), never in WebGuard's database.
- Sent to WebGuard's backend **once per explain request**, forwarded straight to the chosen
  provider, and never logged or persisted server-side.
- Used only to summarise findings a scan **already produced** — this feature never sends new
  requests to the scanned target.

## Disclaimer

WebGuard is designed as a **security assessment and audit tool** for authorized testing only. Users are responsible for ensuring they have proper authorization before scanning any target. The maintainers are not responsible for any misuse of this tool.
