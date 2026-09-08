from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Permission(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="permissions")
    code = models.CharField(max_length=120)
    module = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    conditions = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "code"], name="unique_tenant_permission")]


class Role(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=80)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "name"], name="unique_tenant_role")]


class Membership(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "user"], name="unique_tenant_member")]

    def clean(self):
        if self.role_id and self.tenant_id != self.role.tenant_id:
            raise ValidationError("Role must belong to the membership tenant.")

    def has_permission(self, code, **context):
        if not self.is_active or not self.tenant.is_active or self.role.tenant_id != self.tenant_id:
            return False
        permission = self.role.permissions.filter(code=code).first()
        if not permission:
            return False
        maximum = permission.conditions.get("maximum_amount")
        return maximum is None or context.get("amount", 0) <= maximum


class WorkspaceInvitation(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    token_digest = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Currency(models.Model):
    code = models.CharField(primary_key=True, max_length=3)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)

    def __str__(self):
        return self.code


class Company(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=180)
    legal_name = models.CharField(max_length=220)
    registration_number = models.CharField(max_length=80, blank=True)
    tax_number = models.CharField(max_length=80, blank=True)
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["tenant", "legal_name"], name="unique_tenant_company")]


class FiscalYear(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="fiscal_years")
    name = models.CharField(max_length=40)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_closed = models.BooleanField(default=False)


class AccountingPeriod(models.Model):
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name="periods")
    name = models.CharField(max_length=40)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_closed = models.BooleanField(default=False)


class ExchangeRate(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="exchange_rates")
    from_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="rates_from")
    to_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="rates_to")
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    effective_on = models.DateField()


class AuditLog(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    object_type = models.CharField(max_length=120)
    object_id = models.CharField(max_length=80)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit logs are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit logs cannot be deleted.")
