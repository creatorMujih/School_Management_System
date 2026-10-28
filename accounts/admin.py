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
admin.site.register(Result)
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

  