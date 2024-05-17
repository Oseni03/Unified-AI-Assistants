from rest_framework import routers

from .views import AgentViewSet

app_name = "agents"

router = routers.SimpleRouter()
router.register(r'', AgentViewSet, basename="agents")
urlpatterns = router.urls