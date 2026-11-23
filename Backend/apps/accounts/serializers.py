from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import AuditLog, Staff, User
from .rbac import capabilities_for, effective_job_title, get_staff_profile


def _django_errors(exc):
    """Convert a Django ValidationError into DRF's format."""
    if hasattr(exc, 'message_dict'):
        return exc.message_dict
    return {'non_field_errors': exc.messages}


def _check_unique_ci(field, value, exclude_pk=None):
    if not value:
        return
    qs = User.objects.filter(**{f'{field}__iexact': value})
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    if qs.exists():
        label = 'username' if field == 'username' else 'email address'
        raise serializers.ValidationError(f'A user with that {label} already exists.')


# --------------------------------------------------------------------------- current user

class MeSerializer(serializers.ModelSerializer):
    """The signed-in user's own account, profile and capabilities (drives the frontend)."""

    full_name = serializers.CharField(source='get_full_name', read_only=True)
    job_title = serializers.SerializerMethodField()
    staff_profile = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role',
            'job_title', 'staff_profile', 'capabilities', 'is_superuser', 'last_login', 'date_joined',
        ]
        read_only_fields = fields

    def get_job_title(self, user):
        return effective_job_title(user)

    def get_staff_profile(self, user):
        staff = get_staff_profile(user)
        if staff is None:
            return None
        return {
            'job_title': staff.job_title,
            'job_title_display': staff.get_job_title_display(),
            'department': staff.department,
            'license_no': staff.license_no,
            'phone': staff.phone,
        }

    def get_capabilities(self, user):
        return sorted(capabilities_for(user))


class MeUpdateSerializer(serializers.Serializer):
    """Users update their own contact details (spec §1 'Profile & Password')."""

    email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_email(self, value):
        value = value.strip()
        _check_unique_ci('email', value, exclude_pk=self.instance.pk)
        return value

    def validate(self, attrs):
        if 'phone' in attrs and get_staff_profile(self.instance) is None:
            raise serializers.ValidationError(
                {'phone': 'Only staff accounts have a phone number on their account profile.'})
        return attrs

    @transaction.atomic
    def update(self, user, validated):
        if 'email' in validated:
            user.email = User.objects.normalize_email(validated['email'])
            user.save(update_fields=['email'])
        if 'phone' in validated:
            staff = user.staff_profile
            staff.phone = validated['phone'].strip()
            staff.save(update_fields=['phone'])
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Your current password is incorrect.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if attrs['new_password'] == attrs['current_password']:
            raise serializers.ValidationError({'new_password': 'Choose a password different from your current one.'})
        try:
            validate_password(attrs['new_password'], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.messages})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# --------------------------------------------------------------------------- user management

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    job_title = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    has_staff_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'role',
            'job_title', 'department', 'has_staff_profile', 'is_active', 'is_superuser',
            'last_login', 'date_joined',
        ]
        read_only_fields = fields

    def get_job_title(self, user):
        staff = get_staff_profile(user)
        return staff.job_title if staff else None

    def get_department(self, user):
        staff = get_staff_profile(user)
        return staff.department if staff else ''

    def get_has_staff_profile(self, user):
        return get_staff_profile(user) is not None


class UserDetailSerializer(UserListSerializer):
    license_no = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    effective_job_title = serializers.SerializerMethodField()

    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + ['license_no', 'phone', 'effective_job_title']
        read_only_fields = fields

    def get_license_no(self, user):
        staff = get_staff_profile(user)
        return staff.license_no if staff else None

    def get_phone(self, user):
        staff = get_staff_profile(user)
        return staff.phone if staff else ''

    def get_effective_job_title(self, user):
        return effective_job_title(user)


class _StaffFieldsMixin(serializers.Serializer):
    job_title = serializers.ChoiceField(choices=Staff.JobTitle.choices)
    department = serializers.CharField(required=False, allow_blank=True, max_length=100)
    license_no = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate_license_no(self, value):
        value = (value or '').strip() or None
        if value:
            qs = Staff.objects.filter(license_no=value)
            user = getattr(self, 'instance', None)
            if user is not None:
                qs = qs.exclude(user=user)
            if qs.exists():
                raise serializers.ValidationError('Another staff member already has this license number.')
        return value


JOB_TITLE_REQUIRED = 'Choose a job title.'


