# Run TeamFlow locally

Use two PowerShell terminals. These commands use SQLite and a single-process in-memory channel layer, so PostgreSQL and Redis are not required for local development.

## Backend

```powershell
cd C:\Users\lycon\OneDrive\Documents\CoreWebpplication
$env:DEBUG = "True"
$env:USE_POSTGRESQL = "False"
$env:DB_NAME = "db.sqlite3"
$env:USE_IN_MEMORY_CHANNEL_LAYER = "True"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\daphne.exe -b 127.0.0.1 -p 8000 teamtaskmanager.asgi:application
```

On a fresh checkout, install Python dependencies first:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Frontend

```powershell
cd C:\Users\lycon\OneDrive\Documents\CoreWebpplication
npm.cmd ci
npm.cmd run dev -- --port 5173 --strictPort
```

Visit http://localhost:5173. Use `npm.cmd` to avoid PowerShell execution-policy restrictions on `npm.ps1`. Sign up, create a workspace, then create a project. Workspace administrators can generate an invitation link from **Workspace & invitations**, share it themselves, and revoke pending invitations. No email is sent by this flow. A recipient signs in with the invited email and accepts the link. Existing members can then be added to individual projects.

`FRONTEND_URL` must match the frontend's address for invitation links. The local default is `http://localhost:5173`. In-memory Channels is for a single development process only; use Redis for multiple workers and production.

## Existing data and migration

Apply migrations before starting the updated application. The new tenant columns are nullable solely to preserve legacy data without guessing business ownership. Projects and conversations with no tenant are hidden from customer APIs. Nothing is automatically deleted or assigned to a customer.

Create the intended workspace and establish its memberships, then explicitly map the reviewed record IDs. The command rejects mismatched tenants and records whose owners, participants or assignees lack active membership. It does not grant membership.

```powershell
.\.venv\Scripts\python.exe manage.py map_workspace_records --tenant 1 --projects 2 3 --conversations 4
.\.venv\Scripts\python.exe manage.py map_workspace_records --tenant 1 --projects 2 3 --conversations 4 --apply
```

The first command validates without writing. Replace all IDs with the reviewed real IDs. Project-linked conversations must be explicitly included or mapped later. Back up the database and rehearse the mapping on a staging copy before upgrading an existing installation. Keep unmapped records quarantined until ownership is established.

## API contract and access

- `GET/POST /api/workspaces/`: list memberships / create workspace.
- `GET /api/workspaces/members/`: active workspace members.
- `GET/POST /api/workspaces/invitations/`: list pending invitations / generate an email-bound link (admin only).
- `DELETE /api/workspaces/invitations/<id>/`: revoke a pending invitation (admin only).
- `POST /api/workspaces/invitations/accept/`: consume an unexpired token for the authenticated email.
- Send `X-Workspace-ID` for workspace-bound APIs. A single active membership can be inferred; multiple memberships require explicit selection. The frontend adds this header.
- Global `User.role` no longer grants project or chat access. Workspace administrators have `workspace.manage`; project managers can be given `projects.manage` and must also belong to the project. Project responses expose `can_manage` for UI controls.
- Project and chat sockets validate access when connecting and before transmitting events. Suspended membership, suspended tenants, inactive users and inconsistent membership roles fail closed.
- Task and chat attachments use authenticated `/api/files/tasks/<id>/` and `/api/files/messages/<id>/` endpoints. API payloads return paths relative to the API base. The frontend downloads chat attachments with its authenticated client. Never expose the media directory through a public production web-server alias or public object-storage bucket.
- Email changes through profile PATCH are disabled until a verified email-change flow exists.

## Verification and remaining work

Validation completed: all 70 backend tests passed, the frontend production build passed, ASGI imported successfully, and the migration drift check reported no changes. A focused onboarding regression also passed after checking long workspace names against the database slug limit. The frontend build still reports a large bundle warning.

Backend regression coverage includes workspace selection, global-admin isolation, support access, invitation expiry/replay/revocation, cross-workspace task/chat relationships, protected attachments, legacy mapping and actual WebSocket connections/revocation. Tests use SQLite; PostgreSQL concurrency and a complete browser journey still need validation.

This is the workspace foundation stage, not a completed paid SaaS launch. Outstanding work includes verified email and password recovery, member removal and role administration UI, billing-provider integration and server-side entitlements, durable jobs, finance permission enforcement, truthful financial reporting, production configuration, dependency upgrades, backups and monitoring. `SaaSPlan` and `TenantSubscription` models already exist in `erp_operations`; they need a working billing lifecycle rather than duplicate models.

The frontend dependency installation reported 5 advisories (2 moderate, 3 high); investigate and remediate before public deployment. The existing Django 5.0 requirement also needs an upgrade to a supported release. A passing build is not a dependency security clearance.
