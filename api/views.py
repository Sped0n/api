# Create your views here.
import datetime
import os

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from django.http import JsonResponse
from django_apscheduler import util
from django_apscheduler.jobstores import DjangoJobStore, register_job
from requests import Timeout
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from api.models import ErrorLogs, MetricsCache

apikey: str | None = os.getenv("API_KEY")
site_id: str | None = os.getenv("SITE_ID")
umami_host: str | None = os.getenv("UMAMI_HOST")
var_valid: bool = bool(apikey or site_id or umami_host)
headers: dict[str, str] = {
    "Accept": "application/json",
    "Authorization": str("Bearer " + str(apikey)),
}


def log_error(error_type="unknown", content="n/a") -> None:
    print(f"error: {error_type} {content}", flush=True)
    # log error
    ErrorLogs.objects.create(type=error_type, content=content)  # type: ignore
    # limit the number of logs to 250
    if ErrorLogs.objects.count() > 250:  # type: ignore
        ErrorLogs.objects.earliest().delete()  # type: ignore


def fetch_arc_latest_data() -> dict:
    resp = {}
    # incase there is no data available
    if MetricsCache.objects.count() == 0:  # type: ignore
        MetricsCache.objects.create()  # type: ignore
    # get the latest data from MetricsCache
    latest_data = MetricsCache.objects.latest("created")  # type: ignore
    resp["pageviews"] = latest_data.page_views
    return resp


@api_view(("GET",))
@renderer_classes([JSONRenderer])
def arc_metric_api(request):
    # validate the variables
    if not var_valid:
        return Response("please set variables correctly")
    eager = request.GET.get("eager", "false")
    # initialize the return value
    metrics_json = {}
    # start timestamp (2023/09/03)
    start_timestamp: str = "1693699200000"
    # end timestamp (now)
    end_timestamp: str = str(int(datetime.datetime.now().timestamp()) * 1000)
    # eager mode
    if eager == "true":
        # url preprocess
        url = f"https://{umami_host}/api/websites/{site_id}/stats?startAt={start_timestamp}&endAt={end_timestamp}"
        # get json
        try:
            r = requests.get(url, headers=headers, timeout=5)
            assert r.status_code == 200
        # fallback
        except Exception as e:
            if e.__class__ == Timeout:
                log_error("eager_request_timeout", str(e))
            elif e.__class__ == AssertionError:
                log_error("eager_status_code", str(e))
            else:
                log_error(f"eager_unknown({str(e.__class__)})", str(e))
            metrics_json = fetch_arc_latest_data()
            return Response(metrics_json)
        # simplify json if http response 200
        data: dict = r.json()
        metrics_json["pageviews"] = (
            data["pageviews"]["value"] + 233
        )  # migrate from old data
        # fallback
        return Response(metrics_json)
    # normal mode
    else:
        metrics_json = fetch_arc_latest_data()
    response = JsonResponse(metrics_json)
    return response


scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


@register_job(scheduler, "interval", seconds=10, id="json_fetch", replace_existing=True)
@util.close_old_connections
def json_fetch():
    # validate the variables
    if not var_valid:
        return None
    # start timestamp (2023/09/03)
    start_timestamp: str = "1693699200000"
    # end timestamp (now)
    end_timestamp: str = str(int(datetime.datetime.now().timestamp()) * 1000)
    # url preprocess
    url = f"https://{umami_host}/api/websites/{site_id}/stats?startAt={start_timestamp}&endAt={end_timestamp}"
    # get json
    try:
        r = requests.get(url, headers=headers, timeout=15)
        assert r.status_code == 200
        print("fetch complete", datetime.datetime.now(), flush=True)
    # log error and don't touch the data
    except Exception as e:
        if e.__class__ == Timeout:
            log_error("cron_request_timeout", str(e))
        elif e.__class__ == AssertionError:
            log_error("cron_status_code", str(e))
        else:
            log_error(f"cron_unknown({str(e.__class__)})", str(e))
        return None
    data = r.json()
    MetricsCache.objects.create(  # type: ignore
        page_views=int(data["pageviews"]["value"]) + 233,  # migrate from old data
    )
    if MetricsCache.objects.count() > 10:  # type: ignore
        MetricsCache.objects.earliest("created").delete()  # type: ignore


scheduler.start()
print("Scheduler started!")
