# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import logging
import json
import psycopg2
import datetime

import scrapy
from scrapy.http import Request, Response

from urltheory.urlfilter import *
from croawl.utils import *

field_mappings = {
        'title': (False,['citation_title','DC.Title']),
        'splash_url': (False,['citation_public_url','citation_abstract_html_url']),
        'pdf_url': (False,['citation_pdf_url','eprints.document_url',]),
        }


positive_classifications = ['pdf','abs','absft']

derived_classifications = {
        'nopdf': (False,None,None),
        'noabs': (False,False,False),
        }


class ClassifierMiddleware(object):
    def __init__(self, *args, **kwargs):
        super(ClassifierMiddleware, self).__init__(*args, **kwargs)
        self.trees = {}
        for cls in positive_classifications:
            self.trees[cls] = URLFilter()
            self.trees[cls].load('models/fltr.train%s.pkl' % cls)

        try:
            from croawl.settings import CLASSIFIER_DATABASE
            self.conn = psycopg2.connect(**CLASSIFIER_DATABASE)
            self.conn.set_session(autocommit=True)
        except Exception as e:
            print e
            raise ValueError("Invalid connection parameters")
            self.conn = None

    def update_url_db(self, url, classification):
        """
        Stores the classification of the given URL in the SQL database,
        so that it can be reused later to train a classifier.
        """
        if not self.conn:
            raise ValueError("Database not connected")
        url = url[:1024]
        if not classification:
            return
        if len(classification) > 32:
            raise ValueError('Invalid classification')

        curtime = datetime.datetime.now()

        cur = self.conn.cursor()
        nb_records = cur.execute("UPDATE urls SET (fetched,classification) = (%s,%s) WHERE url = %s", (curtime,classification,url))
        print nb_records
        if not cur.rowcount:
            print (url,curtime,classification)
            cur.execute("INSERT INTO urls (url,fetched,classification) VALUES (%s,%s,%s)", (url,curtime,classification))

    def process_request(self, request, spider):
        stats = spider.crawler.stats

        if 'looking_for' not in request.meta:
            stats.inc_value('classification/ignored')
            return

        classification = self.classify_url(request.url)
        if not classification:
            stats.inc_value('classification/missed')
            return

        stats.inc_value('classification/matched/'+classification)

        flags = ['classified_'+classification]
        if (classification in ['pdf','absft', 'noabs'] or
            (classification == 'nopdf' and request.meta['looking_for'] == 'pdf')):
            stats.inc_value('classification/filtered/'+classification)
            return Response(request.url, flags=flags)

    def process_response(self, request, response, spider):
        if 'looking_for' not in request.meta:
            return response

        for flag in response.flags:
            if flag.startswith('classified_'):
                return response

        classification, metadata = self.classify_document(response)
        self.update_url_db(request.url, classification)
        response.flags.append('classified_'+classification)
        if metadata:
            response = response.replace(body=json.dumps(metadata))
        return response

    def classify_url(self, url):
        """
        Predicts what this URL points to.
        """
        success = {cls: t.predict_success(url) for (cls,t) in self.trees.items()}
        logging.info("filtering "+url+": abs=%s, pdf=%s, absft=%s" % (str(success['abs']),str(success['pdf']),str(success['absft'])))

        if success['pdf']:
            return 'pdf'
        elif success['absft']:
            return 'absft'
        elif success['abs']:
            return 'abs'
        elif success['abs'] == False:
            return 'noabs'
        elif success['pdf'] == False:
            return 'nopdf'
        return None

    def classify_document(self, response):
        """
        Classifies a document based on its content

        :returns: a pair: a string indicating the class of the response
                    and a dict containing the extracted metadata
        """ 
        if (not isinstance(response, scrapy.http.HtmlResponse)
                and check_pdf(response.body)):
            return 'pdf', {}

        if not isinstance(response, scrapy.http.HtmlResponse):
            return 'noabs', {}

        fields = {'splash_url':response.url}
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

        if found:
            return 'abs', fields
        return 'noabs', {}



