# Workspace tools implementation

Implemented on October 12, 2026. The seven screenshot ideas now have database-backed APIs and React screens under **Workspace tools**. They are initial working versions, not complete standalone competitors to specialist products.

## Available tools

| Tool | Working behavior |
| --- | --- |
| Website monitoring | Create/edit/delete monitors, intervals from 5 minutes to 24 hours, queue a manual check, retain check history, calculate 30-day sample uptime and average latency, and send downtime/recovery alerts. A worker must be running. Checks pin a public IP, verify HTTPS certificates and do not follow redirects into other services. |
| Public link pages | Create a unique public address, edit title/bio/theme, add/reorder links, publish/unpublish and view `/p/<slug>`. Only the published profile is public. |
| Habits and goals | Private habits, timezone-specific daily logs, a 30-day calendar, completion toggles, streaks and CSV export. Logging the same day twice updates one record. |
| Feedback widgets | Register website origins, generate an embed snippet, receive feedback, mark read/archive and convert feedback into a project task once. Public submissions have rate and size limits. Registered origins are an abuse boundary, not proof that a submitter is trusted. |
| Client CRM | Create/edit contacts, lead/active/completed/archived stages, notes, search, project linking through the API, conversion into a linked project and CSV export. |
| Flashcards | Private/workspace-shared decks, question/answer cards, reveal-and-rate study sessions, per-user due dates and retry-safe review history. Uses a simple deterministic scheduler, not a claimed SM-2 implementation. |
| Forms and surveys | Field editor with drag and keyboard-button reordering, text/email/choice/dropdown fields, public `/f/<id>` pages, server-side validation, versioned schema snapshots, response review and CSV export. |

Additional adjacent modules are available: a text knowledge base with hierarchy and revision history, client file approvals with private downloads and version-specific sign-off, and personal task time logs. The knowledge base currently uses plain text; it does not include a rich-text editor or document import.

## Foundation changes

- Django upgraded to 5.2.18; the tested backend dependency versions are recorded in `requirements.lock.txt`.
- Password-reset and email-verification APIs and screens; expiring verification/reset links; refresh rotation, blacklisting and password-change revocation checks.
- Gmail-compatible SMTP settings and a persistent job queue with leases, bounded retries and failure records. Assignment notifications and invitations now enqueue jobs; task due reminders can still be run through the existing scheduled management command.
- Account-level notification preferences; approval email preferences apply to review requests.
- Workspace role creation, role assignment, suspension/restoration and protection against removing the last administrator.
- Finance viewing/managing permissions, explicit company selection, company/currency-specific reports and paginated lists.
- A company setup flow creates a starter chart and current-year monthly periods. Draft invoice/bill lines are rounded to company currency; posting creates balanced journals; payments can partially settle documents; repeated payment references do not create duplicate receipts. Statement export is CSV.
- Journal tenant/company/period/date/account checks and a savepoint around source-journal creation retries.
- The cash chart uses posted cash-account entries. Removed fixed fiscal dates and unverified health claims.
- Audit events for tools, invitations, roles, finance and billing. Audit queryset mutation is blocked through the Django manager; this is application enforcement, not database-superuser-proof immutability.
- Separate task completion timestamps and project-name uniqueness scoped to workspace/owner. Existing completed tasks retain unknown completion dates rather than inventing history.
- Lazy-loaded routes remove the frontend's oversized initial bundle warning; modal focus trapping and restoration.
- Docker service paths and addresses corrected, PostgreSQL image updated, Daphne serving, a separate worker, readiness endpoint, backup and job-pruning commands, and CI definitions for frontend/SQLite/PostgreSQL checks.

## Local startup

Use the existing local database configuration in `WORKSPACE_SETUP.md`. This task backed up and migrated `C:\Users\lycon\AppData\Local\TeamFlow\db.sqlite3`; the pre-upgrade SQLite backup is in the ignored `.cache/database-backups` directory. Keep backups private and copy them to your normal secure backup destination.

Install dependencies on another machine using:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c requirements.lock.txt
```

Run the backend and frontend as described in `WORKSPACE_SETUP.md`. Restart any backend process started before these changes. In a third terminal, using the same database/environment as the backend:

```powershell
.\.venv\Scripts\python.exe manage.py run_worker
```

For a bounded worker run:

```powershell
.\.venv\Scripts\python.exe manage.py run_worker --once
```

The worker schedules website checks and handles queued email and payment jobs. The existing `send_due_reminders` command now queues reminders durably; schedule that command and run the worker for delivery. Delivery is at least once: a crash after an external service accepts a request can cause a repeated delivery. Never run a monitor worker against an old schema. Failed jobs retain an error for operator review.

## Gmail setup

In your private, ignored `.env`, set:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=your-google-app-password
DEFAULT_FROM_EMAIL=TeamFlow <your-address@gmail.com>
FRONTEND_URL=http://localhost:5173
```

