from collections import defaultdict
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import models
from django.http import HttpRequest
from django.shortcuts import redirect, render

from .constants import HOURS_LIST, MINUTES_LIST
from .models import Machine, MachineWorkLog, WorkHour
from .utils import (
    get_days_list,
    get_month_machine_logs,
    get_months_list,
    get_tags,
    get_total_hours,
    save_admin_work_hours,
    save_machine_work,
    save_work_hours,
)


@login_required
def dashboard(request: HttpRequest):
    if request.user.is_staff:
        return admin_dashboard(request)
    return user_dashboard(request)


@login_required
def user_dashboard(request: HttpRequest):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)

    if request.method == "POST":
        save_work_hours(request=request, days=days, year=year, month=month)
        return redirect(f"/?month={month}&year={year}")

    today_day = today.day if (year == today.year and month == today.month) else None
    work_hours = WorkHour.objects.filter(
        user=request.user, date__year=year, date__month=month
    )

    return render(
        request,
        "user_dashboard.html",
        {
            "days": days,
            "month": month,
            "year": year,
            "hours": {e.date.day: e for e in work_hours},
            "total_hours": get_total_hours(work_hours),
            "today_day": today_day,  # to recolor current day
            "tags": get_tags(year=year, month=month),
            "months_list": get_months_list(),
            "years_list": list(range(today.year - 2, today.year + 3)),
            "hours_list": HOURS_LIST,
            "minutes_list": MINUTES_LIST,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request: HttpRequest):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)

    User = get_user_model()

    users = list(
        User.objects.filter(is_staff=False)
        .filter(
            models.Q(is_active=True)
            | models.Q(workhour__date__year=year, workhour__date__month=month)
        )
        .distinct()
        .order_by("username")
    )

    if request.method == "POST":
        save_admin_work_hours(
            request=request,
            users=users,
            days=days,
            year=year,
            month=month,
        )
        return redirect(f"/?month={month}&year={year}")

    work_hours = WorkHour.objects.select_related("user", "tag").filter(
        date__year=year, date__month=month, user__in=users
    )

    entries_dict = {u.id: {} for u in users}
    total_hours_dict = {u.id: 0 for u in users}

    for entry in work_hours:
        entries_dict[entry.user.id][entry.date.day] = entry
        total_hours_dict[entry.user.id] += entry.total_hours

    today_day = today.day if (year == today.year and month == today.month) else None

    return render(
        request,
        "admin_dashboard.html",
        {
            "days": days,
            "users": users,
            "entries_dict": entries_dict,
            "total_hours_dict": total_hours_dict,
            "tags": get_tags(year=year, month=month),
            "today_day": today_day,
            "month": month,
            "year": year,
            "months_list": get_months_list(),
            "years_list": list(range(today.year - 2, today.year + 3)),
            "hours_list": HOURS_LIST,
            "minutes_list": MINUTES_LIST,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_monthly_report(request: HttpRequest):  #! Roboty
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    # Tag report
    work_hours = WorkHour.objects.filter(
        date__year=year, date__month=month, user__is_staff=False
    )
    tag_sums = defaultdict(float)
    for wh in work_hours:
        if wh.tag:
            tag_sums[wh.tag.name] += wh.total_hours
    tag_hours = sorted(
        [(tag, total) for tag, total in tag_sums.items() if total > 0],
        key=lambda x: x[0],
    )

    # Machine report
    machine_logs = MachineWorkLog.objects.filter(
        date__year=year, date__month=month
    ).select_related("machine")

    machine_sums = defaultdict(float)

    for log in machine_logs:
        hours = log.total_hours
        if hours > 0:
            machine_sums[log.machine.name] += hours

    machine_hours = sorted(
        [(machine, hours) for machine, hours in machine_sums.items() if hours > 0],
        key=lambda x: x[0],
    )

    return render(
        request,
        "admin_monthly_report.html",
        {
            "month": month,
            "year": year,
            "tag_hours": tag_hours,
            "machine_hours": machine_hours,
            "months_list": get_months_list(),
            "years_list": list(range(today.year - 2, today.year + 3)),
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_employer_report(request: HttpRequest):  #!Pracodawca
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)

    if request.method == "POST":
        save_work_hours(request, days=days, year=year, month=month)
        return redirect(f"/employer-report?month={month}&year={year}")

    today_day = today.day if (year == today.year and month == today.month) else None
    work_hours = WorkHour.objects.filter(
        user=request.user, date__year=year, date__month=month
    )

    return render(
        request,
        "admin_employer_report.html",
        {
            "days": days,
            "month": month,
            "year": year,
            "hours": {e.date.day: e for e in work_hours},
            "total_hours": get_total_hours(work_hours),
            "today_day": today_day,  # to recolor current day
            "tags": get_tags(year=year, month=month),
            "months_list": get_months_list(),
            "years_list": list(range(today.year - 2, today.year + 3)),
            "hours_list": HOURS_LIST,
            "minutes_list": MINUTES_LIST,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_machines_report(request: HttpRequest):  #! Maszyny
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)
    machines = Machine.objects.all().order_by("name")

    logs_dict = get_month_machine_logs(year, month)

    if request.method == "POST":
        save_machine_work(request, days, year, month)
        return redirect(f"/machines-report?month={month}&year={year}")

    today_day = today.day if (year == today.year and month == today.month) else None

    return render(
        request,
        "admin_machines_report.html",
        {
            "days": days,
            "machines": machines,
            "logs_dict": logs_dict,
            "today_day": today_day,
            "month": month,
            "year": year,
            "months_list": get_months_list(),
            "years_list": list(range(today.year - 2, today.year + 3)),
            "hours_list": HOURS_LIST,
            "minutes_list": MINUTES_LIST,
        },
    )
