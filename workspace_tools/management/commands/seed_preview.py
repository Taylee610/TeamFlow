"""Repeatable, offline demo scenarios in the explicitly named preview workspace."""
import calendar
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from erp_foundation.models import Tenant, Membership, Currency, Company, FiscalYear, AccountingPeriod
from erp_foundation.services import workspace_roles
from erp_operations.models import SaaSPlan, TenantSubscription, UOM, Product, Warehouse, StockLevel, PurchaseOrder, PurchaseOrderLine
from projects.models import Project, Task
from chat.models import Conversation, ConversationParticipant, Message
from accounting.models import Account, Party, FinancialDocument, DocumentLine, BankAccount, BankTransaction
from accounting.workflows import post_document, record_payment
from workspace_tools import models as m


class Command(BaseCommand):
    help = 'Add extensive synthetic scenarios to Preview workspace; never sends email or payments.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace', type=int, required=True)
        parser.add_argument('--owner', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        tenant = Tenant.objects.get(pk=options['workspace'])
        if tenant.name != 'Preview workspace':
            raise CommandError('This seed is restricted to the workspace named Preview workspace.')
        owner = get_user_model().objects.get(email=options['owner'])
        if not Membership.objects.filter(tenant=tenant, user=owner, is_active=True).exists():
            raise CommandError('The owner must already belong to this preview workspace.')
        now, today = timezone.now(), timezone.localdate()
        common = {'tenant': tenant, 'created_by': owner}
        for j, state in enumerate(['up', 'down', 'unknown']):
            monitor, created = m.Monitor.objects.get_or_create(tenant=tenant, name=f'Demo · {state.title()} website', defaults={'created_by': owner, 'url': 'https://example.com', 'enabled': False, 'state': state, 'last_checked_at': now if state != 'unknown' else None})
            if created and state != 'unknown':
                for k in range(48): m.MonitorCheck.objects.create(monitor=monitor, checked_at=now-timedelta(minutes=5*k), is_up=not(state=='down' and k<6), status_code=503 if state=='down' and k<6 else 200, latency_ms=80+k*3, error='Synthetic incident' if state=='down' and k<6 else '')
        admin, member = workspace_roles(tenant)
        people = [owner]
        for name in ['Tariro', 'Kuda', 'Rudo', 'Farai', 'Nyasha']:
            user, created = get_user_model().objects.get_or_create(email=f'{name.lower()}.preview-{tenant.pk}@example.test', defaults={'first_name': name, 'email_verified': True})
            if created:
                user.set_unusable_password(); user.save(update_fields=['password'])
            Membership.objects.get_or_create(tenant=tenant, user=user, defaults={'role': member})
            people.append(user)
            m.NotificationPreference.objects.get_or_create(user=user, defaults={'email_notifications': False, 'period_reminders': False, 'approval_alerts': False})
        projects = []
        categories = ['Website launch', 'Month-end finance', 'Supplier onboarding', 'Warehouse stock count', 'Customer campaign', 'Support improvements']
        for index, name in enumerate(categories):
            project, _ = Project.objects.get_or_create(tenant=tenant, owner=owner, name=f'Demo · {name}', defaults={'description': 'Synthetic end-to-end scenario. Start with its tasks, review progress, and explore related tools.'})
            project.members.add(*people[1:])
            projects.append(project)
            for j, title in enumerate(['Gather requirements', 'Confirm scope and owner', 'Prepare first draft', 'Review outstanding issues', 'Request sign-off', 'Complete handover', 'Measure results', 'Resolve urgent blocker']):
                state = ['todo', 'drafting', 'in_review', 'done'][j % 4]
                task, created = Task.objects.get_or_create(project=project, title=f'{title} · {name}', defaults={'status': state, 'priority': ['low', 'medium', 'high'][j % 3], 'assigned_to': people[(index+j) % len(people)] if j != 7 else None, 'due_date': now + timedelta(days=j-3), 'description': f'Demo workflow step {j+1}: record your findings, request review, then move the task to Done.', 'labels': ['demo', name], 'story_points': [2, 3, 5, 8][j % 4]})
                if created and state == 'done':
                    Task.objects.filter(pk=task.pk).update(created_at=now-timedelta(days=12), completed_at=now-timedelta(days=1))
                if j == 0:
                    for step in ['Collect documents', 'Confirm acceptance criteria']:
                        Task.objects.get_or_create(project=project, parent=task, title=step, defaults={'labels': ['demo'], 'assigned_to': people[index]})
            # Balanced historical outcomes, known generation rule, no real-world accuracy claim.
            for j in range(16):
                late = (j + index) % 3 == 0 or j % 5 == 0
                created_day = now - timedelta(days=120-j*3-index)
                due = created_day + timedelta(days=2 if late else 12)
                completed = due + timedelta(days=2 if late else -2)
                task, created = Task.objects.get_or_create(project=project, title=f'Demo history {j+1:02} · {name}', defaults={'status': 'done', 'priority': 'high' if late else 'medium', 'due_date': due, 'story_points': 8 if late else 2, 'assigned_to': None if late else people[index], 'labels': ['demo', 'synthetic-history']})
                if created:
                    Task.objects.filter(pk=task.pk).update(created_at=created_day, completed_at=completed, updated_at=completed)
        clients = []
        for j in range(24):
            client, _ = m.Client.objects.get_or_create(tenant=tenant, name=f'Demo client {j+1:02}', defaults={'created_by': owner, 'company': ['Harare Studio', 'Bulawayo Supplies', 'Mutare Services'][j % 3], 'email': f'client{j+1}@example.test', 'stage': ['lead', 'active', 'completed', 'archived'][j % 4], 'notes': 'Synthetic client: review requirements → connect project → deliver → invoice.'})
            if j % 4 in (1, 2): client.projects.add(projects[j % 6])
            clients.append(client)
        for i, title in enumerate(['Daily planning', 'Review cash position', 'Study accounting basics', 'Follow up with clients']):
            habit, _ = m.Habit.objects.get_or_create(tenant=tenant, created_by=owner, name=f'Demo · {title}')
            for j in range(21): m.HabitLog.objects.get_or_create(habit=habit, day=today-timedelta(days=j), defaults={'completed': (j+i) % 5 != 0})
        for title, items in [('Finance basics', [('What is a receivable?', 'Money owed by a customer.'), ('What does a posted journal require?', 'Equal debits and credits.'), ('What is a partial payment?', 'A payment below the outstanding balance.'), ('What is reconciliation?', 'Matching external records to the ledger.')]), ('Project delivery', [('When is a task done?', 'When its acceptance criteria are met.'), ('What is a blocker?', 'An issue preventing progress.'), ('What is a milestone?', 'A meaningful delivery checkpoint.'), ('Why record time?', 'To understand effort and billable work.')])]:
            deck, _ = m.Deck.objects.get_or_create(tenant=tenant, name=f'Demo · {title}', defaults={'created_by': owner, 'shared': True})
            for j, (question, answer) in enumerate(items):
                card, _ = m.Flashcard.objects.get_or_create(deck=deck, question=question, defaults={**common, 'answer': answer})
                m.CardProgress.objects.get_or_create(card=card, user=owner, defaults={'due_at': now+timedelta(days=j-2), 'reviews': j, 'interval_days': j})
        for name in ['Client brief', 'Delivery feedback', 'Supplier application']:
            fields = [{'key': 'name', 'label': 'Name', 'type': 'text', 'required': True}, {'key': 'email', 'label': 'Email', 'type': 'email', 'required': True}, {'key': 'message', 'label': 'Message', 'type': 'textarea', 'required': True}]
            form, _ = m.Form.objects.get_or_create(tenant=tenant, title=f'Demo · {name}', defaults={'created_by': owner, 'fields': fields, 'description': 'Demo form; publish when ready to test the public submission flow.'})
            if not form.responses.exists():
                for j in range(12): m.FormResponse.objects.create(form=form, version=1, schema=fields, answers={'name': f'Demo visitor {j+1}', 'email': f'visitor{j+1}@example.test', 'message': ['Please send a quotation.', 'The delivery was helpful.', 'Can we schedule a call?'][j % 3]})
        widget, _ = m.FeedbackWidget.objects.get_or_create(tenant=tenant, name='Demo · Website feedback', defaults={'created_by': owner, 'allowed_origins': ['http://localhost:5181']})
        for j, message in enumerate(['Please improve the mobile navigation.', 'Could invoices show payment history?', 'The client portal is helpful.', 'Add a delivery checklist.', 'I need help resetting access.', 'The dashboard is easy to follow.']):
            m.Feedback.objects.get_or_create(widget=widget, message=message, defaults={'email': f'visitor{j}@example.test', 'status': ['new', 'read', 'archived'][j % 3], 'task': projects[0].tasks.filter(parent__isnull=True).first() if j == 1 else None})
        m.LinkProfile.objects.get_or_create(slug=f'demo-preview-{tenant.pk}', defaults={**common, 'title': 'Demo client services', 'bio': 'A sample link page. Publish it to try the public view.', 'links': [{'label': 'Company website', 'url': 'https://example.com'}, {'label': 'Portfolio', 'url': 'https://example.com/portfolio'}]})
        pages = [('Start here', 'Demo walkthrough: CRM → project → tasks → time → approval → invoice → payment. All figures and people are synthetic.'), ('Delivery checklist', 'Confirm requirements. Prepare a draft. Request review. Complete handover. Record lessons.'), ('Finance workflow', 'Create a draft invoice or bill. Post it to the ledger. Record partial or full payment. Inspect journals and trial balance.'), ('Taylee ML', 'Generate a plan, then inspect deadline risk. Demo history is synthetic; validation on it does not establish real-world performance.')]
        for title, body in pages:
            page, created = m.WikiPage.objects.get_or_create(tenant=tenant, title=f'Demo · {title}', defaults={'created_by': owner, 'body': body})
            if created: m.WikiRevision.objects.create(page=page, title=page.title, body=body, actor=owner)
        for task in [p.tasks.filter(parent__isnull=True).exclude(title__startswith='Demo history').first() for p in projects]:
            for k in range(5): m.TimeLog.objects.get_or_create(tenant=tenant, created_by=owner, task=task, work_date=today-timedelta(days=k), defaults={'hours': Decimal('1.5')+Decimal(k)/2, 'note': 'Demo delivery work', 'billable': k % 2 == 0})
        for j, state in enumerate(['pending', 'approved', 'rejected']):
            approval, created = m.ApprovalFile.objects.get_or_create(tenant=tenant, title=f'Demo · Client deliverable {j+1}', defaults={'created_by': owner, 'client': clients[j], 'client_user': owner, 'status': state, 'comment': 'Demo review scenario', 'approved_by': owner if state == 'approved' else None, 'approved_at': now if state == 'approved' else None})
            if created:
                approval.file.save(f'demo-deliverable-{j+1}.txt', ContentFile('Synthetic client deliverable. Review scope and approve or request changes.\n'), save=True)
                m.ApprovalVersion.objects.create(approval=approval, version=1, title=approval.title, file=approval.file.name, status=state, comment=approval.comment)
        for project in projects[:3]:
            channel, _ = Conversation.objects.get_or_create(tenant=tenant, name=f'Demo · {project.name}', type='channel', defaults={'project': project})
            for user in people: ConversationParticipant.objects.get_or_create(conversation=channel, user=user)
            for j, body in enumerate(['Welcome! Review the project brief first.', 'The first draft is ready for review.', 'Please check outstanding tasks before handover.', 'I have recorded the demo time entries.', 'Next step: approval and invoice.']): Message.objects.get_or_create(conversation=channel, body=body, defaults={'sender': people[j]})
        self.finance(tenant, owner, today)
        limits = {'ai': 10000, 'clients': 500, 'seats': 20}
        plan, _ = SaaSPlan.objects.get_or_create(name=f'Preview demo {tenant.pk}', defaults={'monthly_price': 0, 'limits': limits, 'is_public': False})
        TenantSubscription.objects.update_or_create(tenant=tenant, defaults={'plan': plan, 'starts_on': today, 'status': 'active'})
        self.stdout.write(self.style.SUCCESS(f'Demo scenarios ready in workspace {tenant.pk}: 6 projects, 48 workflow tasks, 96 historical tasks, 24 clients, forms, habits, cards, reviews, chat and finance. Reruns preserve existing demo edits.'))

    def finance(self, tenant, owner, today):
        currency, _ = Currency.objects.get_or_create(code='USD', defaults={'name': 'US Dollar', 'symbol': '$'})
        company, _ = Company.objects.get_or_create(tenant=tenant, legal_name='Demo Operations (synthetic)', defaults={'name': 'Demo Operations', 'base_currency': currency})
        year, _ = FiscalYear.objects.get_or_create(company=company, name=str(today.year), defaults={'starts_on': date(today.year, 1, 1), 'ends_on': date(today.year, 12, 31)})
        for month in range(1, 13): AccountingPeriod.objects.get_or_create(fiscal_year=year, name=calendar.month_name[month], defaults={'starts_on': date(today.year, month, 1), 'ends_on': date(today.year, month, calendar.monthrange(today.year, month)[1])})
        for code, name, kind in [('1000', 'Cash', 'asset'), ('1100', 'Receivables', 'asset'), ('1200', 'Input tax', 'asset'), ('2000', 'Payables', 'liability'), ('2100', 'Output tax', 'liability'), ('4000', 'Revenue', 'revenue'), ('5000', 'Expenses', 'expense')]: Account.objects.get_or_create(company=company, code=code, defaults={'tenant': tenant, 'name': name, 'account_type': kind})
        for j in range(20):
            kind = 'invoice' if j < 12 else 'bill'
            party, _ = Party.objects.get_or_create(tenant=tenant, company=company, name=f'Demo {"customer" if j<12 else "supplier"} {j%6+1}', kind='customer' if j<12 else 'supplier', defaults={'email': f'finance{j}@example.test'})
            day = max(date(today.year, 1, 1), today-timedelta(days=40-j))
            total = Decimal(100+j*35)
            doc, created = FinancialDocument.objects.get_or_create(company=company, document_type=kind, number=f'DEMO-{kind.upper()}-{j+1:03}', defaults={'tenant': tenant, 'party': party, 'issue_date': day, 'due_date': day+timedelta(days=14), 'currency': currency, 'subtotal': total, 'total': total})
            if created:
                DocumentLine.objects.create(document=doc, description='Synthetic delivery services' if kind == 'invoice' else 'Synthetic supplier materials', quantity=1, unit_price=total)
                if j % 4:
                    post_document(doc, owner)
                    if j % 4 in (2, 3): record_payment(doc, owner, total if j%4 == 3 else total/2, f'DEMO-PAY-{j+1:03}', min(today, day+timedelta(days=5)))
        uom, _ = UOM.objects.get_or_create(tenant=tenant, code='DEMO-EA', defaults={'name': 'Each'})
        warehouse, _ = Warehouse.objects.get_or_create(company=company, code='DEMO-MAIN', defaults={'name': 'Demo Harare warehouse'})
        supplier = Party.objects.filter(company=company, kind='supplier').first()
        for j in range(8):
            product, _ = Product.objects.get_or_create(tenant=tenant, sku=f'DEMO-{j+1:03}', defaults={'name': f'Demo product {j+1}', 'uom': uom})
            StockLevel.objects.get_or_create(product=product, warehouse=warehouse, defaults={'quantity': 10+j*7})
            order, _ = PurchaseOrder.objects.get_or_create(company=company, number=f'DEMO-PO-{j+1:03}', defaults={'supplier': supplier, 'order_date': today, 'status': ['draft', 'approved', 'closed'][j%3]})
            PurchaseOrderLine.objects.get_or_create(order=order, product=product, defaults={'quantity': 10, 'unit_price': 15+j})
        bank, _ = BankAccount.objects.get_or_create(company=company, name='Demo bank statement', defaults={'account_number': 'SYNTHETIC-0001', 'currency': currency, 'ledger_account': Account.objects.get(company=company, code='1000')})
        for j in range(10): BankTransaction.objects.get_or_create(bank_account=bank, reference=f'DEMO-BANK-{j+1:03}', defaults={'transaction_date': today-timedelta(days=j), 'amount': Decimal(100+j*10)*(1 if j%2 else -1), 'imported_data': {'demo': True}})
