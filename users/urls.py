from django.urls import path

from .views import (
    ActivateAccountView,
    LoginView,
    RefreshTokenView,
    RegisterView,
    LogoutView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "activate/<str:uidb64>/<str:token>/",
        ActivateAccountView.as_view(),
        name="activate-account",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path(
        "token/refresh/",
        RefreshTokenView.as_view(),
        name="token-refresh",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