class StaffAccountCreateSerializer(_StaffFieldsMixin):
    """Admin creates a staff account: User + Staff profile in one transaction."""

    # A new staff account must always have a job title (it decides the role and permissions).
    job_title = serializers.ChoiceField(
        choices=Staff.JobTitle.choices, required=True, allow_null=False, allow_blank=False,
        error_messages={'required': JOB_TITLE_REQUIRED, 'null': JOB_TITLE_REQUIRED,
                        'blank': JOB_TITLE_REQUIRED, 'invalid_choice': JOB_TITLE_REQUIRED},
    )
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        value = value.strip()
        User.username_validator(value)
        _check_unique_ci('username', value)
        return value

    def validate_email(self, value):
        value = value.strip()
        _check_unique_ci('email', value)
        return value

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value.strip()

    validate_last_name = validate_first_name

    def validate(self, attrs):
        candidate = User(username=attrs['username'], email=attrs.get('email', ''),
                         first_name=attrs['first_name'], last_name=attrs['last_name'])
        try:
            validate_password(attrs['password'], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        return attrs

    @transaction.atomic
    def create(self, validated):
        job_title = validated['job_title']
        try:
            user = User.objects.create_user(
                validated['username'], validated.get('email', ''), validated['password'],
                role=Staff.role_for_job_title(job_title),
                first_name=validated['first_name'], last_name=validated['last_name'],
            )
            staff = Staff(
                user=user, job_title=job_title,
                department=validated.get('department', '').strip(),
                license_no=validated.get('license_no'),
                phone=validated.get('phone', '').strip(),
            )
            staff.full_clean()
            staff.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        return user


class StaffAccountUpdateSerializer(_StaffFieldsMixin):
    """
    Admin edits a staff/admin account. Setting `job_title` on an account that has no Staff
    profile (e.g. a clinical_staff account created earlier) creates the profile; the account
    role follows the job title (admin titles -> admin, clinical titles -> clinical_staff).
    """

    job_title = serializers.ChoiceField(choices=Staff.JobTitle.choices, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    first_name = serializers.CharField(required=False, max_length=150)
    last_name = serializers.CharField(required=False, max_length=150)

    def validate_email(self, value):
        value = value.strip()
        _check_unique_ci('email', value, exclude_pk=self.instance.pk)
        return value

    def validate_first_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('This field may not be blank.')
        return value.strip()

    validate_last_name = validate_first_name

    def validate(self, attrs):
        user = self.instance
        request_user = self.context['request'].user
        if user.role == User.Role.PATIENT:
            raise serializers.ValidationError(
                'Patient and donor accounts are managed through the patient registry; '
                'only activation can be changed here.')
        if user.is_superuser and not request_user.is_superuser:
            raise serializers.ValidationError('Only a system superuser can edit a superuser account.')
        if user.pk == request_user.pk and 'job_title' in attrs \
                and attrs['job_title'] != effective_job_title(user):
            raise serializers.ValidationError({'job_title': 'You cannot change your own job title.'})
        staff = get_staff_profile(user)
        staff_fields = {'department', 'license_no', 'phone'} & attrs.keys()
        if staff is None and staff_fields and 'job_title' not in attrs:
            raise serializers.ValidationError(
                {'job_title': 'Assign a job title before setting staff profile details.'})
        return attrs

    @transaction.atomic
    def update(self, user, validated):
        for field in ('email', 'first_name', 'last_name'):
            if field in validated:
                value = validated[field]
                setattr(user, field, User.objects.normalize_email(value) if field == 'email' else value)
        staff = get_staff_profile(user)
        if 'job_title' in validated:
            user.role = Staff.role_for_job_title(validated['job_title'])
            if staff is None:
                staff = Staff(user=user)
            staff.job_title = validated['job_title']
        if staff is not None:
            for field in ('department', 'phone'):
                if field in validated:
                    setattr(staff, field, validated[field].strip())
            if 'license_no' in validated:
                staff.license_no = validated['license_no']
        try:
            user.full_clean(exclude=['password'])
            user.save()
            if staff is not None:
                staff.user = user
                staff.full_clean()
                staff.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_django_errors(exc))
        return user


# --------------------------------------------------------------------------- audit log viewer

class AuditLogSerializer(serializers.ModelSerializer):
    """One audit entry for the Super Admin viewer. Read-only. `changes`/`reason` only for clinical edits."""

    action_label = serializers.CharField(source='get_action_display', read_only=True)
    is_read = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(read_only=True)
    patient = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ('id', 'timestamp', 'actor', 'user_id', 'action', 'action_label', 'is_read',
                  'entity_type', 'entity_id', 'patient', 'ip_address', 'changes', 'reason')
        read_only_fields = fields

    def get_is_read(self, entry):
        return entry.action in AuditLog.READ_ACTIONS

    def get_patient(self, entry):
        patient = entry.patient
        if patient is None:
            return None
        return {'id': patient.pk, 'mrn': patient.mrn, 'name': f'{patient.first_name} {patient.last_name}'}


class AuditLogFilterSerializer(serializers.Serializer):
    """Validates the viewer's query parameters (all optional)."""

    action = serializers.ChoiceField(choices=AuditLog.Action.choices, required=False)
    kind = serializers.ChoiceField(choices=('read', 'write'), required=False)
    user = serializers.IntegerField(min_value=1, required=False)
    patient = serializers.IntegerField(min_value=1, required=False)
    entity_type = serializers.CharField(max_length=100, required=False)
    entity_id = serializers.IntegerField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        start, end = attrs.get('date_from'), attrs.get('date_to')
        if start and end and start > end:
            raise serializers.ValidationError({'date_to': 'Must be on or after date_from.'})
        return attrs
