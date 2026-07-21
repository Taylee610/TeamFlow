from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from erp_foundation.models import AccountingPeriod, Company, Currency, FiscalYear, Tenant
from .models import Account, JournalEntry, JournalEntryLine
from .services import get_or_create_source_journal, post_journal_entry, round_money

class JournalPostingTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test", slug="test")
        currency = Currency.objects.create(code="USD", name="US Dollar")
        self.company = Company.objects.create(tenant=self.tenant, name="Test Co", legal_name="Test Company", base_currency=currency)
        year = FiscalYear.objects.create(company=self.company, name="2026", starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31))
        self.period = AccountingPeriod.objects.create(fiscal_year=year, name="July", starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 31))
        self.cash = Account.objects.create(tenant=self.tenant, company=self.company, code="1000", name="Cash", account_type="asset")
        self.equity = Account.objects.create(tenant=self.tenant, company=self.company, code="3000", name="Capital", account_type="equity")

    def entry(self):
        return JournalEntry.objects.create(tenant=self.tenant, company=self.company, period=self.period, reference="JE-1", entry_date=date(2026, 7, 21))

    def test_balanced_entry_posts(self):
        entry = self.entry()
        JournalEntryLine.objects.create(entry=entry, account=self.cash, debit=Decimal("100"))
        JournalEntryLine.objects.create(entry=entry, account=self.equity, credit=Decimal("100"))
        self.assertEqual(post_journal_entry(entry.pk).status, "posted")

    def test_unbalanced_entry_is_rejected(self):
        entry = self.entry()
        JournalEntryLine.objects.create(entry=entry, account=self.cash, debit=Decimal("100"))
        JournalEntryLine.objects.create(entry=entry, account=self.equity, credit=Decimal("90"))
        with self.assertRaises(ValidationError): post_journal_entry(entry.pk)

    def test_closed_period_is_rejected(self):
        self.period.is_closed = True; self.period.save(update_fields=["is_closed"])
        entry = self.entry()
        JournalEntryLine.objects.create(entry=entry, account=self.cash, debit=Decimal("100"))
        JournalEntryLine.objects.create(entry=entry, account=self.equity, credit=Decimal("100"))
        with self.assertRaises(ValidationError): post_journal_entry(entry.pk)

    def test_currency_rounding_is_half_up(self):
        currency = self.company.base_currency
        self.assertEqual(round_money("10.125", currency), Decimal("10.13"))
        self.assertEqual(round_money("10.124", currency), Decimal("10.12"))

    def test_source_journal_is_idempotent(self):
        kwargs = {"company": self.company, "tenant": self.tenant, "period": self.period, "reference": "INV-POST-1", "entry_date": date(2026, 7, 21), "source_type": "invoice", "source_id": "42"}
        first, created_first = get_or_create_source_journal(**kwargs)
        second, created_second = get_or_create_source_journal(**kwargs)
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)


class TenantIsolationTests(TestCase):
    def test_account_api_never_returns_another_tenants_accounts(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        from erp_foundation.models import Membership, Role
        currency = Currency.objects.create(code="ZAR", name="Rand")
        tenant_a = Tenant.objects.create(name="A", slug="a")
        tenant_b = Tenant.objects.create(name="B", slug="b")
        company_a = Company.objects.create(tenant=tenant_a, name="A", legal_name="A Ltd", base_currency=currency)
        company_b = Company.objects.create(tenant=tenant_b, name="B", legal_name="B Ltd", base_currency=currency)
        role = Role.objects.create(tenant=tenant_a, name="Viewer")
        user = get_user_model().objects.create_user(email="isolation@test.demo", password="test-password")
        Membership.objects.create(tenant=tenant_a, user=user, role=role)
        Account.objects.create(tenant=tenant_a, company=company_a, code="A100", name="Visible", account_type="asset")
        Account.objects.create(tenant=tenant_b, company=company_b, code="B100", name="Secret", account_type="asset")
        client = APIClient(); client.force_authenticate(user)
        response = client.get("/api/v1/erp/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["code"] for row in response.json()], ["A100"])
