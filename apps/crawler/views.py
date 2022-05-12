import glob
import json
import os

from dateutil import parser
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import HttpResponse, redirect
from django.template import loader
from ics import Calendar, Event

from apps.crawler.crawler import crawl, Conference

APP_PATH = os.path.realpath(os.path.dirname(__file__))
DATA_PATH = os.path.join(APP_PATH, 'data')


def index(request: WSGIRequest):
    conferences = []

    for json_path in glob.glob(os.path.join(DATA_PATH, '*.json')):
        with open(os.path.join(json_path)) as json_file:
            data = json.load(json_file)

            data['file_name'] = os.path.basename(json_path)

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
    url: str = request.GET.get("url")

    urls = []
    if url is None:
        json_paths = glob.glob(os.path.join(DATA_PATH, "*.json"))
        for json_path in json_paths:
            with open(os.path.join(json_path)) as json_file:
                conference: Conference = json.load(json_file)
                urls.append(conference["url"])
    else:
        urls.append(url)

    crawl(urls)

    return redirect("index")


def ical(request: WSGIRequest):
    file_name: str = request.GET.get("file")

    if file_name is None:
        json_paths = glob.glob(os.path.join(DATA_PATH, "*.json"))
    else:
        json_path = os.path.join(DATA_PATH, file_name)
        if not os.path.exists(json_path):
            return HttpResponse(f"File not found: {file_name}")
        json_paths = [json_path]

    conferences = []
    for json_path in json_paths:
        with open(os.path.join(json_path)) as json_file:
            conference: Conference = json.load(json_file)
            conferences.append(conference)

    calendar = Calendar(creator="conference-crawler")
    for conference in conferences:
        name = f"{conference['short_title']} {conference['year']}"
        calendar.events.add(Event(
            name=name,
            begin=parser.isoparse(conference["from_date"]),
            end=parser.isoparse(conference["to_date"]),
        ))

        for important_date in conference["important_dates"]:
            calendar.events.add(Event(
                name=f"{name} - {important_date['description']}",
                begin=parser.isoparse(important_date["date"]),
            ))

    out_name = "conference-dates.ics" if file_name is None else f"{os.path.splitext(file_name)[0]}.ics"
    response = HttpResponse(
        content_type='text/calendar',
        headers={'Content-Disposition': 'attachment; filename="' + out_name + '"'},
    )

    response.write(str(calendar))

    return response


if __name__ == '__main__':
    index(None)
