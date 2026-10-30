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
    path(
        "teacher/results/enter/",
        views.teacher_result_entry,
        name="teacher_result_entry",
        ),
    path(
        "teacher/results/drafts/",
        views.teacher_draft_results,
        name="teacher_draft_results",
        ),
    path(
        "teacher/results/drafts/<int:result_id>/edit/",
        views.teacher_edit_draft_result,
        name="teacher_edit_draft_result",
        ),
    path(
        "admin/results/publication/",
        views.admin_result_publication,
        name="admin_result_publication",
        ),
    ]