# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import logging
import timeit
import json
import psycopg2
import datetime
from collections import defaultdict

import scrapy
from scrapy.http import Request, Response

from urltheory.urlfilter import *
from croawl.utils import *
from croawl.spiders.base_spider import field_mappings

positive_classifications = ['pdf','abs','absft','robots']

derived_classifications = {
        'nopdf': (False,None,None,None),
        'noabs': (False,False,False,None),
        }


class ClassifierMiddleware(object):
    def __init__(self, *args, **kwargs):
        super(ClassifierMiddleware, self).__init__(*args, **kwargs)
        try:
            from croawl.settings import CLASSIFIER_DATABASE
            self.conn = psycopg2.connect(**CLASSIFIER_DATABASE)
            self.conn.set_session(autocommit=True)
        except Exception as e:
            print e
            raise ValueError("Invalid connection parameters")
            self.conn = None

        from_db = True
        if from_db and self.conn:
            self.retrain_classifiers()
        else:
            self.trees = {}
            for cls in positive_classifications:
                self.trees[cls] = URLFilter()
                self.trees[cls].load('models/filter-%s-from-db.pkl' % cls)



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
        cur.execute("UPDATE urls SET (fetched,classification) = (%s,%s) WHERE url = %s", (curtime,classification,url))
        if not cur.rowcount:
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
        if (classification in ['pdf','absft', 'noabs','robots'] or
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
        url_history = [request.url]+request.meta.get('redirect_urls',[])
        for url in url_history:
            self.update_url_db(url, classification)
        response.flags.append('classified_'+classification)
        if metadata:
            response = response.replace(body=json.dumps(metadata))
        print "Returning response"
        return response

    def process_exception(self, request, exception, spider):
        if 'looking_for' not in request.meta:
            return

        if isinstance(exception, scrapy.exceptions.IgnoreRequest):
            classification = 'robots'
            url_history = [request.url]+request.meta.get('redirect_urls',[])
            for url in url_history:
                self.update_url_db(url, classification)


    def classify_url(self, url):
        """
        Predicts what this URL points to.
        """
        t1 = timeit.timeit()
        success = {cls: t.predict_success(url) for (cls,t) in self.trees.items()}
        t2 = timeit.timeit()
        logging.info("filtering "+url+": abs=%s, pdf=%s, absft=%s in %s" % (str(success['abs']),str(success['pdf']),str(success['absft']),str(t2-t1)))
        return self.successes_to_class(success)

    def successes_to_class(self, successes):
        """
        Computes the string-based representation of the class based
        on the output of the classifiers
        """
        if successes['robots']:
            return 'robots'
        if successes['pdf']:
            return 'pdf'
        elif successes['absft']:
            return 'absft'
        elif successes['abs']:
            return 'abs'
        elif successes['abs'] == False:
            return 'noabs'
        elif successes['pdf'] == False:
            return 'nopdf'
        return None

    def class_to_successes(self, cls):
        """
        Computes the target value of the individual classifiers based
        on the observed class
        """
        successes = {}
        for clas in positive_classifications:
            successes[clas] = False

        if cls == 'absft':
            successes['abs'] = True
            successes['absft'] = True
        elif cls == 'abs':
            successes['abs'] = True
            successes['absft'] = None
        elif cls == 'pdf':
            successes['pdf'] = True
        elif cls == 'robots':
            for clas in positive_classifications:
                successes[clas] = None
            successes['robots'] = True

        return successes

    def retrain_classifiers(self):
        """
        Retrains fresh classifiers from the URL database
        """
        print "Retraining classifier, this can take a while..."
        # init trees
        self.trees = {}
        for cls in positive_classifications:
            self.trees[cls] = URLFilter(prune_delay=0,min_rate=0.99,
                    threshold=0.95,min_urls_prediction=20,min_urls_prune=40)

        # add urls
        self.conn.set_isolation_level(1)
        cnt = 0
        stats = defaultdict(int)
        with self.conn as conn:
            with conn.cursor(name='dumper') as cur:
                cur.execute('SELECT url, classification FROM urls;')
                for row in cur:
                    url, classification = row
                    cnt += 1
                    stats[classification] += 1
                    successes = self.class_to_successes(classification)
                    for key, val in successes.items():
                        if val is not None:
                            self.trees[key].add_url(url, val, keep_pruned=False)

        self.conn.set_isolation_level(0)

        # prune trees and save them
        for cls in positive_classifications:
            self.trees[cls].force_prune()
            self.trees[cls].save('models/filter-%s-from-db.pkl' % cls)

        print ("%d urls in the train set" % cnt)
        print stats

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



