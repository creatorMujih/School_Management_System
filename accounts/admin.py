from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Parent, Student

admin.site.register(User, UserAdmin)
admin.site.register(Parent)
admin.site.register(Student)

