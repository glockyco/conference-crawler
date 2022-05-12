import json
import os
from datetime import datetime, date
from multiprocessing import Process
from typing import TypedDict, List, Dict

import dateutil
import scrapy
from dateutil.parser import parse
from markdownify import markdownify
from scrapy.crawler import CrawlerRunner
from scrapy.exporters import BaseItemExporter
from scrapy.http import HtmlResponse
from twisted.internet import reactor


APP_PATH = os.path.realpath(os.path.dirname(__file__))
DATA_PATH = os.path.join(APP_PATH, 'data')


class Conference(TypedDict):
    long_title: str
    short_title: str
    location: str
    from_date: str
    to_date: str
    year: int
    url: str
    call_for_papers: str
    important_dates: List[Dict[str, str]]


class ConferenceExporter(BaseItemExporter):
    def __init__(self, file, **kwargs):
        # @TODO: Prevent file from being created.

        super().__init__(dont_fail=True, **kwargs)

    def export_item(self, item: Conference):
        out_file_name = item["short_title"].replace("/", "-").lower() + "-" + str(item["year"]) + ".json"
        out_file_path = os.path.join(DATA_PATH, out_file_name)

        print(f"Writing {out_file_name} ...")

        with open(out_file_path, "w") as out_file:
            def json_serial(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError("Type %s not serializable" % type(obj))

            json.dump(item, out_file, indent=4, default=json_serial)


class ConferenceSpider(scrapy.Spider):
    name = "conference"

    def __init__(self, name=None, **kwargs):
        super(ConferenceSpider, self).__init__(name, **kwargs)
        self.start_urls = kwargs.get("start_urls", [])

    def parse(self, response: HtmlResponse, **kwargs):
        conference = {}

        # long-title
        # @TODO: long-title.
        conference["long_title"] = None

        # short-title / year
        short_title_text: str = response.css(".footer h3 a").xpath("text()").get().strip()

        conference["short_title"] = short_title_text.split(" ")[0]
        conference["year"] = int(short_title_text.split(" ")[1])

        # location
        conference["location"] = response.css(".place a").xpath("text()").get()

        # from / to / year
        from_to_str: str = response.css(".place").xpath("text()").get()
        from_str = from_to_str.split("-")[0]
        to_str = from_to_str.split("-")[1]

        conference["to_date"] = dateutil.parser.parse(to_str)
        conference["from_date"] = dateutil.parser.parse(from_str, default=conference["to_date"])

        # abstract-due / submission-due
        important_dates = []
        for data in response.css(".important-dates-in-sidebar tr"):
            date_str: str = data.xpath("td/text()[1]").get()
            if date_str is None:
                date_str: str = data.xpath("td/strong/text()")[0].get()
            dates = date_str.split("-")  # Sometimes, date ranges are given.

            date = None
            try:
                date = dateutil.parser.parse(dates[-1])
            except:
                print(f"Error parsing date {date_str}")

            description: str = data.xpath("td/text()[2]").get()
            if description is None:
                description = data.xpath("td/strong/text()")[1].get()

            important_dates.append({"date": date, "description": description})

        important_dates.sort(key=lambda d: d["date"])
        conference["important_dates"] = important_dates

        # url
        conference["url"] = response.css(".footer h3 a").xpath("@href").get()

        # call-for-papers
        cfp_html = response.css("#Call-for-Papers").get()
        if cfp_html is None:
            cfp_html = response.css(".tab-pane").xpath("//*[h2[text()[contains(., 'Call for Papers')]]]").get()
        conference["call_for_papers"] = None if cfp_html is None else markdownify(cfp_html, heading_style="ATX")

        yield conference


# poetry run apps/manage.py runserver
# poetry run scrapy runspider apps/crawler/crawler.py -o conferences.json


class CrawlerRunnerProcess(Process):
    def __init__(self, spider, urls: List[str]):
        self.start_urls = urls

        settings = {
            "FEEDS": {
                "conferences.json": {"format": "conferences"}
            },
            "FEED_EXPORTERS": {
                "conferences": "apps.crawler.crawler.ConferenceExporter"
            },
        }

        Process.__init__(self)
        self.runner = CrawlerRunner(settings)
        self.spider = spider

    def run(self):
        deferred = self.runner.crawl(self.spider, start_urls=self.start_urls)
        deferred.addBoth(lambda _: reactor.stop())
        reactor.run(installSignalHandlers=False)


def crawl(urls: List[str]):
    CrawlerRunnerProcess(ConferenceSpider, urls)

    crawler = CrawlerRunnerProcess(ConferenceSpider, urls=urls)
    crawler.start()
    crawler.join()


if __name__ == "__main__":
    # ASE: Long Title
    # ESEC/FSE: Long Title
    # ICPC: Long Title, Location
    # ICSE: Long Title, Location
    # ICST: Long Title, Location
    # ISSTA: Long Title
    # MSR: Long Title, Location
    # PLDI: Long Title
    # POPL: Long Title, Location

    start_urls = [
        # ASE:
        "https://conf.researchr.org/track/ase-2022/ase-2022-research-papers",
        # ESEC/FSE:
        "https://2022.esec-fse.org/track/fse-2022-research-papers",
        # ICPC:
        "https://conf.researchr.org/track/icpc-2022/icpc-2022-research?",
        # ICSE:
        "https://conf.researchr.org/track/icse-2022/icse-2022-papers?",
        # ICST:
        "https://icst2022.vrain.upv.es/track/icst-2022-papers?",
        # ISSTA:
        "https://conf.researchr.org/track/issta-2022/issta-2022-technical-papers",
        # MSR:
        "https://conf.researchr.org/track/msr-2022/msr-2022-technical-papers?",
        # PLDI:
        "https://pldi22.sigplan.org/track/pldi-2022-pldi",
        # POPL:
        "https://conf.researchr.org/track/POPL-2023/POPL-2023-popl-research-papers",

        # APR (custom layout):
        #"https://program-repair.org/workshop-2022/",
        # BotSE (custom layout):
        #"http://botse.org/",
        # ICSME (custom layout):
        #"https://cyprusconferences.org/icsme2022/call-for-research-track/",
        # TACAS (custom layout):
        #"https://etaps.org/2022/tacas",
    ]

    crawl(start_urls)
