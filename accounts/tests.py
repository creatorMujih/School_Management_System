
from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from accounts.services import (
    get_teacher_assignments,
    get_students_for_teacher,
    create_draft_result,
    get_teacher_draft_results,
    update_draft_result
)
from django.urls import reverse
from django.contrib.auth import get_user_model

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


class TeacherAssignmentTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="assignmentteacher",
            password="test-password-123",
            role="teacher",
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
        )

        self.other_teacher_user = User.objects.create_user(
            username="otherassignmentteacher",
            password="test-password-123",
            role="teacher",
        )
        self.other_teacher = Teacher.objects.create(
            user=self.other_teacher_user,
        )

        self.school_class = SchoolClass.objects.create(
            name="JSS 1",
            is_active=True,
        )
        self.session = AcademicSession.objects.create(
            name="2027/2028",
            start_date="2027-09-01",
            end_date="2028-07-31",
            is_current=True,
        )
        self.subject = Subject.objects.create(
            name="Mathematics",
            code="MATH",
        )

        self.assignment = SubjectAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            academic_session=self.session,
        )

        def test_teacher_sees_own_assignments(self):
            assignments = get_teacher_assignments(self.teacher_user)

        self.assertEqual(
            list(assignments),
            [self.assignment],
        )

        def test_teacher_cannot_see_another_teachers_assignments(self):
            other_assignment = SubjectAssignment.objects.create(
                teacher=self.other_teacher,
                subject=self.subject,
                school_class=self.school_class,
                academic_session=self.session,
            )

        assignments = get_teacher_assignments(self.teacher_user)

        self.assertIn(self.assignment, assignments)
        self.assertNotIn(other_assignment, assignments)

        def test_non_teacher_sees_no_assignments(self):
            parent_user = User.objects.create_user(
                username="assignmentparent",
                password="test-password-123",
                role="parent",
            )

        assignments = get_teacher_assignments(parent_user)

        self.assertFalse(assignments.exists())

        def test_inactive_teacher_sees_no_assignments(self):
            self.teacher.is_active = False
            self.teacher.save()

            assignments = get_teacher_assignments(self.teacher_user)

            self.assertFalse(assignments.exists())


        def test_teacher_can_retrieve_students_in_assigned_class(self):
            tudent = Student.objects.create(
                admission_number="0000123",
                first_name="Ada",
                last_name="Okafor",
                date_of_birth="2012-04-10",
                gender="female",
                address="Lagos",
                status="active",
            )

            Enrollment.objects.create(
                student=student,
                school_class=self.school_class,
                academic_session=self.session,
                is_active=True,
            )

            students = get_students_for_teacher(
                self.teacher_user,
                self.school_class,
                self.session,
            )

            self.assertIn(student, students)

        def test_teacher_cannot_retrieve_students_from_unassigned_class(self):
            other_class = SchoolClass.objects.create(
                name="JSS 2",
                is_active=True,
            )

            student = Student.objects.create(
                admission_number="0000124",
                first_name="Tunde",
                last_name="Bello",
                date_of_birth="2011-08-15",
                gender="male",
                address="Lagos",
                status="active",
            )

            Enrollment.objects.create(
                student=student,
                school_class=other_class,
                academic_session=self.session,
                is_active=True,
            )

            students = get_students_for_teacher(
                self.teacher_user,
                other_class,
                self.session,
            )

            self.assertFalse(students.exists())

        def test_teacher_cannot_retrieve_students_from_another_session(self):
            other_session = AcademicSession.objects.create(
                name="2028/2029",
                start_date="2028-09-01",
                end_date="2029-07-31",
                is_current=False,
            )

            students = get_students_for_teacher(
                self.teacher_user,
                self.school_class,
                other_session,
            )

            self.assertFalse(students.exists())

        def test_inactive_student_is_excluded(self):
            student = Student.objects.create(
                admission_number="0000125",
                first_name="Ngozi",
                last_name="Eze",
                date_of_birth="2012-01-20",
                gender="female",
                address="Lagos",
                status="withdrawn",
            )

            Enrollment.objects.create(
                student=student,
                school_class=self.school_class,
                academic_session=self.session,
                is_active=True,
            )

            students = get_students_for_teacher(
                self.teacher_user,
                self.school_class,
                self.session,
            )

            self.assertNotIn(student, students)

    
        def create_active_assessment_configuration(self):
            configuration = AssessmentConfiguration.objects.create(
                name="Teacher Entry Configuration",
                is_active=True,
            )
            test_component = AssessmentComponent.objects.create(
                configuration=configuration,
                name="Test",
                max_score=20,
                order=1,
            )
            exam_component = AssessmentComponent.objects.create(
                configuration=configuration,
                name="Examination",
                max_score=80,
                order=2,
            )
            return configuration, test_component, exam_component

        def create_enrolled_student(self):
            student = Student.objects.create(
                admission_number="0000456",
                first_name="Amina",
                last_name="Bello",
                date_of_birth="2012-05-12",
                gender="female",
                address="Lagos",
                status="active",
            )
            enrollment = Enrollment.objects.create(
                student=student,
                school_class=self.school_class,
                academic_session=self.session,
                is_active=True,
            )
            return enrollment

        def test_teacher_can_create_draft_result(self):
            self.create_active_assessment_configuration()
            enrollment = self.create_enrolled_student()

            result = create_draft_result(
                self.teacher_user,
                enrollment,
                self.subject,
                Term.objects.create(
                    term="First",
                    academic_session=self.session,
                    start_date="2027-09-01",
                    end_date="2027-12-15",
                ),
                {
                    AssessmentComponent.objects.get(name="Test").pk: 18,
                    AssessmentComponent.objects.get(name="Examination").pk: 70,
                },
            )

            self.assertFalse(result.is_published)
            self.assertEqual(result.component_scores.count(), 2)

        def test_non_teacher_cannot_create_draft_result(self):
            self.create_active_assessment_configuration()
            enrollment = self.create_enrolled_student()
            term = Term.objects.create(
                term="First",
                academic_session=self.session,
                start_date="2027-09-01",
                end_date="2027-12-15",
            )

            with self.assertRaisesMessage(
                ValidationError,
                "Only teachers can enter results.",
            ):
                create_draft_result(
                    self.teacher_user.__class__.objects.create_user(
                        username="draftparent",
                        password="test-password-123",
                        role="parent",
                    ),
                    enrollment,
                    self.subject,
                    term,
                    {},
                )

        def test_invalid_component_score_cannot_create_draft(self):
            _, test_component, exam_component = (
                self.create_active_assessment_configuration()
            )
            enrollment = self.create_enrolled_student()
            term = Term.objects.create(
                term="First",
                academic_session=self.session,
                start_date="2027-09-01",
                end_date="2027-12-15",
            )

            with self.assertRaises(ValidationError):
                create_draft_result(
                    self.teacher_user,
                    enrollment,
                    self.subject,
                    term,
                    {
                        test_component.pk: 25,
                        exam_component.pk: 70,
                    },
                )

            self.assertFalse(
                Result.objects.filter(
                    enrollment=enrollment,
                    subject=self.subject,
                    term=term,
                ).exists()
            )


class TeacherResultEntryViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher_user = User.objects.create_user(
            username="viewteacher",
            password="test-password-123",
            role="teacher",
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
        )

        self.parent_user = User.objects.create_user(
            username="viewparent",
            password="test-password-123",
            role="parent",
        )

    def test_logged_out_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("teacher_result_entry")
        )

        self.assertEqual(response.status_code, 302)

    def test_non_teacher_is_denied_access(self):
        self.client.force_login(self.parent_user)

        response = self.client.get(
            reverse("teacher_result_entry")
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_open_result_entry_page_without_configuration(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_result_entry")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "There is no active assessment configuration.",
        )

    
    def test_teacher_can_submit_valid_draft_result(self):
        school_class = SchoolClass.objects.create(
            name="JSS 1",
            is_active=True,
        )
        session = AcademicSession.objects.create(
            name="2027/2028",
            start_date="2027-09-01",
            end_date="2028-07-31",
            is_current=True,
        )
        term = Term.objects.create(
            term="First",
            academic_session=session,
            start_date="2027-09-01",
            end_date="2027-12-15",
        )
        subject = Subject.objects.create(
            name="Mathematics",
            code="MATH",
            is_active=True,
        )
        student = Student.objects.create(
            admission_number="0000789",
            first_name="Amina",
            last_name="Bello",
            date_of_birth="2012-05-12",
            gender="female",
            address="Lagos",
            status="active",
        )
        enrollment = Enrollment.objects.create(
            student=student,
            school_class=school_class,
            academic_session=session,
            is_active=True,
        )

        SubjectAssignment.objects.create(
            teacher=self.teacher,
            subject=subject,
            school_class=school_class,
            academic_session=session,
        )

        configuration = AssessmentConfiguration.objects.create(
            name="View Test Configuration",
            is_active=True,
        )
        test_component = AssessmentComponent.objects.create(
            configuration=configuration,
            name="Test",
            max_score=20,
            order=1,
        )
        exam_component = AssessmentComponent.objects.create(
            configuration=configuration,
            name="Examination",
            max_score=80,
            order=2,
        )

        self.client.force_login(self.teacher_user)

        response = self.client.post(
            reverse("teacher_result_entry"),
            {
                "enrollment": enrollment.pk,
                "subject": subject.pk,
                "term": term.pk,
                f"component_{test_component.pk}": 18,
                f"component_{exam_component.pk}": 70,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/teacher_result_success.html",
        )

        result = Result.objects.get(
            enrollment=enrollment,
            subject=subject,
            term=term,
        )
        self.assertFalse(result.is_published)
        self.assertEqual(result.component_scores.count(), 2)


class TeacherDraftResultsTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="draftteacher",
            password="test-password-123",
            role="teacher",
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
        )

        self.other_teacher_user = User.objects.create_user(
            username="otherdraftteacher",
            password="test-password-123",
            role="teacher",
        )
        self.other_teacher = Teacher.objects.create(
            user=self.other_teacher_user,
        )

        self.school_class = SchoolClass.objects.create(
            name="JSS 1",
            is_active=True,
        )
        self.session = AcademicSession.objects.create(
            name="2027/2028",
            start_date="2027-09-01",
            end_date="2028-07-31",
            is_current=True,
        )
        self.term = Term.objects.create(
            term="First",
            academic_session=self.session,
            start_date="2027-09-01",
            end_date="2027-12-15",
        )

        self.subject = Subject.objects.create(
            name="Mathematics",
            code="MATH",
            is_active=True,
        )
        self.other_subject = Subject.objects.create(
            name="English",
            code="ENG",
            is_active=True,
        )

        self.student = Student.objects.create(
            admission_number="0000781",
            first_name="Amina",
            last_name="Bello",
            date_of_birth="2012-05-12",
            gender="female",
            address="Lagos",
            status="active",
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            school_class=self.school_class,
            academic_session=self.session,
            is_active=True,
        )

        self.configuration = AssessmentConfiguration.objects.create(
            name="Draft Test Configuration",
            is_active=False,
        )

        SubjectAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            academic_session=self.session,
        )

        self.result = Result.objects.create(
            enrollment=self.enrollment,
            subject=self.subject,
            term=self.term,
            assessment_configuration=self.configuration,
        )

    def test_teacher_can_see_own_draft(self):
        drafts = get_teacher_draft_results(self.teacher_user)

        self.assertIn(self.result, drafts)

    def test_teacher_cannot_see_draft_for_unassigned_subject(self):
        other_result = Result.objects.create(
            enrollment=self.enrollment,
            subject=self.other_subject,
            term=self.term,
            assessment_configuration=self.configuration,
        )

        drafts = get_teacher_draft_results(self.teacher_user)

        self.assertNotIn(other_result, drafts)

    def test_published_results_are_excluded(self):
        self.result.is_published = True
        self.result.save(update_fields=["is_published"])

        drafts = get_teacher_draft_results(self.teacher_user)

        self.assertNotIn(self.result, drafts)

    def test_non_teacher_sees_no_drafts(self):
        parent_user = User.objects.create_user(
            username="draftparent",
            password="test-password-123",
            role="parent",
        )

        drafts = get_teacher_draft_results(parent_user)

        self.assertFalse(drafts.exists())



class TeacherDraftResultsViewTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="draftviewteacher",
            password="test-password-123",
            role="teacher",
        )
        Teacher.objects.create(user=self.teacher_user)

        self.parent_user = User.objects.create_user(
            username="draftviewparent",
            password="test-password-123",
            role="parent",
        )

    def test_logged_out_user_is_redirected(self):
        response = self.client.get(
            reverse("teacher_draft_results")
        )

        self.assertEqual(response.status_code, 302)

    def test_parent_is_denied_access(self):
        self.client.force_login(self.parent_user)

        response = self.client.get(
            reverse("teacher_draft_results")
        )

        self.assertEqual(response.status_code, 403)

    def test_teacher_can_open_draft_results_page(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(
            reverse("teacher_draft_results")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/teacher_draft_results.html",
        )
        self.assertContains(response, "My Draft Results")
    




class UpdateDraftResultTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="editteacher",
            password="test-password-123",
            role="teacher",
        )
        self.teacher = Teacher.objects.create(
            user=self.teacher_user,
        )

        self.other_teacher_user = User.objects.create_user(
            username="othereditteacher",
            password="test-password-123",
            role="teacher",
        )
        self.other_teacher = Teacher.objects.create(
            user=self.other_teacher_user,
        )

        self.school_class = SchoolClass.objects.create(
            name="JSS 1",
            is_active=True,
        )
        self.session = AcademicSession.objects.create(
            name="2027/2028",
            start_date="2027-09-01",
            end_date="2028-07-31",
            is_current=True,
        )
        self.term = Term.objects.create(
            term="First",
            academic_session=self.session,
            start_date="2027-09-01",
            end_date="2027-12-15",
        )
        self.subject = Subject.objects.create(
            name="Mathematics",
            code="MATH",
            is_active=True,
        )

        self.student = Student.objects.create(
            admission_number="0000891",
            first_name="Amina",
            last_name="Bello",
            date_of_birth="2012-05-12",
            gender="female",
            address="Lagos",
            status="active",
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            school_class=self.school_class,
            academic_session=self.session,
            is_active=True,
        )

        self.configuration = AssessmentConfiguration.objects.create(
            name="Edit Test Configuration",
            is_active=False,
        )
        self.test_component = AssessmentComponent.objects.create(
            configuration=self.configuration,
            name="Test",
            max_score=20,
            order=1,
        )
        self.exam_component = AssessmentComponent.objects.create(
            configuration=self.configuration,
            name="Examination",
            max_score=80,
            order=2,
        )

        SubjectAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            school_class=self.school_class,
            academic_session=self.session,
        )

        self.result = Result.objects.create(
            enrollment=self.enrollment,
            subject=self.subject,
            term=self.term,
            assessment_configuration=self.configuration,
        )

        ComponentScore.objects.create(
            result=self.result,
            assessment_component=self.test_component,
            score=10,
        )
        ComponentScore.objects.create(
            result=self.result,
            assessment_component=self.exam_component,
            score=60,
        )

    def test_teacher_can_update_own_draft(self):
        update_draft_result(
            self.teacher_user,
            self.result,
            {
                self.test_component.pk: 18,
                self.exam_component.pk: 70,
            },
        )

        self.assertEqual(
            self.result.component_scores.get(
                assessment_component=self.test_component
            ).score,
            18,
        )
        self.assertEqual(
            self.result.component_scores.get(
                assessment_component=self.exam_component
            ).score,
            70,
        )

    def test_invalid_score_does_not_update_draft(self):
        with self.assertRaises(ValidationError):
            update_draft_result(
                self.teacher_user,
                self.result,
                {
                    self.test_component.pk: 25,
                    self.exam_component.pk: 70,
                },
            )

        self.assertEqual(
            self.result.component_scores.get(
                assessment_component=self.test_component
            ).score,
            10,
        )

    def test_unassigned_teacher_cannot_update_draft(self):
        with self.assertRaisesMessage(
            ValidationError,
            "You are not assigned to this student's class and subject.",
        ):
            update_draft_result(
                self.other_teacher_user,
                self.result,
                {
                    self.test_component.pk: 18,
                    self.exam_component.pk: 70,
                },
            )

    def test_published_result_cannot_be_updated(self):
        self.result.is_published = True
        self.result.save(update_fields=["is_published"])

        with self.assertRaisesMessage(
            ValidationError,
            "Published results cannot be edited.",
        ):
            update_draft_result(
                self.teacher_user,
                self.result,
                {
                    self.test_component.pk: 18,
                    self.exam_component.pk: 70,
                },
            )
