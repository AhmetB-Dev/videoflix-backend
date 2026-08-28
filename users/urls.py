from django.urls import path

from .views import ActivateAccountView, LoginView, RegisterView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "activate/<str:uidb64>/<str:token>/",
        ActivateAccountView.as_view(),
        name="activate-account",
    ),
    path("login/", LoginView.as_view(), name="login"),
]
