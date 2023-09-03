from django.db import models


# Create your models here.
class MetricsCache(models.Model):
    page_views = models.IntegerField(default=1)  # type: ignore
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "metrics_all_time"


class ErrorLogs(models.Model):
    type = models.TextField(default="unknown")
    content = models.TextField(default="n/a")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_logs"
