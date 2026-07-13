from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def _display_name(user):
    return user.first_name or user.email


def _send(template_base, subject, to_email, context):
    text_body = render_to_string(f'notifications/{template_base}.txt', context)
    html_body = render_to_string(f'notifications/{template_base}.html', context)
    message = EmailMultiAlternatives(subject=subject, body=text_body, to=[to_email])
    message.attach_alternative(html_body, 'text/html')
    message.send()


def send_task_assigned_email(task, assigned_by=None):
    if not task.assigned_to or not task.assigned_to.email:
        return

    context = {
        'assignee_name': _display_name(task.assigned_to),
        'assigner_name': _display_name(assigned_by) if assigned_by else 'Someone',
        'project_name': task.project.name,
        'task_title': task.title,
        'due_date': task.due_date,
        'task_url': f'{settings.FRONTEND_URL}/projects/{task.project_id}',
    }
    _send(
        'task_assigned',
        subject=f'You were assigned: {task.title}',
        to_email=task.assigned_to.email,
        context=context,
    )


def send_due_date_reminder_email(task):
    if not task.assigned_to or not task.assigned_to.email:
        return

    context = {
        'assignee_name': _display_name(task.assigned_to),
        'project_name': task.project.name,
        'task_title': task.title,
        'due_date': task.due_date,
        'task_url': f'{settings.FRONTEND_URL}/projects/{task.project_id}',
    }
    _send(
        'due_date_reminder',
        subject=f'Due soon: {task.title}',
        to_email=task.assigned_to.email,
        context=context,
    )
