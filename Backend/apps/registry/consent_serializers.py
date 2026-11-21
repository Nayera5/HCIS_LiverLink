"""Serializers for consents (Stage 6, spec §4.7). See models.Consent for the history rules."""
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import Staff, User

from .models import Consent

TYPE_NOT_ELIGIBLE = {
    'donor_surgery': 'A donor surgery consent can only be recorded for a person registered as a living donor.',
    'transplant_surgery': 'A transplant surgery consent can only be recorded for a transplant recipient.',
}


def _staff(staff):
    if staff is None:
        return None
    return {'id': staff.pk, 'name': staff.user.get_full_name() or staff.user.username, 'job_title': staff.job_title}


def active_witnesses():
    """
    Who may be named as witness: active clinical and coordination staff (hepatologist, radiologist,
    transplant surgeon, transplant coordinator). Billing Admin and Super Admin are excluded, and so
    is a profile whose job title does not match the account role (fails closed, like rbac.py).
    """
    return Staff.objects.filter(
        user__is_active=True, user__role=User.Role.CLINICAL_STAFF, job_title__in=Staff.CLINICAL_TITLES,
    ).select_related('user')


class ConsentRecordSerializer(serializers.Serializer):
    """{consent_type, signed_at, witnessed_by?} for the patient in context."""

    consent_type = serializers.ChoiceField(choices=Consent.ConsentType.choices)
    signed_at = serializers.DateTimeField()
    witnessed_by = serializers.PrimaryKeyRelatedField(
        queryset=active_witnesses(), required=False, allow_null=True,
        error_messages={'does_not_exist': 'Choose an active clinical or coordination staff member as the witness.',
                        'incorrect_type': 'Choose an active clinical or coordination staff member as the witness.'})

    def validate_signed_at(self, value):
        if value > timezone.now():
            raise serializers.ValidationError('The signing date cannot be in the future.')
        return value

    def validate(self, attrs):
        patient = self.context['patient']
        kind = attrs['consent_type']
        if patient.category not in Consent.ELIGIBLE_CATEGORIES[kind]:
            raise serializers.ValidationError({'consent_type': TYPE_NOT_ELIGIBLE[kind]})
        if attrs['signed_at'].date() < patient.date_of_birth:
            raise serializers.ValidationError({'signed_at': 'The signing date is before the date of birth.'})
        if Consent.has_active(patient, kind):
            raise serializers.ValidationError(
                {'consent_type': 'This person already has an active consent of this type. Withdraw it first.'})
        return attrs


class ConsentSerializer(serializers.ModelSerializer):
    """Staff view (consents.view): the full record including who recorded and withdrew it."""

    type_label = serializers.CharField(source='get_consent_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    witnessed_by = serializers.SerializerMethodField()
    recorded_by = serializers.SerializerMethodField()
    withdrawn_by = serializers.SerializerMethodField()

    class Meta:
        model = Consent
        fields = ['id', 'patient_id', 'consent_type', 'type_label', 'status', 'status_label', 'is_active',
                  'signed_at', 'witnessed_by', 'recorded_by', 'withdrawn_at', 'withdrawn_by', 'created_at']
        read_only_fields = fields

    def get_witnessed_by(self, consent):
        return _staff(consent.witnessed_by)

    def get_recorded_by(self, consent):
        return _staff(consent.recorded_by)

    def get_withdrawn_by(self, consent):
        return _staff(consent.withdrawn_by)


class OwnConsentSerializer(serializers.ModelSerializer):
    """Portal (self.consents): own consents, read-only; staff are shown by name only."""

    type_label = serializers.CharField(source='get_consent_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    witnessed_by = serializers.SerializerMethodField()

    class Meta:
        model = Consent
        fields = ['id', 'consent_type', 'type_label', 'status', 'status_label', 'signed_at', 'witnessed_by',
                  'withdrawn_at']
        read_only_fields = fields

    def get_witnessed_by(self, consent):
        staff = consent.witnessed_by
        return (staff.user.get_full_name() or staff.user.username) if staff else None


class WitnessSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = ['id', 'name', 'job_title']
        read_only_fields = fields

    def get_name(self, staff):
        return staff.user.get_full_name() or staff.user.username
