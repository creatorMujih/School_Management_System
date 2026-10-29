from .models import AdmissionApplication, Student, AcademicSession, Enrollment, SubjectAssignment, AssessmentConfiguration, AssessmentComponent, Result, ComponentScore, SubjectAssignment
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

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
    
    try:
        current_session = AcademicSession.objects.get(is_current=True)
    except AcademicSession.DoesNotExist:
        raise ValueError("No current academic session has been configured.")
    except AcademicSession.MultipleObjectsReturned:
        raise ValueError("More than one current academic session is configured.")
    

    admission_number = generate_admission_number()

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

        enrollment = Enrollment.objects.create(
            student=student,
            school_class=application.class_applied_for,
            academic_session=current_session,
        )

        application.status = "enrolled"
        application.save()
    return student

@transaction.atomic
def publish_result(result):
    if result.is_published:
        raise ValueError("This result has already been published.")

    result.validate_for_publication()

    result.is_published = True
    result.save(update_fields=["is_published"])

    return result


def get_teacher_assignments(user):
    """Return the subject assignments belonging to a teacher."""
    if not user.is_authenticated or user.role != "teacher":
        return SubjectAssignment.objects.none()

    return SubjectAssignment.objects.filter(
        teacher__user=user,
        teacher__is_active=True,
        school_class__is_active=True,
        academic_session__is_current=True,
    ).select_related(
        "teacher",
        "subject",
        "school_class",
        "academic_session",
    )


def get_students_for_teacher(user, school_class, academic_session):
    """Return students in a class assigned to this teacher and session."""
    assignments = get_teacher_assignments(user).filter(
        school_class=school_class,
        academic_session=academic_session,
    )

    if not assignments.exists():
        return Student.objects.none()

    return Student.objects.filter(
        enrollments__school_class=school_class,
        enrollments__academic_session=academic_session,
        enrollments__is_active=True,
        status="active",
    ).distinct().order_by("last_name", "first_name")


@transaction.atomic
def create_draft_result(user, enrollment, subject, term, scores):
    """Create a draft result and its component scores for an assigned teacher."""
    if not user.is_authenticated or user.role != "teacher":
        raise ValidationError("Only teachers can enter results.")

    teacher_assignments = get_teacher_assignments(user)

    allowed = teacher_assignments.filter(
        teacher__is_active=True,
        school_class=enrollment.school_class,
        academic_session=enrollment.academic_session,
        subject=subject,
    ).exists()

    if not allowed:
        raise ValidationError(
            "You are not assigned to teach this subject "
            "in the student's class for this session."
        )

    if not enrollment.is_active or enrollment.student.status != "active":
        raise ValidationError(
            "The student must have an active enrollment."
        )

    if (
        not enrollment.academic_session.is_current
        or not enrollment.school_class.is_active
    ):
        raise ValidationError(
            "Results can only be entered for an active class "
            "in the current academic session."
        )

    if term.academic_session_id != enrollment.academic_session_id:
        raise ValidationError(
            "The term must belong to the student's academic session."
        )

    configuration = AssessmentConfiguration.objects.filter(
        is_active=True
    ).first()

    if configuration is None:
        raise ValidationError(
            "There is no active assessment configuration."
        )

    components = list(
        configuration.components.all().order_by("order", "id")
    )

    if not components:
        raise ValidationError(
            "The assessment configuration has no components."
        )

    if sum(component.max_score for component in components) != 100:
        raise ValidationError(
            "Assessment component maximums must total 100."
        )

    expected_ids = {component.pk for component in components}

    if set(scores.keys()) != expected_ids:
        raise ValidationError(
            "Scores must be supplied for every assessment component."
        )

    for component in components:
        score = scores[component.pk]

        if isinstance(score, bool) or not isinstance(score, int):
            raise ValidationError(
                f"The score for {component.name} must be a whole number."
            )

        if score < 0 or score > component.max_score:
            raise ValidationError(
                f"The score for {component.name} must be between "
                f"0 and {component.max_score}."
            )

    result, created = Result.objects.get_or_create(
        enrollment=enrollment,
        subject=subject,
        term=term,
        defaults={
            "assessment_configuration": configuration,
            "is_published": False,
        },
    )

    if not created:
        raise ValidationError(
            "A result already exists for this student, subject, and term."
        )

    for component in components:
        ComponentScore.objects.create(
            result=result,
            assessment_component=component,
            score=scores[component.pk],
        )

    return result


def get_teacher_draft_results(user):
    """Return unpublished results matching a teacher's exact assignments."""
    if not user.is_authenticated or user.role != "teacher":
        return Result.objects.none()

    assignments = get_teacher_assignments(user)

    from django.db.models import Q

    allowed = Q(pk__in=[])

    for assignment in assignments:
        allowed |= Q(
            subject_id=assignment.subject_id,
            enrollment__school_class_id=assignment.school_class_id,
            enrollment__academic_session_id=assignment.academic_session_id,
        )

    return Result.objects.filter(
        allowed,
        is_published=False,
    ).select_related(
        "enrollment__student",
        "enrollment__school_class",
        "subject",
        "term",
    ).distinct().order_by(
        "term__academic_session__name",
        "term__term",
        "subject__name",
    )


@transaction.atomic
def update_draft_result(user, result, scores):
    """Update component scores on a teacher's own unpublished result."""
    if not user.is_authenticated or user.role != "teacher":
        raise ValidationError("Only teachers can edit results.")

    result = Result.objects.select_for_update().get(pk=result.pk)

    if result.is_published:
        raise ValidationError(
            "Published results cannot be edited."
        )

    allowed = get_teacher_assignments(user).filter(
        subject=result.subject,
        school_class=result.enrollment.school_class,
        academic_session=result.enrollment.academic_session,
    ).exists()

    if not allowed:
        raise ValidationError(
            "You are not assigned to this student's class and subject."
        )

    components = list(
        result.assessment_configuration.components.all().order_by(
            "order", "id"
        )
    )
    expected_ids = {component.pk for component in components}

    if set(scores.keys()) != expected_ids:
        raise ValidationError(
            "Scores must be supplied for every assessment component."
        )

    for component in components:
        score = scores[component.pk]

        if isinstance(score, bool) or not isinstance(score, int):
            raise ValidationError(
                f"The score for {component.name} must be a whole number."
            )

        if score < 0 or score > component.max_score:
            raise ValidationError(
                f"The score for {component.name} must be between "
                f"0 and {component.max_score}."
            )

    for component in components:
        ComponentScore.objects.update_or_create(
            result=result,
            assessment_component=component,
            defaults={"score": scores[component.pk]},
        )

    return result




    
