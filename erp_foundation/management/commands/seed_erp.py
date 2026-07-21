from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounting.models import Account, FinancialDocument, JournalEntry, JournalEntryLine, Party, TaxCode, TaxRate
from accounting.services import post_journal_entry
from erp_foundation.models import AccountingPeriod, Company, Currency, ExchangeRate, FiscalYear, Membership, Permission, Role, Tenant
from erp_operations.models import (
    Department, Employee, GoodsReceipt, Lead, Milestone, Opportunity, PayComponent,
    PayrollRun, Payslip, Position, PriceList, PriceListItem, Product, PurchaseOrder,
    PurchaseOrderLine, SalesOrder, SalesOrderLine, StockLevel, StockMovement,
    TenantSubscription, SaaSPlan, TimeEntry, UOM, Warehouse,
)
from projects.models import Project, Task


class Command(BaseCommand):
    help = "Create or update a coherent demonstration ERP dataset. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args, **options):
        usd, _ = Currency.objects.update_or_create(code="USD", defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2})
        zig, _ = Currency.objects.update_or_create(code="ZWG", defaults={"name": "Zimbabwe Gold", "symbol": "ZiG", "decimal_places": 2})
        tenant, _ = Tenant.objects.update_or_create(slug="taylee", defaults={"name": "Taylee", "is_active": True})
        company, _ = Company.objects.update_or_create(
            tenant=tenant, legal_name="Taylee (Private) Limited",
            defaults={"name": "Taylee", "registration_number": "TAYLEE-2026-001", "tax_number": "TAYLEE-TIN-001", "base_currency": usd},
        )
        ExchangeRate.objects.update_or_create(tenant=tenant, from_currency=usd, to_currency=zig, effective_on=date(2026, 7, 1), defaults={"rate": Decimal("13.75000000")})

        User = get_user_model()
        users = {}
        for email, first, last, legacy_role in [
            ("taylee@me.com", "Taylee", "", "admin"),
            ("finance@taylee.me", "Rutendo", "Ncube", "manager"),
            ("member@taylee.me", "Tinashe", "Dube", "member"),
        ]:
            user, created = User.objects.get_or_create(email=email, defaults={"first_name": first, "last_name": last, "role": legacy_role, "is_active": True})
            if created:
                user.set_password("Taylee03!" if email == "taylee@me.com" else "ChangeMe123!")
                user.save(update_fields=["password"])
            users[email] = user

        permission_specs = {
            "erp.view": ("platform", {}), "accounting.post": ("accounting", {}),
            "accounting.approve": ("accounting", {"maximum_amount": 10000}),
            "procurement.approve": ("procurement", {"maximum_amount": 5000}), "payroll.run": ("payroll", {}),
        }
        permissions = {}
        for code, (module, conditions) in permission_specs.items():
            permissions[code], _ = Permission.objects.update_or_create(tenant=tenant, code=code, defaults={"module": module, "description": code.replace(".", " ").title(), "conditions": conditions})
        admin_role, _ = Role.objects.get_or_create(tenant=tenant, name="Administrator")
        manager_role, _ = Role.objects.get_or_create(tenant=tenant, name="Finance Manager")
        employee_role, _ = Role.objects.get_or_create(tenant=tenant, name="Employee")
        admin_role.permissions.set(permissions.values())
        manager_role.permissions.set([permissions[x] for x in ("erp.view", "accounting.post", "accounting.approve", "procurement.approve")])
        employee_role.permissions.set([permissions["erp.view"]])
        for email, role in [("taylee@me.com", admin_role), ("finance@taylee.me", manager_role), ("member@taylee.me", employee_role)]:
            Membership.objects.update_or_create(tenant=tenant, user=users[email], defaults={"role": role, "is_active": True})

        fiscal_year, _ = FiscalYear.objects.update_or_create(company=company, name="FY2026", defaults={"starts_on": date(2026, 1, 1), "ends_on": date(2026, 12, 31), "is_closed": False})
        periods = {}
        for month in range(1, 13):
            starts = date(2026, month, 1)
            ends = date(2026, month + 1, 1) - timedelta(days=1) if month < 12 else date(2026, 12, 31)
            periods[month], _ = AccountingPeriod.objects.update_or_create(fiscal_year=fiscal_year, name=starts.strftime("%B"), defaults={"starts_on": starts, "ends_on": ends, "is_closed": month < 7})

        accounts = {}
        for code, name, kind in [
            ("1000", "Cash and Bank", "asset"), ("1100", "Accounts Receivable", "asset"),
            ("1200", "Inventory", "asset"), ("2000", "Accounts Payable", "liability"),
            ("2100", "VAT Payable", "liability"), ("3000", "Share Capital", "equity"),
            ("4000", "Sales Revenue", "revenue"), ("5000", "Cost of Sales", "expense"),
            ("6000", "Payroll Expense", "expense"),
        ]:
            accounts[code], _ = Account.objects.update_or_create(company=company, code=code, defaults={"tenant": tenant, "name": name, "account_type": kind, "is_active": True})
        vat, _ = TaxCode.objects.update_or_create(tenant=tenant, code="VAT15", defaults={"name": "VAT 15%", "account": accounts["2100"], "external_engine_code": "ZIM-VAT-STD"})
        TaxRate.objects.update_or_create(tax_code=vat, effective_from=date(2026, 1, 1), defaults={"rate": Decimal("0.15000")})

        customer, _ = Party.objects.update_or_create(company=company, kind="customer", name="Harare Retailers Ltd", defaults={"tenant": tenant, "tax_number": "CUST-TIN-001", "email": "accounts@harareretailers.demo"})
        supplier, _ = Party.objects.update_or_create(company=company, kind="supplier", name="Msasa Wholesale Ltd", defaults={"tenant": tenant, "tax_number": "SUP-TIN-001", "email": "sales@msasawholesale.demo"})
        each, _ = UOM.objects.update_or_create(tenant=tenant, code="EA", defaults={"name": "Each"})
        consulting, _ = Product.objects.update_or_create(tenant=tenant, sku="SRV-CONSULT", defaults={"name": "ERP Consulting Hour", "uom": each, "is_service": True})
        laptop, _ = Product.objects.update_or_create(tenant=tenant, sku="IT-LAPTOP-01", defaults={"name": "Business Laptop", "uom": each, "is_service": False})
        warehouse, _ = Warehouse.objects.update_or_create(company=company, code="MSA", defaults={"name": "Msasa Main Warehouse"})
        StockLevel.objects.update_or_create(product=laptop, warehouse=warehouse, defaults={"quantity": Decimal("25")})
        price_list, _ = PriceList.objects.update_or_create(tenant=tenant, name="Standard USD", defaults={"currency": usd})
        PriceListItem.objects.update_or_create(price_list=price_list, product=laptop, defaults={"price": Decimal("850")})
        PriceListItem.objects.update_or_create(price_list=price_list, product=consulting, defaults={"price": Decimal("75")})

        po, _ = PurchaseOrder.objects.update_or_create(company=company, number="PO-2026-0001", defaults={"supplier": supplier, "order_date": date(2026, 7, 10), "status": "approved"})
        PurchaseOrderLine.objects.update_or_create(order=po, product=laptop, defaults={"quantity": Decimal("10"), "unit_price": Decimal("650")})
        receipt, _ = GoodsReceipt.objects.update_or_create(order=po, number="GRN-2026-0001", defaults={"warehouse": warehouse, "received_at": timezone.make_aware(datetime(2026, 7, 15, 10, 0))})
        StockMovement.objects.update_or_create(tenant=tenant, reference=receipt.number, product=laptop, warehouse=warehouse, defaults={"movement_type": "receipt", "quantity": Decimal("10"), "unit_cost": Decimal("650"), "occurred_at": receipt.received_at})

        invoice, _ = FinancialDocument.objects.update_or_create(company=company, document_type="invoice", number="INV-2026-0001", defaults={"tenant": tenant, "party": customer, "issue_date": date(2026, 7, 20), "due_date": date(2026, 8, 19), "currency": usd, "status": "approved", "subtotal": Decimal("1500"), "tax_total": Decimal("225"), "total": Decimal("1725")})
        order, _ = SalesOrder.objects.update_or_create(company=company, number="SO-2026-0001", defaults={"customer": customer, "order_date": date(2026, 7, 18), "status": "confirmed", "invoice": invoice})
        SalesOrderLine.objects.update_or_create(order=order, product=consulting, defaults={"quantity": Decimal("20"), "unit_price": Decimal("75")})

        journal, _ = JournalEntry.objects.get_or_create(company=company, reference="JE-OPEN-2026", defaults={"tenant": tenant, "period": periods[7], "description": "Demo opening capital", "entry_date": date(2026, 7, 1), "source_type": "seed"})
        if journal.status == "draft":
            journal.lines.all().delete()
            JournalEntryLine.objects.create(entry=journal, account=accounts["1000"], description="Opening bank balance", debit=Decimal("50000"))
            JournalEntryLine.objects.create(entry=journal, account=accounts["3000"], description="Opening capital", credit=Decimal("50000"))
            post_journal_entry(journal.pk, users["taylee@me.com"])

        department, _ = Department.objects.update_or_create(company=company, name="Finance")
        position, _ = Position.objects.update_or_create(department=department, title="Finance Officer")
        employee, _ = Employee.objects.update_or_create(company=company, employee_number="EMP-001", defaults={"user": users["finance@taylee.me"], "department": department, "position": position, "hired_on": date(2025, 1, 6)})
        PayComponent.objects.update_or_create(tenant=tenant, name="Basic Salary", defaults={"component_type": "earning", "taxable": True})
        payroll, _ = PayrollRun.objects.update_or_create(company=company, period_start=date(2026, 7, 1), period_end=date(2026, 7, 31), defaults={"status": "draft"})
        Payslip.objects.update_or_create(payroll_run=payroll, employee=employee, defaults={"gross": Decimal("2500"), "tax": Decimal("425"), "deductions": Decimal("75"), "net": Decimal("2000"), "tax_engine_result": {"engine": "demo", "jurisdiction": "ZW"}})

        project, _ = Project.objects.update_or_create(owner=users["taylee@me.com"], name="ERP Rollout", defaults={"description": "Demo implementation project connecting operations to accounting."})
        project.members.set(users.values())
        task, _ = Task.objects.update_or_create(project=project, title="Configure chart of accounts", defaults={"description": "Review and approve the seeded account structure.", "status": Task.IN_PROGRESS, "priority": Task.HIGH, "assigned_to": users["finance@taylee.me"], "due_date": timezone.now() + timedelta(days=7)})
        Milestone.objects.update_or_create(project=project, name="Finance go-live", defaults={"due_date": date(2026, 8, 31)})
        TimeEntry.objects.update_or_create(tenant=tenant, user=users["finance@taylee.me"], task=task, work_date=date(2026, 7, 21), defaults={"hours": Decimal("4.50"), "billable": True})
        lead, _ = Lead.objects.update_or_create(tenant=tenant, name="Bulawayo Distribution", defaults={"email": "info@byodistribution.demo", "status": "qualified"})
        Opportunity.objects.update_or_create(lead=lead, name="Inventory rollout", defaults={"value": Decimal("12000"), "stage": "proposal"})
        plan, _ = SaaSPlan.objects.update_or_create(name="Professional", defaults={"monthly_price": Decimal("199"), "limits": {"users": 50, "companies": 5}})
        TenantSubscription.objects.update_or_create(tenant=tenant, defaults={"plan": plan, "starts_on": date(2026, 7, 1), "status": "active"})

        self.stdout.write(self.style.SUCCESS("ERP demo data seeded successfully."))
        self.stdout.write("Demo login: taylee@me.com / Taylee03! (change this password outside development)")
