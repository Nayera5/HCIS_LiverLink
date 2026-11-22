from rest_framework.routers import DefaultRouter

from . import views

app_name = "emr"

router = DefaultRouter()
router.register("encounters", views.EncounterViewSet, basename="encounter")
router.register("medical-history", views.MedicalHistoryViewSet, basename="medical-history")
router.register("diagnoses", views.DiagnosisViewSet, basename="diagnosis")
router.register("vital-signs", views.VitalSignsViewSet, basename="vital-signs")
router.register("documents", views.DocumentViewSet, basename="document")

urlpatterns = router.urls
