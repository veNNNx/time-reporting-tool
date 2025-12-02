import calendar
from datetime import date, time
from typing import Any

from django.contrib import messages
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.http import HttpRequest

from .constants import POLISH_MONTHS, POLISH_WEEKDAYS
from .models import MachineWorkLog, WorkHour, WorkTag


def get_days_list(year: int, month: int) -> list[dict[str, int | str]]:
    num_days = calendar.monthrange(year, month)[1]
    return [
        {"day": d, "weekday": POLISH_WEEKDAYS[date(year, month, d).weekday()]}
        for d in range(1, num_days + 1)
    ]


def get_months_list() -> list[dict[str, str | int]]:
    months = [{"num": i, "name": POLISH_MONTHS[i]} for i in range(1, 13)]
    return months


def get_total_hours(entries: list[WorkHour]) -> float:
    return sum(e.total_hours for e in entries) if entries else 0


def get_tags(year: int, month: int) -> list[WorkTag]:
    return WorkTag.objects.filter(
        models.Q(is_static=True) | models.Q(month=month, year=year)
    )


def save_work_hours(
    request: HttpRequest,
    days: list[dict[str, Any]],
    year: int,
    month: int,
) -> None:
    is_error = False
    for day in days:
        day_num = day["day"]
        date_obj = date(year, month, day_num)

        start_h = request.POST.get(f"start_hour_{day_num}")
        start_m = request.POST.get(f"start_minute_{day_num}")
        end_h = request.POST.get(f"end_hour_{day_num}")
        end_m = request.POST.get(f"end_minute_{day_num}")
        tag_id = request.POST.get(f"tag_{day_num}")

        tag = WorkTag.objects.filter(id=tag_id).first() if tag_id else None
        obj = WorkHour.objects.filter(user=request.user, date=date_obj).first()

        if not (start_h and start_m and end_h and end_m):
            if tag_id:
                if obj:
                    obj.tag = tag
                    obj.save()
                else:
                    WorkHour.objects.create(
                        user=request.user,
                        date=date_obj,
                        tag=tag,
                        start_time=None,
                        end_time=None,
                    )
            continue

        start_time = time(int(start_h), int(start_m))
        end_time = time(int(end_h), int(end_m))

        if end_time < start_time:
            is_error = True
            messages.error(
                request,
                f"Dzień {day_num}: koniec pracy nie może być wcześniejszy niż początek.",
            )
            continue

        WorkHour.objects.update_or_create(
            user=request.user,
            date=date_obj,
            defaults={
                "start_time": start_time,
                "end_time": end_time,
                "tag": tag,
            },
        )

    if not is_error:
        messages.success(request, "Dane zapisano poprawnie.")


def save_admin_work_hours(
    request: HttpRequest,
    users: list[AbstractUser],
    days: list[dict[str, Any]],
    year: int,
    month: int,
) -> None:
    for user in users:
        for day in days:
            day_num = day["day"]
            date_obj = date(year, month, day_num)

            prefix = f"user_{user.id}_day_{day_num}"

            start_h = request.POST.get(f"{prefix}_start_hour")
            start_m = request.POST.get(f"{prefix}_start_minute")
            end_h = request.POST.get(f"{prefix}_end_hour")
            end_m = request.POST.get(f"{prefix}_end_minute")
            tag_id = request.POST.get(f"{prefix}_tag")

            tag = WorkTag.objects.filter(id=tag_id).first() if tag_id else None
            obj = WorkHour.objects.filter(user=user, date=date_obj).first()

            if not (start_h and start_m and end_h and end_m):
                if tag:
                    if obj:
                        obj.tag = tag
                        obj.start_time = None
                        obj.end_time = None
                        obj.save()
                    else:
                        WorkHour.objects.create(
                            user=user,
                            date=date_obj,
                            tag=tag,
                            start_time=None,
                            end_time=None,
                        )
                continue

            start_time = time(int(start_h), int(start_m))
            end_time = time(int(end_h), int(end_m))

            if end_time < start_time:
                messages.error(
                    request,
                    f"{user.username} – {day_num}: koniec pracy nie może być wcześniejszy niż początek.",
                )
                continue

            if obj:
                obj.start_time = start_time
                obj.end_time = end_time
                obj.tag = tag
                obj.save()
            else:
                WorkHour.objects.create(
                    user=user,
                    date=date_obj,
                    start_time=start_time,
                    end_time=end_time,
                    tag=tag,
                )


def get_month_machine_logs(year: int, month: int) -> dict[int, list[MachineWorkLog]]:
    logs = MachineWorkLog.objects.filter(
        date__year=year, date__month=month
    ).select_related("machine")

    result: dict[int, list[MachineWorkLog]] = {}
    num_days = calendar.monthrange(year, month)[1]
    for d in range(1, num_days + 1):
        result[d] = []

    for log in logs:
        result[log.date.day].append(log)

    return result


def save_machine_work(
    request: HttpRequest, days: list[dict[str, Any]], year: int, month: int
) -> None:
    is_error = False

    for day in days:
        day_num = day["day"]
        date_obj = date(year, month, day_num)

        count_raw = request.POST.get(f"day_{day_num}_count")
        if count_raw is not None:
            count = int(count_raw)
        else:
            count = 0
            while True:
                prefix = f"day_{day_num}_machine_{count}"
                if prefix in request.POST:
                    count += 1
                else:
                    break

        MachineWorkLog.objects.filter(date=date_obj).delete()

        for i in range(count):
            machine_id = request.POST.get(f"day_{day_num}_machine_{i}")
            start_h = request.POST.get(f"day_{day_num}_start_hour_{i}")
            start_m = request.POST.get(f"day_{day_num}_start_minute_{i}")
            end_h = request.POST.get(f"day_{day_num}_end_hour_{i}")
            end_m = request.POST.get(f"day_{day_num}_end_minute_{i}")

            if not (machine_id and start_h and start_m and end_h and end_m):
                continue

            start_time = time(int(start_h), int(start_m))
            end_time = time(int(end_h), int(end_m))

            if end_time < start_time:
                is_error = True
                messages.error(
                    request,
                    f"Dzień {day_num}: koniec pracy maszyny nie może być wcześniej niż początek.",
                )
                continue

            MachineWorkLog.objects.create(
                machine_id=machine_id,
                date=date_obj,
                start_time=start_time,
                end_time=end_time,
            )

    if not is_error:
        messages.success(request, "Dane maszyn zapisano poprawnie.")
