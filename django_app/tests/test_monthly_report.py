from datetime import date, time

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from django_app.models import Machine, MachineWorkLog, WorkHour, WorkTag


class AdminMonthlyReportTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin
        self.admin = User.objects.create_superuser(username="admin", password="pass")
        self.client.login(username="admin", password="pass")

        # Users
        self.user1 = User.objects.create_user(username="u1", password="p1")
        self.user2 = User.objects.create_user(username="u2", password="p2")

        # Tags
        self.t1 = WorkTag.objects.create(name="Malowanie")
        self.t2 = WorkTag.objects.create(name="Sprzątanie")

        # Machines
        self.m1 = Machine.objects.create(name="Koparka")
        self.m2 = Machine.objects.create(name="Wozidło")

        self.url = reverse("monthly-report") + "?year=2025&month=1"

    def test_view_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("tag_hours", response.context)
        self.assertIn("machine_hours", response.context)

    def test_tag_summary(self):
        WorkHour.objects.create(
            user=self.user1,
            date=date(2025, 1, 5),
            start_time=time(6, 0),
            end_time=time(10, 0),
            tag=self.t1,
        )
        WorkHour.objects.create(
            user=self.user2,
            date=date(2025, 1, 5),
            start_time=time(6, 0),
            end_time=time(8, 0),
            tag=self.t1,
        )
        # Tag t2 raz
        WorkHour.objects.create(
            user=self.user1,
            date=date(2025, 1, 6),
            start_time=time(7, 0),
            end_time=time(8, 30),
            tag=self.t2,
        )

        response = self.client.get(self.url)
        tag_hours = dict(response.context["tag_hours"])

        self.assertAlmostEqual(tag_hours["Malowanie"], 6.0)
        self.assertAlmostEqual(tag_hours["Sprzątanie"], 1.5)

    def test_machine_summary(self):
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 5),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 7),
            start_time=time(6, 0),
            end_time=time(9, 0),
        )
        MachineWorkLog.objects.create(
            machine=self.m2,
            date=date(2025, 1, 5),
            start_time=time(10, 0),
            end_time=time(13, 0),
        )

        response = self.client.get(self.url)
        machine_hours = dict(response.context["machine_hours"])

        self.assertAlmostEqual(machine_hours["Koparka"], 7.0)
        self.assertAlmostEqual(machine_hours["Wozidło"], 3.0)

    def test_zero_hour_records_are_ignored(self):
        WorkHour.objects.create(
            user=self.user1,
            date=date(2025, 1, 5),
            start_time=None,
            end_time=None,
            tag=self.t1,
        )
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 5),
            start_time=None,
            end_time=None,
        )

        response = self.client.get(self.url)
        tag_hours = response.context["tag_hours"]
        machine_hours = response.context["machine_hours"]

        self.assertEqual(tag_hours, [])
        self.assertEqual(machine_hours, [])

    def test_summary_respects_month_and_year(self):
        WorkHour.objects.create(
            user=self.user1,
            date=date(2025, 1, 5),
            start_time=time(10, 0),
            end_time=time(12, 0),
            tag=self.t1,
        )
        WorkHour.objects.create(
            user=self.user1,
            date=date(2024, 1, 5),
            start_time=time(10, 0),
            end_time=time(11, 0),
            tag=self.t1,
        )

        response = self.client.get(self.url)
        tag_hours = dict(response.context["tag_hours"])

        self.assertAlmostEqual(tag_hours["Malowanie"], 2.0)
        self.assertEqual(len(tag_hours), 1)

    def test_sorted_results(self):
        # Tagi
        WorkHour.objects.create(
            user=self.user1,
            date=date(2025, 1, 5),
            start_time=time(7, 0),
            end_time=time(9, 0),
            tag=self.t2,
        )
        WorkHour.objects.create(
            user=self.user2,
            date=date(2025, 1, 5),
            start_time=time(7, 0),
            end_time=time(10, 0),
            tag=self.t1,
        )

        # Maszyny
        MachineWorkLog.objects.create(
            machine=self.m2,
            date=date(2025, 1, 5),
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        MachineWorkLog.objects.create(
            machine=self.m1,
            date=date(2025, 1, 6),
            start_time=time(6, 0),
            end_time=time(8, 0),
        )

        response = self.client.get(self.url)

        tag_hours = response.context["tag_hours"]
        machine_hours = response.context["machine_hours"]

        self.assertEqual(tag_hours[0][0], "Malowanie")
        self.assertEqual(machine_hours[0][0], "Koparka")
