# TeamFlow: business SaaS readiness and implementation roadmap

## Assessment

Implementation update (October 12, 2026): the seven screenshot tools now have working API/UI flows, alongside knowledge pages, client file approvals, time logs, account recovery, role administration, finance posting/payment flows and Paynow billing integration. See [implemented features, setup and remaining scope](IMPLEMENTED_TOOLS.md). Older assessment rows below are historical; they should not be treated as a claim that recently implemented features are absent.

Update: the first workspace implementation now adds explicit tenant selection, workspace creation/invitation UI and APIs, scoped project/chat access, protected attachment downloads and realtime authorization. See [Workspace setup and remaining work](WORKSPACE_SETUP.md). The gap table below records the initial review; these changes address part of P0 and onboarding, not the entire launch roadmap. Existing `SaaSPlan` and `TenantSubscription` models in `erp_operations` are a billing foundation; the missing piece is the operational subscription/payment/entitlement lifecycle.

This repository is a collaboration application with an early ERP foundation. It is not yet ready to host unrelated paying businesses safely. This assessment is based on repository inspection, not a production penetration test or an accounting certification.

The useful foundation includes React navigation and workspaces, Django authentication, project/task CRUD, boards, chat, notifications, AI assistance, and ERP models for tenants, companies, roles, accounting and operations. Accounting services already check balanced journals and closed periods, and there are backend tests. Preserve these investments.

The recommended initial product hypothesis is a project delivery workspace for small service businesses: create a workspace, invite a team, deliver client work, and track its progress. Validate this with prospective customers before expanding into a full ERP. Finance can follow as a focused invoicing workflow; a complete accounting platform is a much larger product commitment.

## Priority gaps and concrete completion criteria

| Priority | Evidence and business impact | How to close it | Completion criterion |
| --- | --- | --- | --- |
| P0 | `projects/models.py` has no tenant reference; global `User.role` grants administrators access across projects in `projects/api_views.py`. ERP tenancy does not protect collaboration. | Reuse `Tenant` and `Membership` as the organization boundary. Add tenant ownership to projects and conversations; resolve roles per membership. Keep platform administration separate. Scope API, sockets, AI context, exports and attachments consistently. | Two companies can use every feature without reading, writing, linking to or subscribing to each other's records, including when one user is an admin. |
| P0 | Support conversation permissions and WebSocket access explicitly allow any authenticated user (`chat/permissions.py`, `chat/consumers.py`). | Limit access to participants and explicitly authorized support staff; scope support queues and check membership revocation for live connections. Review REST querysets together with object permissions. | An unrelated logged-in customer cannot list, retrieve, send to or subscribe to another customer's support conversation. |
| P0 | `accounting/api_views.py` selects the first active membership, does not filter inactive tenants and does not apply the permission codes modeled in ERP roles. | Require explicit tenant context for multi-membership users, validate active tenant/membership and role ownership, and enforce a permission per operation. | Tenant switching is deterministic; suspended tenants and unauthorized finance viewers receive denial. |
| P0 | `teamtaskmanager/settings.py` defaults to debug and a development secret; hosts are empty and Redis is loopback. Compose uses `runserver`, mounts `/code` while Docker works in `/app`, and does not override DB hostname. | Separate development and production configuration; fail startup on missing production secrets; configure hosts, TLS, secure cookies, origins, service URLs, ASGI serving and protected media. Align Compose paths and add readiness probes. | A clean staging deployment serves HTTP and sockets with debug off and passes deployment checks plus a restore drill. |
| P0 | `requirements.txt` pins Django 5.0 and leaves several dependencies unpinned. | Upgrade to a supported Django release through compatibility tests; lock backend dependencies and automate vulnerability review. | Reproducible builds on the chosen Python version with supported dependencies and reviewed findings. |
| P1 | Signup creates only a user; there is no complete organization setup, invitation acceptance, email verification or password recovery API in `accounts/api_urls.py`. | Build signup -> verified email -> workspace -> invite -> first project. Add expiring invitations, reset flows, login abuse protection and session revocation. | A new business can onboard and recover access without an administrator or seed command. |
| P1 | No SaaS subscription lifecycle or entitlement service was found. ERP invoices are customer business records, not SaaS billing. | Add plans, subscriptions, trials, seat/storage/AI limits and server-side entitlements. Integrate a payment provider appropriate to the seller's country and customer currencies after confirming requirements. Verify webhook signatures and deduplicate events. | Trial, upgrade, failed payment, cancellation and repeated/out-of-order webhook scenarios produce correct access and charges. |
| P1 | ERP APIs inspected are read-only. `src/pages/ERP.jsx` hardcodes cash-flow bars, a fiscal month and healthy control claims. | Remove or explicitly label demonstrations; calculate reports from real records. Deliver one workflow end-to-end: draft invoice -> approval/posting -> payment allocation -> statement/export. | Every visible metric traces to source records; customers can complete the advertised workflow without database edits. |
| P1 | Accounting totals aggregate across a tenant while UI defaults to USD. `accounting/services.py` needs deeper review of period/company/tenant consistency and concurrent posting. | Scope reports by company and currency, validate related records and posting dates, handle reversals and partial settlement, and test financial concurrency on PostgreSQL. Review the IntegrityError retry inside the atomic source-journal function using a nested savepoint. | Reports never mix currencies silently; invalid periods and cross-company records cannot post; concurrent retries create one source journal. |
| P1 | `AuditLog` exists but instance save/delete overrides do not protect against queryset updates/deletes. Notification delivery uses daemon threads. | Record sensitive changes transactionally, strengthen append-only audit enforcement, and use a durable worker/outbox with retry and idempotency. | Role changes and finance mutations have attributable audit events; worker restarts do not lose committed notifications. |
| P1 | Production monitoring, backup/restore automation and CI were not established by this review. | Add CI for backend tests, frontend build and migration drift; PostgreSQL integration tests; error tracking, structured logs, uptime checks, database backups and a tested recovery runbook. | Failed checks block releases; an operator can detect a failure and restore an isolated staging copy from backup. |
| P2 | Customer administration, portable exports, retention controls, usage analytics and support operations need product definition. | Add workspace settings, billing ownership, member offboarding, export/deletion workflows and support processes. Define activation and retention metrics. | Customers can administer and leave the service; operators can measure adoption and resolve incidents. |

