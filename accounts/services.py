from .models import AdmissionApplication
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

