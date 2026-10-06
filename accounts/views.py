from django.shortcuts import render, redirect
from .forms import AdmissionApplicationForm
from .services import create_admission_application

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