Django 5.0's extended support ended April 2, 2025. Verify the latest supported patch when implementing the upgrade: [official Django support table](https://www.djangoproject.com/download/). Use the [official deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) for environment hardening.

## Expanded enhancement backlog — October 12, 2026

The user requested adding the screenshot's seven beginner SaaS ideas and the accompanying pasted article to this assessment. The article is reference material: its suggested stacks, vendors, instructions and promotional links are not implementation requirements. These entries are planned opportunities, not implemented features or additional launch blockers. Preserve Django, React, PostgreSQL and Channels unless a concrete requirement justifies a change. Vendor selection and commercial availability remain to be verified before integration.

### Current review corrections and remaining launch gaps

The initial gap table above is historical. Workspace creation, invitation acceptance, explicit tenant selection, scoped collaboration/support access, private downloads and realtime membership checks now exist. Finance APIs use the shared workspace resolver, but still lack operation-specific finance permission checks. Remaining priorities are production configuration, supported dependencies, finance authorization and company/currency reporting, journal posting invariants and concurrency, email verification and recovery, durable notifications and transactional auditing, truthful ERP indicators, and release/restore verification.

Additional product gaps identified in the current review: completion charts use last-edit dates; notification preferences are browser-only; project name uniqueness spans an owner's workspaces; workspace responses flatten roles to admin/member; ERP lists lack pagination; and modal focus handling needs improvement.

Verification from this review: the frontend production build passed with a roughly 898 KB JavaScript bundle warning. Django discovered 70 tests and system checks passed, but the suite stopped progressing and was interrupted. This is not a full-suite pass or PostgreSQL/browser verification.

### Beginner ideas from the screenshot

