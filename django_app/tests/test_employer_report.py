from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from django_app.models import Machine, MachineWorkLog, WorkHour, WorkTag


class EmployerReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        self.client.login(username="admin", password="pass")
        self.url = reverse("employer-report") + "?year=2025&month=1"

    def test_save_single_day(self):
        data = {
            "start_hour_10": "08",
            "start_minute_10": "00",
            "end_hour_10": "16",
            "end_minute_10": "00",
        }

        self.client.post(self.url, data)

        w = WorkHour.objects.get(user=self.user, date=date(2025, 1, 10))
        self.assertEqual(w.start_time, time(8, 0))
        self.assertEqual(w.end_time, time(16, 0))

    def test_overwrite_existing(self):
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 10),
            start_time=time(6, 0),
            end_time=time(10, 0),
        )

        data = {
            "start_hour_10": "07",
            "start_minute_10": "00",
            "end_hour_10": "15",
            "end_minute_10": "00",
        }

        self.client.post(self.url, data)

        w = WorkHour.objects.get(user=self.user, date=date(2025, 1, 10))
        self.assertEqual(w.total_hours, 8.0)

    def test_end_before_start_error(self):
        data = {
            "start_hour_5": "12",
            "start_minute_5": "00",
            "end_hour_5": "08",
            "end_minute_5": "00",
        }

        response = self.client.post(self.url, data)
        msgs = list(get_messages(response.wsgi_request))

        self.assertTrue(any("wcześniejszy" in str(m) for m in msgs))
        self.assertEqual(
            WorkHour.objects.filter(date=date(2025, 1, 5)).count(),
            0,
        )

    def test_no_delete_other_days(self):
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 11),
            start_time=time(6, 0),
            end_time=time(8, 0),
        )

        data = {
            "start_hour_10": "10",
            "start_minute_10": "00",
            "end_hour_10": "12",
            "end_minute_10": "00",
        }

        self.client.post(self.url, data)

        self.assertEqual(
            WorkHour.objects.filter(date=date(2025, 1, 11)).count(),
            1,
        )

    def test_redirect_after_post(self):
        data = {
            "start_hour_10": "10",
            "start_minute_10": "00",
            "end_hour_10": "12",
            "end_minute_10": "00",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/employer-report?month=1&year=2025", response.url)

    def test_workhour_not_used_in_monthly_machine_report(self):
        tag = WorkTag.objects.create(
            name="Kopanie", month=1, year=2025, is_static=False
        )
        user1 = User.objects.create_user(username="u1", password="p1")
        WorkHour.objects.create(
            user=user1,
            date=date(2025, 1, 5),
            start_time=time(6, 0),
            end_time=time(10, 0),
            tag=tag,
        )

        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 10),
            start_time=time(4, 0),
            end_time=time(12, 0),
            tag=tag,
        )
        url = reverse("monthly-report") + "?year=2025&month=1"
        response = self.client.get(url)
        tag_hours = dict(response.context["tag_hours"])
        self.assertAlmostEqual(tag_hours["Kopanie"], 4.0)
