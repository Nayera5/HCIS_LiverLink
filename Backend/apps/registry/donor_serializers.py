"""
Serializers for donor applications (Stage 5, spec §2 "Donor Application" and §4.6).

Privacy rules:
- Donors name the intended recipient by MRN only. The backend looks the MRN up; the donor never
  sees the recipient's name or any other data, and a wrong MRN and an ineligible patient get the
  same error, so the endpoint cannot be used to probe who is registered.
- Donors never see screening notes or who screened their application.
"""
from rest_framework import serializers

from apps.transplant.models import TransplantCase

from .models import DonorApplication, Patient

MRN_NOT_FOUND = 'No eligible recipient was found with this MRN. Please check the number with the recipient.'


def normalize_mrn(value):
    return (value or '').strip().upper()


def find_recipient(mrn, *, for_update=False):
    """The patient who may be named as recipient for this MRN, or None (not found / not eligible)."""
    cases = TransplantCase.objects.filter(
        recipient__mrn=normalize_mrn(mrn),
        recipient__category__in=DonorApplication.RECIPIENT_CATEGORIES,
        status__in=TransplantCase.DONOR_MATCHING_STATUSES,
    ).select_related('recipient')
    if for_update:
        cases = cases.select_for_update()
    case = cases.first()
    return case.recipient if case else None


class _ApplicationInputMixin(serializers.Serializer):
    recipient_mrn = serializers.CharField(max_length=20)
    relationship = serializers.CharField(max_length=50)

    def validate_relationship(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Describe your relationship to the recipient (e.g. son, wife).')
        return value

    def resolve(self, attrs, donor):
        """Validates the recipient against `donor`; returns the extra fields for create()."""
        if normalize_mrn(attrs['recipient_mrn']) == donor.mrn:
            raise serializers.ValidationError({'recipient_mrn': 'The donor and the recipient must be different people.'})
        recipient = find_recipient(attrs['recipient_mrn'])
        if recipient is None:
            raise serializers.ValidationError({'recipient_mrn': MRN_NOT_FOUND})
        if DonorApplication.objects.filter(donor=donor, recipient=recipient,
                                           status__in=DonorApplication.OPEN_STATUSES).exists():
            raise serializers.ValidationError(
                {'recipient_mrn': 'There is already an open application for this recipient.'})
        return {'donor': donor, 'recipient': recipient, 'relationship': attrs['relationship']}


class OwnApplicationCreateSerializer(_ApplicationInputMixin):
    """Donor portal: {recipient_mrn, relationship}. The donor is always the signed-in person."""

    def validate(self, attrs):
        return self.resolve(attrs, self.context['donor'])


class StaffApplicationCreateSerializer(_ApplicationInputMixin):
    """Coordinator on the donor's behalf: {donor_mrn, recipient_mrn, relationship}."""

    donor_mrn = serializers.CharField(max_length=20)

    def validate(self, attrs):
        donor = Patient.objects.filter(mrn=normalize_mrn(attrs['donor_mrn'])).first()
        if donor is None:
            raise serializers.ValidationError({'donor_mrn': 'No patient was found with this MRN.'})
        if donor.category != Patient.Category.DONOR:
            raise serializers.ValidationError(
                {'donor_mrn': 'This person is not registered as a living donor. Change their category first.'})
        return self.resolve(attrs, donor)


class OwnApplicationSerializer(serializers.ModelSerializer):
    """What a donor sees about their own application: no recipient details, notes or screener."""

    recipient_mrn = serializers.CharField(source='recipient.mrn', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    can_withdraw = serializers.BooleanField(source='is_open', read_only=True)

    class Meta:
        model = DonorApplication
        fields = ['id', 'recipient_mrn', 'relationship', 'status', 'status_label', 'can_withdraw',
                  'submitted_at', 'updated_at']
        read_only_fields = fields


def _person(patient):
    return {'id': patient.pk, 'mrn': patient.mrn, 'name': patient.full_name, 'category': patient.category,
            'blood_group': patient.blood_group}


class StaffApplicationSerializer(serializers.ModelSerializer):
    """Staff view (donor_applications.view): both people, screening details and next statuses."""

    donor = serializers.SerializerMethodField()
    recipient = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    screened_by = serializers.SerializerMethodField()
    next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = DonorApplication
        fields = ['id', 'donor', 'recipient', 'relationship', 'status', 'status_label', 'is_open',
                  'next_statuses', 'screened_by', 'screened_at', 'screening_notes', 'submitted_at', 'updated_at']
        read_only_fields = fields

    def get_donor(self, application):
        return _person(application.donor)

    def get_recipient(self, application):
        return _person(application.recipient)

    def get_screened_by(self, application):
        staff = application.screened_by
        if staff is None:
            return None
        return {'name': staff.user.get_full_name() or staff.user.username, 'job_title': staff.job_title}

    def get_next_statuses(self, application):
        return list(application.next_screening_statuses())


class ScreeningSerializer(serializers.Serializer):
    """Coordinator decision: {status, screening_notes?}. Notes are required to reject."""

    status = serializers.ChoiceField(choices=['screening', 'accepted', 'rejected'])
    screening_notes = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    def validate(self, attrs):
        notes = attrs.get('screening_notes')
        if notes is not None:
            attrs['screening_notes'] = notes.strip()
        existing = (self.context['application'].screening_notes or '').strip()
        if attrs['status'] == 'rejected' and not (attrs.get('screening_notes') or existing):
            raise serializers.ValidationError({'screening_notes': 'Give the reason for rejecting the application.'})
        return attrs
