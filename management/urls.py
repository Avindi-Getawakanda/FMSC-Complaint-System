from django.urls import path

from . import views

app_name = "management"

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/<int:pk>/", views.case_detail, name="case_detail"),
    path("cases/<int:pk>/assign/", views.case_assign, name="case_assign"),
    path("cases/<int:pk>/reject/", views.case_reject, name="case_reject"),

    path(
        "authorities/",
        views.authority_list,
        name="authority_list",
    ),
    path(
        "authorities/add/",
        views.authority_create,
        name="authority_create",
    ),
    path(
        "authorities/<int:pk>/edit/",
        views.authority_edit,
        name="authority_edit",
    ),

        path(
        "assigned-cases/",
        views.assigned_case_list,
        name="assigned_case_list",
    ),

        path(
        "assigned-cases/<int:pk>/",
        views.assigned_case_detail,
        name="assigned_case_detail",
    ),

        path(
        "assigned-cases/<int:pk>/progress/",
        views.case_progress_update,
        name="case_progress_update",
    ),
]