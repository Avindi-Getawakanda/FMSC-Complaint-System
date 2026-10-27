from django.urls import path
from . import views

urlpatterns = [
    path("submit/", views.submit_case, name="submit_case"),
]