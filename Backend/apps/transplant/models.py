"""
Modules 11 & 12 – Transplant Case Management and Post-Transplant Follow-up.

Entities (ER §4.29–§4.37):
    TransplantCase, CaseDonor, ChecklistItem, CommitteeDecision,
    CommitteeMember, Surgery, SurgeryTeamMember, FollowUpPlan, FollowUpVisit.

Owner: Person 4.
Linked modules:
  - module 1 (accounts): Staff, User
  - module 2 (registry): Patient, DonorApplication, Consent
  - module 3 (scheduling): Appointment
  - module 4 (emr): Encounter
"""
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone


# ───────────────────────────────────────────────────────────────────────────
# ABO compatibility helper
# ───────────────────────────────────────────────────────────────────────────
# For liver transplant, ABO (not Rh) determines compatibility.
_ABO_MAP = {
    'A+': 'A', 'A-': 'A',
    'B+': 'B', 'B-': 'B',
    'AB+': 'AB', 'AB-': 'AB',
    'O+': 'O', 'O-': 'O',
}
# ABO rules: O → universal donor, AB → universal recipient, same type compat.
_ABO_COMPAT = {
    'O': {'A', 'B', 'AB', 'O'},
    'A': {'A', 'AB'},
    'B': {'B', 'AB'},
    'AB': {'AB'},
}


def check_abo_compatibility(donor_blood, recipient_blood):
    """Return True/False/None. None when either blood group is unknown."""
    d = _ABO_MAP.get(donor_blood)
    r = _ABO_MAP.get(recipient_blood)
    if d is None or r is None:
        return None
    return r in _ABO_COMPAT.get(d, set())


# ───────────────────────────────────────────────────────────────────────────
# 4.29  TransplantCase
# ───────────────────────────────────────────────────────────────────────────
class TransplantCase(models.Model):
    """The transplant process for one recipient, from referral to follow-up."""

    class Status(models.TextChoices):
        REFERRED = 'referred', 'Referred'
        UNDER_EVALUATION = 'under_evaluation', 'Under evaluation'
        COMMITTEE_REVIEW = 'committee_review', 'Committee review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SURGERY_SCHEDULED = 'surgery_scheduled', 'Surgery scheduled'
        TRANSPLANTED = 'transplanted', 'Transplanted'
        FOLLOW_UP = 'follow_up', 'Follow-up'
        CLOSED = 'closed', 'Closed'

    # Valid forward transitions (business rule §4.29).
    TRANSITIONS = {
        'referred': {'under_evaluation'},
        'under_evaluation': {'committee_review'},
        'committee_review': {'approved', 'rejected', 'under_evaluation'},  # under_evaluation = more_tests_needed
        'approved': {'surgery_scheduled', 'closed'},
        'rejected': {'closed'},
        'surgery_scheduled': {'transplanted', 'closed'},
        'transplanted': {'follow_up'},
        'follow_up': {'closed'},
        'closed': set(),
    }

    recipient = models.ForeignKey(
        'registry.Patient', on_delete=models.PROTECT,
        related_name='transplant_cases',
        help_text='Patient who needs the transplant.',
    )
    referral_encounter = models.ForeignKey(
        'emr.Encounter', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='transplant_referrals',
        help_text='Visit in which the referral was made.',
    )
    referred_by = models.ForeignKey(
        'accounts.Staff', on_delete=models.PROTECT,
        related_name='referred_cases',
        help_text='Hepatologist who referred the patient.',
    )
    coordinator = models.ForeignKey(
        'accounts.Staff', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='coordinated_cases',
        help_text='Coordinator managing the case.',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REFERRED,
    )
    referral_date = models.DateField()
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'],
                         name='transplant_case_status_idx'),
            models.Index(fields=['recipient', 'status'],
                         name='transplant_case_recip_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_case_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(status__in=[
                    'referred', 'under_evaluation', 'committee_review',
                    'approved', 'rejected', 'surgery_scheduled',
                    'transplanted', 'follow_up', 'closed',
                ]),
                name='transplant_case_status_valid',
            ),
            # Business rule: a recipient has at most one open case at a time.
            models.UniqueConstraint(
                fields=['recipient'],
                condition=~Q(status='closed'),
                name='transplant_case_one_open_per_recipient',
                violation_error_message=(
                    'This recipient already has an open transplant case.'
                ),
            ),
        ]

    def __str__(self):
        return f'Case #{self.pk} – {self.recipient_id} ({self.status})'

    def can_transition_to(self, new_status):
        return new_status in self.TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        """Validate and apply a status transition. Raises ValidationError on failure."""
        if not self.can_transition_to(new_status):
            raise ValidationError({
                'status': (
                    f'Cannot move from "{self.get_status_display()}" '
                    f'to "{new_status}".'
                ),
            })
        # Gate: committee_review requires all required checklist items done/waived.
        if new_status == self.Status.COMMITTEE_REVIEW:
            pending = self.checklist_items.filter(
                is_required=True, status='pending',
            ).exists()
            if pending:
                raise ValidationError({
                    'status': (
                        'Cannot move to committee review: required checklist '
                        'items are still pending.'
                    ),
                })
        old_status = self.status
        self.status = new_status
        if new_status == self.Status.CLOSED:
            self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at', 'updated_at'])

        from apps.notifications import events  # module 14: case status updates
        events.case_stage_changed(self, old_status)


