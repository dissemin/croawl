# -*- encoding: utf-8 -*-
import scrapy
import logging
import json

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
    date = scrapy.Field()
    year = scrapy.Field()
    pmid = scrapy.Field()
    firstpage = scrapy.Field()
    lastpage = scrapy.Field()
    doi = scrapy.Field()
    jtitle = scrapy.Field()
    volume = scrapy.Field()
    issue = scrapy.Field()
    conftitle = scrapy.Field()
    booktitle = scrapy.Field()
    authors = scrapy.Field()
    emails = scrapy.Field()
    issn = scrapy.Field()
    absft_url = scrapy.Field()
    base_oa = scrapy.Field()
    from_abs = scrapy.Field()

field_mappings = {
        'title': (False,['citation_title','eprints.title','DC.Title']),
        'splash_url': (False,['citation_public_url','citation_abstract_html_url']),
        'pdf_url': (False,['citation_pdf_url','eprints.document_url']),
        'date': (False,['citation_date','citation_publication_date','eprints.date']),
        'year': (False,['citation_year']),
        'pmid': (False,['citation_pmid']),
        'firstpage': (False,['citation_firstpage']),
        'lastpage': (False,['citation_lastpage']),
        'doi': (False,['citation_doi','eprints.id_number']),
        'jtitle': (False,['citation_journal_title']),
        'volume': (False,['citation_volume']),
        'issue': (False,['citation_issue']),
        'conftitle': (False,['citation_conference_title','citation_conference']),
        'booktitle': (False,['citation_book_title']),
        'authors': (True,['citation_author','eprints.creator_name','DC.creator']),
        'emails': (True,['eprints.creators_id']),
        'issn': (False,['eprints.issn']),
        }

class BaseSpider(scrapy.Spider):
    name = "base"

    def start_requests(self):
        fname = 'doi_list.txt' #'base_urls.uniq'
        with codecs.open(fname, 'r', 'utf-8') as f:
            for line in f:
                fields = line.strip().split('\t')
                if len(fields) != 2 or fields[1] != '2':
                    continue
                metadata = {'base_oa':fields[1],
                        'splash_url':fields[0]}
                yield self.filter_url(fields[0], metadata, looking_for='any')

    def filter_url(self, url, metadata, looking_for=None):
        try:
            req = Request(url, self.parse, meta={
                'metadata':metadata,
                'looking_for':looking_for}, priority=10)
            return req
        except ValueError:
            print "ValueError for url "+url
            pass


    def parse(self, response):
        logging.info("processing "+response.url)

        # Check if the response was classified
        classification = None
        flags = response.flags
        for flag in flags:
            if flag.startswith('classified_'):
                classification = flag[len('classified_'):]

        if not classification:
            return

        # Otherwise, classify it by looking at the response
        base_metadata = response.meta.get('metadata',{})
        if classification == 'pdf':
            # If it's a PDF, just return an item saying that the full
            # text is available
            base_metadata['pdf_url'] = response.url
            yield OAIMetadata(**base_metadata)
        elif classification == 'absft':
            # That's an abstract page where we think the full text is available
            base_metadata['absft_url'] = response.url
            yield OAIMetadata(**base_metadata)
        elif classification == 'abs':
            # Update the original metadata with the new one, extracted from the page
            dc_metadata = json.loads(response.body)
            base_metadata.update(dc_metadata)
            # We're not sure this abstract page links to a full text or not
            if 'pdf_url' in dc_metadata:
                new_metadata = base_metadata.copy()
                new_metadata['from_abs'] = response.url
                req = self.filter_url(dc_metadata['pdf_url'], new_metadata,
                        looking_for='pdf')
                if req:
                    yield req
            else:
                yield OAIMetadata(**base_metadata)

