from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import User, Parent, Student, SchoolClass, AdmissionApplication, AcademicSession, Term, Enrollment, Teacher, SubjectAssignment, AssessmentConfiguration, AssessmentComponent, Result, ComponentScore
admin.site.register(User, UserAdmin)
admin.site.register(Parent)
admin.site.register(Student)
admin.site.register(SchoolClass)
admin.site.register(AdmissionApplication)
admin.site.register(Term)
admin.site.register(AcademicSession)
admin.site.register(Enrollment)
admin.site.register(Teacher)
admin.site.register(SubjectAssignment)
admin.site.register(AssessmentComponent)
admin.site.register(ComponentScore)


class AssessmentComponentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        if any(self.errors):
            return

        total = 0

        for form in self.forms:
            if not form.cleaned_data:
                continue

            if form.cleaned_data.get("DELETE", False):
                continue

            score = form.cleaned_data.get("max_score")

            if score is not None:
                total += score

        if self.instance.is_active and total != 100:
            raise ValidationError(
                "An active assessment configuration "
                "must total 100 marks."
            )

        
class AssessmentComponentInline(admin.TabularInline):
    model = AssessmentComponent
    formset = AssessmentComponentFormSet
    extra = 1


@admin.register(AssessmentConfiguration)
class AssessmentConfigurationAdmin(admin.ModelAdmin):
    inlines = [AssessmentComponentInline]

class ComponentScoreForm(forms.ModelForm):
    class Meta:
        model = ComponentScore
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        if (
            cleaned_data.get("score") is not None
            and cleaned_data.get("assessment_component") is not None
        ):
            score = cleaned_data["score"]
            component = cleaned_data["assessment_component"]

            if score > component.max_score:
                raise forms.ValidationError(
                    f"Score cannot exceed {component.max_score} "
                    f"for {component.name}."
                )
        result = cleaned_data.get("result")
        component = cleaned_data.get("assessment_component")

        if result and component:
            if (
                component.configuration_id
                != result.assessment_configuration_id
            ):
                raise forms.ValidationError(
                    "This component does not belong to "
                    "the result's assessment configuration."
                )
        return cleaned_data


class ComponentScoreInline(admin.TabularInline):
    model = ComponentScore
    extra = 1

    def has_add_permission(self, request, obj=None):
        if obj and obj.is_published:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_published:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_published:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "enrollment",
        "subject",
        "term",
        "is_published",
    )

    list_filter = (
        "is_published",
        "term",
        "subject",
    )

    search_fields = (
        "enrollment__student__first_name",
        "enrollment__student__last_name",
        "enrollment__student__admission_number",
        "subject__name",
    )

    inlines = [ComponentScoreInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_published:
            return (
                "enrollment",
                "subject",
                "term",
                "assessment_configuration",
                "is_published",
            )
        return ()