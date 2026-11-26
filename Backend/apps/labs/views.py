"""
Laboratory API (Module 5). Capabilities (apps/accounts/rbac.py):

    labs.view          orders, pending tests, patient results/trends   clinical readers
    labs.order         create / cancel orders                          hepatologist, transplant_surgeon
    labs.enter_result  enter a result received from the external lab   super_admin, coordinator, hepatologist
    labs.release       release results to the patient portal           hepatologist, transplant_surgeon
    self.lab_results   own RELEASED results + trends (portal)          patients

Audited: order creation/cancel, result entry, release, and opening a patient's results.
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability
from apps.accounts.rbac import get_staff_profile
from apps.registry.models import Patient

from . import services
from .models import LabOrder, LabResult, LabTest
from .serializers import (
    LabOrderCreateSerializer, LabOrderSerializer, LabResultSerializer, LabTestSerializer,
    MyLabOrderSerializer, PendingResultSerializer, ResultEntrySerializer,
)

A = AuditLog.Action


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _bad(detail):
    return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)


def _trend_payload(patient, test_code, released_only):
    test = get_object_or_404(LabTest, code=test_code)
    points = services.trend_points(patient, test_code, released_only)
    return {
        'test': LabTestSerializer(test).data,
        'points': [{'date': r.result_time, 'value': float(r.value), 'flag': r.flag} for r in points],
    }


class LabTestListView(generics.ListAPIView):
    """GET /api/lab/tests/  the catalog (needed to build an order)."""
    serializer_class = LabTestSerializer
    queryset = LabTest.objects.all()
    permission_classes = [IsAuthenticated, HasCapability('labs.view', 'labs.order')]


class LabOrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/lab/orders/?patient=&status=&priority=   (labs.view)
    POST /api/lab/orders/  {patient, encounter, priority, tests:[ids]}   (labs.order)
    """
    serializer_class = LabOrderSerializer
    pagination_class = Pagination

    def get_permissions(self):
        cap = 'labs.order' if self.request.method == 'POST' else 'labs.view'
        return [IsAuthenticated(), HasCapability(cap)()]

    def get_queryset(self):
        qs = LabOrder.objects.select_related('patient', 'ordered_by__user').prefetch_related('results__lab_test')
        p = self.request.query_params
        if p.get('patient', '').isdigit():
            qs = qs.filter(patient_id=int(p['patient']))
        if p.get('status') in LabOrder.Status.values:
            qs = qs.filter(status=p['status'])
        if p.get('priority') in LabOrder.Priority.values:
            qs = qs.filter(priority=p['priority'])
        if p.get('encounter', '').isdigit():
            qs = qs.filter(encounter_id=int(p['encounter']))
        return qs

    def create(self, request, *args, **kwargs):
        ser = LabOrderCreateSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        staff = get_staff_profile(request.user)
        if staff is None:
            return _bad('Only staff members can place lab orders.')
        d = ser.validated_data
        order = services.create_order(d['patient'], staff, d['tests'], d['priority'], encounter=d['encounter'])
        audit(request, A.CREATE, 'labs.laborder', entity_id=order.pk, patient=order.patient)
        return Response(LabOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class LabOrderDetailView(generics.RetrieveAPIView):
    """GET /api/lab/orders/<id>/"""
    serializer_class = LabOrderSerializer
    queryset = LabOrder.objects.select_related('patient', 'ordered_by__user').prefetch_related('results__lab_test')
    permission_classes = [IsAuthenticated, HasCapability('labs.view')]


class LabOrderCancelView(APIView):
    """POST /api/lab/orders/<id>/cancel/"""
    permission_classes = [IsAuthenticated, HasCapability('labs.order')]

    def post(self, request, pk):
        order = get_object_or_404(LabOrder, pk=pk)
        try:
            services.cancel_order(order)
        except services.LabError as e:
            return _bad(e)
        audit(request, A.UPDATE, 'labs.laborder', entity_id=order.pk, patient=order.patient)
        return Response(LabOrderSerializer(order).data)


class LabOrderReleaseView(APIView):
    """POST /api/lab/orders/<id>/release/  show the resulted tests to the patient."""
    permission_classes = [IsAuthenticated, HasCapability('labs.release')]

    def post(self, request, pk):
        order = get_object_or_404(LabOrder, pk=pk)
        try:
            services.release_order(order)
        except services.LabError as e:
            return _bad(e)
        audit(request, A.UPDATE, 'labs.laborder', entity_id=order.pk, patient=order.patient)
        return Response(LabOrderSerializer(order).data)


class PendingTestsView(generics.ListAPIView):
    """GET /api/lab/pending/?patient=&priority=  tests still waiting for the external lab (urgent first)."""
    serializer_class = PendingResultSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, HasCapability('labs.view')]

    def get_queryset(self):
        qs = (LabResult.objects.filter(value__isnull=True)
              .exclude(lab_order__status=LabOrder.Status.CANCELLED)
              .select_related('lab_test', 'lab_order__patient'))
        p = self.request.query_params
        if p.get('patient', '').isdigit():
            qs = qs.filter(lab_order__patient_id=int(p['patient']))
        if p.get('priority') in LabOrder.Priority.values:
            qs = qs.filter(lab_order__priority=p['priority'])
        # 'urgent' sorts after 'routine' alphabetically, so descending puts urgent first.
        return qs.order_by('-lab_order__priority', 'lab_order__order_date', 'id')


