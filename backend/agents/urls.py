from django.urls import path 

from . import views


app_name = "agents"

url_patterns = [
    path("", views.AgentAPIView.as_view(), name="agent-list"),
]