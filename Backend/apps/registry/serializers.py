import re

from django.contrib.auth.password_validation import (
    UserAttributeSimilarityValidator, get_default_password_validators, validate_password,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User

from .models import Patient, national_id_validator

SIGNUP_PHONE_PATTERN = re.compile(r'[0-9]{11}')
SIGNUP_PHONE_MESSAGE = 'Enter an 11-digit phone number using numbers only, e.g. 01012345678.'


def signup_password_validators():
    """
    The configured AUTH_PASSWORD_VALIDATORS minus the user-attribute similarity check, so a
    portal password may contain parts of the username. Length, common-password and
    all-numeric checks stay exactly as configured.
    """
    return [v for v in get_default_password_validators()
            if not isinstance(v, UserAttributeSimilarityValidator)]


NATIONAL_ID_TAKEN = ('A patient record with this national ID already exists. '
                     'Please contact the hospital to get access to it.')

# Demographic fields staff may write. MRN, category, account link and registrar never are.
DEMOGRAPHIC_FIELDS = [
    'first_name', 'last_name', 'date_of_birth', 'sex', 'national_id', 'phone', 'address',
    'emergency_contact', 'blood_group', 'height_cm', 'weight_kg',
]
# Contact details a patient may change on their own record (spec §1 "Profile & Password").
PATIENT_CONTACT_FIELDS = ['phone', 'address', 'emergency_contact']


def _django_errors(exc):
    return exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}


def integrity_error_detail(national_id):
    """Explain a unique-constraint race precisely instead of guessing."""
    if national_id and Patient.objects.filter(national_id=national_id).exists():
        return {'national_id': NATIONAL_ID_TAKEN}
    return {'non_field_errors': ['This record could not be saved because of a conflicting change. '
                                 'Please check the details and try again.']}


def reject_unknown_fields(serializer, allowed):
    """Refuse (instead of silently ignoring) attempts to write protected fields."""
    extra = set(serializer.initial_data) - set(allowed)
    if extra:
        raise serializers.ValidationError({name: 'This field cannot be changed here.' for name in sorted(extra)})


class _DemographicsMixin(serializers.ModelSerializer):
    """Shared validation for staff create/update and self-registration."""

    def validate_national_id(self, value):
        value = (value or '').strip() or None
        if value is None:
            return None
        national_id_validator(value)
        qs = Patient.objects.filter(national_id=value)
        if self.instance is not None and isinstance(self.instance, Patient):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(NATIONAL_ID_TAKEN)
        return value

    def validate_blood_group(self, value):
        return value or None  # '' means unknown, stored as NULL

    def validate_date_of_birth(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('Date of birth cannot be in the future.')
        return value

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value.strip()

    validate_last_name = validate_first_name

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value.strip()


# --------------------------------------------------------------------------- read

class PatientListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.SerializerMethodField()
    has_account = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'mrn', 'first_name', 'last_name', 'full_name', 'date_of_birth', 'age', 'sex',
                  'category', 'phone', 'has_account', 'created_at']
        read_only_fields = fields

    def get_age(self, patient):
        return patient.age_on()

    def get_has_account(self, patient):
        return patient.user_id is not None


class PatientDetailSerializer(PatientListSerializer):
    registered_by = serializers.SerializerMethodField()
    account_username = serializers.SerializerMethodField()

    class Meta(PatientListSerializer.Meta):
        fields = PatientListSerializer.Meta.fields + [
            'national_id', 'address', 'emergency_contact', 'blood_group', 'height_cm', 'weight_kg',
            'registered_by', 'account_username', 'updated_at',
        ]
        read_only_fields = fields

    def get_registered_by(self, patient):
        staff = patient.registered_by
        if staff is None:
            return None
        return {'name': staff.user.get_full_name() or staff.user.username, 'job_title': staff.job_title}

    def get_account_username(self, patient):
        return patient.user.username if patient.user_id else None


class OwnPatientRecordSerializer(PatientListSerializer):
    """A patient's view of their own record (no staff/registrar details)."""

    class Meta(PatientListSerializer.Meta):
        fields = [f for f in PatientListSerializer.Meta.fields if f != 'has_account'] + [
            'national_id', 'address', 'emergency_contact', 'blood_group', 'height_cm', 'weight_kg', 'updated_at',
        ]
        read_only_fields = fields


