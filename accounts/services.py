from .models import AdmissionApplication, Student
from django.utils import timezone
from django.db import transaction

def generate_application_number():
    if not AdmissionApplication.objects.exists():
        return "APP0001"
    last_application = AdmissionApplication.objects.last()
    number = last_application.application_number[3:]
    number = int(number)
    number += 1
    formatted_number = str(number).zfill(4)
    
    return f"APP{formatted_number}"

def create_admission_application(data):
    application_number = generate_application_number()
    application = AdmissionApplication.objects.create(
    application_number=application_number,
    first_name=data["first_name"],
    last_name=data["last_name"],
    other_name=data["other_name"],
    date_of_birth=data["date_of_birth"],
    gender=data["gender"],
    address=data["address"],
    parent=data["parent"],
    class_applied_for=data["class_applied_for"],
    previous_school=data["previous_school"],
    previous_class=data["previous_class"],
    previous_result=data["previous_result"],
    passport=data["passport"],
)
    return application

def start_application_review(application, reviewer):

    if application.status != "pending":
        raise ValueError("Application is not pending.")

    application.status = "under_review"
    application.reviewed_by = reviewer
    application.reviewed_date = timezone.now()
    application.save()

    return application

def approve_application(application, reviewer):
    if application.status != "under_review":
        raise ValueError("Application is not under review.")

    application.status = "approved"
    application.reviewed_by = reviewer
    application.reviewed_date = timezone.now()
    application.save()

    return application


def reject_application(application, reviewer):
    if application.status != "under_review":
        raise ValueError("Application is not under review.")
    
    application.status = "not_admitted"
    application.reviewed_by = reviewer
    application.reviewed_date = timezone.now()
    application.save()
    
    return application

def generate_admission_number():
    if not Student.objects.exists():
        return "0000001"
    last_student = Student.objects.last()
    number = last_student.admission_number[3:]
    number = int(number)
    number += 1
    formatted_number = str(number).zfill(4)
    
    return f"000{formatted_number}"

def enroll_student(application):
    if application.status != "approved":
        raise ValueError("Application is not approved.")
    admission_number = generate_admission_number()
    student = Student.objects.create(
        admission_number=admission_number,
        first_name=application.first_name,
        last_name=application.last_name,
        other_name=application.other_name,
        date_of_birth=application.date_of_birth,
        gender=application.gender,
        address=application.address,
        parent=application.parent,
        passport=application.passport,
        status="active",
    )

    with transaction.atomic():
        student = Student.objects.create(
            admission_number=admission_number,
            first_name=application.first_name,
            last_name=application.last_name,
            other_name=application.other_name,
            date_of_birth=application.date_of_birth,
            gender=application.gender,
            address=application.address,
            parent=application.parent,
            passport=application.passport,
            status="active",
        )

        application.status = "enrolled"
        application.save()

    return student
    
