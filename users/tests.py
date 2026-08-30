from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase


TEST_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    },
}


@override_settings(MAILERS=TEST_MAILERS)
class AuthTests(APITestCase):
    email = "test@example.com"
    password = "StrongTestPassword123!"

    def create_user(self, is_active=True):
        return User.objects.create_user(
            username=self.email,
            email=self.email,
            password=self.password,
            is_active=is_active,
        )

    def test_registration_creates_inactive_user(self):
        data = {
            "email": self.email,
            "password": self.password,
            "confirmed_password": self.password,
        }
        response = self.client.post("/api/register/", data, format="json")
        user = User.objects.get(email=self.email)

        self.assertEqual(response.status_code, 201)
        self.assertFalse(user.is_active)

    def test_registration_sends_activation_email(self):
        data = {
            "email": self.email,
            "password": self.password,
            "confirmed_password": self.password,
        }
        self.client.post("/api/register/", data, format="json")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])

    def test_activation_activates_user(self):
        user = self.create_user(is_active=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(f"/api/activate/{uid}/{token}/")
        user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(user.is_active)

    def test_active_user_can_login(self):
        self.create_user()
        data = {"email": self.email, "password": self.password}

        response = self.client.post("/api/login/", data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_inactive_user_cannot_login(self):
        self.create_user(is_active=False)
        data = {"email": self.email, "password": self.password}

        response = self.client.post("/api/login/", data, format="json")

        self.assertEqual(response.status_code, 401)

    def test_password_reset_sends_email(self):
        self.create_user()

        response = self.client.post(
            "/api/password_reset/",
            {"email": self.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.email])

    def test_password_reset_hides_unknown_email(self):
        response = self.client.post(
            "/api/password_reset/",
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_confirm_changes_password(self):
        user = self.create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        data = {
            "new_password": "NewStrongPassword123!",
            "confirm_password": "NewStrongPassword123!",
        }

        response = self.client.post(
            f"/api/password_confirm/{uid}/{token}/",
            data,
            format="json",
        )

        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(user.check_password(data["new_password"]))

    def test_refresh_token_creates_new_access_cookie(self):
        self.create_user()
        self.client.post(
            "/api/login/",
            {"email": self.email, "password": self.password},
            format="json",
        )

        response = self.client.post("/api/token/refresh/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.cookies)

    def test_logout_invalidates_refresh_token(self):
        self.create_user()
        self.client.post(
            "/api/login/",
            {
                "email": self.email,
                "password": self.password,
            },
            format="json",
        )

        response = self.client.post("/api/logout/")

        self.assertEqual(response.status_code, 200)

        refresh_response = self.client.post(
            "/api/token/refresh/",
        )
        self.assertEqual(
            refresh_response.status_code,
            401,
        )
