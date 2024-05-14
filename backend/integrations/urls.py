from django.urls import path 

from . import views


app_name = "integrations"

urlpatterns = [
    path("oauth/agents/<str:thirdparty>/connect/", views.OAUTHView.as_view(), name="agent-install"),
    path("oauth/bots/<str:thirdparty>/install/<agent_id>/", views.OAUTHView.as_view(), name="bot-install"),
    path("oauth/callback/", views.OAUTHCallbackView.as_view(), name="oauth-callback"),
    path("event/", views.EventView.as_view(), name="event"),
    path("", views.IntegrationListView.as_view(), name="integration-list"),
]
