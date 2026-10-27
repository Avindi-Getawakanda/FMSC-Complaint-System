
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Avindi's Management Module
    path("management/", include("management.urls")),

    # Authentication and User Roles
    path("accounts/", include("accounts.urls")),

    # Complaint and Suggestion Submission
    path("cases/", include("cases.urls")),

    # Redirect homepage to login
    path(
        "",
        RedirectView.as_view(
            pattern_name="login",
            permanent=False
        ),
    ),
]
