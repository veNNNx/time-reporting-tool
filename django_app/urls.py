from django.contrib.auth import views as auth_views
from django.urls import path

from . import auth, views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"
    ),
    path("logout/", auth.logout_view, name="logout"),
]
