from accounts.models import AssessmentConfiguration
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AdmissionApplicationForm, TeacherResultEntryForm, ComponentScoreEntryForm
from .services import create_admission_application, create_draft_result, get_teacher_draft_results, update_draft_result


def admission_application(request):
    if request.method == "GET":
        form = AdmissionApplicationForm()

        return render(request, "accounts/admission_application.html", {"form": form})

    if request.method == "POST":
        form = AdmissionApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            data = form.cleaned_data
            application = create_admission_application(data)
        

        return render(
            request,
            "accounts/admission_application.html",
            {"form": form}
)
    
    return redirect(
        "admission_success",
        application_number=application.application_number,
        )

def admission_success(request, application_number):
    return render(
        request, 
        "accounts/admission_success.html",
        {"application_number": application_number},
        )


@login_required
def teacher_result_entry(request):
    if request.user.role != "teacher":
        raise PermissionDenied(
            "Only teachers can enter results."
        )

    configuration = AssessmentConfiguration.objects.filter(
        is_active=True
    ).first()

    if configuration is None:
        configuration_error = (
            "There is no active assessment configuration."
        )
        component_form = None
    else:
        configuration_error = None
        component_form = ComponentScoreEntryForm(
            configuration,
            request.POST if request.method == "POST" else None,
        )

    entry_form = TeacherResultEntryForm(
        request.user,
        request.POST if request.method == "POST" else None,
    )

    if request.method == "POST" and component_form is not None:
        if entry_form.is_valid() and component_form.is_valid():
            scores = {
                int(field_name.removeprefix("component_")): score
                for field_name, score
                in component_form.cleaned_data.items()
                if field_name.startswith("component_")
            }

            try:
                result = create_draft_result(
                    request.user,
                    entry_form.cleaned_data["enrollment"],
                    entry_form.cleaned_data["subject"],
                    entry_form.cleaned_data["term"],
                    scores,
                )
            except ValidationError as exc:
                entry_form.add_error(None, exc)
            else:
                return render(
                    request,
                    "accounts/teacher_result_success.html",
                    {"result": result},
                )

    return render(
        request,
        "accounts/teacher_result_entry.html",
        {
            "entry_form": entry_form,
            "component_form": component_form,
            "configuration_error": configuration_error,
        },
    )


@login_required
def teacher_draft_results(request):
    if request.user.role != "teacher":
        raise PermissionDenied(
            "Only teachers can view teacher drafts."
        )

    drafts = get_teacher_draft_results(request.user)

    return render(
        request,
        "accounts/teacher_draft_results.html",
        {"drafts": drafts},
    )

@login_required
def teacher_edit_draft_result(request, result_id):
    if request.user.role != "teacher":
        raise PermissionDenied(
            "Only teachers can edit draft results."
        )

    result = get_object_or_404(
        get_teacher_draft_results(request.user),
        pk=result_id,
    )

    initial_scores = {
        f"component_{score.assessment_component_id}": score.score
        for score in result.component_scores.all()
    }

    form = ComponentScoreEntryForm(
        result.assessment_configuration,
        request.POST or None,
        initial=initial_scores,
    )

    if request.method == "POST" and form.is_valid():
        components = (
            result.assessment_configuration.components.all()
        )

        scores = {
            component.pk: form.cleaned_data[
                f"component_{component.pk}"
            ]
            for component in components
        }

        try:
            update_draft_result(
                request.user,
                result,
                scores,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("teacher_draft_results")

    return render(
        request,
        "accounts/teacher_edit_draft_result.html",
        {
            "result": result,
            "form": form,
        },
    )
