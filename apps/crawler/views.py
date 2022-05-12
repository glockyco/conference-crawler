import glob
import json
import os

from dateutil import parser
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import HttpResponse, redirect
from django.template import loader

from apps.crawler.crawler import crawl

APP_PATH = os.path.realpath(os.path.dirname(__file__))
DATA_PATH = os.path.join(APP_PATH, 'data')


def index(request: WSGIRequest):
    conferences = []

    for json_path in glob.glob(os.path.join(DATA_PATH, '*.json')):
        with open(os.path.join(json_path)) as json_file:
            data = json.load(json_file)

            data['from_date'] = parser.isoparse(data['from_date'])
            data['to_date'] = parser.isoparse(data['to_date'])

            if 'important_dates' in data:
                for i, date in enumerate(data['important_dates']):
                    data['important_dates'][i]['date'] = parser.isoparse(date['date'])

            conferences.append(data)

    conferences.sort(key=lambda c: c['short_title'])

    context = {'conferences': conferences}

    template = loader.get_template('crawler/index.html')
    return HttpResponse(template.render(context, request))


def add_conference(request: WSGIRequest):
    url = request.GET.get("url")
    crawl([url])
    return redirect("index")


if __name__ == '__main__':
    index(None)
