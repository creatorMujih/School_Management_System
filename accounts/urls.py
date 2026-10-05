from django.urls import path
from . import views

urlpatterns = [
    path(
        "admission/", views.admission_application, name="admission_application"
        ),
    path(
        "admission/success/<str:application_number>/",
        views.admission_success,
        name="admission_success",
        ),
        ]
