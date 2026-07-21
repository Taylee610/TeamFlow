from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from accounting.models import FinancialDocument, JournalEntry, Party
from erp_foundation.models import Company, Currency, Tenant

class UOM(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); code = models.CharField(max_length=20); name = models.CharField(max_length=80)
class Product(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); sku = models.CharField(max_length=60); name = models.CharField(max_length=180)
    uom = models.ForeignKey(UOM, on_delete=models.PROTECT); is_service = models.BooleanField(default=False)
class Warehouse(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE); code = models.CharField(max_length=30); name = models.CharField(max_length=120)
class StockMovement(models.Model):
    TYPES = [(x, x.title()) for x in ("receipt", "issue", "transfer", "adjustment")]
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT); product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT); movement_type = models.CharField(max_length=12, choices=TYPES)
    quantity = models.DecimalField(max_digits=19, decimal_places=4); unit_cost = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    occurred_at = models.DateTimeField(); reference = models.CharField(max_length=100); journal_entry = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)
class StockLevel(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE); warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    class Meta: constraints = [models.UniqueConstraint(fields=["product", "warehouse"], name="unique_stock_level")]
class PriceList(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); name = models.CharField(max_length=100); currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="items"); product = models.ForeignKey(Product, on_delete=models.CASCADE); price = models.DecimalField(max_digits=19, decimal_places=4)

class PurchaseOrder(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); supplier = models.ForeignKey(Party, on_delete=models.PROTECT)
    number = models.CharField(max_length=60); order_date = models.DateField(); status = models.CharField(max_length=20, default="draft")
class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines"); product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=19, decimal_places=4); unit_price = models.DecimalField(max_digits=19, decimal_places=4)
class GoodsReceipt(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="receipts"); warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    number = models.CharField(max_length=60); received_at = models.DateTimeField(); journal_entry = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)

class Lead(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); name = models.CharField(max_length=180); email = models.EmailField(blank=True); status = models.CharField(max_length=30, default="new")
class Opportunity(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE); name = models.CharField(max_length=180); value = models.DecimalField(max_digits=19, decimal_places=4); stage = models.CharField(max_length=30)
class SalesOrder(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); customer = models.ForeignKey(Party, on_delete=models.PROTECT); number = models.CharField(max_length=60)
    order_date = models.DateField(); status = models.CharField(max_length=20, default="draft"); invoice = models.ForeignKey(FinancialDocument, null=True, blank=True, on_delete=models.PROTECT)
class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines"); product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=19, decimal_places=4); unit_price = models.DecimalField(max_digits=19, decimal_places=4)
class Quotation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); customer = models.ForeignKey(Party, on_delete=models.PROTECT); number = models.CharField(max_length=60); valid_until = models.DateField()
class Contract(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); customer = models.ForeignKey(Party, on_delete=models.PROTECT); name = models.CharField(max_length=160)
    starts_on = models.DateField(); ends_on = models.DateField(null=True, blank=True); billing_frequency = models.CharField(max_length=30, blank=True)

class Department(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE); name = models.CharField(max_length=120)
class Position(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE); title = models.CharField(max_length=120)
class Employee(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    employee_number = models.CharField(max_length=40); department = models.ForeignKey(Department, on_delete=models.PROTECT); position = models.ForeignKey(Position, on_delete=models.PROTECT); hired_on = models.DateField()
class PayComponent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); name = models.CharField(max_length=120); component_type = models.CharField(max_length=12, choices=[("earning", "Earning"), ("deduction", "Deduction")]); taxable = models.BooleanField(default=True)
class PayrollRun(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT); period_start = models.DateField(); period_end = models.DateField(); status = models.CharField(max_length=20, default="draft"); journal_entry = models.ForeignKey(JournalEntry, null=True, blank=True, on_delete=models.PROTECT)
class Payslip(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.PROTECT, related_name="payslips"); employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    gross = models.DecimalField(max_digits=19, decimal_places=4); tax = models.DecimalField(max_digits=19, decimal_places=4); deductions = models.DecimalField(max_digits=19, decimal_places=4); net = models.DecimalField(max_digits=19, decimal_places=4); tax_engine_result = models.JSONField(default=dict, blank=True)
class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT); leave_type = models.CharField(max_length=40); starts_on = models.DateField(); ends_on = models.DateField(); status = models.CharField(max_length=20, default="pending")
class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE); leave_type = models.CharField(max_length=40); balance = models.DecimalField(max_digits=8, decimal_places=2)

class TimeEntry(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    task = models.ForeignKey("projects.Task", on_delete=models.PROTECT, related_name="time_entries"); work_date = models.DateField(); hours = models.DecimalField(max_digits=6, decimal_places=2)
    billable = models.BooleanField(default=False); invoice = models.ForeignKey(FinancialDocument, null=True, blank=True, on_delete=models.PROTECT)
class Milestone(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="milestones"); name = models.CharField(max_length=120); due_date = models.DateField(null=True, blank=True)

class Attachment(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); file = models.FileField(upload_to="erp_attachments/%Y/%m/"); original_name = models.CharField(max_length=255); scan_status = models.CharField(max_length=20, default="pending")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE); object_id = models.PositiveBigIntegerField(); content_object = GenericForeignKey()
class ApprovalChain(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); name = models.CharField(max_length=120); module = models.CharField(max_length=60); rules = models.JSONField(default=list)
class ApprovalRequest(models.Model):
    chain = models.ForeignKey(ApprovalChain, on_delete=models.PROTECT); requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT); status = models.CharField(max_length=20, default="pending")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE); object_id = models.PositiveBigIntegerField(); content_object = GenericForeignKey()
class Webhook(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); event = models.CharField(max_length=80); url = models.URLField(); secret = models.CharField(max_length=255); is_active = models.BooleanField(default=True)
class SavedReport(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE); owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE); name = models.CharField(max_length=120); definition = models.JSONField(default=dict)
class SaaSPlan(models.Model):
    name = models.CharField(max_length=80); monthly_price = models.DecimalField(max_digits=12, decimal_places=2); limits = models.JSONField(default=dict)
class TenantSubscription(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE); plan = models.ForeignKey(SaaSPlan, on_delete=models.PROTECT); starts_on = models.DateField(); status = models.CharField(max_length=20, default="active")
