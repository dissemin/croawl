# -*- encoding: utf-8 -*-
import scrapy
import logging

from collections import defaultdict
from scrapy.http import Request, Response

from urltheory.preftree import *
from urltheory.tokenizer import *
from urltheory.urlfilter import *

from time import sleep

from croawl.utils import *
import codecs

class OAIMetadata(scrapy.Item):
    title = scrapy.Field()
    splash_url = scrapy.Field()
    pdf_url = scrapy.Field()
    base_oa = scrapy.Field()

field_mappings = {
        'title': (False,['citation_title','DC.Title']),
        'splash_url': (False,['citation_public_url','citation_abstract_html_url']),
        'pdf_url': (False,['citation_pdf_url']),
        }

class BaseSpider(scrapy.Spider):
    name = "base"

    def start_requests(self):
        fname = 'base_urls.uniq' # 'base_urls.uniq'
        with codecs.open(fname, 'r', 'utf-8') as f:
            for line in f:
                fields = line.strip().split('\t')
                if len(fields) == 1:
                    fields.append('2')
                if len(fields) != 2:
                    continue
                metadata = {'base_oa':fields[1],
                        'splash_url':fields[0]}
                req_or_item = self.filter_url(fields[0], metadata)
                if isinstance(req_or_item, scrapy.Request):
                    yield req_or_item
                else:
                    logging.info('SKIPPED seed url: '+str(fields[0]))

    def filter_url(self, url, metadata):
        """
        Returns a request or an item, depending on whether we trust
        the url based on the prefix trees
        """
        pdf_success = self.pdf_tree.predict_success(url)
        abs_success = self.abs_tree.predict_success(url)
        logging.info(("filtering "+url+": abs=%s, pdf=%s" % (str(abs_success),str(pdf_success))))
        if pdf_success == True or abs_success == True:
            metadata['pdf_url'] = url
            return OAIMetadata(**metadata)
        if pdf_success == False or abs_success == True:
            metadata['pdf_url'] = None
            return OAIMetadata(**metadata)
        
        try:
            req = Request(url, self.parse, meta={'metadata':metadata}, priority=10)
            return req
        except ValueError:
            metadata['pdf_url'] = None
            return OAIMetadata(**metadata)
        

    def __init__(self, *args, **kwargs):
        super(BaseSpider, self).__init__(*args, **kwargs)
        self.pdf_tree = URLCorpus() #URLFilter(prune_delay=50,min_children=2,min_urls_prune=25,min_rate=1)
        self.abs_tree = URLCorpus() #URLFilter(prune_delay=50,min_children=2,min_urls_prune=25,min_rate=1)

        self.pdf_tree.write_to_file('pdf.urls', True)
        self.abs_tree.write_to_file('abs.urls', True)

    def parse(self, response):
        logging.info("processing "+response.url)
        is_pdf = False
        if not isinstance(response, scrapy.http.HtmlResponse):
            is_pdf = check_pdf(response.body)

        self.pdf_tree.add_url(response.url, success=is_pdf)

        if is_pdf:
            logging.info("found pdf")
            # If it's a PDF, just return an item saying that the full
            # text is available
            metadata = response.meta['metadata']
            metadata['pdf_url'] = response.url
            yield OAIMetadata(**metadata)

            self.abs_tree.add_url(response.url, success=False)
            return

        if not isinstance(response, scrapy.http.HtmlResponse):
            return

        # Otherwise, try to scrape the page to find metadata

        # Parse oai fields
        fields = {}
        found = False
        for key, (is_list,names) in field_mappings.items():
            values = []
            for name in names:
                values += response.xpath(
                        '//meta[@name="%s"]/@content' % name).extract()
            if values:
                found = True
                if is_list:
                    fields[key] = values
                else:
                    fields[key] = values[0]

        # update the abs tree
        self.abs_tree.add_url(response.url, success=found)

        if found:
            logging.info("found metadata")
            pdf_url = None
            if fields.get('pdf_url'):
                pdf_url = fields['pdf_url']

            if pdf_url:
                # check the PDF url
                yield self.filter_url(pdf_url, metadata=fields)
            else:
                yield OAIMetadata(**fields)
                