# ───────────────────────────────────────────────────────────────────────────
# 4.30  CaseDonor
# ───────────────────────────────────────────────────────────────────────────
class CaseDonor(models.Model):
    """Links a candidate donor to a transplant case."""

    class Status(models.TextChoices):
        CANDIDATE = 'candidate', 'Candidate'
        UNDER_EVALUATION = 'under_evaluation', 'Under evaluation'
        APPROVED = 'approved', 'Approved'
        NOT_SUITABLE = 'not_suitable', 'Not suitable'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    case = models.ForeignKey(
        TransplantCase, on_delete=models.CASCADE,
        related_name='case_donors',
    )
    donor = models.ForeignKey(
        'registry.Patient', on_delete=models.PROTECT,
        related_name='case_donor_links',
        help_text='Candidate donor.',
    )
    application = models.OneToOneField(
        'registry.DonorApplication', null=True, blank=True,
        on_delete=models.PROTECT, related_name='case_donor',
        help_text='Donor application this came from.',
    )
    abo_compatible = models.BooleanField(
        null=True, blank=True,
        help_text='Calculated from donor and recipient blood groups.',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CANDIDATE,
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_casedonor_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(status__in=[
                    'candidate', 'under_evaluation', 'approved',
                    'not_suitable', 'withdrawn',
                ]),
                name='transplant_casedonor_status_valid',
            ),
            # Business rule: only one donor per case can be approved.
            models.UniqueConstraint(
                fields=['case'],
                condition=Q(status='approved'),
                name='transplant_casedonor_one_approved',
                violation_error_message=(
                    'Only one donor per case can be approved for surgery.'
                ),
            ),
            # A donor cannot be the same person as the recipient (via model clean).
        ]
        indexes = [
            models.Index(fields=['case', 'status'],
                         name='transplant_casedonor_case_idx'),
        ]

    def __str__(self):
        return f'CaseDonor #{self.pk} – donor {self.donor_id} for case {self.case_id}'

    def clean(self):
        super().clean()
        if self.donor_id and self.case_id:
            recipient_id = TransplantCase.objects.filter(
                pk=self.case_id,
            ).values_list('recipient_id', flat=True).first()
            if recipient_id is None:
                raise ValidationError({'case': 'The transplant case does not exist.'})
            if self.donor_id == recipient_id:
                raise ValidationError({
                    'donor': 'The donor and the recipient must be different people.',
                })

    def calculate_abo(self):
        """Calculate and store ABO compatibility from both blood groups."""
        donor_bg = self.donor.blood_group
        recipient_bg = self.case.recipient.blood_group
        self.abo_compatible = check_abo_compatibility(donor_bg, recipient_bg)


