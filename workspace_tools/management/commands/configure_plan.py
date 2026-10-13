import json
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from erp_operations.models import SaaSPlan
from workspace_tools.billing import DEFAULT_LIMITS


class Command(BaseCommand):
    help='Configure an offered plan. Prices are explicit operator inputs; this never initiates a payment.'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True)
        parser.add_argument('--price', required=True)
        parser.add_argument('--limits', help='Path to a JSON file of module limits.')

    def handle(self, *args, **options):
        try:
            price=Decimal(options['price'])
            if not price.is_finite() or price<0 or price>=Decimal('10000000000') or price!=price.quantize(Decimal('0.01')):
                raise ValueError('Use a nonnegative price with at most two decimal places.')
            if not options['name'].strip() or len(options['name'])>80:
                raise ValueError('Use a nonempty plan name of up to 80 characters.')
            limits=dict(DEFAULT_LIMITS)
            if options['limits']:
                from pathlib import Path
                overrides=json.loads(Path(options['limits']).read_text(encoding='utf-8'))
                if not isinstance(overrides,dict) or set(overrides)-set(DEFAULT_LIMITS) or any(type(x) is not int or not 0<=x<=100000 for x in overrides.values()):
                    raise ValueError('Limits must be supported module names with integer values from 0 to 100000.')
                limits.update(overrides)
        except (ValueError,InvalidOperation,OSError) as exc:
            raise CommandError(str(exc))
        plan=SaaSPlan.objects.filter(name=options['name']).first()
        if plan:
            plan.monthly_price,plan.limits,plan.is_public,plan.currency=price,limits,True,'USD'
            plan.save()
        else:
            plan=SaaSPlan.objects.create(name=options['name'],monthly_price=price,limits=limits,is_public=True,currency='USD')
        self.stdout.write(f'Configured plan {plan.pk}: {plan.name}.')
