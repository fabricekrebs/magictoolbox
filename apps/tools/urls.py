"""URL configuration for tools app (web interface)."""

from django.urls import path

from . import views

app_name = "tools"

urlpatterns = [
    path("", views.tool_list, name="tool_list"),
    path("my-conversions/", views.my_conversions, name="my_conversions"),
    path(
        "conversions/<uuid:execution_id>/delete/", views.delete_conversion, name="delete_conversion"
    ),
    path("conversions/delete-all/", views.delete_all_conversions, name="delete_all_conversions"),
    path("<slug:tool_slug>/", views.tool_detail, name="tool_detail"),
]