| Enhancement | Fit and priority | Initial scope | Completion criterion |
| --- | --- | --- | --- |
| Uptime and website monitoring | P2: optional client-service module; platform uptime monitoring remains a launch operations requirement. | Workspace-owned monitors, configurable checks, response latency/history, downtime and recovery alerts, incident log and uptime calculations. Use a durable scheduler/worker with timeouts, concurrency limits and quotas. Prevent requests to private/internal addresses, including redirect and DNS changes. | Authorized users manage monitors; simulated downtime produces one incident and deduplicated alerts; recovery closes it; reports explain missing checks and measurement windows. |
| Link-in-bio builder | P3: optional public business profile. | Unique public slug, ordered links, theme and branding, publish/unpublish, optional click analytics. Only explicitly published fields are public; accept safe URL schemes and sanitize content. | A customer publishes and edits a profile without exposing workspace records; premium customization is enforced server-side. |
| Habit and goal tracker | P3: optional personal/team productivity module. | Recurring goals, daily logs, calendar, streaks, progress charts and export; configurable user timezone and team visibility. Plan limits are product decisions rather than the article's fixed three-habit rule. | Daily completion is idempotent; timezone boundaries and missed days produce correct streaks; private goals remain private. |
| Customer feedback widget | P2: strong extension of existing support/chat. | Small embeddable widget, registered sites, feedback inbox, tags, assignment, read/archive states and optional conversion into tasks/tickets. Public widget identifiers are not secret credentials; validate inputs and add spam/rate controls. | A registered site submits feedback into its owning workspace; unrelated users cannot read submissions; duplicate and abusive requests are controlled. |
| Freelancer CRM | P2: strong fit with projects, leads and parties already modeled. | Client/contact management, lead stages, client-project links, deadlines, searchable history and scoped PDF/CSV exports. Distinguish prospects from accounting customer records and define conversion rules. | A user creates a client, converts a lead to a project, manages delivery and exports that client's records within the workspace. |
| Flashcards and study platform | P3: optional training companion. | Decks/cards, study mode, review scheduling, review history, scoped sharing and import/export. | Easy/hard responses change review dates deterministically; private/shared decks respect access rules; progress persists across sessions. |
| Form and survey builder | P2: strong fit for client intake, feedback and approvals. | Reorderable field editor, versioned JSON schema, public form links, response validation, response table and CSV export. Start with text, choice and dropdown fields. | Published forms accept only valid responses against their published version; edits preserve historical responses; workspace access and submission limits are enforced. |

### Additional ideas from the pasted article

| Enhancement | Priority and relationship to this project | Initial deliverable |
| --- | --- | --- |
| Social media scheduler | P3: optional marketing module. | OAuth connections, drafts/calendar, durable publishing jobs, retry history and explicit publish authorization. |
| Client portal and file approvals | P2: strong collaboration extension. | Restricted client access, file versions, comments and attributable approval of a specific version; new versions require fresh approval. |
| Subscription billing portal | P1: expands the existing paid-pilot requirement. | Plan, trial and usage display, upgrade/downgrade/cancel flows, billing history, verified idempotent webhooks and server-side entitlements. Keep SaaS billing separate from customers' ERP invoices. |
| Internal knowledge base/wiki | P2: supports teams and helpdesk. | Hierarchical pages, rich text, search, revision history and inherited access rules without exposing restricted pages through search. |
| Course hosting/LMS | P3: larger optional training module. | Courses, lessons, enrollments, progress and access-controlled media; certificates only after defined completion rules. |
| Newsletter broadcasting | P3: optional marketing module. | Audiences, consent records, templates, queued campaigns, unsubscribe/suppression and bounce handling. |
| Webinar/event ticketing | P3: separate expansion. | Events, capacity reservations, ticket/payment state and restricted attendance; concurrency and failed-payment recovery checks. |
| Visual automation workflow engine | P3: advanced extension after durable jobs. | Begin with internal triggers such as task completion or invoice approval; bounded actions, versioned workflows, retries, idempotency and execution logs. |
| AI support helpdesk | P2: extends existing support and Anthropic assistance. | Ticket triage and suggested replies grounded in workspace knowledge; cite retrieved material, respect document permissions and require agent approval before sending. |
| POS and inventory | P3: extends existing operations models but is a substantial product commitment. | Transactional sales, stock movements, returns and location reports; define currencies, taxes, payment integration and offline behavior before implementation. |
| Enterprise project management | P2 for milestones/time tracking; P3 for advanced scheduling. | Directed dependencies separate from current symmetric task links, Gantt views, portfolios and configurable workload capacity; validate cycles and preview rescheduling. |
| E-commerce storefront builder | P3: separate product expansion. | Tenant-owned catalog, public themes/domains, order lifecycle and payment reconciliation; strict separation of public/private records. |
| Collaborative whiteboard | P3: optional collaboration module. | Shared canvas, presence, conflict-safe editing, persistent snapshots and workspace permissions. |
| Financial forecasting and analytics | P3: only after financial data is reliable. | Scoped imports, actual-versus-forecast charts, explicit assumptions, scenarios and provenance; subscription metrics require subscription data, and acquisition-cost metrics require marketing-cost data. |
| Newsletter referrals | P3: depends on newsletter/audience infrastructure. | Unique referral links, verified attribution, abuse controls and idempotent reward fulfillment. |
| Video testimonials | P3: optional client-feedback extension. | Branded capture links, recording/upload, consent and publication approval, storage quotas and embed controls. |
| Open Graph image API | P3: optional public-page utility. | Constrained branded templates, sanitized inputs, cached images, quotas and isolated rendering. |
| AI text expansion browser extension | P3: separate client application. | Scoped snippets, secure account sync, least-privilege browser permissions and optional user-invoked generation. |
| AI resume tailoring | P3: separate product opportunity with low fit to current core. | User-approved revisions, factual constraints, private uploads, comparison and export. |

