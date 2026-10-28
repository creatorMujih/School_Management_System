from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Parent, Student, SchoolClass, AdmissionApplication, AcademicSession, Term, Enrollment, Teacher, SubjectAssignment, AssessmentConfiguration, AssessmentComponent
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
admin.site.register(AssessmentConfiguration)
admin.site.register(AssessmentComponent)
