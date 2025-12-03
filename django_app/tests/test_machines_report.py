from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from django_app.models import Machine, MachineWorkLog


class MachineReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", password="adminpass", is_staff=True
        )
        self.client.login(username="admin", password="adminpass")

        self.m1 = Machine.objects.create(name="Tokarka")
        self.m2 = Machine.objects.create(name="Frezarka")

        self.url = reverse("machines-report") + "?year=2025&month=1"

    def d(self, day, field, idx):
        return f"day_{day}_{field}_{idx}"

    def payload(self, day, count, entries):
        data = {f"day_{day}_count": count}
        for idx, e in enumerate(entries):
            data[self.d(day, "machine", idx)] = e["machine"].id
            data[self.d(day, "start_hour", idx)] = e["sh"]
            data[self.d(day, "start_minute", idx)] = e["sm"]
            data[self.d(day, "end_hour", idx)] = e["eh"]
            data[self.d(day, "end_minute", idx)] = e["em"]
        return data

    def test_overwrite_existing(self):
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 10),
            start_time=time(6, 0),
            end_time=time(10, 0),
        )

        data = self.payload(
            10,
            1,
            [{"machine": self.m1, "sh": "07", "sm": "00", "eh": "15", "em": "00"}],
        )
        self.client.post(self.url, data)

        entry = MachineWorkLog.objects.get(machine=self.m1, date=date(2025, 1, 10))
        self.assertEqual(entry.start_time, time(7, 0))
        self.assertEqual(entry.end_time, time(15, 0))

    def test_multiple_logs_same_day(self):
        data = self.payload(
            12,
            2,
            [
                {"machine": self.m1, "sh": "06", "sm": "00", "eh": "10", "em": "00"},
                {"machine": self.m2, "sh": "11", "sm": "00", "eh": "15", "em": "00"},
            ],
        )
        self.client.post(self.url, data)

        logs = MachineWorkLog.objects.filter(date=date(2025, 1, 12)).order_by(
            "machine_id"
        )
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].machine, self.m1)
        self.assertEqual(logs[1].machine, self.m2)

    def test_end_before_start_error(self):
        data = self.payload(
            5, 1, [{"machine": self.m1, "sh": "10", "sm": "00", "eh": "08", "em": "00"}]
        )
        response = self.client.post(self.url, data, follow=True)

        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("nie może być wcześniej niż" in m for m in messages))
        self.assertEqual(
            MachineWorkLog.objects.filter(date=date(2025, 1, 5)).count(), 0
        )

    def test_redirect_after_save(self):
        data = self.payload(
            3, 1, [{"machine": self.m1, "sh": "07", "sm": "00", "eh": "09", "em": "00"}]
        )
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/machines-report", response.url)
