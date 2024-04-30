from django.urls import path, include

from . import views


app_name = "agents"

urlpatterns = [
    path("", views.AgentListView.as_view(), name="agents_list"),
    path("<pk>/", views.AgentDetailView.as_view(), name="agents_detail_update_destroy"),
    path("oauth/callback/", views.OAuthCallBackAPIView.as_view(), name="oauth-callback"),
    path("oauth/<thirdparty>/connect/", views.OAuthAPIView.as_view(), name="oauth-connect"),
]