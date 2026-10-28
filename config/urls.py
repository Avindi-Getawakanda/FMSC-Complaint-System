
from django.contrib import admin
from django.urls import path, include
from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),

    #  Management Module
    path("management/", include("management.urls")),

    # Authentication and User Roles
    path("accounts/", include("accounts.urls")),

    # Complaint and Suggestion Submission
    path("cases/", include("cases.urls")),

    # Public welcome page
    path("", account_views.home_view, name="home"),
]
