from django.urls import path

from .views import (
    ActivateAccountView,
    LoginView,
    LogoutView,
    PasswordConfirmView,
    PasswordResetView,
    RefreshTokenView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "activate/<str:uidb64>/<str:token>/",
        ActivateAccountView.as_view(),
        name="activate-account",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "token/refresh/",
        RefreshTokenView.as_view(),
        name="token-refresh",
    ),
    path(
        "password_reset/",
        PasswordResetView.as_view(),
        name="password-reset",
    ),
    path(
        "password_confirm/<str:uidb64>/<str:token>/",
        PasswordConfirmView.as_view(),
        name="password-confirm",
    ),
]
