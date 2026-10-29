from django import forms
from .models import AdmissionApplication
from accounts.models import (
    Enrollment,
    Subject,
    Term,
    AssessmentConfiguration,
)
from accounts.services import get_teacher_assignments

class AdmissionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = [
            "class_applied_for",
            "first_name",
            "last_name",
            "other_name",
            "date_of_birth",
            "gender",
            "address",
            "parent",
            "previous_school",
            "previous_class",
            "previous_result",
            "passport",
            ]


class TeacherResultEntryForm(forms.Form):
    enrollment = forms.ModelChoiceField(
        queryset=Enrollment.objects.none(),
        label="Student",
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        label="Subject",
    )
    term = forms.ModelChoiceField(
        queryset=Term.objects.none(),
        label="Term",
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        assignments = get_teacher_assignments(user)

        class_ids = assignments.values_list(
            "school_class_id", flat=True
        )
        session_ids = assignments.values_list(
            "academic_session_id", flat=True
        )

        self.fields["enrollment"].queryset = (
            Enrollment.objects.filter(
                school_class_id__in=class_ids,
                academic_session_id__in=session_ids,
                is_active=True,
                student__status="active",
                school_class__is_active=True,
                academic_session__is_current=True,
            )
            .select_related("student", "school_class")
            .distinct()
        )

        self.fields["subject"].queryset = Subject.objects.filter(
            id__in=assignments.values_list(
                "subject_id", flat=True
            ),
            is_active=True,
        ).distinct()

        self.fields["term"].queryset = Term.objects.filter(
            academic_session__is_current=True,
        ).select_related("academic_session")

    def clean(self):
        cleaned_data = super().clean()

        enrollment = cleaned_data.get("enrollment")
        subject = cleaned_data.get("subject")
        term = cleaned_data.get("term")

        if not all([enrollment, subject, term]):
            return cleaned_data

        assignments = get_teacher_assignments(self.user)

        allowed = assignments.filter(
            school_class=enrollment.school_class,
            academic_session=enrollment.academic_session,
            subject=subject,
        ).exists()

        if not allowed:
            raise forms.ValidationError(
                "You are not assigned to teach this subject "
                "in the student's class for this session."
            )

        if (
            term.academic_session_id
            != enrollment.academic_session_id
        ):
            raise forms.ValidationError(
                "The selected term does not belong to the "
                "student's academic session."
            )

        return cleaned_data



class ComponentScoreEntryForm(forms.Form):
    def __init__(self, configuration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuration = configuration

        components = configuration.components.all().order_by("order", "id")

        for component in components:
            self.fields[f"component_{component.pk}"] = (
                forms.IntegerField(
                    label=f"{component.name} (max {component.max_score})",
                    min_value=0,
                    max_value=component.max_score,
                    required=True,
                )
            )

