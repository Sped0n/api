from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
import requests
import os
import datetime
from api.models import MetricsCache
from api.models import ErrorLogs
from django_apscheduler import util
from django.http import JsonResponse
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_job

apikey = os.getenv("API_KEY")
site_id = os.getenv("SITE_ID")
pls_host = os.getenv("PLS_HOST")
query_string = "visitors,pageviews,bounce_rate,visit_duration"
var_valid = apikey or site_id or pls_host
headers = {"Accept": "application/json", "Authorization": str("Bearer " + str(apikey))}


def log_error(error_type="unknown", content="n/a"):
    # log error
    ErrorLogs.objects.create(
        type=error_type,
        content=content
    )
    # limit the number of logs to 250
    if ErrorLogs.objects.count() > 250:
        ErrorLogs.objects.earliest().delete()


def fetch_latest_data():
    resp = {}
    # incase there is no data available
    if MetricsCache.objects.count() == 0:
        MetricsCache.objects.create()
    # get the latest data from MetricsCache
    latest_data = MetricsCache.objects.latest('created')
    resp["bounce_rate"] = latest_data.bounce_rate
    resp["pageviews"] = latest_data.page_views
    resp["visit_duration"] = latest_data.visit_duration
    resp["visitors"] = latest_data.visitors
    return resp


@api_view(('GET',))
@renderer_classes([JSONRenderer])
def arc_metric_api(request):
    # validate the variables
    if not var_valid:
        return Response("please set variables correctly")
    eager = request.GET.get("eager", "false")
    # initialize the return value
    metrics_json = {}
    # period setting
    period = request.GET.get("period")
    if not period:
        period = "custom&date=2023-01-29," + str(datetime.date.today())
    else:
        eager = "true"
    # eager mode
    if eager == "true":
        # url preprocess
        url = f'https://{pls_host}/api/v1/stats/aggregate/?site_id={site_id}&period={period}&metrics={query_string}'
        # get json
        try:
            r = requests.get(url, headers=headers, timeout=15)
        # fallback
        except Exception as e:
            log_error("eager_requests", str(e))
            metrics_json = fetch_latest_data()
            return Response(metrics_json)
        # simplify json if http response 200
        if r.status_code == 200:
            data = r.json()["results"]
            metrics_json["bounce_rate"] = data["bounce_rate"]["value"]
            metrics_json["pageviews"] = data["pageviews"]["value"]
            metrics_json["visit_duration"] = data["visit_duration"]["value"]
            metrics_json["visitors"] = data["visitors"]["value"]
        # fallback
        else:
            log_error("eager_status_code", r.status_code)
            metrics_json = fetch_latest_data()
        return Response(data)
    # normal mode
    else:
        metrics_json = fetch_latest_data()
    response = JsonResponse(metrics_json)
    return response


scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), 'default')


@register_job(scheduler, "interval", seconds=30, id='json_fetch', replace_existing=True)
@util.close_old_connections
def json_fetch():
    # validate the variables
    if not var_valid:
        return None
    # period setting
    period = "custom&date=2023-01-29," + str(datetime.date.today())
    # url preprocess
    url = f'https://{pls_host}/api/v1/stats/aggregate/?site_id={site_id}&period={period}&metrics={query_string}'
    # get json
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print("fetch complete", datetime.datetime.now())
    # log error and don't touch the data
    except Exception as e:
        log_error("cron_request", str(e))
        return None
    # log data if http response 200
    if r.status_code == 200:
        data = r.json()["results"]
        MetricsCache.objects.create(
            bounce_rate=float(data["bounce_rate"]["value"]),
            page_views=int(data["pageviews"]["value"]),
            visit_duration=float(data["visit_duration"]["value"]),
            visitors=int(data["visitors"]["value"])
        )
        if MetricsCache.objects.count() > 10:
            MetricsCache.objects.earliest('created').delete()
    # log error http error code
    else:
        log_error("cron_status_code", r.status_code)
        return None


scheduler.start()
print("Scheduler started!")