Replace the sample address with your address. Use a Google app password where your account supports it; do not use or commit your regular Gmail password. Without SMTP configuration, queued emails print to the worker console. Account verification is required for invitation acceptance by default when `DEBUG=False`; local development can explicitly opt out. See [Google SMTP settings](https://support.google.com/mail/answer/7104828) and [app passwords](https://support.google.com/mail/answer/185833).

## Paynow, EcoCash and cards

The billing screen supports Paynow hosted checkout and an EcoCash phone-confirmation flow. Configure:

```dotenv
PAYNOW_INTEGRATION_ID=your-integration-id
PAYNOW_INTEGRATION_KEY=your-integration-key
PAYNOW_RESULT_URL=https://your-api-host/api/tools/billing/paynow/result/
FRONTEND_URL=https://your-app-host
```

Do not use these placeholder values in a real deployment. Enable the desired payment methods in your Paynow integration and complete merchant test-mode verification. Card details are entered on Paynow, never stored in TeamFlow. The callback URL must be publicly reachable over HTTPS.

Configure actual offered prices explicitly; this implementation does not invent your business's paid prices:

```powershell
.\.venv\Scripts\python.exe manage.py configure_plan --name Business --price <your-USD-price>
```

An optional `--limits` file can override module/seat/AI limit values. The free plan is available automatically with conservative tool record limits. The current checkout currency is USD. Each customer-confirmed payment buys 30 days; recurring automatic debits, tokenized cards and proration are not enabled. Changing to a different paid plan starts a fresh paid period at the full stated price. Switching to free at period end preserves the already-paid period.

Signed callback messages enqueue an authoritative status check; only a signed, matching amount/reference from Paynow activates access. Successful Paid/Awaiting Delivery/Delivered statuses are recognized. Replayed callbacks/payments do not extend access twice. Refunds/disputes suspend the currently affected subscription. An uncertain initiation is not blindly retried, particularly for mobile payments; use the stored reference to reconcile it with Paynow before paying again. See [Paynow initiation](https://developers.paynow.co.zw/docs/paynow/initiate_transaction/), [status updates](https://developers.paynow.co.zw/docs/paynow/status_update/) and [express checkout](https://developers.paynow.co.zw/docs/paynow/express_checkout_transactions/).

Record limits are enforced on tool creation and subscription state on tool writes. Seat limits apply when accepting invitations or restoring suspended members. Storage limits apply to task/chat/approval uploads and count currently referenced files and retained approval versions; unreferenced files still need a retention/cleanup policy and infrastructure disk monitoring. AI attempts are metered per workspace per UTC calendar month, including failed provider attempts. Tool read/export/delete access remains available for inactive subscriptions. Existing collaboration text writes are not fully gated by paid entitlements.

An administrator can start one trial from the free plan for an offered paid plan. Trial duration defaults to 14 days and is configurable through `TRIAL_DAYS` (1–90). Expired trials deny tool writes until the administrator pays or returns to free; a used trial cannot be restarted by switching plans.

## Deployment and operations

The development Compose file runs the API/database/Redis/worker. Run migrations before starting application traffic. Do not point PostgreSQL 17 at a PostgreSQL 13 data directory: use a tested dump/restore or supported database upgrade procedure.

`deploy/Dockerfile.frontend` and `deploy/nginx.conf` provide a static frontend/reverse-proxy starting point. They are not a deployed HTTPS service; configure actual domains, TLS, secure proxy handling and static admin files for your hosting environment. Never serve `/media/` publicly. Only trust a forwarded HTTPS header from an ingress you control. Health readiness currently checks the database; monitor the worker, Redis, email failures and backup freshness separately.

```powershell
.\.venv\Scripts\python.exe manage.py backup_database --output .cache/database-backups
.\.venv\Scripts\python.exe manage.py prune_jobs
```

Schedule backups and retention jobs using your deployment scheduler. A SQLite backup is integrity-checked. PostgreSQL backup requires `pg_dump`/`pg_restore`; its archive is checked for readability. Rehearse a restore in an isolated environment before relying on a recovery target. Financial reversal, multi-currency invoice posting, bank imports and period administration are not included in this initial workflow.

## Verification and remaining scope

The final full suite passed 107 tests, including workspace boundaries, private habits, form version history, feedback origins/conversion, card scheduling, monitor internal-address rejection, job retry/lease recovery, finance permissions/payment flows, account recovery, Paynow signatures/replay/amount checks, trial expiry, seat/storage/AI limits, role changes, audit protections, retained approval history and socket/password revocation. Queued private alerts are suppressed after membership revocation. The frontend production build passed without the previous large-bundle warning, and migration drift checks passed.

Browser checks used an isolated database and verified sign-in, the tools overview, saving a CRM contact, finance company setup and saving a draft invoice. The preview at `http://localhost:5181` connects to its isolated API on port 8001; it does not display the normal AppData database. The main local database was backed up and migrated separately. Restart your normal backend to use the new code with your existing records.

Docker Desktop was not running during local validation. PostgreSQL integration jobs are defined in CI but have not been run here. Paynow and Gmail were tested through local configuration paths and mocked payment/email tests, not with live merchant credentials or a real outgoing email.

The broader article also proposes separate products (social publishing, courses, newsletters, ticketing, visual automation, POS, e-commerce, whiteboards, predictive finance, referral programs, video capture, an Open Graph API, browser extensions and resume tailoring). Those remain in the expansion backlog; they are not disguised as working features in this release. Advanced Gantt/dependency scheduling and an AI helpdesk also remain future scope. The working screenshot tools and adjacent modules above are the concrete implementation delivered here.
# Local ML and preview walkthrough

Taylee now defaults to local ML task planning and experimental deadline-risk analysis. The preview workspace has an extensive offline seed with real application relationships and synthetic values. See [DEMO_WORKFLOW.md](DEMO_WORKFLOW.md) for the walkthrough, model limitations and repeatable seed instructions.
