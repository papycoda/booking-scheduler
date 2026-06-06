# Security Review: booking-scheduler

## Scope

- Scan mode: Codex Security repository-wide review of `C:\Users\Administrator\Documents\Yemi's Projects\booking-scheduler` at commit `ee305cf`.
- In scope: FastAPI backend, Next.js frontend, Docker/config files, migrations, tests, and dependency metadata.
- Scan artifacts: `tmp/codex-security-scans/booking-scheduler/ee305cf_20260605T000000Z`.
- Validation: static source-to-sink tracing, existing targeted tests, `npm audit`, and `git check-ignore`.
- Limitations: the installed Codex Security plugin cache did not include the referenced repository-wide helper docs, report validator, or HTML renderer. `pip-audit` was not installed, so Python dependency advisory coverage is not complete.

### Scan Summary

| Field | Value |
| --- | --- |
| Reportable findings | 7 |
| Severity mix | 2 high, 3 medium, 2 low |
| Confidence mix | 4 high, 3 medium |
| Coverage | Auth, tenant isolation, public booking, demo payments, Paystack webhooks, payouts, uploads, frontend redirects/token storage, config, npm dependencies |
| Tests run | `pytest backend/tests/test_webhooks.py backend/tests/test_tenants_router.py -q` -> 24 passed |

## Threat Model

See `artifacts/01_context/threat_model.md`. Key invariants: tenant owners must only access their own tenant data; public booking users must not confirm payments or alter bookings without the correct token; demo mode must not bypass payment collection for ordinary clients; Paystack webhooks must be signed and amount/reference checked; payout and provider secrets must not leak.

## Findings

