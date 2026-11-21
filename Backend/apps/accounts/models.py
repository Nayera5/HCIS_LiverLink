from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(DjangoUserManager):
    """Django's standard username manager, plus LiverLink's required `role`."""

    def _create_user_object(self, username, email, password, **extra_fields):
        user = super()._create_user_object(username, email, password, **extra_fields)
        # Turn constraint violations (e.g. "Nada" vs "nada", duplicate email, bad role)
        # into a clear ValidationError instead of a database IntegrityError.
        user.validate_constraints()
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not extra_fields.get('role'):
            raise ValueError('A role is required.')
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Django's create_superuser already forces is_staff=True and is_superuser=True.
        extra_fields.setdefault('role', User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    LiverLink login account, stored in Django's original `auth_user` table.

    - Login: username + password (Django standard; the username lookup is case-sensitive).
    - Email: optional; for contact, notifications and password recovery only.
    - Names: first_name / last_name; use get_full_name() (replaces the spec's Staff.full_name).
    - Access is split in two independent layers:
        * `role` drives LiverLink's own RBAC (with Staff.job_title as the sub-role);
        * `is_staff` / `is_superuser` only control the Django admin site.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        CLINICAL_STAFF = 'clinical_staff', 'Clinical staff'
        PATIENT = 'patient', 'Patient'

    # The existing auth_user.id column is a 32-bit integer; keep it.
    id = models.AutoField(primary_key=True, verbose_name='ID')
    role = models.CharField(max_length=20, choices=Role.choices)

    objects = UserManager()

    # Inherited unchanged from AbstractUser: USERNAME_FIELD = 'username',
    # EMAIL_FIELD = 'email', REQUIRED_FIELDS = ['email'] (prompted, may be left blank).

    class Meta(AbstractUser.Meta):
        db_table = 'auth_user'
        constraints = [
            models.CheckConstraint(
                condition=Q(role__in=['admin', 'clinical_staff', 'patient']),
                name='accounts_user_role_valid',
            ),
            models.UniqueConstraint(
                Lower('username'),
                name='accounts_user_username_ci_unique',
                violation_error_message='A user with that username already exists.',
            ),
            models.UniqueConstraint(
                Lower('email'),
                condition=~Q(email=''),
                name='accounts_user_email_ci_unique',
                violation_error_message='A user with that email address already exists.',
            ),
            # Patient/donor accounts can never reach the Django admin site.
            models.CheckConstraint(
                condition=~Q(role='patient') | Q(is_staff=False, is_superuser=False),
                name='accounts_user_patient_no_admin_access',
                violation_error_message='Patient accounts cannot have Django admin access.',
            ),
        ]


class Staff(models.Model):
    """
    Profile of a hospital employee (spec §4.3). The job title is the sub-role that decides
    what a staff member may do (see apps/accounts/rbac.py).

    Deviation from the spec (agreed): no `full_name` column. The display name comes from
    `user.get_full_name()` (User.first_name / User.last_name), which is required for staff.
    """

    class JobTitle(models.TextChoices):
        HEPATOLOGIST = 'hepatologist', 'Hepatologist'
        RADIOLOGIST = 'radiologist', 'Radiologist'
        TRANSPLANT_SURGEON = 'transplant_surgeon', 'Transplant surgeon'
        TRANSPLANT_COORDINATOR = 'transplant_coordinator', 'Transplant coordinator'
        SUPER_ADMIN = 'super_admin', 'Super admin'
        BILLING_ADMIN = 'billing_admin', 'Billing admin'

    ADMIN_TITLES = frozenset({JobTitle.SUPER_ADMIN, JobTitle.BILLING_ADMIN})
    CLINICAL_TITLES = frozenset({
        JobTitle.HEPATOLOGIST, JobTitle.RADIOLOGIST,
        JobTitle.TRANSPLANT_SURGEON, JobTitle.TRANSPLANT_COORDINATOR,
    })

    user = models.OneToOneField(
        'accounts.User', on_delete=models.PROTECT, related_name='staff_profile',
    )
    job_title = models.CharField(max_length=30, choices=JobTitle.choices)
    license_no = models.CharField(max_length=50, null=True, blank=True, unique=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'staff member'
        verbose_name_plural = 'staff'
        constraints = [
            models.CheckConstraint(
                condition=Q(job_title__in=[
                    'hepatologist', 'radiologist', 'transplant_surgeon',
                    'transplant_coordinator', 'super_admin', 'billing_admin',
                ]),
                name='accounts_staff_job_title_valid',
            ),
        ]

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_job_title_display()})'

    @classmethod
    def role_for_job_title(cls, job_title):
        return User.Role.ADMIN if job_title in cls.ADMIN_TITLES else User.Role.CLINICAL_STAFF

    def save(self, *args, **kwargs):
        # Store "no licence" as NULL so the unique constraint allows many of them.
        self.license_no = (self.license_no or '').strip() or None
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        self.license_no = (self.license_no or '').strip() or None
        user = self.user
        errors = {}
        if user.role == User.Role.PATIENT:
            errors['user'] = 'Patient accounts cannot have a staff profile.'
        elif user.role != self.role_for_job_title(self.job_title):
            errors['job_title'] = (
                f'Job title "{self.job_title}" requires role '
                f'"{self.role_for_job_title(self.job_title)}", but the account has role "{user.role}".'
            )
        if not (user.first_name.strip() and user.last_name.strip()):
            errors['user'] = 'Staff members must have a first and last name.'
        if errors:
            raise ValidationError(errors)


class AuditLogQuerySet(models.QuerySet):
    """Audit rows are append-only: bulk updates and deletes are refused."""

    def update(self, **kwargs):
        raise PermissionError('Audit log entries cannot be changed.')

    def delete(self):
        raise PermissionError('Audit log entries cannot be deleted.')


class AuditLog(models.Model):
    """
    Security log of important actions (spec §4.4): who viewed, created or changed which record,
    and when. Rows are only ever added (spec business rule): updates and deletes are refused at
    the model and queryset level (no database trigger), and the referenced user/patient cannot
    be deleted (PROTECT).

    `user` is empty for events without an authenticated account (e.g. a failed login or a
    password-reset request); `actor` then identifies who acted. `actor` also keeps the username
    as it was at the time of the event. Never store passwords, tokens or other secrets in it.
    """

    class Action(models.TextChoices):
        VIEW = 'view', 'View'
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        EXPORT = 'export', 'Export'
        PROFILE_VIEW = 'profile_view', 'Profile view'        # opening one patient's profile (a read)
        CATEGORY_CHANGE = 'category_change', 'Category change'
        ACTIVATE = 'activate', 'Activate'                    # account re-enabled
        DEACTIVATE = 'deactivate', 'Deactivate'              # account disabled

    # Actions that only read data; every other action is a write or session event.
    READ_ACTIONS = frozenset({Action.VIEW, Action.PROFILE_VIEW, Action.EXPORT})

    # db_index=False: the composite (user, timestamp) / (patient, timestamp) indexes below
    # already serve lookups by user or patient, so single-column indexes would be redundant.
    user = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.PROTECT, related_name='audit_logs',
        db_index=False, help_text='User who did the action (empty for anonymous events).',
    )
    actor = models.CharField(
        max_length=150, blank=True,
        help_text='Who acted: the username at the time, or for anonymous events the identifier '
                  'given (e.g. the username typed at a failed login). Never a password or token.',
    )
    patient = models.ForeignKey(
        'registry.Patient', null=True, blank=True, on_delete=models.PROTECT, related_name='audit_logs',
        db_index=False, help_text='Patient whose record was touched (if any).',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    entity_type = models.CharField(max_length=100, help_text='Table the action was on, e.g. registry.patient.')
    entity_id = models.BigIntegerField(null=True, blank=True, help_text='ID of the row the action was on.')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, editable=False)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ['-timestamp', '-id']
        indexes = [
            models.Index(fields=['patient', 'timestamp'], name='accounts_audit_patient_idx'),
            models.Index(fields=['user', 'timestamp'], name='accounts_audit_user_idx'),
            models.Index(fields=['entity_type', 'entity_id'], name='accounts_audit_entity_idx'),
            models.Index(fields=['timestamp'], name='accounts_audit_time_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(action__in=['view', 'create', 'update', 'delete', 'login', 'logout', 'export',
                                        'profile_view', 'category_change', 'activate', 'deactivate']),
                name='accounts_auditlog_action_valid'),
            # Every entry must say who acted: a linked user, or an actor identifier.
            models.CheckConstraint(
                condition=Q(user__isnull=False) | ~Q(actor=''),
                name='accounts_auditlog_has_actor'),
        ]

    def __str__(self):
        who = self.actor or self.user_id
        return f'{self.timestamp:%Y-%m-%d %H:%M} {who} {self.action} {self.entity_type}#{self.entity_id}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError('Audit log entries cannot be changed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('Audit log entries cannot be deleted.')

    @classmethod
    def record(cls, action, entity_type, *, user=None, actor='', entity_id=None, patient=None,
               ip_address=None):
        """
        Append one entry. `entity_type` is a model label such as 'registry.patient'.
        With a user, `actor` defaults to their current username. Anonymous events must pass
        `actor` (an identifier only, never a secret).
        """
        if user is not None and not getattr(user, 'is_authenticated', False):
            user = None  # AnonymousUser
        actor = (actor or (user.get_username() if user is not None else '')).strip()[:150]
        return cls.objects.create(
            user=user, actor=actor, action=action, entity_type=entity_type, entity_id=entity_id,
            patient=patient, ip_address=ip_address,
        )
