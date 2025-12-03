from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jan", password="pass123")
        self.client.login(username="jan", password="pass123")
        self.url = reverse("logout")

    def test_logout_redirects_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_user_is_logged_out(self):
        self.client.get(self.url)

        self.client.get(reverse("login"))
        self.assertFalse("_auth_user_id" in self.client.session)
