from django.urls import path, include
from django.urls import re_path
from social_django import views as django_social_views

from . import views

app_name = "accounts"

social_patterns = [
    # authentication / association
    re_path(r'^login/(?P<backend>[^/]+)/$', django_social_views.auth, name='begin'),
    re_path(r'^complete/(?P<backend>[^/]+)/$', views.complete, name='complete'),
    # disconnection
    re_path(r'^disconnect/(?P<backend>[^/]+)/$', django_social_views.disconnect, name='disconnect'),
    re_path(
        r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/$',
        django_social_views.disconnect,
        name='disconnect_individual',
    ),
]

user_patterns = [
    path("register/", views.CreateUserView.as_view(), name="register"),
    path("account-confirm/<user>/<token>/", views.UserAccountConfirmationView.as_view(), name="account-confirm"),
    path("login/", views.CookieTokenObtainPairView.as_view(), name="login"),
    path("password-reset/", views.RequestPasswordResetView.as_view(), name="password-reset"),
    path("reset-password/<user_id>/<token>/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("password-change/", views.UserAccountChangePasswordView.as_view(), name="password-change"),
    path("token-refresh/", views.CookieTokenRefreshView.as_view(), name="jwt_token_refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path('social/', include((social_patterns, 'social'), namespace='social')),
]

urlpatterns = [path("auth/", include(user_patterns))]
