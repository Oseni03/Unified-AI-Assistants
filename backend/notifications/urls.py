from rest_framework import routers

from .views import NotificationViewet

app_name = "notifications"

router = routers.SimpleRouter()
router.register(r'', NotificationViewet, basename="notifications")
urlpatterns = router.urls