import calendar
from datetime import date
from typing import Any

from django.contrib.auth.models import User
from django.db import models

from .constants import POLISH_MONTHS, POLISH_WEEKDAYS
from .models import WorkHour, WorkTag


def get_days_list(year: int, month: int) -> list[dict[str, Any]]:  #! change Any
    num_days = calendar.monthrange(year, month)[1]
    return [
        {"day": d, "weekday": POLISH_WEEKDAYS[date(year, month, d).weekday()]}
        for d in range(1, num_days + 1)
    ]


def get_months_list() -> list[dict[str, Any]]:  #! change Any
    months = [{"num": i, "name": POLISH_MONTHS[i]} for i in range(1, 13)]
    return months


def get_total_hours(entries: WorkHour) -> int:
    return sum(e.hours for e in entries) if entries else 0


def get_tags(year: int, month: int) -> list[WorkTag]:
    return WorkTag.objects.filter(
        models.Q(is_static=True) | models.Q(month=month, year=year)
    )


def save_work_hours(
    request,
    days: list[dict[str, Any]],  #! change Any
    year: int,
    month: int,
) -> None:
    for item in days:
        day = item["day"]
        hours_raw = request.POST.get(str(day), "")
        tag_value = request.POST.get(f"tag_{day}", "")
        tag_obj = WorkTag.objects.get(id=tag_value) if tag_value else None

        try:
            hours_value = float(hours_raw.strip()) if hours_raw.strip() else 0
        except ValueError:
            hours_value = 0

        if hours_value < 0:
            hours_value = 0
        if tag_obj and tag_obj.is_static:
            hours_value = 0

        entry_date = date(year, month, day)
        WorkHour.objects.update_or_create(
            user=request.user,
            date=entry_date,
            defaults={"hours": hours_value, "tag": tag_obj},
        )


def save_admin_work_hours(
    request,
    users: list[User],
    days: list[dict[str, Any]],  #! change Any
    year: int,
    month: int,
) -> None:
    for user in users:
        for item in days:
            day = item["day"]
            hours_raw = request.POST.get(f"{user.id}_{day}", "")
            tag_value = request.POST.get(f"tag_{user.id}_{day}", "")
            tag_obj = WorkTag.objects.get(id=tag_value) if tag_value else None

            try:
                hours_value = float(hours_raw.strip()) if hours_raw.strip() else 0
            except ValueError:
                hours_value = 0

            if hours_value < 0:
                hours_value = 0
            if tag_obj and tag_obj.is_static:
                hours_value = 0

            entry_date = date(year, month, day)
            WorkHour.objects.update_or_create(
                user=user,
                date=entry_date,
                defaults={"hours": hours_value, "tag": tag_obj},
            )
