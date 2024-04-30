from django.urls import path, include

from . import views


app_name = "agents"

urlpatterns = [
    path("", views.AgentListView.as_view(), name="agents_list"),
    path("<pk>/", views.AgentDetailView.as_view(), name="agents_detail_update_destroy"),
]