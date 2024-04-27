from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views


app_name = "agents"


router = DefaultRouter()
router.register(r"", views.AgentViewset, basename="agent")

urlpatterns = [
    path("", include(router.urls)),
    path("oauth/callback/", views.OAuthCallBackAPIView.as_view(), name="oauth-callback"),
    path("oauth/<thirdparty>/connect/", views.OAuthAPIView.as_view(), name="oauth-connect"),
]