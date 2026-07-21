from django.urls import path
from .api_views import AccountsView, DashboardView, DocumentsView, JournalsView, ProcurementView, ReconciliationView, TrialBalanceView

urlpatterns = [
    path("dashboard/", DashboardView.as_view()),
    path("accounts/", AccountsView.as_view()),
    path("journals/", JournalsView.as_view()),
    path("documents/", DocumentsView.as_view()),
    path("procurement/", ProcurementView.as_view()),
    path("reconciliation/", ReconciliationView.as_view()),
    path("reports/trial-balance/", TrialBalanceView.as_view()),
]