# ───────────────────────────────────────────────────────────────────────────
# 4.31  ChecklistItem
# ───────────────────────────────────────────────────────────────────────────
class ChecklistItem(models.Model):
    """A test, visit or document required before committee review."""

    class ItemType(models.TextChoices):
        LAB_TEST = 'lab_test', 'Lab test'
        IMAGING = 'imaging', 'Imaging'
        CONSULTATION = 'consultation', 'Consultation'
        DOCUMENT = 'document', 'Document'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DONE = 'done', 'Done'
        WAIVED = 'waived', 'Waived'

    case = models.ForeignKey(
        TransplantCase, on_delete=models.CASCADE,
        related_name='checklist_items',
    )
    patient = models.ForeignKey(
        'registry.Patient', on_delete=models.PROTECT,
        related_name='checklist_items',
        help_text='Recipient or donor who must complete the item.',
    )
    item_name = models.CharField(max_length=200)
    item_type = models.CharField(max_length=15, choices=ItemType.choices)
    is_required = models.BooleanField(default=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['item_type', 'item_name']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_checklist_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(item_type__in=['lab_test', 'imaging', 'consultation', 'document']),
                name='transplant_checklist_type_valid',
            ),
            models.CheckConstraint(
                condition=Q(status__in=['pending', 'done', 'waived']),
                name='transplant_checklist_status_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['case', 'status'],
                         name='transplant_checklist_case_idx'),
        ]

    def __str__(self):
        return f'{self.item_name} ({self.status})'

    def mark_done(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])

    def mark_waived(self):
        self.status = self.Status.WAIVED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])


# ───────────────────────────────────────────────────────────────────────────
# 4.32  CommitteeDecision
# ───────────────────────────────────────────────────────────────────────────
class CommitteeDecision(models.Model):
    """The transplant committee's decision on a case."""

    class Decision(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        MORE_TESTS_NEEDED = 'more_tests_needed', 'More tests needed'

    case = models.ForeignKey(
        TransplantCase, on_delete=models.PROTECT,
        related_name='committee_decisions',
    )
    recorded_by = models.ForeignKey(
        'accounts.Staff', on_delete=models.PROTECT,
        related_name='recorded_decisions',
        help_text='Hepatologist who recorded the decision.',
    )
    meeting_date = models.DateField()
    decision = models.CharField(
        max_length=20, choices=Decision.choices, null=True, blank=True,
    )
    reasons = models.TextField(help_text='Reasons for the decision.')
    extra_tests = models.TextField(
        blank=True, default='',
        help_text='Additional tests requested by the committee.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-meeting_date', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_decision_id_gte_1',
            ),
            models.CheckConstraint(
                condition=(
                    Q(decision__isnull=True)
                    | Q(decision__in=['approved', 'rejected', 'more_tests_needed'])
                ),
                name='transplant_decision_valid',
            ),
        ]

    def __str__(self):
        return f'Decision #{self.pk} for case {self.case_id} ({self.decision})'

    def apply_decision(self):
        """Apply the committee decision to the transplant case status."""
        if not self.decision:
            return
        mapping = {
            'approved': TransplantCase.Status.APPROVED,
            'rejected': TransplantCase.Status.REJECTED,
            'more_tests_needed': TransplantCase.Status.UNDER_EVALUATION,
        }
        new_status = mapping.get(self.decision)
        if new_status:
            self.case.transition_to(new_status)


# ───────────────────────────────────────────────────────────────────────────
# 4.33  CommitteeMember
# ───────────────────────────────────────────────────────────────────────────
class CommitteeMember(models.Model):
    """Staff who participated in a committee decision."""

    class Vote(models.TextChoices):
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'
        ABSTAIN = 'abstain', 'Abstain'

    decision = models.ForeignKey(
        CommitteeDecision, on_delete=models.CASCADE,
        related_name='members',
    )
    staff = models.ForeignKey(
        'accounts.Staff', on_delete=models.PROTECT,
        related_name='committee_memberships',
    )
    vote = models.CharField(
        max_length=10, choices=Vote.choices, null=True, blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_committee_member_id_gte_1',
            ),
            models.UniqueConstraint(
                fields=['decision', 'staff'],
                name='transplant_committee_member_unique',
            ),
            models.CheckConstraint(
                condition=(
                    Q(vote__isnull=True)
                    | Q(vote__in=['approve', 'reject', 'abstain'])
                ),
                name='transplant_committee_vote_valid',
            ),
        ]

    def __str__(self):
        return f'Member {self.staff_id} on decision {self.decision_id}'


