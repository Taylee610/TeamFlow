from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import JournalEntry, JournalEntryLine

def round_money(amount, currency):
    from decimal import Decimal, ROUND_HALF_UP
    quantum = Decimal(1).scaleb(-currency.decimal_places)
    return Decimal(amount).quantize(quantum, rounding=ROUND_HALF_UP)

@transaction.atomic
def get_or_create_source_journal(*, company, tenant, period, reference, entry_date, source_type, source_id, description=""):
    existing = JournalEntry.objects.select_for_update().filter(company=company, source_type=source_type, source_id=source_id).first()
    if existing:
        return existing, False
    try:
        with transaction.atomic():
            return JournalEntry.objects.create(company=company, tenant=tenant, period=period, reference=reference, entry_date=entry_date, source_type=source_type, source_id=source_id, description=description), True
    except IntegrityError:
        winner = JournalEntry.objects.filter(company=company, source_type=source_type, source_id=source_id).first()
        if winner is None:
            raise
        return winner, False

@transaction.atomic
def post_journal_entry(entry_id, user=None):
    entry = JournalEntry.objects.select_for_update().prefetch_related("lines__account").get(pk=entry_id)
    if entry.status != "draft": raise ValidationError("Only draft journal entries can be posted.")
    if entry.company.tenant_id != entry.tenant_id or entry.period.fiscal_year.company_id != entry.company_id:
        raise ValidationError('Journal tenant, company and accounting period must match.')
    if not entry.period.starts_on <= entry.entry_date <= entry.period.ends_on:
        raise ValidationError('Journal date must fall within the selected period.')
    if not entry.period.fiscal_year.starts_on <= entry.entry_date <= entry.period.fiscal_year.ends_on:
        raise ValidationError('Journal date must fall within the fiscal year.')
    if entry.period.is_closed or entry.period.fiscal_year.is_closed: raise ValidationError("Cannot post into a closed accounting period.")
    if entry.lines.count() < 2 or entry.debit_total != entry.credit_total: raise ValidationError("Journal entry debits must equal credits.")
    if entry.debit_total <= 0: raise ValidationError("Journal entry total must be positive.")
    if entry.lines.exclude(account__company=entry.company).exists(): raise ValidationError("Every account must belong to the journal company.")
    if entry.lines.exclude(account__tenant=entry.tenant, account__is_active=True).exists():
        raise ValidationError('Every journal account must be active and belong to the journal tenant.')
    entry.status = "posted"; entry.posted_by = user; entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_by", "posted_at"])
    return entry

def general_ledger(company, account=None, starts_on=None, ends_on=None):
    rows = JournalEntryLine.objects.filter(entry__company=company, entry__status="posted").select_related("entry", "account")
    if account: rows = rows.filter(account=account)
    if starts_on: rows = rows.filter(entry__entry_date__gte=starts_on)
    if ends_on: rows = rows.filter(entry__entry_date__lte=ends_on)
    return rows.order_by("entry__entry_date", "entry_id", "id")
