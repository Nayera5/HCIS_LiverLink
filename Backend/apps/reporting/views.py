"""
Reporting & Analytics API (spec §15). Read-only reports computed from existing data:

    GET /api/reports/patients/       reports.patients       super_admin, transplant_coordinator, hepatologist
    GET /api/reports/financial/      reports.financial      super_admin, billing_admin
    GET /api/reports/transplant/     reports.transplant     super_admin, transplant_coordinator, hepatologist,
                                                            transplant_surgeon
    GET /api/reports/system-usage/   reports.system_usage   super_admin

Query params: `date_from`, `date_to` (YYYY-MM-DD, optional, inclusive) and `export=csv|pdf`
to download the report instead of getting JSON. (`format` is not used because DRF reserves it.)
Every export is written to the audit log; viewing a report on screen is not (audit policy:
dashboard reads are not logged).

Imaging/AI reports are not served yet: modules 7 and 9 have no data models.
"""
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import AuditLog
from apps.accounts.permissions import HasCapability

from . import reports
from .exports import report_to_csv, report_to_pdf

EXPORTERS = {'csv': report_to_csv, 'pdf': report_to_pdf}


class _ReportView(APIView):
    """Subclasses set `permission_classes` and `build_report` (a function from reports.py)."""

    build_report = None

    def get(self, request):
        export = (request.query_params.get('export') or '').strip().lower()
        if export and export not in EXPORTERS:
            raise ValidationError({'export': 'Choose csv or pdf.'})

        date_from, date_to = reports.parse_period(request.query_params)
        report = type(self).build_report(date_from, date_to)
        if not export:
            return Response(report)

        audit(request, AuditLog.Action.EXPORT, f"reporting.{report['key']}")
        return EXPORTERS[export](report)


class PatientReportView(_ReportView):
    permission_classes = [IsAuthenticated, HasCapability('reports.patients')]
    build_report = reports.patient_report


class FinancialReportView(_ReportView):
    permission_classes = [IsAuthenticated, HasCapability('reports.financial')]
    build_report = reports.financial_report


class TransplantReportView(_ReportView):
    permission_classes = [IsAuthenticated, HasCapability('reports.transplant')]
    build_report = reports.transplant_report


class SystemUsageReportView(_ReportView):
    permission_classes = [IsAuthenticated, HasCapability('reports.system_usage')]
    build_report = reports.system_usage_report
