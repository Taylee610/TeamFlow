# Run TeamFlow locally

Use two PowerShell terminals. These commands use SQLite and a single-process in-memory channel layer, so PostgreSQL and Redis are not required for local development.

The added tools also require a third terminal running `python manage.py run_worker` with the same database/environment. See [implemented tools and Paynow/Gmail setup](IMPLEMENTED_TOOLS.md). Restart the backend after upgrading dependencies and applying the latest migrations.

## Backend

```powershell
cd C:\Users\lycon\OneDrive\Documents\CoreWebpplication
$env:DEBUG = "True"
$env:USE_POSTGRESQL = "False"
$teamflowData = Join-Path $env:LOCALAPPDATA "TeamFlow"
New-Item -ItemType Directory -Force -Path $teamflowData | Out-Null
$env:DB_NAME = Join-Path $teamflowData "db.sqlite3"
$env:USE_IN_MEMORY_CHANNEL_LAYER = "True"
.\.venv\Scripts\python.exe manage.py migrate
if ($LASTEXITCODE -eq 0) {
    .\.venv\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 teamtaskmanager.asgi:application
}
```

On a fresh checkout, install Python dependencies first:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The AppData path avoids the database-write failure observed in the Documents project folder. Launching Daphne through Python avoids the Windows executable-launch denial observed for `daphne.exe`. This database starts empty; there are no default accounts. To create a Django administration account, run ` .\.venv\Scripts\python.exe manage.py createsuperuser` in another terminal with the same `DEBUG`, `USE_POSTGRESQL` and `DB_NAME` environment values. Choose your email and password interactively, then visit http://127.0.0.1:8000/admin/. Workspace administration is separate: sign in to the frontend and create a workspace.

## Frontend

```powershell
cd C:\Users\lycon\OneDrive\Documents\CoreWebpplication
npm.cmd ci
npm.cmd run dev -- --port 5173 --strictPort
```

Visit http://localhost:5173. Use `npm.cmd` to avoid PowerShell execution-policy restrictions on `npm.ps1`. Sign up, create a workspace, then create a project. Workspace administrators can generate an invitation link from **Workspace & invitations**, share it themselves, and revoke pending invitations. Invitations and verification emails are queued for delivery by the worker; configure Gmail SMTP to send them, or inspect the worker console in development. A recipient signs in with the invited email and accepts the link. Production invitation acceptance requires verified email by default. Existing members can then be added to individual projects.

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

The newer implementation adds account recovery and verification, role administration, durable jobs, finance permissions and posting/payment workflows, Paynow billing and trial/usage controls, backup tooling and website monitoring. See [implementation status](IMPLEMENTED_TOOLS.md) for verification and limits. Live Paynow/Gmail setup, hosting/TLS, tested PostgreSQL concurrency and restore rehearsals, broader ERP workflows and the separate advanced product ideas remain outstanding.

The earlier frontend dependency installation reported 5 advisories (2 moderate, 3 high); investigate and remediate before public deployment. Django is now pinned to 5.2.18. A passing build is not a dependency security clearance.
