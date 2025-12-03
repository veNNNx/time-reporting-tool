from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from django_app.models import WorkHour, WorkTag


class EmployerReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        self.client.login(username="admin", password="pass")

        self.url = reverse("employer-report")
        self.base_qs = "?year=2025&month=1"

    def p(self, day, field):
        return f"{field}_{day}"

    def time_payload(self, day, sh, sm, eh, em):
        return {
            self.p(day, "start_hour"): sh,
            self.p(day, "start_minute"): sm,
            self.p(day, "end_hour"): eh,
            self.p(day, "end_minute"): em,
        }

    def test_save_single_day(self):
        data = self.time_payload(10, "08", "00", "16", "00")
        self.client.post(self.url + self.base_qs, data)

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

        data = self.time_payload(10, "07", "00", "15", "00")
        self.client.post(self.url + self.base_qs, data)

        w = WorkHour.objects.get(user=self.user, date=date(2025, 1, 10))
        self.assertEqual(w.total_hours, 8.0)

    def test_end_before_start_error(self):
        data = self.time_payload(5, "12", "00", "08", "00")
        response = self.client.post(self.url + self.base_qs, data)

        msgs = list(get_messages(response.wsgi_request))
        self.assertTrue(any("wcześniejszy" in str(m) for m in msgs))
        self.assertEqual(WorkHour.objects.filter(date=date(2025, 1, 5)).count(), 0)

    def test_no_delete_other_days(self):
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 11),
            start_time=time(6, 0),
            end_time=time(8, 0),
        )

        data = self.time_payload(10, "10", "00", "12", "00")
        self.client.post(self.url + self.base_qs, data)

        self.assertEqual(WorkHour.objects.filter(date=date(2025, 1, 11)).count(), 1)

    def test_redirect_after_post(self):
        data = self.time_payload(10, "10", "00", "12", "00")
        response = self.client.post(self.url + self.base_qs, data)

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

        response = self.client.get(reverse("monthly-report") + self.base_qs)
        tag_hours = dict(response.context["tag_hours"])

        self.assertAlmostEqual(tag_hours["Kopanie"], 4.0)

    def test_today_day_and_hours_context(self):
        tag = WorkTag.objects.create(
            name="Kopanie", month=1, year=2025, is_static=False
        )
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 10),
            start_time=time(8, 0),
            end_time=time(12, 0),
            tag=tag,
        )
        WorkHour.objects.create(
            user=self.user,
            date=date(2025, 1, 11),
            start_time=time(9, 0),
            end_time=time(11, 30),
            tag=tag,
        )

        response = self.client.get(self.url + self.base_qs)
        ctx = response.context

        self.assertEqual(ctx["today_day"], None)  # 2025-01 ≠ dzisiaj
        self.assertIn(10, ctx["hours"])
        self.assertIn(11, ctx["hours"])
        self.assertEqual(ctx["hours"][10].total_hours, 4.0)
        self.assertEqual(ctx["hours"][11].total_hours, 2.5)
        self.assertAlmostEqual(ctx["total_hours"], 6.5)
        self.assertIn(tag, ctx["tags"])
