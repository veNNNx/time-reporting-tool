from datetime import date, time, timedelta

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

        self.static_tag = WorkTag.objects.create(name="Urlop", is_static=True)

        today = date.today()
        self.normal_tag = WorkTag.objects.create(
            name="Kopanie",
            month=today.month,
            year=today.year,
            is_static=False,
        )

        self.url = reverse("dashboard")

        self.year = today.year
        self.month = today.month

        self.editable_day_1 = today - timedelta(days=1)
        self.editable_day_2 = today - timedelta(days=2)
        self.editable_day_3 = today

        self.old_day = today - timedelta(days=4)

    def test_dashboard_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)

    def test_save_single_day(self):
        day = self.editable_day_1

        response = self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"start_hour_{day.day}": "08",
                f"start_minute_{day.day}": "00",
                f"end_hour_{day.day}": "12",
                f"end_minute_{day.day}": "00",
            },
        )

        self.assertEqual(response.status_code, 302)

        entry = WorkHour.objects.get(user=self.user, date=day)
        self.assertEqual(entry.total_hours, 4.0)

    def test_save_multiple_days(self):
        d1 = self.editable_day_1
        d2 = self.editable_day_2

        self.client.post(
            self.url + f"?year={self.year}&month={self.month}",
            {
                f"start_hour_{d1.day}": "07",
                f"start_minute_{d1.day}": "00",
                f"end_hour_{d1.day}": "15",
                f"end_minute_{d1.day}": "00",
                f"start_hour_{d2.day}": "06",
                f"start_minute_{d2.day}": "30",
                f"end_hour_{d2.day}": "14",
                f"end_minute_{d2.day}": "00",
            },
        )

        e1 = WorkHour.objects.get(user=self.user, date=d1)
        e2 = WorkHour.objects.get(user=self.user, date=d2)

        self.assertEqual(e1.total_hours, 8.0)
        self.assertEqual(e2.total_hours, 7.5)

    def test_static_tag(self):
        day = self.editable_day_1

        self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"tag_{day.day}": str(self.static_tag.id),
                f"start_hour_{day.day}": "08",
                f"start_minute_{day.day}": "00",
                f"end_hour_{day.day}": "16",
                f"end_minute_{day.day}": "00",
            },
        )

        entry = WorkHour.objects.get(user=self.user, date=day)
        self.assertEqual(entry.tag, self.static_tag)
        self.assertEqual(entry.start_time, time(8, 0))
        self.assertEqual(entry.end_time, time(16, 0))

    def test_tag_without_time(self):
        day = self.editable_day_2

        self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {f"tag_{day.day}": str(self.normal_tag.id)},
        )

        entry = WorkHour.objects.get(user=self.user, date=day)
        self.assertEqual(entry.tag, self.normal_tag)
        self.assertEqual(entry.total_hours, 0.0)

    def test_time_end_before_start_error(self):
        day = self.editable_day_3

        response = self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"start_hour_{day.day}": "12",
                f"start_minute_{day.day}": "00",
                f"end_hour_{day.day}": "08",
                f"end_minute_{day.day}": "00",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("nie może być wcześniejszy" in str(m) for m in messages))

        self.assertFalse(WorkHour.objects.filter(user=self.user, date=day).exists())

    def test_update_existing_entry(self):
        day = self.editable_day_1

        WorkHour.objects.create(
            user=self.user,
            date=day,
            start_time=time(7, 0),
            end_time=time(10, 0),
        )

        self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"start_hour_{day.day}": "08",
                f"start_minute_{day.day}": "00",
                f"end_hour_{day.day}": "16",
                f"end_minute_{day.day}": "00",
                f"tag_{day.day}": str(self.normal_tag.id),
            },
        )

        entry = WorkHour.objects.get(user=self.user, date=day)
        self.assertEqual(entry.total_hours, 8.0)
        self.assertEqual(entry.tag, self.normal_tag)

    def test_empty_fields_do_not_create(self):
        day = self.editable_day_3

        self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"start_hour_{day.day}": "",
                f"start_minute_{day.day}": "",
                f"end_hour_{day.day}": "",
                f"end_minute_{day.day}": "",
            },
        )
        exists = WorkHour.objects.filter(user=self.user, date=day).exists()
        self.assertFalse(exists)

    def test_success_message_on_save(self):
        day = self.editable_day_1

        response = self.client.post(
            self.url + f"?year={day.year}&month={day.month}",
            {
                f"start_hour_{day.day}": "08",
                f"start_minute_{day.day}": "00",
                f"end_hour_{day.day}": "12",
                f"end_minute_{day.day}": "00",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Dane zapisano" in str(m) for m in messages))

    def test_cannot_edit_day_older_than_3_days(self):
        old = self.old_day
        response = self.client.post(
            self.url + f"?year={old.year}&month={old.month}",
            {
                f"start_hour_{old.day}": "08",
                f"start_minute_{old.day}": "00",
                f"end_hour_{old.day}": "12",
                f"end_minute_{old.day}": "00",
            },
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("nie można edytować" in str(m) for m in messages))

        self.assertFalse(WorkHour.objects.filter(user=self.user, date=old).exists())
