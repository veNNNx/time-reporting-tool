from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from django_app.models import WorkHour, WorkTag


class UserDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="jan", password="pass123")
        self.client.login(username="jan", password="pass123")

        # Stały tag
        self.static_tag = WorkTag.objects.create(name="Urlop", is_static=True)

        # Tag normalny
        self.normal_tag = WorkTag.objects.create(
            name="Kopanie", month=1, year=2025, is_static=False
        )

        self.url = reverse("dashboard")

    def test_dashboard_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)

    def test_save_single_day(self):
        response = self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_5": "08",
                "start_minute_5": "00",
                "end_hour_5": "12",
                "end_minute_5": "00",
            },
        )
        self.assertEqual(response.status_code, 302)  # redirect

        entry = WorkHour.objects.get(user=self.user, date=date(2025, 1, 5))
        self.assertEqual(entry.total_hours, 4.0)

    def test_save_multiple_days(self):
        self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_2": "07",
                "start_minute_2": "00",
                "end_hour_2": "15",
                "end_minute_2": "00",
                "start_hour_3": "06",
                "start_minute_3": "30",
                "end_hour_3": "14",
                "end_minute_3": "00",
            },
        )

        e1 = WorkHour.objects.get(user=self.user, date=date(2025, 1, 2))
        e2 = WorkHour.objects.get(user=self.user, date=date(2025, 1, 3))

        self.assertEqual(e1.total_hours, 8.0)
        self.assertEqual(e2.total_hours, 7.5)

    def test_static_tag(self):
        self.client.post(
            self.url + "?year=2025&month=1",
            {
                "tag_10": str(self.static_tag.id),
                "start_hour_10": "08",
                "start_minute_10": "00",
                "end_hour_10": "16",
                "end_minute_10": "00",
            },
        )

        entry = WorkHour.objects.get(user=self.user, date=date(2025, 1, 10))
        self.assertEqual(entry.tag, self.static_tag)
        self.assertEqual(entry.start_time, time(8, 0))
        self.assertEqual(entry.end_time, time(16, 0))

    def test_tag_without_time(self):
        self.client.post(
            self.url + "?year=2025&month=1",
            {"tag_6": str(self.normal_tag.id)},
        )

        entry = WorkHour.objects.get(user=self.user, date=date(2025, 1, 6))
        self.assertEqual(entry.tag, self.normal_tag)
        self.assertEqual(entry.total_hours, 0.0)

    def test_time_end_before_start_error(self):
        response = self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_7": "12",
                "start_minute_7": "00",
                "end_hour_7": "08",
                "end_minute_7": "00",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("nie może być wcześniejszy" in str(m) for m in messages))

        self.assertFalse(
            WorkHour.objects.filter(user=self.user, date=date(2025, 1, 7)).exists()
        )

    def test_update_existing_entry(self):
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 15),
            start_time=time(7, 0),
            end_time=time(10, 0),
        )

        self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_15": "08",
                "start_minute_15": "00",
                "end_hour_15": "16",
                "end_minute_15": "00",
            },
        )

        entry = WorkHour.objects.get(user=self.user, date=date(2025, 1, 15))
        self.assertEqual(entry.total_hours, 8.0)

    def test_empty_fields_do_not_create(self):
        self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_4": "",
                "start_minute_4": "",
                "end_hour_4": "",
                "end_minute_4": "",
            },
        )
        exists = WorkHour.objects.filter(user=self.user, date=date(2025, 1, 4)).exists()
        self.assertFalse(exists)

    def test_success_message_on_save(self):
        response = self.client.post(
            self.url + "?year=2025&month=1",
            {
                "start_hour_1": "08",
                "start_minute_1": "00",
                "end_hour_1": "12",
                "end_minute_1": "00",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Dane zapisano" in str(m) for m in messages))