# --------------------------------------------------------------------------- staff write

class PatientCreateSerializer(_DemographicsMixin):
    """Staff registration: a hospital record WITHOUT a login account."""

    class Meta:
        model = Patient
        fields = DEMOGRAPHIC_FIELDS + ['category']
        extra_kwargs = {'national_id': {'validators': []}}  # handled in validate_national_id

    def validate(self, attrs):
        reject_unknown_fields(self, DEMOGRAPHIC_FIELDS + ['category'])
        return attrs

    def create(self, validated):
        patient = Patient(**validated, registered_by=self.context.get('registered_by'))
        try:
            patient.full_clean(exclude=['mrn'])
            with transaction.atomic():
                patient.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        except IntegrityError:  # e.g. a concurrent registration with the same national ID
            raise serializers.ValidationError(integrity_error_detail(patient.national_id))
        return patient


class PatientUpdateSerializer(_DemographicsMixin):
    """Staff demographic edits. Category has its own endpoint; MRN/account never change here."""

    class Meta:
        model = Patient
        fields = DEMOGRAPHIC_FIELDS
        extra_kwargs = {'national_id': {'validators': []}}

    def validate(self, attrs):
        reject_unknown_fields(self, DEMOGRAPHIC_FIELDS)
        return attrs

    def update(self, patient, validated):
        for field, value in validated.items():
            setattr(patient, field, value)
        try:
            patient.full_clean(exclude=['mrn'])
            patient.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        except IntegrityError:
            raise serializers.ValidationError(integrity_error_detail(patient.national_id))
        return patient


class PatientCategorySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Patient.Category.choices)


class OwnContactUpdateSerializer(serializers.ModelSerializer):
    """A patient updates only the contact details on their own record."""

    class Meta:
        model = Patient
        fields = PATIENT_CONTACT_FIELDS

    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value.strip()

    def validate(self, attrs):
        reject_unknown_fields(self, PATIENT_CONTACT_FIELDS)
        return attrs


# --------------------------------------------------------------------------- self-registration

class SelfRegistrationSerializer(_DemographicsMixin):
    """
    Portal self-registration: creates a `role=patient` account AND its own patient record in one
    transaction. Category may only be liver_patient or donor (recipient is assigned by clinicians).
    """

    SELF_CATEGORIES = [(Patient.Category.LIVER_PATIENT, 'Liver patient'), (Patient.Category.DONOR, 'Living donor')]

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(max_length=254)  # required for self-registration (D5)
    category = serializers.ChoiceField(choices=SELF_CATEGORIES)
    phone = serializers.CharField(max_length=20, error_messages={
        'required': SIGNUP_PHONE_MESSAGE, 'blank': SIGNUP_PHONE_MESSAGE, 'null': SIGNUP_PHONE_MESSAGE})

    class Meta:
        model = Patient
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'date_of_birth', 'sex',
                  'national_id', 'phone', 'address', 'emergency_contact', 'category']
        extra_kwargs = {'national_id': {'validators': []}}

    def validate_username(self, value):
        value = value.strip()
        User.username_validator(value)
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def validate_email(self, value):
        value = value.strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with that email address already exists.')
        return value

    def validate_phone(self, value):
        """Exactly 11 ASCII digits, kept as a string (leading zero preserved)."""
        value = value.strip()
        if not SIGNUP_PHONE_PATTERN.fullmatch(value):
            raise serializers.ValidationError(SIGNUP_PHONE_MESSAGE)
        return value

    def validate(self, attrs):
        allowed = self.Meta.fields
        reject_unknown_fields(self, allowed)
        candidate = User(username=attrs['username'], email=attrs['email'],
                         first_name=attrs['first_name'], last_name=attrs['last_name'])
        try:
            validate_password(attrs['password'], candidate, password_validators=signup_password_validators())
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated):
        account_fields = {k: validated.pop(k) for k in ('username', 'password', 'email')}
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    account_fields['username'], account_fields['email'], account_fields['password'],
                    role=User.Role.PATIENT, first_name=validated['first_name'],
                    last_name=validated['last_name'],
                )
                patient = Patient(**validated, user=user, registered_by=None)
                patient.full_clean(exclude=['mrn'])
                patient.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        except IntegrityError:
            raise serializers.ValidationError(integrity_error_detail(validated.get('national_id')))
        return patient
