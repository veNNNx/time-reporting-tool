from datetime import date, time

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from django_app.models import WorkHour, WorkTag


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_user(
            username="admin", password="pass123", is_staff=True
        )
        self.client.login(username="admin", password="pass123")

        self.u1 = User.objects.create_user(username="jan", password="pass")
        self.u2 = User.objects.create_user(username="ola", password="pass")

        self.static_tag = WorkTag.objects.create(name="Urlop", is_static=True)
        self.normal_tag = WorkTag.objects.create(
            name="AAAAA", month=1, year=2025, is_static=False
        )

        self.url = reverse("dashboard")
        self.base_qs = "?year=2025&month=1"

    def p(self, user, day, field):
        return f"user_{user.id}_day_{day}_{field}"

    def time_payload(self, user, day, sh, sm, eh, em):
        return {
            self.p(user, day, "start_hour"): sh,
            self.p(user, day, "start_minute"): sm,
            self.p(user, day, "end_hour"): eh,
            self.p(user, day, "end_minute"): em,
        }

    def tag_payload(self, user, day, tag):
        return {self.p(user, day, "tag"): str(tag.id)}

    def test_dashboard_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.context)

    def test_save_single_day(self):
        payload = self.time_payload(self.u1, 5, "08", "00", "12", "00")
        response = self.client.post(self.url + self.base_qs, payload)
        self.assertEqual(response.status_code, 302)

        entry = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 5))
        self.assertEqual(entry.total_hours, 4.0)

    def test_save_multiple_days(self):
        payload = {}
        payload.update(self.time_payload(self.u1, 2, "07", "00", "15", "00"))
        payload.update(self.time_payload(self.u1, 3, "06", "30", "14", "00"))

        self.client.post(self.url + self.base_qs, payload)

        e1 = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 2))
        e2 = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 3))

        self.assertEqual(e1.total_hours, 8.0)
        self.assertEqual(e2.total_hours, 7.5)

    def test_static_tag(self):
        payload = {}
        payload.update(self.tag_payload(self.u1, 10, self.static_tag))
        payload.update(self.time_payload(self.u1, 10, "08", "00", "16", "00"))

        self.client.post(self.url + self.base_qs, payload)

        entry = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 10))
        self.assertEqual(entry.tag, self.static_tag)
        self.assertEqual(entry.start_time, time(8, 0))
        self.assertEqual(entry.end_time, time(16, 0))

    def test_tag_without_time(self):
        payload = self.tag_payload(self.u1, 6, self.normal_tag)

        self.client.post(self.url + self.base_qs, payload)

        entry = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 6))
        self.assertEqual(entry.tag, self.normal_tag)
        self.assertEqual(entry.total_hours, 0.0)

    def test_time_end_before_start_error(self):
        payload = self.time_payload(self.u1, 7, "12", "00", "08", "00")

        response = self.client.post(self.url + self.base_qs, payload)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("nie może być wcześniejszy" in str(m) for m in messages))

        self.assertFalse(
            WorkHour.objects.filter(user=self.u1, date=date(2025, 1, 7)).exists()
        )

    def test_update_existing_entry(self):
        WorkHour.objects.create(
            user=self.u1,
            date=date(2025, 1, 15),
            start_time=time(7, 0),
            end_time=time(10, 0),
        )

        payload = self.time_payload(self.u1, 15, "08", "00", "16", "00")
        self.client.post(self.url + self.base_qs, payload)

        entry = WorkHour.objects.get(user=self.u1, date=date(2025, 1, 15))
        self.assertEqual(entry.total_hours, 8.0)

    def test_empty_fields_do_not_create(self):
        payload = {
            self.p(self.u1, 4, "start_hour"): "",
            self.p(self.u1, 4, "start_minute"): "",
            self.p(self.u1, 4, "end_hour"): "",
            self.p(self.u1, 4, "end_minute"): "",
        }

        self.client.post(self.url + self.base_qs, payload)

        exists = WorkHour.objects.filter(user=self.u1, date=date(2025, 1, 4)).exists()
        self.assertFalse(exists)

    def test_success_message_on_save(self):
        payload = self.time_payload(self.u1, 1, "08", "00", "12", "00")

        response = self.client.post(self.url + self.base_qs, payload)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Dane zapisano" in str(m) for m in messages))

    def test_entries_dict_and_total_hours(self):
        WorkHour.objects.create(
            user=self.u1,
            date=date(2025, 1, 5),
            start_time=time(8, 0),
            end_time=time(12, 0),
            tag=self.static_tag,
        )
        WorkHour.objects.create(
            user=self.u1,
            date=date(2025, 1, 6),
            start_time=time(9, 0),
            end_time=time(11, 30),
            tag=self.normal_tag,
        )
        WorkHour.objects.create(
            user=self.u2,
            date=date(2025, 1, 5),
            start_time=time(7, 30),
            end_time=time(12, 0),
            tag=self.static_tag,
        )

        response = self.client.get(self.url + self.base_qs)
        self.assertEqual(response.status_code, 200)

        entries_dict = response.context["entries_dict"]
        total_hours_dict = response.context["total_hours_dict"]

        self.assertIn(self.u1.id, entries_dict)
        self.assertIn(self.u2.id, entries_dict)
        self.assertIn(5, entries_dict[self.u1.id])
        self.assertIn(6, entries_dict[self.u1.id])
        self.assertIn(5, entries_dict[self.u2.id])

        e1 = entries_dict[self.u1.id][5]
        self.assertEqual(e1.start_time, time(8, 0))
        self.assertEqual(e1.end_time, time(12, 0))
        self.assertEqual(e1.tag, self.static_tag)

        e2 = entries_dict[self.u1.id][6]
        self.assertEqual(e2.total_hours, 2.5)

        e3 = entries_dict[self.u2.id][5]
        self.assertEqual(e3.total_hours, 4.5)

        self.assertAlmostEqual(total_hours_dict[self.u1.id], 4 + 2.5)
        self.assertAlmostEqual(total_hours_dict[self.u2.id], 4.5)
