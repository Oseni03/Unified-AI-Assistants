from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views


app_name = "agents"


router = DefaultRouter()
router.register(r"", views.AgentViewset, basename="agent")

urlpatterns = [
    path("", include(router.urls)),
]