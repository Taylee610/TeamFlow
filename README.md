# TeamFlow – Intelligent Business Management SaaS

**A full-stack business management and collaboration platform combining enterprise application development, workflow automation and applied machine learning.**

TeamFlow is an independently developed SaaS application designed to help businesses manage projects, teams, clients, operational workflows and financial activities from a unified workspace.

The platform combines a Django REST backend with a React frontend, real-time collaboration, business management tools and locally implemented machine learning capabilities.

**Project status:** Actively under development  
**Development started:** Approximately October 2025

## Key Features

### Project and Team Management
- Project creation, task assignment and progress tracking.
- Kanban workflow management, subtasks and deadlines.
- Workspace-based collaboration and role management.
- Real-time updates and team communication.
- Notifications and task time logging.

### AI and Machine Learning
- Naive Bayes-style intent classification for intelligent task planning.
- Automated task checklist generation using predefined templates.
- Logistic regression for experimental task deadline-risk prediction.
- Historical task analysis and temporal model validation.
- Local ML processing to keep task data within the application environment.

### Business Management
- Customer Relationship Management (CRM).
- Customer feedback collection and management.
- Client file approvals and knowledge management.
- Financial workflows covering invoices, bills, journal entries and payment allocation.
- Forms, surveys, habit tracking and website monitoring.
- Subscription management and Paynow payment integration.

### Backend and Infrastructure
- RESTful APIs with Django REST Framework.
- JWT authentication and workspace-level access controls.
- PostgreSQL database support.
- Real-time communication using Django Channels and Redis.
- Containerization using Docker and Docker Compose.
- Nginx and Daphne deployment configuration.
- Automated checks using GitHub Actions.

## Technology Stack

| Area | Technologies |
|---|---|
| Backend | Python, Django 5.2 |
| API | Django REST Framework |
| Frontend | React 18, JavaScript, Vite |
| Database | PostgreSQL, SQLite for local development |
| Machine Learning | Naive Bayes-style classification, Logistic Regression |
| Real-time | Django Channels, Redis |
| Authentication | JWT, SimpleJWT |
| DevOps | Docker, Docker Compose, GitHub Actions |
| Web infrastructure | Nginx, Daphne |

## Machine Learning Implementation

TeamFlow includes two locally implemented machine learning workflows.

**1. Intelligent Task Planning**

A Naive Bayes-style intent classifier categorizes user task requests into finance, inventory, onboarding, engineering and marketing domains. The predicted category determines an appropriate task checklist.

The classifier uses 15 curated training examples and falls back to a general checklist when confidence is insufficient.

**2. Predictive Deadline-Risk Analysis**

A logistic regression model estimates the likelihood of a task being completed after its deadline.

Model features include:
- Task lead time.
- Task priority.
- Story points.
- Assignment status.

The implementation includes a chronological training/validation split, accuracy measurement and comparison with a majority-class baseline.

These models are experimental decision-support features, not guaranteed predictions. The deadline model requires sufficient historical data before producing estimates.

## Architecture

- React frontend communicates with Django REST APIs.
- Django manages authentication, business logic and persistence.
- PostgreSQL stores application records.
- Redis and Django Channels support real-time communication.
- Background workers handle queued jobs and scheduled operations.
- Local ML services support intelligent task planning and deadline analysis.

## Testing and Continuous Integration

The repository includes:
- Django backend tests.
- ML-specific tests.
- API and access-control tests.
- Frontend production build checks.
- Database migration checks.
- GitHub Actions workflows for SQLite and PostgreSQL testing.

## Project Documentation

Further technical documentation is available in the `docs/` directory:

- `IMPLEMENTED_TOOLS.md` – implemented modules and limitations.
- `SAAS_READINESS.md` – architecture assessment and development roadmap.
- `WORKSPACE_SETUP.md` – local setup and workspace configuration.
- `DEMO_WORKFLOW.md` – application walkthrough and ML explanation.

## Current Development Focus

TeamFlow remains an evolving independent project. Development priorities include improving SaaS readiness, strengthening production security, expanding automated testing, refining machine learning capabilities and improving deployment reliability.

**Note:** The project is not presented as a fully production-certified financial or accounting platform. Some deployment integrations require external configuration and verification.

---

Developed independently by **Lycon Tanyaradzwa Bhegedhe**.