class ResultEntryView(APIView):
    """POST /api/lab/results/<id>/enter/  {value, result_time?}  (result received from the external lab)."""
    permission_classes = [IsAuthenticated, HasCapability('labs.enter_result')]

    def post(self, request, pk):
        result = get_object_or_404(LabResult.objects.select_related('lab_test', 'lab_order__patient'), pk=pk)
        ser = ResultEntrySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.record_result(result, ser.validated_data['value'], ser.validated_data.get('result_time'))
        except services.LabError as e:
            return _bad(e)
        audit(request, A.UPDATE, 'labs.labresult', entity_id=result.pk, patient=result.lab_order.patient)
        return Response(LabResultSerializer(result).data)


class PatientResultsView(generics.ListAPIView):
    """GET /api/lab/patients/<patient_id>/results/?test=<code>   (labs.view) resulted tests, newest first."""
    serializer_class = LabResultSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, HasCapability('labs.view')]

    def get_queryset(self):
        self.patient = get_object_or_404(Patient, pk=self.kwargs['patient_id'])
        qs = (LabResult.objects.filter(lab_order__patient=self.patient, value__isnull=False)
              .exclude(lab_order__status=LabOrder.Status.CANCELLED)
              .select_related('lab_test').order_by('-result_time', '-id'))
        if code := self.request.query_params.get('test'):
            qs = qs.filter(lab_test__code=code)
        return qs

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        audit(request, A.VIEW, 'labs.labresult', patient=self.patient)
        return resp


class PatientTrendView(APIView):
    """GET /api/lab/patients/<patient_id>/trends/?test=<code>  points for a line chart."""
    permission_classes = [IsAuthenticated, HasCapability('labs.view')]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, pk=patient_id)
        code = request.query_params.get('test')
        if not code:
            return _bad('The "test" query parameter (test code) is required.')
        return Response(_trend_payload(patient, code, released_only=False))


class MyResultsView(generics.ListAPIView):
    """GET /api/lab/my/results/  the signed-in patient's RELEASED results only."""
    serializer_class = LabResultSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, HasCapability('self.lab_results')]

    def get_queryset(self):
        patient = Patient.objects.filter(user=self.request.user).first()
        if patient is None:
            return LabResult.objects.none()
        return (LabResult.objects.filter(lab_order__patient=patient, is_released=True, value__isnull=False)
                .exclude(lab_order__status=LabOrder.Status.CANCELLED)
                .select_related('lab_test').order_by('-result_time', '-id'))


class MyLabOrdersView(generics.ListAPIView):
    """GET /api/lab/my/orders/  the signed-in patient's own orders with a status per test (never values)."""
    serializer_class = MyLabOrderSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, HasCapability('self.lab_results')]

    def get_queryset(self):
        patient = Patient.objects.filter(user=self.request.user).first()
        if patient is None:
            return LabOrder.objects.none()
        qs = LabOrder.objects.filter(patient=patient)
        encounter = self.request.query_params.get('encounter', '')
        if encounter.isdigit():
            qs = qs.filter(encounter_id=int(encounter))
        return qs.select_related('ordered_by__user').prefetch_related('results__lab_test')


class MyTrendView(APIView):
    """GET /api/lab/my/trends/?test=<code>  released values only."""
    permission_classes = [IsAuthenticated, HasCapability('self.lab_results')]

    def get(self, request):
        patient = Patient.objects.filter(user=request.user).first()
        code = request.query_params.get('test')
        if patient is None:
            return Response({'detail': 'No hospital record is linked to your account.'},
                            status=status.HTTP_404_NOT_FOUND)
        if not code:
            return _bad('The "test" query parameter (test code) is required.')
        return Response(_trend_payload(patient, code, released_only=True))
