from django.db import models


# Create your models here.
class MetricsCache(models.Model):
    bounce_rate = models.FloatField(default=0.0)
    page_views = models.IntegerField(default=1)
    visit_duration = models.FloatField(default=0.0)
    visitors = models.IntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'metrics_all_time'


class ErrorLogs(models.Model):
    type = models.TextField(default="unknown")
    content = models.TextField(default="n/a")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'error_logs'
