from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase

from django_app.models import Machine, MachineWorkLog, WorkHour, WorkTag


class WorkHourModelTest(TestCase):
    def test_total_hours(self):
        user = User.objects.create(username="u")
        wh = WorkHour.objects.create(
            user=user,
            date=date(2025, 12, 1),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.assertEqual(wh.total_hours, 8)


class WorkTagModelTest(TestCase):
    def test_tag_creation(self):
        tag = WorkTag.objects.create(name="Office", is_static=False)
        self.assertEqual(tag.name, "Office")
        self.assertFalse(tag.is_static)


class MachineModelTest(TestCase):
    def test_machine_creation(self):
        machine = Machine.objects.create(name="Excavator")
        self.assertEqual(machine.name, "Excavator")


class MachineWorkLogModelTest(TestCase):
    def test_machine_work_log_creation(self):
        machine = Machine.objects.create(name="Excavator")
        mwh = MachineWorkLog.objects.create(
            machine=machine,
            date=date(2025, 12, 1),
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        self.assertEqual(mwh.total_hours, 8)
