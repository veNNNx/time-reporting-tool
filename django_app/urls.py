from django.contrib.auth import views as auth_views
from django.urls import path

from . import auth, views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("monthly-report", views.admin_monthly_report, name="monthly-report"),
    path("employer-report", views.admin_employer_report, name="employer-report"),
    path("machines-report", views.admin_machines_report, name="machines-report"),
    path(
        "login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"
    ),
    path("logout/", auth.logout_view, name="logout"),
]
