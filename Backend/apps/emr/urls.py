from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "emr"

router = DefaultRouter()
router.register("encounters", views.EncounterViewSet, basename="encounter")
router.register("medical-history", views.MedicalHistoryViewSet, basename="medical-history")
router.register("diagnoses", views.DiagnosisViewSet, basename="diagnosis")
router.register("vital-signs", views.VitalSignsViewSet, basename="vital-signs")
router.register("documents", views.DocumentViewSet, basename="document")

urlpatterns = [
    path("icd10/", views.Icd10SearchView.as_view(), name="icd10-search"),
    *router.urls,
]
