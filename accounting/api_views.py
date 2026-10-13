import calendar
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from erp_foundation.access import workspace_membership, can_admin_workspace
from erp_foundation.models import Company, Currency, FiscalYear, AccountingPeriod
from erp_operations.models import PurchaseOrder, StockLevel
from workspace_tools.services import audit
from workspace_tools.views import csv_response
from projects.pagination import StandardPagination
from .models import Account, BankTransaction, FinancialDocument, JournalEntry, JournalEntryLine, DocumentLine, Party
from .services import round_money
from .workflows import post_document, record_payment


def membership_for(request):
    return workspace_membership(request)


class TenantAPIView(APIView):
    def membership(self, request, write=False):
        membership = membership_for(request)
        if not (can_admin_workspace(membership) or membership.has_permission('finance.manage') or (not write and membership.has_permission('finance.view'))):
            self.permission_denied(request, message='Finance permission is required for this workspace.')
        return membership

    def company(self, request, write=False):
        membership = self.membership(request, write)
        companies = Company.objects.filter(tenant=membership.tenant)
        pk = request.query_params.get('company') or request.data.get('company')
        if pk:
            return get_object_or_404(companies, pk=serializers.IntegerField(min_value=1).run_validation(pk))
        candidates = list(companies[:2])
        if len(candidates) != 1:
            raise serializers.ValidationError({'company': 'Select a company, or create one to begin.'})
        return candidates[0]

    def page(self, request, queryset, transform=lambda x: x):
        paginator = StandardPagination()
        rows = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response([transform(row) for row in rows])


class CompaniesView(TenantAPIView):
    def get(self, request):
        tenant = self.membership(request).tenant
        return Response(list(Company.objects.filter(tenant=tenant).values('id', 'name', 'legal_name', 'base_currency_id')))

    @transaction.atomic
    def post(self, request):
        tenant = self.membership(request, True).tenant
        name = serializers.CharField(max_length=180).run_validation(request.data.get('name'))
        code = serializers.RegexField(r'^[A-Z]{3}$').run_validation(request.data.get('currency', 'USD'))
        legal = serializers.CharField(max_length=220).run_validation(request.data.get('legal_name', name))
        if Company.objects.filter(tenant=tenant, legal_name=legal).exists():
            raise serializers.ValidationError('This company already exists.')
        currency, _ = Currency.objects.get_or_create(code=code, defaults={'name': code})
        company = Company.objects.create(tenant=tenant, name=name, legal_name=legal, base_currency=currency)
        n = timezone.now().year
        year = FiscalYear.objects.create(company=company, name=str(n), starts_on=date(n, 1, 1), ends_on=date(n, 12, 31))
        for month in range(1, 13):
            AccountingPeriod.objects.create(fiscal_year=year, name=calendar.month_name[month], starts_on=date(n, month, 1), ends_on=date(n, month, calendar.monthrange(n, month)[1]))
        for code, title, kind in [('1000', 'Cash', 'asset'), ('1100', 'Receivables', 'asset'), ('1200', 'Input tax', 'asset'), ('2000', 'Payables', 'liability'), ('2100', 'Output tax', 'liability'), ('4000', 'Revenue', 'revenue'), ('5000', 'Expenses', 'expense')]:
            Account.objects.create(tenant=tenant, company=company, code=code, name=title, account_type=kind)
        audit(company, request.user, 'create')
        return Response({'id': company.pk, 'name': name, 'base_currency_id': currency.code}, status=201)


def document_data(document):
    paid = sum((x.amount for x in document.payments.all()), Decimal('0'))
    return {'id': document.pk, 'number': document.number, 'type': document.document_type, 'party': document.party.name, 'date': document.issue_date,
            'due_date': document.due_date, 'currency': document.currency_id, 'total': document.total, 'paid': paid, 'outstanding': document.total - paid, 'status': document.status}


class DashboardView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        posted = JournalEntry.objects.filter(tenant=company.tenant, company=company, status='posted')
        def outstanding(kind):
            docs = FinancialDocument.objects.filter(tenant=company.tenant, company=company, currency=company.base_currency, document_type=kind, status__in=['posted', 'partial']).prefetch_related('payments')
            return sum((document_data(x)['outstanding'] for x in docs), Decimal('0'))
        cash = JournalEntryLine.objects.filter(entry__in=posted, account__company=company, account__code='1000').values('entry__entry_date').annotate(inflow=Sum('debit'), outflow=Sum('credit')).order_by('entry__entry_date')
        return Response({'company': company.name, 'currency': company.base_currency_id,
            'metrics': {'receivables': outstanding('invoice'), 'payables': outstanding('bill'), 'posted_journals': posted.count(),
                        'open_purchase_orders': PurchaseOrder.objects.filter(company=company).exclude(status__in=['closed', 'cancelled']).count(),
                        'stock_units': StockLevel.objects.filter(warehouse__company=company, product__tenant=company.tenant).aggregate(n=Sum('quantity'))['n'] or 0},
            'cash_flow': [{'day': x['entry__entry_date'], 'inflow': x['inflow'], 'outflow': x['outflow']} for x in cash],
            'recent_journals': list(posted.order_by('-entry_date', '-id').values('id', 'reference', 'entry_date', 'description')[:6])})


class AccountsView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        return self.page(request, Account.objects.filter(tenant=company.tenant, company=company).order_by('code').values('id', 'code', 'name', 'account_type', 'is_active'))


