from django.urls import path 

from . import views


app_name = "agents"

urlpatterns = [
    path("", views.AgentListCreateView.as_view(), name="agent-list-create"),
    path("<id>/", views.AgentRetrieveUpdateView.as_view(), name="agent-retrieve-update-destroy"),
]