from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import models


class WorkTag(models.Model):
    name = models.CharField(max_length=100)
    month = models.IntegerField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    is_static = models.BooleanField(default=False)

    class Meta:
        ordering = ["is_static", "year", "month", "name"]

    def __str__(self):
        return self.name


class WorkHour(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    tag = models.ForeignKey(WorkTag, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.user.username} — {self.date}: {self.total_hours}h"

    @property
    def total_hours(self) -> float:
        if not self.start_time or not self.end_time:
            return 0.0
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)

        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        delta = end_dt - start_dt
        return round(delta.total_seconds() / 3600, 2)


class Machine(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class MachineWorkLog(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    @property
    def total_hours(self) -> float:
        if not self.start_time or not self.end_time:
            return 0.0
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)

        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        delta = end_dt - start_dt
        return round(delta.total_seconds() / 3600, 2)

    def __str__(self):
        return f"{self.machine.name} - {self.date}"
