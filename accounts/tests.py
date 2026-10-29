
from django.test import TestCase
from django.core.exceptions import ValidationError

from accounts.models import (
    User,
    Parent,
    Student,
    SchoolClass,
    AcademicSession,
    Term,
    Enrollment,
    Subject,
    SubjectAssignment,
    Teacher,
    AssessmentConfiguration,
    AssessmentComponent,
    Result,
    ComponentScore,
)


class ResultPublicationTests(TestCase):
    
    def setUp(self):
        user = User.objects.create_user(
            username="testparent",
            password="testpassword123",
            role="parent",
        )

        parent = Parent.objects.create(
            user=user,
            phone="08012345678",
            address="Test Address",
        )

        student = Student.objects.create(
            admission_number="0000001",
            first_name="Test",
            last_name="Student",
            date_of_birth="2012-05-10",
            gender="male",
            address="Test Address",
            parent=parent,
            status="active",
            passport="students/test.jpg",
        )

        self.school_class = SchoolClass.objects.create(
            name="JSS 1"
    )

        self.session = AcademicSession.objects.create(
            name="2026/2027",
            start_date="2026-09-01",
            end_date="2027-07-31",
            is_current=True,
        )

        self.term = Term.objects.create(
            term="First",
            academic_session=self.session,
            start_date="2026-09-01",
            end_date="2026-12-18",
        )

        self.enrollment = Enrollment.objects.create(
            student=student,
            school_class=self.school_class,
            academic_session=self.session,
        )

        self.subject = Subject.objects.create(
            name="Mathematics",
            code="MATH",
        )

        self.configuration = AssessmentConfiguration.objects.create(
            name="Test Configuration",
        )

        self.result = Result.objects.create(
            enrollment=self.enrollment,
            subject=self.subject,
            term=self.term,
            assessment_configuration=self.configuration,
        )

    # Give each test a valid subject assignment by default.
        teacher_user = User.objects.create_user(
            username="testteacher",
            password="testpassword123",
            role="teacher",
        )

        teacher = Teacher.objects.create(
            user=teacher_user,
            phone="08087654321",
            address="School Address",
        )

        SubjectAssignment.objects.create(
            teacher=teacher,
            subject=self.subject,
            school_class=self.school_class,
            academic_session=self.session,
        )

    def add_component(self, name, max_score, order=1):
        return AssessmentComponent.objects.create(
            configuration=self.configuration,
            name=name,
            max_score=max_score,
            order=order,
        )

    def test_result_without_components_cannot_be_published(self):
        with self.assertRaises(ValidationError):
            self.result.validate_for_publication()

    def test_component_maximums_must_total_100(self):
        self.add_component("Test", 20, 1)
        self.add_component("Assignment", 20, 2)
        self.add_component("Examination", 50, 3)

        with self.assertRaisesMessage(
            ValidationError,
            "Assessment component maximums must total 100.",
        ):
            self.result.validate_for_publication()

    def test_missing_component_score_prevents_publication(self):
        self.add_component("Test", 20, 1)
        self.add_component("Examination", 80, 2)

        with self.assertRaisesMessage(
            ValidationError,
            "Missing score for Test.",
        ):
            self.result.validate_for_publication()

    def test_score_above_component_maximum_prevents_publication(self):
        component = self.add_component("Test", 20, 1)
        self.add_component("Examination", 80, 2)

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=component,
            score=25,
        )

        with self.assertRaises(ValidationError):
            self.result.validate_for_publication()

    def test_component_from_another_configuration_is_rejected(self):
        other_configuration = AssessmentConfiguration.objects.create(
            name="Other Configuration",
        )

        other_component = AssessmentComponent.objects.create(
            configuration=other_configuration,
            name="Other Test",
            max_score=20,
            order=1,
        )

        with self.assertRaises(ValidationError):
            ComponentScore(
                result=self.result,
                assessment_component=other_component,
                score=10,
            ).full_clean()

    def test_term_from_another_session_prevents_publication(self):
        self.add_component("Test", 20, 1)
        self.add_component("Examination", 80, 2)

        another_session = AcademicSession.objects.create(
            name="2027/2028",
            start_date="2027-09-01",
            end_date="2028-07-31",
            is_current=False,
        )

        another_term = Term.objects.create(
            term="First",
            academic_session=another_session,
            start_date="2027-09-01",
            end_date="2027-12-18",
        )

        self.result.term = another_term
        self.result.save()

        with self.assertRaises(ValidationError):
            self.result.validate_for_publication()

    def test_unassigned_subject_prevents_publication(self):
        SubjectAssignment.objects.all().delete()

        self.add_component("Test", 20, 1)
        self.add_component("Examination", 80, 2)

        with self.assertRaises(ValidationError):
            self.result.validate_for_publication()


    def test_valid_result_passes_publication_validation(self):
        test_component = self.add_component("Test", 20, 1)
        exam_component = self.add_component("Examination", 80, 2)

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=test_component,
            score=18,
        )

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=exam_component,
            score=70,
        )

        # Should not raise ValidationError.
        self.result.validate_for_publication()

    def test_published_result_cannot_be_published_twice(self):
        self.add_component("Test", 20, 1)
        self.add_component("Examination", 80, 2)

        test_component = self.result.assessment_configuration.components.get(
            name="Test"
        )
        exam_component = self.result.assessment_configuration.components.get(
            name="Examination"
        )

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=test_component,
            score=18,
        )

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=exam_component,
            score=70,
        )

        self.result.is_published = True
        self.result.save(update_fields=["is_published"])

        from accounts.services import publish_result

        with self.assertRaisesMessage(
            ValueError,
            "This result has already been published.",
        ):
            publish_result(self.result)

    def test_publish_result_sets_published_status(self):
        from accounts.services import publish_result

        test_component = self.add_component("Test", 20, 1)
        exam_component = self.add_component("Examination", 80, 2)

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=test_component,
            score=18,
        )
        ComponentScore.objects.create(
            result=self.result,
            assessment_component=exam_component,
            score=70,
        )

        publish_result(self.result)

        self.result.refresh_from_db()
        self.assertTrue(self.result.is_published)

    def test_invalid_result_is_not_published(self):
        from accounts.services import publish_result

        with self.assertRaises(ValidationError):
            publish_result(self.result)

        self.result.refresh_from_db()
        self.assertFalse(self.result.is_published)

    def test_published_result_service_rejects_second_publication(self):
        from accounts.services import publish_result

        self.result.is_published = True
        self.result.save(update_fields=["is_published"])

        with self.assertRaisesMessage(
            ValueError,
            "This result has already been published.",
        ):
            publish_result(self.result)

    def create_published_result(self):
        from accounts.services import publish_result

        test_component = self.add_component("Test", 20, 1)
        exam_component = self.add_component("Examination", 80, 2)

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=test_component,
            score=18,
        )
        ComponentScore.objects.create(
            result=self.result,
            assessment_component=exam_component,
            score=70,
        )

        publish_result(self.result)
        self.result.refresh_from_db()
        return test_component


    def test_published_result_cannot_be_modified(self):
        self.create_published_result()

        another_subject = Subject.objects.create(
            name="English",
            code="ENG",
        )
        self.result.subject = another_subject

        with self.assertRaisesMessage(
            ValidationError,
            "A published result cannot be modified.",
        ):
            self.result.save()


    def test_published_result_cannot_be_deleted(self):
        self.create_published_result()

        with self.assertRaisesMessage(
            ValidationError,
            "A published result cannot be deleted.",
        ):
            self.result.delete()


    def test_score_for_published_result_cannot_be_modified(self):
        test_component = self.create_published_result()

        score = ComponentScore.objects.get(
            result=self.result,
            assessment_component=test_component,
        )
        score.score = 19

        with self.assertRaisesMessage(
            ValidationError,
            "Scores for a published result cannot be modified.",
        ):
            score.save()


    def test_score_for_published_result_cannot_be_deleted(self):
        test_component = self.create_published_result()

        score = ComponentScore.objects.get(
            result=self.result,
            assessment_component=test_component,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Scores for a published result cannot be deleted.",
        ):
            score.delete()