### Sequencing and shared prerequisites

1. Finish launch gaps: deployment, finance permissions, account verification/recovery, trustworthy reporting, durable workers, auditing and repeatable checks.
2. Complete a project-to-invoice/payment journey and the subscription/entitlement lifecycle.
3. Expand adjacent capabilities: CRM, client portal, feedback widget and forms; then wiki, AI support and milestones/time tracking.
4. Keep all remaining ideas in the optional backlog. Select a module using customer demand and a defined acceptance scope rather than treating the article as a requirement to ship every product.

Every module needs workspace ownership, operation-specific permissions, validation, pagination where appropriate, storage/usage quotas, audit events for sensitive changes, export/retention behavior and tests for cross-workspace access. Public pages/widgets need a separate publication/submission boundary. Outbound integrations need protected credentials, explicit connection and action authorization, durable execution, retry limits and observable results. Build shared infrastructure once rather than introducing a separate backend/database for each article example.

## First enhancement implemented

`projects/serializers.py` now rejects moving an existing task between projects, assigning a task to an outsider or inactive user, cyclic parent relationships and self-links. Existing same-project relationship checks remain. Regression tests cover rejected writes and valid member assignment, unassignment and relationships.

Project transfer is deliberately unavailable through generic task updates because it changes the audience of children, links and files. If required later, implement a dedicated transactional transfer operation with source and destination authorization and explicit relationship handling. These serializer checks protect this API path; they do not create organization isolation or repair pre-existing invalid records. Inventory existing data before enforcing additional database invariants.

Validation: all 29 tests in `projects`, `accounts` and `accounting` passed using an isolated SQLite in-memory database, including seven new task-boundary tests. Django system checks reported no issues. This does not verify PostgreSQL concurrency, browser journeys, deployment configuration or the full application's security. The local test environment used Python 3.13 and the repository's Django 5.0 pin; passing these tests does not establish supported runtime compatibility.

## Delivery sequence

1. **Security and tenant foundation:** address all P0 boundaries; write adversarial tests before migrating. Create an explicit ownership mapping for existing projects/chat, backfill it, validate ambiguous records, then enforce non-null tenant ownership. Never infer that every global admin belongs to every company.
2. **Usable private pilot:** complete workspace onboarding, invitation and recovery flows, remove misleading demo indicators, and make project delivery reliable. Gate the pilot on tenant isolation tests and successful staging recovery.
3. **Paid pilot:** implement subscription state and entitlements, billing administration, durable notifications and support workflows. Test full onboarding-to-cancellation journeys using provider test mode.
4. **Focused finance expansion:** build the customer-validated invoice/payment workflow, with company/currency boundaries, auditability and accounting review before advertising bookkeeping capabilities.
5. **Scale based on evidence:** optimize measured query bottlenecks, paginate ERP lists, enforce quotas, add integrations customers request and consider enterprise identity features when there is demand.

## Business decisions to settle before expanding scope

- Who is the first paying customer: agencies, consultancies, internal teams, or inventory-based businesses?
- What recurring problem earns payment: project delivery visibility, client collaboration, invoicing, or full operations management?
- Which countries and currencies will the business sell in, and which payment methods are needed?
- What is the initial packaging hypothesis: per workspace, per active seat, or a base subscription plus usage? Model hosting, email, storage, payment fees and AI costs before setting prices.
- What evidence defines a successful pilot? Track workspace activation, invitations accepted, weekly active teams, completed work, trial conversion, cancellations and support demand. Agree targets with pilot customers rather than inventing market benchmarks.

Keep the present Django/React architecture for the next stage. The immediate work is consistent authorization, complete customer journeys and dependable operation; a framework rewrite is not necessary to deliver those outcomes.
