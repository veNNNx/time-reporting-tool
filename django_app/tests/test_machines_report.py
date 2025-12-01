from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from django_app.models import Machine, MachineWorkLog


class MachineReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="admin", password="adminpass", is_staff=True
        )
        self.client.login(username="admin", password="adminpass")

        self.m1 = Machine.objects.create(name="Tokarka")
        self.m2 = Machine.objects.create(name="Frezarka")

        self.url = reverse("machines-report") + "?year=2025&month=1"

    def test_overwrite_existing(self):
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 10),
            start_time=time(6, 0),
            end_time=time(10, 0),
        )

        post_data = {
            "day_10_count": 1,
            "day_10_machine_0": self.m1.id,
            "day_10_start_hour_0": "07",
            "day_10_start_minute_0": "00",
            "day_10_end_hour_0": "15",
            "day_10_end_minute_0": "00",
        }

        self.client.post(self.url, post_data)

        entry = MachineWorkLog.objects.get(machine=self.m1, date=date(2025, 1, 10))
        self.assertEqual(entry.start_time, time(7, 0))
        self.assertEqual(entry.end_time, time(15, 0))

    def test_multiple_logs_same_day(self):
        post_data = {
            "day_12_count": 2,
            "day_12_machine_0": self.m1.id,
            "day_12_start_hour_0": "06",
            "day_12_start_minute_0": "00",
            "day_12_end_hour_0": "10",
            "day_12_end_minute_0": "00",
            "day_12_machine_1": self.m2.id,
            "day_12_start_hour_1": "11",
            "day_12_start_minute_1": "00",
            "day_12_end_hour_1": "15",
            "day_12_end_minute_1": "00",
        }

        self.client.post(self.url, post_data)

        logs = MachineWorkLog.objects.filter(date=date(2025, 1, 12)).order_by(
            "machine_id"
        )
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].machine, self.m1)
        self.assertEqual(logs[1].machine, self.m2)

    def test_end_before_start_error(self):
        post_data = {
            "day_5_count": 1,
            "day_5_machine_0": self.m1.id,
            "day_5_start_hour_0": "10",
            "day_5_start_minute_0": "00",
            "day_5_end_hour_0": "08",
            "day_5_end_minute_0": "00",
        }

        response = self.client.post(self.url, post_data, follow=True)

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("nie może być wcześniej niż" in m for m in messages))

        self.assertEqual(
            MachineWorkLog.objects.filter(date=date(2025, 1, 5)).count(),
            0,
        )

    def test_redirect_after_save(self):
        post_data = {
            "day_3_count": 1,
            "day_3_machine_0": self.m1.id,
            "day_3_start_hour_0": "07",
            "day_3_start_minute_0": "00",
            "day_3_end_hour_0": "09",
            "day_3_end_minute_0": "00",
        }

        response = self.client.post(self.url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/machines-report", response.url)
