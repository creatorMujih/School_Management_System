from django.contrib.auth.models import AbstractUser
from django.db import models

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("teacher", "Teacher"),
    ("parent", "Parent"),
    ("student", "Student"),
]

GENDER_CHOICES = [
    ("male", "Male"),
    ("female", "Female"),
]

STATUS_CHOICES = [
    ("active", "Active"),
    ("graduated", "Graduated"),
    ("withdrawn", "Withdrawn"),
]

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

class Parent(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    phone = models.CharField(
        max_length=15,
    )

    address = models.CharField(
        max_length=50,
    )

    occupation = models.CharField(
        max_length=20,
        blank=True
    )
        
class Student(models.Model):
    admission_number = models.CharField(
        max_length=7,
        unique=True
        )

    first_name = models.CharField(
        max_length=15,
    )

    last_name = models.CharField(
        max_length=15,
    )

    other_name = models.CharField(
        max_length=15,
        blank=True
    )

    date_of_birth = models.DateField()


    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )
   
    address = models.CharField(
        max_length=50,
    )

    parent = models.ForeignKey(
        Parent, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True, 
    )


    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES 
    )

    passport = models.ImageField(
        upload_to="media/students/"
    )


