"""
Prescriptions & treatment plans API (Module 6). Capabilities (apps/accounts/rbac.py):

    prescriptions.view        prescriptions + medication lists          clinical readers
    prescriptions.prescribe   prescribe / stop / complete               hepatologist, transplant_surgeon
    treatment_plans.view      treatment plans                           clinical readers
    treatment_plans.manage    create / edit / complete / cancel plans   hepatologist, transplant_surgeon
    drugs.manage              add / edit drugs in the catalog           super_admin, hepatologist, surgeon
    self.medications          own medications and plans (portal)        patients

Audited: every write (with changed values and reason for stops and plan edits) and opening a
patient's medication list or plans.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile, has_capability
from apps.registry.models import Patient
from apps.transplant.models import TransplantCase

from . import services
from .models import Drug, Prescription, TreatmentPlan
from .serializers import (
    DrugSerializer, MyPrescriptionSerializer, MyTreatmentPlanSerializer, OptionalReasonSerializer,
    PrescriptionCreateSerializer, PrescriptionSerializer, ReasonSerializer, TreatmentPlanCreateSerializer,
    TreatmentPlanSerializer, TreatmentPlanUpdateSerializer,
)

A = AuditLog.Action
RX_ENTITY = 'prescriptions.prescription'
PLAN_ENTITY = 'prescriptions.treatmentplan'
DRUG_ENTITY = 'prescriptions.drug'


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _bad(detail):
    return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)


def _doctor(request):
    return get_staff_profile(request.user)


def _rx_qs():
    return Prescription.objects.select_related('patient', 'drug', 'prescribed_by__user')


def _plan_qs():
    return TreatmentPlan.objects.select_related('patient', 'created_by__user')


def _split_medications(qs):
    """(current, past): current = active and not past the end date; past = everything else."""
    today = timezone.localdate()
    current_q = Q(status=Prescription.Status.ACTIVE) & (Q(end_date__isnull=True) | Q(end_date__gte=today))
    return qs.filter(current_q), qs.exclude(current_q).order_by('-end_date', '-start_date', '-id')


def _own_patient(request):
    return Patient.objects.filter(user=request.user).first()


# --------------------------------------------------------------------------- drug catalog

class DrugListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/rx/drugs/?q=&include_inactive=1   autocomplete (prescribers & readers)
    POST /api/rx/drugs/                         add a drug (drugs.manage)
    """
    serializer_class = DrugSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), HasCapability('drugs.manage')()]
        return [IsAuthenticated(), HasCapability('prescriptions.view', 'prescriptions.prescribe', 'drugs.manage')()]

    def get_queryset(self):
        qs = Drug.objects.all()
        p = self.request.query_params
        if not (p.get('include_inactive') == '1' and has_capability(self.request.user, 'drugs.manage')):
            qs = qs.filter(is_active=True)
        if q := p.get('q', '').strip():
            qs = qs.filter(Q(name__icontains=q) | Q(generic_name__icontains=q) | Q(code__iexact=q)
                           | Q(drug_class__icontains=q))
        return qs[:50] if p.get('q') else qs

    def perform_create(self, serializer):
        drug = serializer.save(created_by=self.request.user)
        audit(self.request, A.CREATE, DRUG_ENTITY, entity_id=drug.pk)


class DrugDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/rx/drugs/<id>/  edit or deactivate a catalog entry (drugs.manage)."""
    serializer_class = DrugSerializer
    queryset = Drug.objects.all()
    http_method_names = ['get', 'patch']

    def get_permissions(self):
        cap = ('drugs.manage',) if self.request.method == 'PATCH' else (
            'prescriptions.view', 'prescriptions.prescribe', 'drugs.manage')
        return [IsAuthenticated(), HasCapability(*cap)()]

    def perform_update(self, serializer):
        changes = services.diff(serializer.instance, serializer.validated_data,
                                [f for f in DrugSerializer.Meta.fields if f not in ('id', 'code')])
        drug = serializer.save()
        if changes:
            audit(self.request, A.UPDATE, DRUG_ENTITY, entity_id=drug.pk, changes=changes)


# --------------------------------------------------------------------------- prescriptions

class PrescriptionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/rx/prescriptions/?patient=&status=    (prescriptions.view)
    POST /api/rx/prescriptions/                     (prescriptions.prescribe: doctors only)
    """
    serializer_class = PrescriptionSerializer
    pagination_class = Pagination

    def get_permissions(self):
        cap = 'prescriptions.prescribe' if self.request.method == 'POST' else 'prescriptions.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = _rx_qs()
        p = self.request.query_params
        if p.get('patient', '').isdigit():
            qs = qs.filter(patient_id=int(p['patient']))
        if p.get('status') in Prescription.Status.values:
            qs = qs.filter(status=p['status'])
        return qs

    def create(self, request, *args, **kwargs):
        ser = PrescriptionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        staff = _doctor(request)
        if staff is None:
            return _bad('Only doctors can prescribe.')
        d = dict(ser.validated_data)
        patient, drug = d.pop('patient'), d.pop('drug')
        # TODO(EMR): when MedicalHistory exists, return the patient's allergies as warnings here.
        try:
            rx = services.prescribe(patient, staff, drug, **d)
        except services.RxError as e:
            return _bad(e)
        audit(request, A.CREATE, RX_ENTITY, entity_id=rx.pk, patient=patient)
        return Response(PrescriptionSerializer(rx).data, status=status.HTTP_201_CREATED)


