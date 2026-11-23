"""Admin registration for transplant models."""
from django.contrib import admin

from .models import (
    CaseDonor, ChecklistItem, CommitteeDecision, CommitteeMember,
    FollowUpPlan, FollowUpVisit, Surgery, SurgeryTeamMember, TransplantCase,
)


class CaseDonorInline(admin.TabularInline):
    model = CaseDonor
    extra = 0
    raw_id_fields = ['donor', 'application']


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    raw_id_fields = ['patient']


@admin.register(TransplantCase)
class TransplantCaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'status', 'referral_date', 'coordinator', 'created_at']
    list_filter = ['status', 'referral_date']
    search_fields = ['recipient__first_name', 'recipient__last_name', 'recipient__mrn']
    raw_id_fields = ['recipient', 'referred_by', 'coordinator', 'referral_encounter']
    inlines = [CaseDonorInline, ChecklistItemInline]


@admin.register(CaseDonor)
class CaseDonorAdmin(admin.ModelAdmin):
    list_display = ['id', 'case', 'donor', 'abo_compatible', 'status', 'added_at']
    list_filter = ['status', 'abo_compatible']
    raw_id_fields = ['case', 'donor', 'application']


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'case', 'patient', 'item_name', 'item_type', 'is_required', 'status']
    list_filter = ['item_type', 'status', 'is_required']
    raw_id_fields = ['case', 'patient']


class CommitteeMemberInline(admin.TabularInline):
    model = CommitteeMember
    extra = 0
    raw_id_fields = ['staff']


@admin.register(CommitteeDecision)
class CommitteeDecisionAdmin(admin.ModelAdmin):
    list_display = ['id', 'case', 'decision', 'meeting_date', 'recorded_by']
    list_filter = ['decision', 'meeting_date']
    raw_id_fields = ['case', 'recorded_by']
    inlines = [CommitteeMemberInline]


class SurgeryTeamMemberInline(admin.TabularInline):
    model = SurgeryTeamMember
    extra = 0
    raw_id_fields = ['staff']


@admin.register(Surgery)
class SurgeryAdmin(admin.ModelAdmin):
    list_display = ['id', 'case', 'case_donor', 'lead_surgeon', 'status', 'scheduled_at']
    list_filter = ['status', 'graft_type']
    raw_id_fields = ['case', 'case_donor', 'lead_surgeon']
    inlines = [SurgeryTeamMemberInline]


@admin.register(FollowUpPlan)
class FollowUpPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'case', 'patient', 'patient_role', 'status', 'start_date']
    list_filter = ['patient_role', 'status']
    raw_id_fields = ['case', 'patient']


@admin.register(FollowUpVisit)
class FollowUpVisitAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan', 'due_date', 'status', 'immuno_level', 'rejection_episode']
    list_filter = ['status']
    raw_id_fields = ['plan', 'appointment']
