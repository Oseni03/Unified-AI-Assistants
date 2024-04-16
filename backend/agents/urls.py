from django.urls import path 

from . import views


app_name = "agents"

urlpatterns = [
    path("", views.AgentAPIView.as_view(), name="agent-list"),
]