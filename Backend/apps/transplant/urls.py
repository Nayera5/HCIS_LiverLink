"""URL routing for the transplant module."""
from django.urls import path

from . import views

app_name = 'transplant'

urlpatterns = [
    path('staff-picker/',
         views.StaffPickerView.as_view(),
         name='staff-picker'),

    # ── Transplant Cases ──────────────────────────────────────────────────
    path('cases/',
         views.TransplantCaseListCreateView.as_view(),
         name='case-list'),
    path('cases/<int:pk>/',
         views.TransplantCaseDetailView.as_view(),
         name='case-detail'),
    path('cases/<int:pk>/update/',
         views.TransplantCaseUpdateView.as_view(),
         name='case-update'),
    path('cases/<int:pk>/status/',
         views.TransplantCaseStatusView.as_view(),
         name='case-status'),

    # ── Case Donors ───────────────────────────────────────────────────────
    path('cases/<int:case_pk>/donors/',
         views.CaseDonorListCreateView.as_view(),
         name='case-donor-list'),
    path('donors/<int:pk>/',
         views.CaseDonorDetailView.as_view(),
         name='donor-detail'),
    path('donors/<int:pk>/status/',
         views.CaseDonorStatusView.as_view(),
         name='donor-status'),
    path('donors/<int:pk>/abo-check/',
         views.ABOCheckView.as_view(),
         name='donor-abo-check'),

    # ── Checklist ─────────────────────────────────────────────────────────
    path('cases/<int:case_pk>/checklist/',
         views.ChecklistItemListCreateView.as_view(),
         name='checklist-list'),
    path('checklist/<int:pk>/',
         views.ChecklistItemDetailView.as_view(),
         name='checklist-detail'),
    path('checklist/<int:pk>/status/',
         views.ChecklistItemStatusView.as_view(),
         name='checklist-status'),

    # ── Committee Decisions ───────────────────────────────────────────────
    path('cases/<int:case_pk>/decisions/',
         views.CommitteeDecisionListCreateView.as_view(),
         name='decision-list'),
    path('decisions/<int:pk>/',
         views.CommitteeDecisionDetailView.as_view(),
         name='decision-detail'),

    # ── Surgery ───────────────────────────────────────────────────────────
    path('cases/<int:case_pk>/surgeries/',
         views.SurgeryListCreateView.as_view(),
         name='surgery-list'),
    path('surgeries/<int:pk>/',
         views.SurgeryDetailView.as_view(),
         name='surgery-detail'),
    path('surgeries/<int:pk>/complete/',
         views.SurgeryCompleteView.as_view(),
         name='surgery-complete'),
    path('surgeries/<int:surgery_pk>/team/',
         views.SurgeryTeamMemberView.as_view(),
         name='surgery-team'),
    path('team-members/<int:pk>/',
         views.SurgeryTeamMemberDeleteView.as_view(),
         name='team-member-delete'),

    # ── Follow-up ─────────────────────────────────────────────────────────
    path('followup/plans/',
         views.FollowUpPlanListView.as_view(),
         name='followup-plan-list'),
    path('followup/plans/<int:pk>/',
         views.FollowUpPlanDetailView.as_view(),
         name='followup-plan-detail'),
    path('followup/plans/<int:plan_pk>/visits/',
         views.FollowUpVisitListCreateView.as_view(),
         name='followup-visit-list'),
    path('followup/plans/<int:plan_pk>/recovery/',
         views.RecoveryStatsView.as_view(),
         name='followup-recovery'),
    path('followup/visits/<int:pk>/',
         views.FollowUpVisitDetailView.as_view(),
         name='followup-visit-detail'),
]
