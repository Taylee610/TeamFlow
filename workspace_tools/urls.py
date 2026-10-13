from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .billing import BillingView, CheckoutView, PaymentStatusView, PaynowResultView, TrialView

router = DefaultRouter()
for prefix, view in [('monitors', views.MonitorViewSet), ('clients', views.ClientViewSet), ('profiles', views.LinkProfileViewSet),
                     ('habits', views.HabitViewSet), ('decks', views.DeckViewSet), ('cards', views.FlashcardViewSet),
                     ('forms', views.FormViewSet), ('widgets', views.FeedbackWidgetViewSet), ('feedback', views.FeedbackViewSet),
                     ('wiki', views.WikiViewSet), ('approvals', views.ApprovalViewSet), ('time', views.TimeLogViewSet)]:
    router.register(prefix, view, basename=prefix)

urlpatterns = [path('widget.js', views.widget_script), path('', include(router.urls)), path('preferences/', views.PreferencesView.as_view()), path('jobs/', views.JobsView.as_view()),
               path('billing/', BillingView.as_view()), path('billing/checkout/', CheckoutView.as_view()),
               path('billing/trial/', TrialView.as_view()),
               path('billing/payments/<int:pk>/', PaymentStatusView.as_view()), path('billing/paynow/result/', PaynowResultView.as_view()),
               path('public/profiles/<slug:slug>/', views.PublicProfileView.as_view()),
               path('public/forms/<uuid:public_id>/', views.PublicFormView.as_view()),
               path('public/widgets/<uuid:public_id>/', views.PublicFeedbackView.as_view())]