class PrescriptionDetailView(generics.RetrieveAPIView):
    """GET /api/rx/prescriptions/<id>/"""
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, HasCapability('prescriptions.view')]

    def get_queryset(self):
        return _rx_qs()


class _RxActionView(APIView):
    permission_classes = [IsAuthenticated, HasCapability('prescriptions.prescribe')]
    reason_serializer = OptionalReasonSerializer

    def act(self, rx, reason):
        raise NotImplementedError

    def post(self, request, pk):
        rx = get_object_or_404(_rx_qs(), pk=pk)
        ser = self.reason_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data['reason']
        try:
            changes = self.act(rx, reason)
        except services.RxError as e:
            return _bad(e)
        audit(request, A.UPDATE, RX_ENTITY, entity_id=rx.pk, patient=rx.patient, changes=changes, reason=reason)
        return Response(PrescriptionSerializer(rx).data)


class PrescriptionStopView(_RxActionView):
    """POST /api/rx/prescriptions/<id>/stop/  {reason}  discontinue an active medication."""
    reason_serializer = ReasonSerializer

    def act(self, rx, reason):
        return services.stop_prescription(rx, reason)


class PrescriptionCompleteView(_RxActionView):
    """POST /api/rx/prescriptions/<id>/complete/  {reason?}  course finished."""

    def act(self, rx, reason):
        return services.complete_prescription(rx)


class PatientMedicationsView(APIView):
    """GET /api/rx/patients/<patient_id>/medications/  {current: [...], past: [...]}"""
    permission_classes = [IsAuthenticated, HasCapability('prescriptions.view')]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        current, past = _split_medications(_rx_qs().filter(patient=patient))
        audit(request, A.VIEW, RX_ENTITY, patient=patient)
        return Response({'current': PrescriptionSerializer(current, many=True).data,
                         'past': PrescriptionSerializer(past, many=True).data})


class MyMedicationsView(APIView):
    """GET /api/rx/my/medications/  the signed-in patient's own medications."""
    permission_classes = [IsAuthenticated, HasCapability('self.medications')]

    def get(self, request):
        patient = _own_patient(request)
        if patient is None:
            return Response({'current': [], 'past': []})
        current, past = _split_medications(_rx_qs().filter(patient=patient))
        return Response({'current': MyPrescriptionSerializer(current, many=True).data,
                         'past': MyPrescriptionSerializer(past, many=True).data})


# --------------------------------------------------------------------------- treatment plans

class TreatmentPlanListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/rx/plans/?patient=&status=&plan_type=&review_due=1   (treatment_plans.view)
    POST /api/rx/plans/                                           (treatment_plans.manage)
    """
    serializer_class = TreatmentPlanSerializer
    pagination_class = Pagination

    def get_permissions(self):
        cap = 'treatment_plans.manage' if self.request.method == 'POST' else 'treatment_plans.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = _plan_qs()
        p = self.request.query_params
        if p.get('patient', '').isdigit():
            qs = qs.filter(patient_id=int(p['patient']))
        if p.get('status') in TreatmentPlan.Status.values:
            qs = qs.filter(status=p['status'])
        if p.get('plan_type') in TreatmentPlan.PlanType.values:
            qs = qs.filter(plan_type=p['plan_type'])
        if p.get('review_due') == '1':
            qs = qs.filter(status=TreatmentPlan.Status.ACTIVE, review_date__lte=timezone.localdate())
        return qs

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        pid = request.query_params.get('patient', '')
        if pid.isdigit() and (patient := Patient.objects.filter(pk=int(pid)).first()):
            audit(request, A.VIEW, PLAN_ENTITY, patient=patient)
        return resp

    def create(self, request, *args, **kwargs):
        ser = TreatmentPlanCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        staff = _doctor(request)
        if staff is None:
            return _bad('Only doctors can create treatment plans.')
        d = dict(ser.validated_data)
        if (d['plan_type'] == TreatmentPlan.PlanType.TRANSPLANT_REFERRAL
                and not has_capability(request.user, 'transplant.refer')):
            return Response(
                {'detail': 'Only a hepatologist can submit a transplant referral.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        patient = d.pop('patient')
        try:
            plan, case, case_created = services.create_plan(patient, staff, **d)
        except services.RxError as e:
            return _bad(e)
        audit(request, A.CREATE, PLAN_ENTITY, entity_id=plan.pk, patient=patient)
        if case_created:
            audit(request, A.CREATE, 'transplant.transplantcase',
                  entity_id=case.pk, patient=patient)
        data = TreatmentPlanSerializer(plan).data
        if case:
            data['transplant_case_id'] = case.pk
            data['transplant_case_created'] = case_created
        return Response(data, status=status.HTTP_201_CREATED)


class TreatmentPlanDetailView(APIView):
    """
    GET   /api/rx/plans/<id>/                                (treatment_plans.view)
    PATCH /api/rx/plans/<id>/  {goals?, steps?, review_date?, plan_type?, start_date?, reason}
          (treatment_plans.manage) active plans only; changed values + reason go to the audit log.
    """

    def get_permissions(self):
        cap = 'treatment_plans.manage' if self.request.method == 'PATCH' else 'treatment_plans.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get(self, request, pk):
        return Response(TreatmentPlanSerializer(get_object_or_404(_plan_qs(), pk=pk)).data)

    def patch(self, request, pk):
        plan = get_object_or_404(_plan_qs(), pk=pk)
        ser = TreatmentPlanUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        reason = data.pop('reason')
        if (data.get('plan_type') == TreatmentPlan.PlanType.TRANSPLANT_REFERRAL
                and not has_capability(request.user, 'transplant.refer')):
            return Response(
                {'detail': 'Only a hepatologist can submit a transplant referral.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        staff = _doctor(request)
        if staff is None:
            return Response({'detail': 'Only doctors can manage treatment plans.'},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            plan, changes, case, case_created = services.update_plan(plan, data, staff)
        except services.RxError as e:
            return _bad(e)
        if not changes:
            return _bad('Nothing was changed.')
        audit(request, A.UPDATE, PLAN_ENTITY, entity_id=plan.pk, patient=plan.patient,
              changes=changes, reason=reason)
        if case_created:
            audit(request, A.CREATE, 'transplant.transplantcase',
                  entity_id=case.pk, patient=plan.patient)
        response_data = TreatmentPlanSerializer(get_object_or_404(_plan_qs(), pk=pk)).data
        if case:
            response_data['transplant_case_id'] = case.pk
            response_data['transplant_case_created'] = case_created
        return Response(response_data)


class _PlanCloseView(APIView):
    """POST {reason}: close an active plan; the reason is mandatory and audited."""
    permission_classes = [IsAuthenticated, HasCapability('treatment_plans.manage')]
    new_status = None

    def post(self, request, pk):
        plan = get_object_or_404(_plan_qs(), pk=pk)
        ser = ReasonSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            changes = services.close_plan(plan, self.new_status)
        except services.RxError as e:
            return _bad(e)
        audit(request, A.UPDATE, PLAN_ENTITY, entity_id=plan.pk, patient=plan.patient,
              changes=changes, reason=ser.validated_data['reason'])
        return Response(TreatmentPlanSerializer(plan).data)


class TreatmentPlanCompleteView(_PlanCloseView):
    """POST /api/rx/plans/<id>/complete/"""
    new_status = TreatmentPlan.Status.COMPLETED


class TreatmentPlanCancelView(_PlanCloseView):
    """POST /api/rx/plans/<id>/cancel/"""
    new_status = TreatmentPlan.Status.CANCELLED


class MyTreatmentPlansView(generics.ListAPIView):
    """GET /api/rx/my/plans/  the signed-in patient's own plans."""
    serializer_class = MyTreatmentPlanSerializer
    permission_classes = [IsAuthenticated, HasCapability('self.medications')]

    def get_queryset(self):
        patient = _own_patient(self.request)
        if patient is None:
            return TreatmentPlan.objects.none()
        return _plan_qs().filter(patient=patient)
