from django import forms
from .models import AdmissionApplication

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