class JournalsView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        entries = JournalEntry.objects.filter(tenant=company.tenant, company=company).prefetch_related('lines').order_by('-entry_date', '-id')
        return self.page(request, entries, lambda x: {'id': x.pk, 'reference': x.reference, 'date': x.entry_date, 'description': x.description, 'status': x.status, 'debit': x.debit_total, 'credit': x.credit_total, 'currency': company.base_currency_id})


class LineInput(serializers.Serializer):
    description = serializers.CharField(max_length=240)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal('0.0001'))
    unit_price = serializers.DecimalField(max_digits=15, decimal_places=4, min_value=0)
    tax_rate = serializers.DecimalField(max_digits=7, decimal_places=4, min_value=0, max_value=100, default=0)


class DocumentInput(serializers.Serializer):
    number = serializers.CharField(max_length=50)
    type = serializers.ChoiceField(choices=['invoice', 'bill'])
    party_name = serializers.CharField(max_length=180)
    party_email = serializers.EmailField(required=False, allow_blank=True)
    issue_date = serializers.DateField()
    due_date = serializers.DateField(required=False, allow_null=True)
    lines = LineInput(many=True, allow_empty=False)

    def validate(self, attrs):
        if len(attrs['lines']) > 100 or (attrs.get('due_date') and attrs['due_date'] < attrs['issue_date']):
            raise serializers.ValidationError('Use up to 100 lines and a due date on or after issue date.')
        return attrs


class DocumentsView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        rows = FinancialDocument.objects.filter(tenant=company.tenant, company=company).select_related('party', 'currency').prefetch_related('payments').order_by('-issue_date', '-id')
        return self.page(request, rows, document_data)

    @transaction.atomic
    def post(self, request):
        company = self.company(request, True)
        serializer = DocumentInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if FinancialDocument.objects.filter(company=company, document_type=data['type'], number=data['number']).exists():
            raise serializers.ValidationError({'number': 'This document number already exists.'})
        party, _ = Party.objects.get_or_create(tenant=company.tenant, company=company, kind='customer' if data['type'] == 'invoice' else 'supplier', name=data['party_name'], defaults={'email': data.get('party_email', '')})
        subtotal = sum((round_money(x['quantity'] * x['unit_price'], company.base_currency) for x in data['lines']), Decimal('0'))
        tax = sum((round_money(x['quantity'] * x['unit_price'] * x['tax_rate'] / 100, company.base_currency) for x in data['lines']), Decimal('0'))
        if subtotal + tax <= 0 or subtotal + tax >= Decimal('1000000000000000'):
            raise serializers.ValidationError('Total must be positive and within the supported range.')
        document = FinancialDocument.objects.create(tenant=company.tenant, company=company, party=party, document_type=data['type'], number=data['number'], issue_date=data['issue_date'], due_date=data.get('due_date'), currency=company.base_currency, subtotal=subtotal, tax_total=tax, total=subtotal + tax)
        for line in data['lines']:
            DocumentLine.objects.create(document=document, **line)
        audit(document, request.user, 'create')
        return Response(document_data(document), status=201)


class DocumentActionView(TenantAPIView):
    def post(self, request, pk, operation):
        company = self.company(request, True)
        document = get_object_or_404(FinancialDocument, pk=pk, tenant=company.tenant, company=company)
        try:
            if operation == 'post':
                document = post_document(document, request.user)
            elif operation == 'payment':
                amount = serializers.DecimalField(max_digits=15, decimal_places=4, min_value=Decimal('0.0001')).run_validation(request.data.get('amount'))
                reference = serializers.CharField(max_length=80).run_validation(request.data.get('reference'))
                day = serializers.DateField().run_validation(request.data.get('date', timezone.now().date().isoformat()))
                record_payment(document, request.user, amount, reference, day)
                document.refresh_from_db()
            else:
                raise serializers.ValidationError('Unknown operation.')
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return Response(document_data(document))


class DocumentExportView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        docs = FinancialDocument.objects.filter(company=company, tenant=company.tenant).select_related('party').prefetch_related('payments').order_by('issue_date', 'pk')
        return csv_response('statement', ['Number', 'Type', 'Party', 'Date', 'Currency', 'Total', 'Paid', 'Outstanding', 'Status'], [[x[k] for k in ['number', 'type', 'party', 'date', 'currency', 'total', 'paid', 'outstanding', 'status']] for x in map(document_data, docs)])


class ProcurementView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        rows = PurchaseOrder.objects.filter(company=company).select_related('supplier').prefetch_related('lines').order_by('-order_date', '-pk')
        return self.page(request, rows, lambda x: {'id': x.pk, 'number': x.number, 'supplier': x.supplier.name, 'date': x.order_date, 'status': x.status, 'currency': company.base_currency_id, 'total': sum((line.quantity * line.unit_price for line in x.lines.all()), Decimal('0'))})


class ReconciliationView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        rows = BankTransaction.objects.filter(bank_account__company=company).select_related('bank_account').order_by('-transaction_date', '-pk')
        return self.page(request, rows, lambda x: {'id': x.pk, 'date': x.transaction_date, 'reference': x.reference, 'amount': x.amount, 'currency': x.bank_account.currency_id, 'bank': x.bank_account.name, 'matched': bool(x.journal_entry_id)})


class TrialBalanceView(TenantAPIView):
    def get(self, request):
        company = self.company(request)
        rows = JournalEntryLine.objects.filter(entry__tenant=company.tenant, entry__company=company, entry__status='posted', account__company=company).values('account_id', 'account__code', 'account__name', 'account__account_type').annotate(debit=Sum('debit'), credit=Sum('credit')).order_by('account__code')
        return self.page(request, rows, lambda x: {**x, 'currency': company.base_currency_id})
