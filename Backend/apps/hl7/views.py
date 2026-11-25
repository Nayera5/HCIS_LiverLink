"""
HL7 Message Monitor API (Module 16). Capability: hl7.monitor (super admin only), because the raw
messages contain patient names and lab results. Opening and resending a message are audited.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability

from . import services
from .models import HL7Message
from .serializers import HL7MessageDetailSerializer, HL7MessageSerializer

A = AuditLog.Action


class Pagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class HL7MessageListView(generics.ListAPIView):
    """GET /api/hl7/messages/?direction=&status=&type=&search=   newest first, without message text."""
    serializer_class = HL7MessageSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated, HasCapability('hl7.monitor')]

    def get_queryset(self):
        qs = HL7Message.objects.select_related('system', 'patient')
        p = self.request.query_params
        if p.get('direction') in HL7Message.Direction.values:
            qs = qs.filter(direction=p['direction'])
        if p.get('status') in HL7Message.Status.values:
            qs = qs.filter(status=p['status'])
        if p.get('type'):
            qs = qs.filter(message_type=p['type'])
        if search := p.get('search', '').strip():
            qs = qs.filter(Q(control_id__icontains=search) | Q(patient__mrn__icontains=search))
        return qs


class HL7MessageDetailView(generics.RetrieveAPIView):
    """GET /api/hl7/messages/<id>/   with the raw message and its ACK."""
    serializer_class = HL7MessageDetailSerializer
    queryset = HL7Message.objects.select_related('system', 'patient')
    permission_classes = [IsAuthenticated, HasCapability('hl7.monitor')]

    def retrieve(self, request, *args, **kwargs):
        msg = self.get_object()
        audit(request, A.VIEW, 'hl7.hl7message', entity_id=msg.pk, patient=msg.patient)
        return Response(self.get_serializer(msg).data)


class HL7MessageResendView(APIView):
    """POST /api/hl7/messages/<id>/resend/   try again to send a failed outbound message."""
    permission_classes = [IsAuthenticated, HasCapability('hl7.monitor')]

    def post(self, request, pk):
        msg = get_object_or_404(HL7Message.objects.select_related('system', 'patient'), pk=pk)
        try:
            services.resend(msg)
        except services.ResendError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        audit(request, A.UPDATE, 'hl7.hl7message', entity_id=msg.pk, patient=msg.patient)
        return Response(HL7MessageDetailSerializer(msg).data)
