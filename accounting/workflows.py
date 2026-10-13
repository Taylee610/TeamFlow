from decimal import Decimal
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from erp_foundation.models import AccountingPeriod
from workspace_tools.services import audit
from .models import Account, JournalEntryLine, Payment, FinancialDocument
from .services import get_or_create_source_journal, post_journal_entry, round_money


def period_for(company, day):
    periods = list(AccountingPeriod.objects.filter(fiscal_year__company=company, starts_on__lte=day, ends_on__gte=day, is_closed=False, fiscal_year__is_closed=False)[:2])
    if len(periods) != 1:
        raise ValidationError('The date must match exactly one open accounting period.')
    return periods[0]


def account_for(company, code):
    try:
        return Account.objects.get(company=company, tenant=company.tenant, code=code, is_active=True)
    except Account.DoesNotExist:
        raise ValidationError(f'Required account {code} is missing or inactive.')


@transaction.atomic
def post_document(document, user):
    document = FinancialDocument.objects.select_for_update().get(pk=document.pk)
    if document.status != 'draft' or document.journal_entry_id:
        raise ValidationError('Only draft documents can be posted.')
    if document.company.tenant_id != document.tenant_id or document.party.company_id != document.company_id or document.party.tenant_id != document.tenant_id:
        raise ValidationError('Document, customer and company must belong together.')
    if document.currency_id != document.company.base_currency_id:
        raise ValidationError('This workflow supports the company base currency only.')
    if document.document_type not in ('invoice', 'bill') or not document.lines.exists() or document.total <= 0:
        raise ValidationError('Create a positive invoice or bill with at least one line.')
    entry, created = get_or_create_source_journal(company=document.company, tenant=document.tenant, period=period_for(document.company, document.issue_date), reference=f'DOC-{document.pk}', entry_date=document.issue_date, source_type='document', source_id=str(document.pk), description=document.number)
    if not created:
        raise ValidationError('This document already has a source journal.')
    invoice = document.document_type == 'invoice'
    JournalEntryLine.objects.create(entry=entry, account=account_for(document.company, '1100' if invoice else '2000'), **({'debit': document.total} if invoice else {'credit': document.total}))
    JournalEntryLine.objects.create(entry=entry, account=account_for(document.company, '4000' if invoice else '5000'), **({'credit': document.subtotal} if invoice else {'debit': document.subtotal}))
    if document.tax_total:
        JournalEntryLine.objects.create(entry=entry, account=account_for(document.company, '2100' if invoice else '1200'), **({'credit': document.tax_total} if invoice else {'debit': document.tax_total}))
    post_journal_entry(entry.pk, user)
    document.journal_entry, document.status = entry, 'posted'
    document.save(update_fields=['journal_entry', 'status'])
    audit(document, user, 'post', after={'journal': entry.pk})
    return document


@transaction.atomic
def record_payment(document, user, amount, reference, day):
    document = FinancialDocument.objects.select_for_update().get(pk=document.pk)
    amount = round_money(amount, document.currency)
    existing = Payment.objects.filter(company=document.company, reference=reference).first()
    if existing:
        if existing.document_id != document.pk or existing.amount != amount or existing.payment_date != day:
            raise ValidationError('This reference belongs to a different payment.')
        return existing
    if document.status not in ('posted', 'partial'):
        raise ValidationError('Only posted or partly paid documents accept payments.')
    paid = sum(document.payments.values_list('amount', flat=True), Decimal('0'))
    if amount <= 0 or paid + amount > document.total:
        raise ValidationError('Payment must be positive and cannot exceed the outstanding balance.')
    try:
        with transaction.atomic():
            payment = Payment.objects.create(tenant=document.tenant, company=document.company, party=document.party, document=document, currency=document.currency, amount=amount, reference=reference, payment_date=day)
    except IntegrityError:
        raise ValidationError('This payment reference is already used. Refresh the statement before retrying.')
    entry, _ = get_or_create_source_journal(company=document.company, tenant=document.tenant, period=period_for(document.company, day), reference=f'PAY-{payment.pk}', entry_date=day, source_type='payment', source_id=str(payment.pk), description=reference)
    cash = account_for(document.company, '1000')
    balance = account_for(document.company, '1100' if document.document_type == 'invoice' else '2000')
    debit, credit = (cash, balance) if document.document_type == 'invoice' else (balance, cash)
    JournalEntryLine.objects.create(entry=entry, account=debit, debit=amount)
    JournalEntryLine.objects.create(entry=entry, account=credit, credit=amount)
    post_journal_entry(entry.pk, user)
    payment.journal_entry = entry
    payment.save(update_fields=['journal_entry'])
    document.status = 'paid' if paid + amount == document.total else 'partial'
    document.save(update_fields=['status'])
    audit(document, user, 'payment', after={'payment': payment.pk, 'amount': str(amount), 'status': document.status})
    return payment
