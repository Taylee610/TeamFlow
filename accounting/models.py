from decimal import Decimal
from django.conf import settings
from django.db import models
from erp_foundation.models import AccountingPeriod, Company, Currency, Tenant

class Account(models.Model):
    TYPES = [(x, x.title()) for x in ("asset", "liability", "equity", "revenue", "expense")]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="accounts")
    code = models.CharField(max_length=30); name = models.CharField(max_length=160)
    account_type = models.CharField(max_length=12, choices=TYPES)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "code"], name="unique_company_account_code")]

class TaxCode(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    code = models.CharField(max_length=30); name = models.CharField(max_length=120)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    external_engine_code = models.CharField(max_length=80, blank=True)

class TaxRate(models.Model):
    tax_code = models.ForeignKey(TaxCode, on_delete=models.CASCADE, related_name="rates")
    rate = models.DecimalField(max_digits=8, decimal_places=5)
    effective_from = models.DateField(); effective_to = models.DateField(null=True, blank=True)

class JournalEntry(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="journal_entries")
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT)
    reference = models.CharField(max_length=80); description = models.TextField(blank=True)
    entry_date = models.DateField()
    status = models.CharField(max_length=10, choices=[("draft", "Draft"), ("posted", "Posted"), ("reversed", "Reversed")], default="draft")
    source_type = models.CharField(max_length=80, blank=True); source_id = models.CharField(max_length=80, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    posted_at = models.DateTimeField(null=True, blank=True)
    reversal_of = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "reference"], name="unique_company_journal_reference"),
            models.UniqueConstraint(fields=["company", "source_type", "source_id"], condition=~models.Q(source_type="") & ~models.Q(source_id=""), name="unique_journal_source"),
        ]
    @property
    def debit_total(self): return sum((x.debit for x in self.lines.all()), Decimal("0"))
    @property
    def credit_total(self): return sum((x.credit for x in self.lines.all()), Decimal("0"))

class JournalEntryLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    description = models.CharField(max_length=240, blank=True)
    debit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    credit = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    class Meta:
        constraints = [models.CheckConstraint(check=(models.Q(debit__gt=0, credit=0) | models.Q(credit__gt=0, debit=0)), name="journal_line_one_side")]

class Party(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); company = models.ForeignKey(Company, on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=[("customer", "Customer"), ("supplier", "Supplier")])
    name = models.CharField(max_length=180); tax_number = models.CharField(max_length=80, blank=True); email = models.EmailField(blank=True)

class FinancialDocument(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT); company = models.ForeignKey(Company, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, on_delete=models.PROTECT)
    document_type = models.CharField(max_length=12, choices=[(x, x.title()) for x in ("invoice", "bill", "credit_note", "debit_note")])
    number = models.CharField(max_length=50); issue_date = models.DateField(); due_date = models.DateField(null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, default="draft")
    subtotal = models.DecimalField(max_digits=19, decimal_places=4, default=0); tax_total = models.DecimalField(max_digits=19, decimal_places=4, default=0); total = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "document_type", "number"], name="unique_financial_document_number")]

class Payment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT); company = models.ForeignKey(Company, on_delete=models.PROTECT)
    party = models.ForeignKey(Party, on_delete=models.PROTECT); document = models.ForeignKey(FinancialDocument, null=True, blank=True, on_delete=models.PROTECT, related_name="payments")
    reference = models.CharField(max_length=80); payment_date = models.DateField(); amount = models.DecimalField(max_digits=19, decimal_places=4)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT); journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['company', 'reference'], name='unique_company_payment_reference')]

class DocumentLine(models.Model):
    document = models.ForeignKey(FinancialDocument, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    unit_price = models.DecimalField(max_digits=19, decimal_places=4)
    tax_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)

    class Meta:
        constraints = [models.CheckConstraint(check=models.Q(quantity__gt=0, unit_price__gte=0, tax_rate__gte=0, tax_rate__lte=100), name='valid_document_line')]

class BankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE); name = models.CharField(max_length=120); account_number = models.CharField(max_length=80)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT); ledger_account = models.ForeignKey(Account, on_delete=models.PROTECT)

class BankTransaction(models.Model):
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="transactions")
    transaction_date = models.DateField(); reference = models.CharField(max_length=120); amount = models.DecimalField(max_digits=19, decimal_places=4)
    imported_data = models.JSONField(default=dict, blank=True); journal_entry = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)

class BankReconciliation(models.Model):
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT); statement_date = models.DateField()
    statement_balance = models.DecimalField(max_digits=19, decimal_places=4); transactions = models.ManyToManyField(BankTransaction, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
