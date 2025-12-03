from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from django_app.models import Machine, MachineWorkLog, WorkHour, WorkTag


class AdminMonthlyReportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        self.client.login(username="admin", password="pass")

        self.user1 = User.objects.create_user(username="u1", password="p1")
        self.user2 = User.objects.create_user(username="u2", password="p2")

        self.t1 = WorkTag.objects.create(name="Painting")
        self.t2 = WorkTag.objects.create(name="Cleaning")

        self.m1 = Machine.objects.create(name="AAAAA")
        self.m2 = Machine.objects.create(name="BBBBB")

        self.url = reverse("monthly-report") + "?year=2025&month=1"

    def wh(self, user, d, sh, sm, eh, em, tag):
        return WorkHour.objects.create(
            user=user,
            date=d,
            start_time=time(sh, sm) if sh is not None else None,
            end_time=time(eh, em) if eh is not None else None,
            tag=tag,
        )

    def mw(self, machine, d, sh, sm, eh, em):
        return MachineWorkLog.objects.create(
            machine=machine,
            date=d,
            start_time=time(sh, sm) if sh is not None else None,
            end_time=time(eh, em) if eh is not None else None,
        )

    def test_view_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("tag_hours", response.context)
        self.assertIn("machine_hours", response.context)

    def test_tag_summary(self):
        self.wh(self.user1, date(2025, 1, 5), 6, 0, 10, 0, self.t1)
        self.wh(self.user2, date(2025, 1, 5), 6, 0, 8, 0, self.t1)
        self.wh(self.user1, date(2025, 1, 6), 7, 0, 8, 30, self.t2)

        resp = self.client.get(self.url)
        tag_hours = dict(resp.context["tag_hours"])

        self.assertAlmostEqual(tag_hours["Painting"], 6.0)
        self.assertAlmostEqual(tag_hours["Cleaning"], 1.5)

    def test_machine_summary(self):
        self.mw(self.m1, date(2025, 1, 5), 8, 0, 12, 0)
        self.mw(self.m1, date(2025, 1, 7), 6, 0, 9, 0)
        self.mw(self.m2, date(2025, 1, 5), 10, 0, 13, 0)

        resp = self.client.get(self.url)
        machine_hours = dict(resp.context["machine_hours"])

        self.assertAlmostEqual(machine_hours["AAAAA"], 7.0)
        self.assertAlmostEqual(machine_hours["BBBBB"], 3.0)

    def test_zero_hour_records_are_ignored(self):
        self.wh(self.user1, date(2025, 1, 5), None, None, None, None, self.t1)
        self.mw(self.m1, date(2025, 1, 5), None, None, None, None)

        resp = self.client.get(self.url)

        self.assertEqual(resp.context["tag_hours"], [])
        self.assertEqual(resp.context["machine_hours"], [])

    def test_summary_respects_month_and_year(self):
        self.wh(self.user1, date(2025, 1, 5), 10, 0, 12, 0, self.t1)
        self.wh(self.user1, date(2024, 1, 5), 10, 0, 11, 0, self.t1)

        resp = self.client.get(self.url)
        tag_hours = dict(resp.context["tag_hours"])

        self.assertAlmostEqual(tag_hours["Painting"], 2.0)
        self.assertEqual(len(tag_hours), 1)

    def test_sorted_results(self):
        self.wh(self.user1, date(2025, 1, 5), 7, 0, 9, 0, self.t2)
        self.wh(self.user2, date(2025, 1, 5), 7, 0, 10, 0, self.t1)

        self.mw(self.m2, date(2025, 1, 5), 8, 0, 9, 0)
        self.mw(self.m1, date(2025, 1, 6), 6, 0, 8, 0)

        resp = self.client.get(self.url)

        tag_hours = resp.context["tag_hours"]
        machine_hours = resp.context["machine_hours"]

        self.assertEqual(tag_hours[0][0], "Cleaning")
        self.assertEqual(machine_hours[0][0], "AAAAA")
