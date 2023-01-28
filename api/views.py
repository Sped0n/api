from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
import requests
import json


@api_view(('GET',))
@renderer_classes([JSONRenderer])
def get_pageviews(request):
    apikey = "BRTHdPvMz-6JRsEy48Rx6xufHfCpYyzENk5LXin0TecJP1TOGIHqLKtc9RNmzs8V";
    url = "https://pls.sped0nwen.com/api/v1/stats/aggregate/?site_id=arc.sped0nwen.com&metrics=pageviews"
    headers = {"Accept": "application/json", "Authorization": str("Bearer " + str(apikey))}
    r = requests.get(url, headers=headers)
    data = r.json()
    counts = data["results"]["pageviews"]["value"]
    return Response(counts)
