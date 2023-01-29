from django.contrib import admin

# Register your models here.
from api.models import MetricsCache
from api.models import ErrorLogs

admin.site.register(MetricsCache)
admin.site.register(ErrorLogs)
