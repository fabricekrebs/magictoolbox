"""URL configuration for authentication endpoints."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = "authentication"

urlpatterns = [
    # Web interface
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    # API endpoints (keep for API access)
    path("api/register/", views.RegisterView.as_view(), name="api_register"),
    path("api/login/", views.CustomTokenObtainPairView.as_view(), name="api_token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("api/profile/", views.ProfileView.as_view(), name="api_profile"),
    path("api/password/change/", views.PasswordChangeView.as_view(), name="api_password_change"),
]
