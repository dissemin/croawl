# -*- encoding: utf-8 -*-
import scrapy

from collections import defaultdict

field_mappings = {
        'title':['citation_title','DC.Title'],
        'splash_url':['citation_public_url','citation_abstract_html_url']
        }


class OaiSpider(scrapy.Spider):
    name = "oai"
    allowed_domains = ["biorxiv.org","eprint.iacr.org"]
    start_urls = [
           # 'http://biorxiv.org',
           # 'http://www.ssrn.com',
            'http://eprint.iacr.org',
            ]

    def parse(self, response):
        if not isinstance(response, scrapy.http.HtmlResponse):
            return

        # Parse oai fields
        fields = {}
        found = False
        for key, names in field_mappings.items():
            values = []
            for name in names:
                values += response.xpath('//meta[@name="%s"]/@content' % name).extract()
            
            if values:
                found = True
                fields[key] = values

        if found:
            yield fields

        # Parse other urls
        for url in response.xpath('//a/@href').extract():
            url = response.urljoin(url)
            yield scrapy.Request(url, self.parse)

