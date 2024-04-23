from django.urls import path 

from . import views


app_name = "bots"

urlpatterns = [
    path("install/<str:thirdparty>/<agent_id>/", views.OAUTHView.as_view(), name="install"),
    path("oauth/callback/", views.OAUTHCallbackView.as_view(), name="oauth-callback"),
    path("event/", views.EventView.as_view(), name="event"),
]