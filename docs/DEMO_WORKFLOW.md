# Exploring Preview workspace

Open http://localhost:5181/login with the existing preview account. The isolated preview database is `.cache/ui-check.sqlite3`; customer data in the normal AppData database is not seeded.

Hover over the thin **Preview workspace** strip to open navigation. Moving away closes it. Keyboard users can focus the strip and tab into the panel; it remains open while focus is inside. The dark rail now holds Create, Search and the theme toggle, with destinations shown once in the workspace panel.

## Suggested walkthrough

1. **Workspace tools → CRM:** inspect the 24 demo clients across lead, active, completed and archived stages. Active clients have related projects. You can convert another lead into a project.
2. **Projects:** open **Demo · Website launch**. Follow work through To do → Drafting → In review → Done. Try assignment, labels, subtasks and due dates. Six projects contain 48 workflow tasks, 12 subtasks and 96 historical completed tasks.
3. **Taylee AI:** choose a Demo project, select an example or describe a goal, then Generate plan. Review the suggestion and save it as a task with subtasks. Open the project to continue editing. Analyse deadlines shows measured overdue tasks and learned risk estimates for future deadlines.
4. **Workspace tools → Time logs / Client approvals:** inspect billable and non-billable time and pending, approved and rejected deliverables. The preview owner is the designated reviewer for these sample files.
5. **Finance:** select **Demo Operations** in the company selector. Twenty invoices/bills demonstrate draft, posted, partly paid and paid states. Posting creates balanced journals; recording a payment updates the outstanding balance and cash ledger. Inspect Journal entries and Trial balance. Demo bank statement rows remain unmatched for reconciliation inspection. Procurement shows eight products, stock levels and purchase orders.
6. **Workspace tools:** inspect three forms with 36 responses, feedback in multiple stages, four habits with 84 daily entries, two decks with eight cards, a link profile and four wiki guides. Forms and the link profile start unpublished; publishing enables their public pages. Three disabled monitors have synthetic up/down/unknown states and 96 recorded sample checks. Enable a monitor only when you want actual checks.
7. **Chat / People / Dashboard:** three project channels show example conversations; five synthetic teammates plus your preview account appear in the directory. Dashboard totals come from these records.

The in-app **Help** page and **Demo · Start here** wiki page also explain the workflow. The preview-only, zero-price subscription increases the AI request allowance for exploration; it is hidden from the public plan catalogue. No gateway billing history is invented, and seeding sends no email, HTTP monitor request or payment. Synthetic teammate accounts have unusable passwords.

## What the ML does

The local task planner uses a multinomial Naive Bayes intent classifier trained on 15 curated examples in finance, inventory, onboarding, engineering and marketing. It chooses a matching checklist; unfamiliar requests receive a general checklist. Description, priority and checklist composition are templates/rules, not unrestricted language generation. Dates are left unset. It does not learn from your prompts automatically.

Deadline analysis fits a small regularized logistic regression from accessible completed tasks. The outcome is completion after the stored deadline; inputs are lead time, priority, story points and assignment. It requires at least 30 dated completions and five examples of each outcome. The earlier 80% of history trains the validation model, and the later 20% tests it; the final model uses all eligible history. Accuracy and a majority-class baseline are displayed. Predictions are experimental and not calibrated guarantees. Historical priority, assignment and dates are mutable current values, so immutable snapshots and stronger validation are needed before relying on this for business decisions.

Demo projects use demo history; real projects exclude demo-labelled completions. Synthetic validation results demonstrate the flow and do not establish real-world performance. Missing deadlines or insufficient history produce no prediction; already overdue tasks are labelled from their actual deadline rather than a guessed score. Only projects the requesting user can access contribute training data. Data stays local in `local_ml` mode. Optional `TAYLEE_ENGINE=anthropic` retains the existing cloud assistant instead.

## Repeat the seed

With the same preview database environment used by the running backend:

```powershell
$env:DEBUG = 'True'
$env:USE_POSTGRESQL = 'False'
$env:USE_IN_MEMORY_CHANNEL_LAYER = 'True'
$env:DB_NAME = Join-Path (Get-Location) '.cache/ui-check.sqlite3'
.\.venv\Scripts\python.exe manage.py seed_preview --workspace 1 --owner ui-check@example.test
```

The command requires an existing owner membership and the exact workspace name **Preview workspace**. It preserves existing matching demo records on rerun. It recreates the preview subscription, but does not reset edited tasks, forms or financial documents. Uploaded sample approval files use the configured Django media storage. A preview database backup was taken before seeding.
