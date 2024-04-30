from django.urls import path 

from . import views


app_name = "integrations"

urlpatterns = [
    path("oauth/<str:thirdparty>/install/<agent_id>/", views.OAUTHView.as_view(), name="install"),
    path("oauth/callback/<str:thirdparty>/", views.OAUTHCallbackView.as_view(), name="oauth-callback"),
    path("event/", views.EventView.as_view(), name="event"),
]
