from django.contrib.auth.models import User
from django.db import models


class WorkTag(models.Model):
    name = models.CharField(max_length=100)
    month = models.IntegerField(null=True, blank=True)  # 1–12 lub null dla stałych
    year = models.IntegerField(null=True, blank=True)  # lub null dla stałych
    is_static = models.BooleanField(default=False)

    class Meta:
        ordering = ["is_static", "year", "month", "name"]

    def __str__(self):
        return self.name


class WorkHour(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    hours = models.FloatField()
    tag = models.ForeignKey(WorkTag, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.user.username} — {self.date}: {self.hours}h"