# ───────────────────────────────────────────────────────────────────────────
# 4.34  Surgery
# ───────────────────────────────────────────────────────────────────────────
class Surgery(models.Model):
    """The transplant operation."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class GraftType(models.TextChoices):
        RIGHT_LOBE = 'right_lobe', 'Right lobe'
        LEFT_LOBE = 'left_lobe', 'Left lobe'
        LEFT_LATERAL = 'left_lateral_segment', 'Left lateral segment'

    case = models.ForeignKey(
        TransplantCase, on_delete=models.PROTECT,
        related_name='surgeries',
    )
    case_donor = models.ForeignKey(
        CaseDonor, on_delete=models.PROTECT,
        related_name='surgeries',
        help_text='Donor who gave the graft.',
    )
    lead_surgeon = models.ForeignKey(
        'accounts.Staff', on_delete=models.PROTECT,
        related_name='led_surgeries',
    )
    scheduled_at = models.DateTimeField(help_text='Planned date and time.')
    operating_room = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.SCHEDULED,
    )
    graft_type = models.CharField(
        max_length=25, choices=GraftType.choices, blank=True, default='',
    )
    graft_weight_g = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text='Actual graft weight in grams.',
    )
    duration_min = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Length of the operation in minutes.',
    )
    operative_notes = models.TextField(blank=True, default='')
    complications = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'surgeries'
        ordering = ['-scheduled_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_surgery_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(status__in=[
                    'scheduled', 'in_progress', 'completed', 'cancelled',
                ]),
                name='transplant_surgery_status_valid',
            ),
            models.CheckConstraint(
                condition=(
                    Q(graft_type='')
                    | Q(graft_type__in=['right_lobe', 'left_lobe', 'left_lateral_segment'])
                ),
                name='transplant_surgery_graft_valid',
            ),
            models.CheckConstraint(
                condition=Q(graft_weight_g__isnull=True) | Q(graft_weight_g__gt=0),
                name='transplant_surgery_weight_positive',
            ),
        ]
        indexes = [
            models.Index(fields=['case', 'status'],
                         name='transplant_surgery_case_idx'),
        ]

    def __str__(self):
        return f'Surgery #{self.pk} – case {self.case_id} ({self.status})'

    def clean(self):
        super().clean()
        # The donor must belong to this case.
        if self.case_donor_id and self.case_id:
            if self.case_donor.case_id != self.case_id:
                raise ValidationError({
                    'case_donor': 'The donor must belong to this transplant case.',
                })
            if self.case_donor.status != CaseDonor.Status.APPROVED:
                raise ValidationError({
                    'case_donor': 'Only an approved donor can be assigned to surgery.',
                })

    @transaction.atomic
    def complete(self):
        """Mark surgery completed, create follow-up plans and invoice the operation."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status', 'updated_at'])
        # Update case status to transplanted
        self.case.transition_to(TransplantCase.Status.TRANSPLANTED)
        # Business rule: completing a surgery creates follow-up plans
        self._create_followup_plans()
        from apps.billing.services import invoice_for_surgery

        invoice_for_surgery(self)

    def _create_followup_plans(self):
        """Create separate follow-up plans for recipient and donor."""
        today = timezone.localdate()
        # Recipient plan
        FollowUpPlan.objects.get_or_create(
            case=self.case,
            patient=self.case.recipient,
            patient_role=FollowUpPlan.PatientRole.RECIPIENT,
            defaults={'start_date': today, 'status': FollowUpPlan.Status.ACTIVE},
        )
        # Donor plan
        FollowUpPlan.objects.get_or_create(
            case=self.case,
            patient=self.case_donor.donor,
            patient_role=FollowUpPlan.PatientRole.DONOR,
            defaults={'start_date': today, 'status': FollowUpPlan.Status.ACTIVE},
        )


