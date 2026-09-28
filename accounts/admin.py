from django.contrib import admin

# Register your models here.
from .models import Student, Parent

admin.site.register(Student)
admin.site.register(Parent)