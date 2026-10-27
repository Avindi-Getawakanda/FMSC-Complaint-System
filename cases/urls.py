from django.urls import path
from . import views

urlpatterns = [
    path("submit/", views.submit_case, name="submit_case"),
    path("my-cases/", views.my_cases, name="my_cases"),
    path("my-cases/<int:case_id>/", views.case_detail, name="case_detail"),
]