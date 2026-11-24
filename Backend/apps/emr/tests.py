"""EMR tests: links to module 1 (RBAC, Staff, audit) and module 2 (Patient, Consent)."""
import shutil
import tempfile
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.models import AuditLog, User
from apps.registry.models import Consent
from apps.registry.test_api import PW, PatientAPITestBase, make_patient

from .models import Diagnosis, Document, Encounter, Icd10Code, VitalSigns

ENC = '/api/emr/encounters/'
DOCS = '/api/emr/documents/'
DIAG = '/api/emr/diagnoses/'
ICD = '/api/emr/icd10/'
MEDIA = tempfile.mkdtemp()


def pdf(name='report.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test', content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA)
class EMRTestBase(PatientAPITestBase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def encounter(self, patient=None, doctor=None, **extra):
        doctor = doctor or self.hep
        return Encounter.objects.create(patient=patient or self.own, staff=doctor.staff_profile, **extra)

    def create(self, user, **data):
        self.as_(user)
        payload = {'patient': self.own.pk, 'chief_complaint': 'Jaundice'}
        payload.update(data)
        return self.client.post(ENC, payload, format='json')


class PermissionTests(EMRTestBase):
    def test_read_matrix(self):
        for user, code in ((self.root, 200), (self.admin, 200), (self.coord, 200), (self.hep, 200),
                           (self.rad, 200), (self.surg, 200), (self.pat_user, 200),
                           (self.billing, 403), (self.nojob, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(ENC).status_code, code)

    def test_only_doctors_write(self):
        for user in (self.root, self.admin, self.coord, self.rad, self.billing, self.nojob, self.pat_user):
            with self.subTest(user=user.username):
                self.assertEqual(self.create(user).status_code, 403)
        for user in (self.hep, self.surg):
            with self.subTest(user=user.username):
                self.assertEqual(self.create(user).status_code, 201)

    def test_anonymous_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(ENC).status_code, 401)


class EncounterTests(EMRTestBase):
    def test_treating_doctor_defaults_to_logged_in_doctor(self):
        r = self.create(self.hep)
        self.assertEqual(r.data['staff'], self.hep.staff_profile.pk)
        self.assertEqual(r.data['staff_name'], 'Hep Staff')

    def test_treating_doctor_must_be_a_doctor(self):
        r = self.create(self.hep, staff=self.coord.staff_profile.pk)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.create(self.hep, staff=self.surg.staff_profile.pk).status_code, 201)

    def test_sign_then_only_addenda(self):
        enc = self.encounter()
        self.as_(self.surg)
        self.assertFalse(self.client.get(f'{ENC}{enc.pk}/').data['can_sign'])
        self.assertEqual(self.client.post(f'{ENC}{enc.pk}/sign/').status_code, 403)  # not the treating doctor
        self.as_(self.hep)
        self.assertTrue(self.client.get(f'{ENC}{enc.pk}/').data['can_sign'])
        self.assertEqual(self.client.post(f'{ENC}{enc.pk}/sign/').status_code, 200)
        self.assertEqual(self.client.patch(f'{ENC}{enc.pk}/', {'clinical_notes': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(f'{ENC}{enc.pk}/').status_code, 400)
        call_command('seed_icd10', stdout=StringIO())
        r = self.client.post(DIAG, {'encounter': enc.pk, 'icd10_code': 'K74.60'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('encounter', r.data)  # refused because it is signed, not because of the code
        r = self.client.post(f'{ENC}{enc.pk}/addenda/', {'text': 'Correction'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['author_name'], 'Hep Staff')

    def test_writes_are_audited_with_patient(self):
        r = self.create(self.hep)
        enc_id = r.data['encounter_id']
        self.client.post(f'{ENC}{enc_id}/sign/')
        self.client.post(f'{ENC}{enc_id}/addenda/', {'text': 'Note'}, format='json')
        rows = AuditLog.objects.filter(entity_type__startswith='emr.').order_by('id')
        self.assertEqual([(r.action, r.entity_type) for r in rows], [
            ('create', 'emr.encounter'), ('status_change', 'emr.encounter'), ('create', 'emr.encounteraddendum'),
        ])
        self.assertTrue(all(row.patient_id == self.own.pk and row.user_id == self.hep.pk for row in rows))

    def test_medical_history_records_staff(self):
        self.as_(self.hep)
        r = self.client.post('/api/emr/medical-history/', {'patient': self.own.pk, 'history_type': 'allergy',
                                                           'description': 'Penicillin'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['recorded_by'], self.hep.staff_profile.pk)


class Icd10Tests(EMRTestBase):
    def setUp(self):
        super().setUp()
        call_command('seed_icd10', stdout=StringIO())

    def search(self, q):
        self.as_(self.hep)
        return [row['code'] for row in self.client.get(ICD, {'q': q}).data]

    def add(self, **data):
        self.as_(self.hep)
        return self.client.post(DIAG, data, format='json')

    def test_search_by_code_and_by_name(self):
        for q in ('K74.6', 'k74.6', 'K746'):
            self.assertEqual(self.search(q), ['K74.60', 'K74.69'])
        for q in ('C22.0', 'liver cell', 'HCC', 'hepatocellular carcinoma'):
            self.assertIn('C22.0', self.search(q))
        self.assertIn('B18.2', self.search('chronic viral hepatitis C'))
        for q in ('', '.', 'no such disease'):
            self.assertEqual(self.search(q), [])

    def test_search_permissions(self):
        for user, code in ((self.hep, 200), (self.surg, 200), (self.coord, 200), (self.rad, 200),
                           (self.billing, 403), (self.nojob, 403), (self.pat_user, 403)):
            with self.subTest(user=user.username):
                self.as_(user)
                self.assertEqual(self.client.get(ICD, {'q': 'C22'}).status_code, code)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(ICD, {'q': 'C22'}).status_code, 401)

    def test_name_always_comes_from_the_catalog(self):
        enc = self.encounter()
        r = self.add(encounter=enc.pk, icd10_code='c22.0', description='typed by hand')
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['icd10_code'], r.data['description']), ('C22.0', 'Liver cell carcinoma'))
        url = f"{DIAG}{r.data['diagnosis_id']}/"
        r = self.client.patch(url, {'icd10_code': 'B18.2'}, format='json')
        self.assertEqual(r.data['description'], 'Chronic viral hepatitis C')
        r = self.client.patch(url, {'description': 'typed by hand'}, format='json')
        self.assertEqual(r.data['description'], 'Chronic viral hepatitis C')

    def test_code_outside_the_catalog_rejected(self):
        enc = self.encounter()
        for code in ('K74.6', 'A00.0', 'cirrhosis', ''):  # K74.6 is only a heading in ICD-10-CM
            with self.subTest(code=code):
                r = self.add(encounter=enc.pk, icd10_code=code, description='Cirrhosis')
                self.assertEqual(r.status_code, 400)
                self.assertIn('icd10_code', r.data)
        self.assertFalse(Diagnosis.objects.exists())

    def test_model_validation_uses_the_catalog(self):  # Django admin
        enc = self.encounter()
        diagnosis = Diagnosis(encounter=enc, patient=self.own, icd10_code='c22.0')
        diagnosis.full_clean(exclude=['description'])
        self.assertEqual(diagnosis.description, 'Liver cell carcinoma')
        with self.assertRaises(ValidationError):
            Diagnosis(encounter=enc, patient=self.own, icd10_code='A00.0').full_clean(exclude=['description'])

    def test_seed_can_run_twice(self):
        self.assertEqual(Icd10Code.objects.count(), 143)
        call_command('seed_icd10', stdout=StringIO())
        self.assertEqual(Icd10Code.objects.count(), 143)

    def test_records_cannot_be_moved_to_another_encounter(self):
        signed, other = self.encounter(), self.encounter()
        diagnosis = Diagnosis.objects.create(encounter=signed, icd10_code='C22.0', description='Liver cell carcinoma')
        vitals = VitalSigns.objects.create(encounter=signed, pulse=70)
        Encounter.objects.filter(pk=signed.pk).update(status=Encounter.Status.SIGNED)
        self.as_(self.hep)
        for url in (f'{DIAG}{diagnosis.pk}/', f'/api/emr/vital-signs/{vitals.pk}/'):
            with self.subTest(url=url):
                r = self.client.patch(url, {'encounter': other.pk}, format='json')
                self.assertEqual(r.status_code, 400)
                self.assertIn('encounter', r.data)
        # Resolving a diagnosis after signing is still allowed.
        r = self.client.patch(f'{DIAG}{diagnosis.pk}/', {'status': 'resolved'}, format='json')
        self.assertEqual(r.status_code, 200)


class PortalTests(EMRTestBase):
    def test_patient_sees_only_own_signed_encounters(self):
        signed = self.encounter(status=Encounter.Status.SIGNED)
        self.encounter()                                              # open: hidden
        self.encounter(patient=self.other, status=Encounter.Status.SIGNED)  # other person: hidden
        self.as_(self.pat_user)
        r = self.client.get(ENC)
        self.assertEqual([row['encounter_id'] for row in r.data], [signed.pk])

    def test_patient_account_without_record_sees_nothing(self):
        User.objects.create_user('lonely', '', PW, role='patient')
        self.client.force_authenticate(User.objects.get(username='lonely'))
        self.encounter(status=Encounter.Status.SIGNED)
        self.assertEqual(self.client.get(ENC).data, [])


class DocumentTests(EMRTestBase):
    def upload(self, user=None, patient=None, **over):
        self.as_(user or self.hep)
        data = {'patient': (patient or self.own).pk, 'title': 'Outside CT', 'document_type': 'external_report',
                'file_path': pdf()}
        data.update(over)
        return self.client.post(DOCS, data, format='multipart')

    def test_upload_release_and_portal_download(self):
        r = self.upload()
        self.assertEqual(r.status_code, 201)
        doc_id = r.data['document_id']
        self.assertTrue(r.data['file_url'].endswith(f'/api/emr/documents/{doc_id}/download/'))

        self.as_(self.pat_user)
        self.assertEqual(self.client.get(DOCS).data, [])
        self.assertEqual(self.client.get(f'{DOCS}{doc_id}/download/').status_code, 404)

        self.as_(self.hep)
        self.assertEqual(self.client.post(f'{DOCS}{doc_id}/release/').status_code, 200)
        self.as_(self.pat_user)
        self.assertEqual(len(self.client.get(DOCS).data), 1)
        resp = self.client.get(f'{DOCS}{doc_id}/download/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b''.join(resp.streaming_content), b'%PDF-1.4 test')

    def test_rejects_unsupported_file_type(self):
        r = self.upload(file_path=SimpleUploadedFile('run.exe', b'MZ', content_type='application/octet-stream'))
        self.assertEqual(r.status_code, 400)

    def test_non_doctor_cannot_release(self):
        doc_id = self.upload().data['document_id']
        self.as_(self.coord)
        self.assertEqual(self.client.post(f'{DOCS}{doc_id}/release/').status_code, 403)


class ConsentDocumentTests(EMRTestBase):
    """Module 2 link: Consent.document → EMR Document (scanned signed form)."""

    def setUp(self):
        super().setUp()
        self.donor = make_patient(first_name='Dina', last_name='Donor', category='donor', phone='0122')

    def consent_form(self, patient):
        return Document.objects.create(patient=patient, uploaded_by=self.coord, title='Signed form',
                                       document_type='consent_form', file_path=pdf('consent.pdf'))

    def record(self, document):
        self.as_(self.coord)
        return self.client.post(f'/api/patients/{self.donor.pk}/consents/', {
            'consent_type': 'donor_surgery', 'signed_at': '2026-03-01T09:30:00Z', 'document': document.pk,
        }, format='json')

    def test_attach_scanned_form(self):
        doc = self.consent_form(self.donor)
        r = self.record(doc)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['document_id'], doc.pk)
        # The signed copy cannot be deleted while the consent exists.
        self.as_(self.hep)
        self.assertEqual(self.client.delete(f'{DOCS}{doc.pk}/').status_code, 400)

    def test_document_of_another_person_rejected(self):
        r = self.record(self.consent_form(self.own))
        self.assertEqual(r.status_code, 400)
        self.assertIn('document', r.data)
        self.assertFalse(Consent.objects.exists())
