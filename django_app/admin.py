from django.contrib import admin

from .models import Machine, WorkHour, WorkTag

admin.site.register(WorkHour)
admin.site.register(WorkTag)
admin.site.register(Machine)