| # | Severity | Confidence | Finding |
| --- | --- | --- | --- |
| 1 | high | high | [Unauthenticated demo payment completion bypasses payment collection](#1-unauthenticated-demo-payment-completion-bypasses-payment-collection) |
| 2 | high | high | [Installed Next.js version has high-severity advisories](#2-installed-nextjs-version-has-high-severity-advisories) |
| 3 | medium | medium | [Tokenless booking status endpoint leaks payment references](#3-tokenless-booking-status-endpoint-leaks-payment-references) |
| 4 | medium | medium | [SVG uploads can be served back as active API-origin content](#4-svg-uploads-can-be-served-back-as-active-api-origin-content) |
| 5 | medium | medium | [Tenant staff role can reach payout mutation routes](#5-tenant-staff-role-can-reach-payout-mutation-routes) |
| 6 | low | high | [Login accepts an attacker-controlled post-auth redirect](#6-login-accepts-an-attacker-controlled-post-auth-redirect) |
| 7 | low | high | [Local secret files are not ignored by git](#7-local-secret-files-are-not-ignored-by-git) |

### Confidence Scale

| Label | Meaning |
| --- | --- |
| high | Direct source, command, or test evidence supports the finding with no material unresolved blocker. |
| medium | Source evidence supports the issue, but runtime behavior, deployment configuration, or role provisioning affects exploitability. |
| low | Weak or incomplete evidence; used only for follow-up candidates. |

### [1] Unauthenticated demo payment completion bypasses payment collection

| Field | Value |
| --- | --- |
| Severity | high |
| Confidence | high |
| Confidence rationale | Direct route tracing shows the endpoint checks only `DEMO_MODE` and mutates payment state by public reference. |
| Category | Missing authentication / payment bypass |
| CWE | CWE-306, CWE-639 |
| Affected lines | `backend/app/routers/webhooks.py:23-68`, `backend/app/services/payment_provider.py:33-38,83-91`, `backend/app/services/booking_service.py:103,152-155` |

#### Summary
`POST /api/v1/webhooks/demo/complete-payment` accepts only a `reference` and checks `settings.demo_mode`. It then finds the payment by reference, sets `payment.status = "success"`, queues payout review, sets `booking.status = "confirmed"`, commits, and sends confirmation. The intended demo control in `initialize_checkout_payment()` only decides whether to issue a demo URL for `DEMO_ADMIN_EMAILS`; the completion endpoint does not re-check that control.

#### Validation
Static trace confirms the path. Existing webhook tests validate the signed Paystack path, but there is no corresponding auth test for demo completion. `DEMO_MODE` defaults false and docs warn against production use, which limits exposure but does not fix shared staging or misconfiguration risk.

#### Dataflow
Public booking response returns `reference` -> unauthenticated caller posts reference to demo completion -> route loads `Payment` by `paystack_reference` -> route sets payment success and booking confirmed.

#### Reachability
Any public booking user can receive a payment reference. If `DEMO_MODE=true` is enabled on a reachable environment, that user can confirm without Paystack.

#### Severity
High because the path directly bypasses payment collection and booking confirmation. Severity would drop if demo endpoints were unreachable outside a private local network.

#### Remediation
Require a signed one-time demo completion token tied to the reference and client email, or require authenticated admin access and validate the booking email against `DEMO_ADMIN_EMAILS`. Add a negative test for non-admin demo completion.

### [2] Installed Next.js version has high-severity advisories

| Field | Value |
| --- | --- |
| Severity | high |
| Confidence | high |
| Confidence rationale | `npm audit --omit=dev --audit-level=high` reported high-severity advisories for the installed `next` range. |
| Category | Vulnerable dependency |
| CWE | none |
| Affected lines | `frontend/package.json:13`, `frontend/package-lock.json` |

#### Summary
`npm audit` reports `next` in a vulnerable range with high-severity advisories including DoS, cache poisoning, request smuggling, SSRF, and XSS classes. The suggested automatic fix is a breaking upgrade to `next@16.2.7`.

#### Validation
The audit command returned a high-severity finding for `next` and a moderate `postcss` issue under Next's dependency tree.

#### Dataflow
Remote browser/request traffic -> Next.js runtime -> advisory-specific affected server/app-router/image/middleware behavior.

#### Reachability
This matters when the frontend is self-hosted with affected features/configuration. Individual advisory exploitability was not reproduced in this scan.

#### Severity
High because the package advisory source marks the installed range high severity. Severity can be lowered per advisory if the affected feature is disabled or unreachable.

#### Remediation
Plan and test an upgrade to a patched Next.js release. Review the listed GHSAs against actual deployment features before deciding whether an interim mitigation is acceptable.

### [3] Tokenless booking status endpoint leaks payment references

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | medium |
| Confidence rationale | Static route evidence is direct, but exploitation requires knowing or leaking a booking UUID. |
| Category | IDOR / information disclosure |
| CWE | CWE-639 |
| Affected lines | `backend/app/routers/public.py:160-193`, `backend/app/schemas/booking.py:37-49` |

#### Summary
`GET /api/v1/book/{slug}/bookings/{booking_id}/status` accepts an optional `token`. It returns booking status, payment status, payment reference, start/end time, service, staff, deposit, and pricing fields without requiring the token; only `manage_url` is token-gated.

#### Validation
Static trace confirms the optional token and returned fields. Manage/cancel/reschedule endpoints require token, so this is disclosure rather than mutation.

#### Dataflow
Attacker supplies public tenant slug and booking UUID -> route loads booking by tenant/id -> response includes `payment.paystack_reference` and appointment metadata.

#### Reachability
An attacker needs a booking UUID from logs, URLs, browser history, screenshots, email leakage, or another disclosure. UUID guessing alone is unlikely.

#### Severity
Medium because this exposes payment/appointment metadata and helps chain with demo completion when demo mode is enabled.

#### Remediation
Require the manage token for all booking-specific status fields, or return only a minimal anonymous status that excludes reference, staff, service, time, and pricing.

### [4] SVG uploads can be served back as active API-origin content

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | medium |
| Confidence rationale | Source evidence shows type trust and serving behavior; browser script execution was not dynamically reproduced. |
| Category | Dangerous file upload / stored active content |
| CWE | CWE-434, CWE-79 |
| Affected lines | `backend/app/routers/public.py:145-151,263-265`, `backend/app/services/inspo_service.py:20-21,43`, `frontend/app/dashboard/page.tsx:247-250` |

#### Summary
Public booking uploads accept any client-declared `image/*` type, store the supplied content type, and serve the bytes back with that media type. Dashboard links open uploaded assets in a new tab. `image/svg+xml` can contain active content in top-level browser contexts.

#### Validation
Static trace confirms content type trust and serving. Counterevidence: UUID filenames, size limits, DB storage, and normal `<img>` rendering reduce impact, but top-level open remains plausible.

#### Dataflow
Multipart upload -> `file.content_type` starts with `image/` -> content and media type stored -> `/book/{slug}/inspo/{stored_filename}` returns bytes with attacker content type -> dashboard link opens asset.

#### Reachability
Any public booking client can upload inspiration images for a tenant. Tenant dashboard users can view/open them.

#### Severity
Medium because this can become stored active content or phishing on the API origin, though exploit impact depends on browser handling and cookie/header exposure.

#### Remediation
Allowlist safe raster types such as JPEG, PNG, and WebP; verify magic bytes; reject SVG; serve with `X-Content-Type-Options: nosniff`; optionally use attachment disposition or a separate asset domain.

### [5] Tenant staff role can reach payout mutation routes

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | medium |
| Confidence rationale | Role and route evidence is direct, but no current route creates `tenant_staff`, so reachability depends on provisioning/imports. |
| Category | Missing authorization |
| CWE | CWE-862 |
| Affected lines | `backend/app/models/user.py:15,24`, `backend/app/dependencies.py:17-62`, `backend/app/routers/bookings.py:187-192,244-262,272-290` |

#### Summary
The user model supports `tenant_staff`, JWTs include roles, but payout mutation endpoints depend only on `get_current_user`, which authenticates user and tenant but not role. If tenant staff accounts exist, they can initiate, approve, or retry payout workflows within the tenant.

#### Validation
Static trace confirms no role guard. Counterevidence: registration creates only tenant owners, and no self-service staff-user creation route was found.

#### Dataflow
Tenant-staff bearer token -> `get_current_user` returns active user -> payout route uses `current_user.tenant_id` -> calls payout mutation service.

#### Reachability
Reachable in deployments with seeded, imported, or future tenant staff user accounts.

#### Severity
Medium due to cash-movement integrity within a tenant; lower if staff accounts are impossible in production.

#### Remediation
Add `require_tenant_owner` or role-scoped dependencies for payout, tenant settings, service/staff management, and other owner-only mutations. Add negative tests for `tenant_staff`.

### [6] Login accepts an attacker-controlled post-auth redirect

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Direct client source-to-sink trace from `next` query to `window.location.href`. |
| Category | Open redirect |
| CWE | CWE-601 |
| Affected lines | `frontend/app/(auth)/login/page.tsx:26-28`, `frontend/middleware.ts:10-13` |

#### Summary
After successful login, the page reads `next` from `window.location.search` and assigns it to `window.location.href` without checking that it is a same-origin path. Middleware-generated values are path-only, but direct attacker URLs can supply absolute URLs.

#### Validation
Static trace is sufficient. The token is stored before redirect, but the external site cannot directly read same-origin localStorage.

#### Dataflow
`/login?next=https://evil.example` -> successful login -> `storeAccessToken()` -> `window.location.href = next`.

#### Reachability
Any unauthenticated user can be sent a crafted login link.

#### Severity
Low because the main impact is phishing/session confusion, not direct token exfiltration.

#### Remediation
Allow only relative paths that start with `/` and reject `//`, absolute URLs, backslashes, and control characters. Default to `/dashboard` on invalid input.

### [7] Local secret files are not ignored by git

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | `git check-ignore` showed `backend/.env` is not ignored while it exists untracked. |
| Category | Secret exposure risk |
| CWE | CWE-200 |
| Affected lines | `.gitignore:1-14`, `backend/app/config.py:8-20,30` |

#### Summary
The app loads secrets from `backend/.env` and `.env`, but `.gitignore` does not ignore those paths. `backend/.env` is currently untracked and not ignored.

#### Validation
`git check-ignore -v backend\.env .env` returned no ignore match; `git ls-files backend\.env .env backend\.env.example` showed only `backend/.env.example` tracked.

#### Dataflow
Developer creates local secret file -> git status shows it as untracked -> accidental add/commit can expose secrets.

#### Reachability
Developer workflow risk, not a runtime attacker path.

#### Severity
Low, but fixing is urgent hygiene because the file can contain Paystack, JWT, database, Redis, Resend, and WhatsApp secrets.

#### Remediation
Add `.env`, `.env.*`, `backend/.env`, and `backend/.env.*` to `.gitignore`, while explicitly allowing `.env.example` files if needed.

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Auth/JWT | Token validation and tenant context | No issue found | JWT type, active user, and token tenant vs user tenant are checked. |
| Tenant routes | Tenant scoping and payout account responses | Rejected | Account masking is implemented via serializers and covered by tests. |
| Paystack webhook | Signature/payment verification | No issue found | HMAC, amount, currency, reference, and expired-state checks are present. |
| Payout retries | Retry/review state machine | No issue found | Existing tests cover retry limits; `needs_review` tenant approval is blocked. |
| Public manage/cancel/reschedule | Manage token authorization | No issue found | Mutating operations require HMAC manage tokens. |
| Frontend XSS sinks | Dangerous HTML/eval/postMessage | No issue found | No `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, or `postMessage` found in reviewed frontend. |
| Access token storage | Browser-readable bearer token | Needs follow-up | Token is in localStorage, but no XSS sink was found in this scan. Consider moving to memory/BFF session cookies. |
| Python dependencies | Advisory scan | Needs follow-up | `pip-audit` was unavailable. |

## Open Questions And Follow Up

- Confirm whether production or shared staging can ever set `DEMO_MODE=true`; if yes, fix CS-BS-001 before wider demos.
- Confirm whether tenant staff users are seeded, imported, or planned; if yes, add role guards before exposing staff accounts.
- Map the Next.js GHSAs from `npm audit` against deployed features and upgrade path.

## Artifact Paths

- Markdown report: `tmp/codex-security-scans/booking-scheduler/ee305cf_20260605T000000Z/report.md`
- HTML report: `tmp/codex-security-scans/booking-scheduler/ee305cf_20260605T000000Z/report.html`
- Threat model: `tmp/codex-security-scans/booking-scheduler/ee305cf_20260605T000000Z/artifacts/01_context/threat_model.md`
- Coverage ledger: `tmp/codex-security-scans/booking-scheduler/ee305cf_20260605T000000Z/artifacts/03_coverage/repository_coverage_ledger.md`