# ───────────────────────────────────────────────────────────────────────────
# 4.35  SurgeryTeamMember
# ───────────────────────────────────────────────────────────────────────────
class SurgeryTeamMember(models.Model):
    """Staff on a surgical team."""

    surgery = models.ForeignKey(
        Surgery, on_delete=models.CASCADE,
        related_name='team_members',
    )
    staff = models.ForeignKey(
        'accounts.Staff', on_delete=models.PROTECT,
        related_name='surgery_team_memberships',
    )
    team_role = models.CharField(
        max_length=100,
        help_text='Role in the operation (e.g. assistant surgeon, anesthesiologist).',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_surgery_team_member_id_gte_1',
            ),
            models.UniqueConstraint(
                fields=['surgery', 'staff'],
                name='transplant_surgery_team_unique',
            ),
        ]

    def __str__(self):
        return f'{self.staff_id} as {self.team_role} in surgery {self.surgery_id}'


# ───────────────────────────────────────────────────────────────────────────
# 4.36  FollowUpPlan
# ───────────────────────────────────────────────────────────────────────────
class FollowUpPlan(models.Model):
    """Follow-up schedule after surgery — one for recipient, one for donor."""

    class PatientRole(models.TextChoices):
        RECIPIENT = 'recipient', 'Recipient'
        DONOR = 'donor', 'Donor'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'

    case = models.ForeignKey(
        TransplantCase, on_delete=models.PROTECT,
        related_name='followup_plans',
    )
    patient = models.ForeignKey(
        'registry.Patient', on_delete=models.PROTECT,
        related_name='followup_plans',
    )
    patient_role = models.CharField(
        max_length=10, choices=PatientRole.choices,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_followup_plan_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(patient_role__in=['recipient', 'donor']),
                name='transplant_followup_role_valid',
            ),
            models.CheckConstraint(
                condition=Q(status__in=['active', 'completed']),
                name='transplant_followup_status_valid',
            ),
            # One plan per role per case.
            models.UniqueConstraint(
                fields=['case', 'patient_role'],
                name='transplant_followup_one_per_role',
                violation_error_message='A follow-up plan already exists for this role in this case.',
            ),
        ]

    def __str__(self):
        return f'FollowUp #{self.pk} – {self.patient_role} for case {self.case_id}'


# ───────────────────────────────────────────────────────────────────────────
# 4.37  FollowUpVisit
# ───────────────────────────────────────────────────────────────────────────
class FollowUpVisit(models.Model):
    """One follow-up visit with recovery findings."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        MISSED = 'missed', 'Missed'
        CANCELLED = 'cancelled', 'Cancelled'

    plan = models.ForeignKey(
        FollowUpPlan, on_delete=models.CASCADE,
        related_name='visits',
    )
    appointment = models.OneToOneField(
        'scheduling.Appointment', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='followup_visit',
        help_text='Appointment booked for this visit.',
    )
    due_date = models.DateField(help_text='Date the visit is due.')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SCHEDULED,
    )
    # Recipient measurements
    immuno_level = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
        help_text='Immunosuppressant blood level (ng/mL), recipients only.',
    )
    rejection_episode = models.BooleanField(
        null=True, blank=True,
        help_text='Whether signs of graft rejection were found.',
    )
    # Donor measurements
    liver_regrowth_ml = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Liver volume on follow-up CT (mL), donors only.',
    )
    # Shared fields
    complications = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date']
        constraints = [
            models.CheckConstraint(
                condition=Q(id__gte=1),
                name='transplant_visit_id_gte_1',
            ),
            models.CheckConstraint(
                condition=Q(status__in=['scheduled', 'completed', 'missed', 'cancelled']),
                name='transplant_visit_status_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['plan', 'due_date'],
                         name='transplant_visit_plan_idx'),
        ]

    def __str__(self):
        return f'Visit #{self.pk} – {self.due_date} ({self.status})'
