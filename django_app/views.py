from collections import defaultdict
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from .models import WorkHour
from .utils import (
    get_days_list,
    get_months_list,
    get_tags,
    get_total_hours,
    save_admin_work_hours,
    save_work_hours,
)


@login_required
def dashboard(request):
    if request.user.is_staff:
        return admin_dashboard(request)
    return user_dashboard(request)


@login_required
def user_dashboard(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)

    if request.method == "POST":
        save_work_hours(request, days=days, year=year, month=month)
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
            "months": get_months_list(),
            "years": list(range(today.year - 2, today.year + 3)),
            "hours": {e.date.day: e for e in work_hours},
            "total_hours": get_total_hours(work_hours),
            "today_day": today_day,
            "tags": get_tags(year=year, month=month),
        },
    )


@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    days = get_days_list(year=year, month=month)

    users = list(
        {entry.user for entry in WorkHour.objects.select_related("user").all()}
    )

    if request.method == "POST":
        save_admin_work_hours(
            request=request, users=users, days=days, year=year, month=month
        )
        return redirect(f"?month={month}&year={year}")

    work_hours = WorkHour.objects.select_related("user", "tag").filter(
        date__year=year, date__month=month
    )
    entries_dict = {}
    total_hours_dict = defaultdict(float)

    for work_hour in work_hours:
        entries_dict.setdefault(work_hour.user.id, {})[work_hour.date.day] = work_hour
        total_hours_dict[work_hour.user.id] += work_hour.hours

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
            "months": get_months_list(),
            "years": list(range(today.year - 2, today.year + 3)),
        },
    )
