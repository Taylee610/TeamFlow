from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from erp_foundation.models import Membership
from erp_foundation.access import workspace_membership
from erp_operations.models import PurchaseOrder, SalesOrder, StockLevel
from .models import Account, BankTransaction, FinancialDocument, JournalEntry, JournalEntryLine


def membership_for(request):
    return workspace_membership(request)


class TenantAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def membership(self, request):
        membership = membership_for(request)
        if not membership:
            self.permission_denied(request, message="No active tenant membership.")
        return membership


class DashboardView(TenantAPIView):
    def get(self, request):
        membership = self.membership(request)
        tenant = membership.tenant
        posted = JournalEntry.objects.filter(tenant=tenant, status="posted")
        receivables = FinancialDocument.objects.filter(tenant=tenant, document_type="invoice").exclude(status__in=["paid", "void"]).aggregate(value=Coalesce(Sum("total"), Decimal("0")))["value"]
        payables = FinancialDocument.objects.filter(tenant=tenant, document_type="bill").exclude(status__in=["paid", "void"]).aggregate(value=Coalesce(Sum("total"), Decimal("0")))["value"]
        return Response({
            "tenant": {"id": tenant.pk, "name": tenant.name},
            "metrics": {"receivables": receivables, "payables": payables, "posted_journals": posted.count(), "open_purchase_orders": PurchaseOrder.objects.filter(company__tenant=tenant).exclude(status__in=["closed", "cancelled"]).count(), "stock_units": StockLevel.objects.filter(product__tenant=tenant).aggregate(value=Coalesce(Sum("quantity"), Decimal("0")))["value"]},
            "recent_journals": list(posted.order_by("-entry_date", "-id").values("id", "reference", "entry_date", "description")[:6]),
        })


class AccountsView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        rows = Account.objects.filter(tenant=tenant).order_by("code").values("id", "code", "name", "account_type", "is_active")
        return Response(list(rows))


class JournalsView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        entries = JournalEntry.objects.filter(tenant=tenant).prefetch_related("lines").order_by("-entry_date", "-id")
        return Response([{"id": x.pk, "reference": x.reference, "date": x.entry_date, "description": x.description, "status": x.status, "debit": x.debit_total, "credit": x.credit_total} for x in entries])


class DocumentsView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        rows = FinancialDocument.objects.filter(tenant=tenant).select_related("party", "currency").order_by("-issue_date")
        return Response([{"id": x.pk, "number": x.number, "type": x.document_type, "party": x.party.name, "date": x.issue_date, "due_date": x.due_date, "currency": x.currency_id, "total": x.total, "status": x.status} for x in rows])


class ProcurementView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        rows = PurchaseOrder.objects.filter(company__tenant=tenant).select_related("supplier").order_by("-order_date")
        return Response([{"id": x.pk, "number": x.number, "supplier": x.supplier.name, "date": x.order_date, "status": x.status, "total": sum((line.quantity * line.unit_price for line in x.lines.all()), Decimal("0"))} for x in rows.prefetch_related("lines")])


class ReconciliationView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        rows = BankTransaction.objects.filter(bank_account__company__tenant=tenant).select_related("bank_account").order_by("-transaction_date")
        return Response([{"id": x.pk, "date": x.transaction_date, "reference": x.reference, "amount": x.amount, "bank": x.bank_account.name, "matched": bool(x.journal_entry_id)} for x in rows])


class TrialBalanceView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        rows = JournalEntryLine.objects.filter(entry__tenant=tenant, entry__status="posted").values("account__code", "account__name", "account__account_type").annotate(debit=Coalesce(Sum("debit"), Decimal("0")), credit=Coalesce(Sum("credit"), Decimal("0"))).order_by("account__code")
        return Response(list(rows))
