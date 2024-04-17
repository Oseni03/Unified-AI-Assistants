from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        "api/",
        include(
            [
                path("", include("common.urls", namespace="common")),
                path("", include("accounts.urls", namespace="accounts")),
                path("bots/", include("bots.urls", namespace="bots")),
                path("agents/", include("agents.urls", namespace="agents")),
            ]
        ),
    ),
]
