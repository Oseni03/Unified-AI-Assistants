from rest_framework import routers

from .views import IntegrationViewSet

app_name = "integration"

router = routers.SimpleRouter()
router.register(r'', IntegrationViewSet, basename="integrations")
urlpatterns = router.urls