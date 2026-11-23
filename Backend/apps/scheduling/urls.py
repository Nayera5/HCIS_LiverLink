from rest_framework.routers import DefaultRouter

from . import views

app_name = "scheduling"

router = DefaultRouter()
router.register("schedules", views.DoctorScheduleViewSet, basename="schedule")
router.register("appointments", views.AppointmentViewSet, basename="appointment")

urlpatterns = router.urls
