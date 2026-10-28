from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

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

ADMISSION_CHOICES = [
    ("pending", "Pending"),
    ("under_review", "Under Review"),
    ("approved", "Approved"),
    ("not_admitted", "Not Admitted"),
    ("enrolled", "Enrolled"),
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

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
        
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

    def __str__(self):
        return f"{self.admission_number} - {self.first_name} {self.last_name}"


class SchoolClass(models.Model):
    name = models.CharField(
        max_length=15,
        )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.name}"

class AdmissionApplication(models.Model):
    class_applied_for = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT
    )

    application_number = models.CharField(
        max_length=7,
        unique=True,
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
        on_delete=models.PROTECT,
    )

    previous_school = models.CharField(
        max_length=30,
    )

    previous_class = models.CharField(
        max_length=10,
    )

    previous_result = models.FileField(
        upload_to="media/students/"
    )

    status = models.CharField(
        max_length=12,
        choices=ADMISSION_CHOICES,
        default="pending",
    )

    passport = models.ImageField(
        upload_to="media/students/"
    )

    submitted_date = models.DateTimeField(auto_now_add=True)

    reviewed_date = models.DateTimeField(
        null=True,
        blank=True,
    )


    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.application_number} - {self.first_name} {self.last_name}"


class AcademicSession(models.Model):
    name = models.CharField(
        max_length=9
    )
   
    start_date = models.DateField()

    end_date = models.DateField()

    is_current = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_current"],
                condition=models.Q(is_current=True),
                name="unique_current_academic_session",
            )
        ]


class Term(models.Model):
    term = models.CharField(
    max_length=7,
    )

    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
    )

    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.term} - {self.academic_session.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
    )

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
    )

    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
    )

    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True
        )

    def __str__(self):
        return f"{self.student} - {self.school_class} - {self.academic_session} - {self.enrollment_date}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_session"],
                name="unique_student_session_enrollment",
            )
        ]

class Subject(models.Model):
    name = models.CharField(
        max_length=50, 
        unique=True
        )
    code = models.CharField(
        max_length=10,
        unique=True
        )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE
        )
    phone = models.CharField(max_length=15)
    address = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class SubjectAssignment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT)

    def __str__(self):
        return (
            f"{self.teacher} - {self.subject} - "
            f"{self.school_class} - {self.academic_session}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "subject",
                    "school_class",
                    "academic_session",
                ],
                name="unique_teacher_subject_class_session",
            )
        ]


class AssessmentConfiguration(models.Model):
    name = models.CharField(max_length=50, unique=True, default="Standard Assessment")
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_assessment_configuration",
            )
        ]
    
class AssessmentComponent(models.Model):
    configuration = models.ForeignKey(
        AssessmentConfiguration,
        on_delete=models.CASCADE,
        related_name="components",
        )
        
    name = models.CharField(max_length=30)
    max_score = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return f"{self.name} ({self.max_score})"
    

class Result(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
    )

    term = models.ForeignKey(
        Term,
        on_delete=models.PROTECT,
    )
    
    assessment_configuration = models.ForeignKey(
        AssessmentConfiguration,
        on_delete=models.PROTECT,
    )

    is_published = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.enrollment} - {self.subject} - {self.term}"
    
    def validate_for_publication(self):
        if (
            self.term.academic_session_id
            != self.enrollment.academic_session_id
        ):
            raise ValidationError(
                "The result term must belong to the student's enrolled academic session."
            )
            
        assignment_exists = SubjectAssignment.objects.filter(
            subject=self.subject,
            school_class=self.enrollment.school_class,
            academic_session=self.enrollment.academic_session,
        ).exists()

        if not assignment_exists:
            raise ValidationError(
                "This subject is not assigned to the student's class "
                "for the enrolled academic session."
            )  
             
        components = list(
            self.assessment_configuration.components.all()
        )

        if not components:
            raise ValidationError(
                "The assessment configuration has no components."
            )

        if sum(component.max_score for component in components) != 100:
            raise ValidationError(
                "Assessment component maximums must total 100."
            )

        scores = {
            item.assessment_component_id: item
            for item in self.component_scores.select_related(
                "assessment_component"
            )
        }

        for score in scores.values():
            score.full_clean()

        for component in components:
            if component.id not in scores:
                raise ValidationError(
                    f"Missing score for {component.name}."
                )

        score = scores[component.id]

        if score.score > component.max_score:
            raise ValidationError(
                f"The score for {component.name} exceeds its maximum."
            )

    class Meta:
        constraints = [
            models.UniqueConstraint(
            fields=["enrollment", "subject", "term"],
            name="unique_enrollment_subject_term_result",
            )
        ]

class ComponentScore(models.Model):
    result = models.ForeignKey(
        Result,
        on_delete=models.CASCADE,
        related_name="component_scores",
    )

    assessment_component = models.ForeignKey(
        AssessmentComponent,
        on_delete=models.PROTECT,
    )

    score = models.PositiveSmallIntegerField()

    def __str__(self):
        return (
            f"{self.result} - "
            f"{self.assessment_component.name}: {self.score}"
        )
    
    def clean(self):
        if self.score > self.assessment_component.max_score:
            raise ValidationError({
            "score": "Score cannot exceed the component maximum."
        })

        if (
            self.assessment_component.configuration_id
            != self.result.assessment_configuration_id
        ):
            raise ValidationError(
                "The component must belong to the result's assessment configuration."
            )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["result", "assessment_component"],
                name="unique_result_assessment_component",
            )
        ]

