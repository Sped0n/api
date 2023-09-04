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

from api.ctyper import GetError, VarNotValid
from api.models import ErrorLogs, MetricsCache


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


class Poster:
    def __init__(self, start_timestamp_in_ms: int = 1693699200000) -> None:
        self.__api_key: str = os.getenv("API_KEY", "")
        self.__site_id: str = os.getenv("SITE_ID", "")
        self.__umami_host: str = os.getenv("UMAMI_HOST", "")
        # validate the variables we get
        self.var_valid: bool = (
            self.__api_key != "" and self.__site_id != "" and self.__umami_host != ""
        )
        self.__headers: dict[str, str] = {
            "Accept": "application/json",
            "Authorization": str("Bearer " + str(self.__api_key)),
        }
        # start timestamp (2023/09/03)
        self.__start_timestamp: str = str(start_timestamp_in_ms)

    def __url_gen(self) -> str:
        end_timestamp: str = str(int(datetime.datetime.now().timestamp()) * 1000)
        return f"https://{self.__umami_host}/api/websites/{self.__site_id}/stats?startAt={self.__start_timestamp}&endAt={end_timestamp}"

    def get(self, timeout: int = 5, error_print_header: str = "") -> dict:
        if not self.var_valid:
            raise VarNotValid("please set variables correctly")
        metrics_json: dict = {}
        # get json
        try:
            # request get
            r: requests.models.Response = requests.get(
                self.__url_gen(), headers=self.__headers, timeout=timeout
            )
            # status check
            assert r.status_code == 200
            # print
            print("fetch complete", datetime.datetime.now(), flush=True)
        except Exception as e:
            # error log
            if e.__class__ == Timeout:
                log_error(f"{error_print_header}_request_timeout", str(e))
            elif e.__class__ == AssertionError:
                log_error(f"{error_print_header}eager_status_code", str(e))
            else:
                log_error(f"{error_print_header}_unknown({str(e.__class__)})", str(e))
            # raise error
            raise GetError(f"{error_print_header}_get_error")
        # simplify json
        data: dict = r.json()
        metrics_json["pageviews"] = (
            data["pageviews"]["value"] + 233  # migrate from old data
        )
        return metrics_json


# create a poster
p = Poster()


@api_view(("GET",))
@renderer_classes([JSONRenderer])
def arc_metric_api(request) -> JsonResponse:
    # validate the variables
    if not p.var_valid:
        return JsonResponse("please set variables correctly")
    eager = request.GET.get("eager", "false")
    tmp: dict = {}
    # eager mode
    if eager == "true":
        try:
            tmp = p.get(timeout=15, error_print_header="eager")
        except GetError:
            tmp = fetch_arc_latest_data()
    # normal mode
    else:
        tmp = fetch_arc_latest_data()
    return JsonResponse(tmp)


scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")


@register_job(scheduler, "interval", seconds=60, id="json_fetch", replace_existing=True)
@util.close_old_connections
def json_fetch():
    # validate the env variables
    if not p.var_valid:
        return None
    # get json
    try:
        data = p.get(timeout=15, error_print_header="cron")
    except GetError:
        return None
    # save to db
    MetricsCache.objects.create(  # type: ignore
        page_views=int(data["pageviews"]),
    )
    if MetricsCache.objects.count() > 10:  # type: ignore
        MetricsCache.objects.earliest("created").delete()  # type: ignore


scheduler.start()
print("Scheduler started!")
