from django.urls import path

from . import views

app_name = "management"

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/<int:pk>/", views.case_detail, name="case_detail"),
    path("cases/<int:pk>/assign/", views.case_assign, name="case_assign"),
    path("cases/<int:pk>/reject/", views.case_reject, name="case_reject"),
]