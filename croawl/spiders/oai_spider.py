# -*- encoding: utf-8 -*-
import scrapy

from collections import defaultdict

from urltheory.preftree import *
from urltheory.tokenizer import *

field_mappings = {
        'title':['citation_title','DC.Title'],
        'splash_url':['citation_public_url','citation_abstract_html_url'],
        'pdf_url':['citation_pdf_url'],
        }


class OaiSpider(scrapy.Spider):
    name = "oai"
    allowed_domains = ["biorxiv.org","eprint.iacr.org"]
    start_urls = [
           'http://biorxiv.org',
           'http://biorxiv.org/content/early/2016/01/22/037713',
           # 'http://www.ssrn.com',
        # 'http://eprint.iacr.org',
            ]

    def __init__(self, *args, **kwargs):
        super(OaiSpider, self).__init__(*args, **kwargs)
        self.pdf_tree = PrefTree()
        self.abs_tree = PrefTree()

    def parse(self, response):
        if not isinstance(response, scrapy.http.HtmlResponse):
            return
        # TODO if we landed on a PDF, register it

        # Parse oai fields
        fields = {}
        found = False
        for key, names in field_mappings.items():
            values = []
            for name in names:
                values += response.xpath(
                        '//meta[@name="%s"]/@content' % name).extract()
            if values:
                found = True
                fields[key] = values

        if found:
            print "METADATA FOUND"
            # update the abs tree
            self.abs_tree.add_url(prepare_url(response.url), success=True)
            self.abs_tree, pruned = self.abs_tree.prune(reverse=True,min_urls=20)
            self.abs_tree.print_as_tree()

            download_required = False
            pdf_url = None
            if fields['pdf_url']:
                pdf_url = fields['pdf_url'][0]

            if pdf_url:
                # check the PDF url
                success = self.pdf_tree.predict_success(prepare_url(pdf_url))
                download_required = (success is None)
                if not download_required and not success:
                    del fields['pdf_url']
                
            if not download_required:
                print "NO DOWNLOAD REQUIRED"
                yield fields
            else:
                print "STARTING DOWNLOAD"
                req = scrapy.Request(pdf_url, self.parse_pdf, priority=20)
                fields['pdf_url'] = [pdf_url] 
                req.meta['metadata'] = fields
                yield req

        # Parse other urls
        for url in response.xpath('//a/@href').extract():
            url = response.urljoin(url)
            tokenized = prepare_url(url)
            priority = 0

            # skip links to PDF files when they're not in a meta tag
            if (self.pdf_tree.predict_success(tokenized) == True):
                continue
            if self.abs_tree.predict_success(tokenized) == True:
                priority = 10

            #yield scrapy.Request(url, self.parse, priority=priority)

    def parse_pdf(self, response):
        # check the first bytes
        print "GOT A PDF BACK"
        valid = True
        if isinstance(response, scrapy.http.HtmlResponse):
            valid = False

        self.pdf_tree.add_url(prepare_url(response.url), success=valid)
        self.pdf_tree, success = self.pdf_tree.prune(reverse=True,min_urls=20)
        self.pdf_tree.print_as_tree()

        metadata = response.meta['metadata']
        if not valid:
            print "SORRY, INVALID"
            del metadata['pdf_url']
        else:
            print "YAY, VALID"
        return metadata
            



