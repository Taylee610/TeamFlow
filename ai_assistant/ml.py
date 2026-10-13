"""Small, transparent local models. No customer data leaves this process."""
import math
import re
from collections import Counter
from functools import lru_cache
from django.utils import timezone

TRAINING = {
    'finance': ['review overdue customer invoices payments receivables', 'prepare month end close reconcile bank transactions', 'budget expenses cash accounting supplier bills'],
    'inventory': ['plan warehouse stock count inventory products', 'receive supplier goods purchase order shipment', 'audit stock quantities reorder warehouse items'],
    'onboarding': ['create supplier onboarding checklist vendor', 'welcome new employee team induction training', 'onboard client customer collect requirements access'],
    'engineering': ['set up CI backend tests deployment pipeline', 'fix website bug error outage security', 'build feature API application release software'],
    'marketing': ['launch campaign social content newsletter', 'publish website landing page brand copy', 'plan marketing customer feedback promotion'],
}
CHECKLISTS = {
    'finance': ['Collect source documents and balances', 'Review exceptions and outstanding items', 'Reconcile totals and request approval', 'Record the outcome and follow-up actions'],
    'inventory': ['Confirm products, locations and count owners', 'Count stock and record discrepancies', 'Review discrepancies before adjustments', 'Approve results and update the stock register'],
    'onboarding': ['Confirm requirements and responsible owner', 'Collect required documents and access requests', 'Complete introduction and training', 'Confirm readiness and document sign-off'],
    'engineering': ['Define acceptance criteria and reproduce the issue', 'Implement the change and review it', 'Run relevant tests and resolve failures', 'Prepare release notes and verify deployment'],
    'marketing': ['Confirm audience, goals and message', 'Prepare content and request review', 'Publish approved material', 'Measure results and record improvements'],
    'general': ['Clarify the outcome and acceptance criteria', 'Assign an owner and gather requirements', 'Complete the work and request review', 'Record the outcome and follow-up actions'],
}

def tokens(text):
    return re.findall(r'[a-z]{2,}', text.lower())

@lru_cache(maxsize=1)
def intent_model():
    counts = {label: Counter(tokens(' '.join(rows))) for label, rows in TRAINING.items()}
    vocabulary = set().union(*(set(c) for c in counts.values()))
    return counts, vocabulary

def plan(prompt):
    counts, vocabulary = intent_model()
    words = [w for w in tokens(prompt) if w in vocabulary]
    scores = {label: sum(math.log((count[w] + 1) / (sum(count.values()) + len(vocabulary))) for w in words) for label, count in counts.items()}
    best = max(scores, key=scores.get)
    weights = {label: math.exp(score - max(scores.values())) for label, score in scores.items()}
    confidence = weights[best] / sum(weights.values())
    label = best if words and confidence >= .40 else 'general'
    urgent = any(w in tokens(prompt) for w in ['urgent', 'outage', 'overdue', 'critical'])
    return {'description': prompt.strip(), 'subtasks': CHECKLISTS[label], 'priority': 'high' if urgent else 'medium', 'due_date': None,
            'engine': 'local_ml', 'intent': label, 'confidence': round(confidence, 3),
            'model_note': 'Naive Bayes intent classifier trained on 15 curated examples. Checklist and priority are templates/rules; review before saving.'}

def features(task):
    lead = max(0, (task.due_date - task.created_at).total_seconds() / 86400)
    return [1., min(lead, 60) / 30, float(task.priority == 'high'), min(task.story_points or 0, 20) / 10, float(task.assigned_to_id is None)]

def probability(weights, row):
    z = max(-30, min(30, sum(a*b for a, b in zip(weights, row))))
    return 1 / (1 + math.exp(-z))

def fit(rows):
    weights = [0.] * 5
    for _ in range(400):
        gradients = [0.] * 5
        for row, label in rows:
            error = probability(weights, row) - label
            for j in range(5):
                gradients[j] += error * row[j]
        weights = [w - .2 * (g / len(rows) + (.02 * w if j else 0)) for j, (w, g) in enumerate(zip(weights, gradients))]
    return weights

def project_insights(project, accessible_projects):
    from projects.models import Task
    history = list(Task.objects.filter(project__in=accessible_projects, status='done', due_date__isnull=False, completed_at__isnull=False).order_by('-completed_at', '-id')[:2000])
    demo = project.name.startswith('Demo · ')
    history = [t for t in history if ('demo' in (t.labels or [])) == demo and t.completed_at >= t.created_at and t.due_date >= t.created_at]
    history.sort(key=lambda t: (t.completed_at, t.pk))
    # Completion timestamps provide labels only. Mutable historical fields are
    # current stored values; immutable feature snapshots are a future improvement.
    rows = [(features(t), int(t.completed_at > t.due_date)) for t in history]
    positives = sum(y for _, y in rows)
    ready = len(rows) >= 30 and positives >= 5 and len(rows) - positives >= 5
    split = int(len(rows) * .8)
    validation = None
    weights = None
    if ready and len({y for _, y in rows[:split]}) == 2:
        heldout_weights = fit(rows[:split])
        heldout = rows[split:]
        validation = {'samples': len(heldout), 'accuracy': round(sum((probability(heldout_weights, x) >= .5) == bool(y) for x, y in heldout) / len(heldout), 3),
                      'baseline_accuracy': round(max(sum(y for _, y in heldout), sum(1-y for _, y in heldout)) / len(heldout), 3)}
        weights = fit(rows)
    now = timezone.now()
    tasks = list(project.tasks.all())
    open_tasks = [t for t in tasks if t.status != 'done']
    risks = []
    for task in open_tasks:
        late = bool(task.due_date and task.due_date < now)
        score = round(probability(weights, features(task)), 3) if weights and task.due_date and not late else None
        risks.append({'id': task.pk, 'title': task.title, 'already_overdue': late, 'late_probability': score, 'due_date': task.due_date,
                      'reason': 'Deadline has passed' if late else 'No due date' if not task.due_date else 'Learned from lead time, priority, size and assignment' if weights else 'More completed history is needed'})
    risks.sort(key=lambda r: (r['already_overdue'], r['late_probability'] or 0), reverse=True)
    done = len(tasks) - len(open_tasks)
    overdue = sum(r['already_overdue'] for r in risks)
    return {'summary': f'{project.name}: {done} of {len(tasks)} tasks completed. {len(open_tasks)} remain open; {overdue} are overdue. Review the overdue and highest-risk tasks with their owners.',
            'engine': 'local_ml', 'risks': risks, 'model': {'available': bool(weights), 'training_samples': len(rows), 'late_samples': positives, 'validation': validation,
            'demo_history': demo, 'note': 'Experimental logistic regression; scores are estimates, not calibrated guarantees. Minimum 30 dated completions and 5 examples of each outcome. Historical fields use current stored values; demo and real history are kept separate.'}}
