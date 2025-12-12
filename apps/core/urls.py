"""URL configuration for core app."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health_check, name="health"),
    path("health/ready/", views.readiness_check, name="readiness"),
    path("troubleshooting/", views.troubleshooting, name="troubleshooting"),
    path("troubleshooting/cleanup/", views.cleanup_all_data, name="cleanup_all_data"),
]
