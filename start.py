import codecs

from accesspredict.pdfpredictor import *
from accesspredict.zoteropredictor import *
from accesspredict.scraperpredictor import *
from accesspredict.forest import URLForest
from accesspredict.spider import *
from accesspredict.urldataset import URLDataset
from accesspredict.combinedpredictor import P
from accesspredict.statistics import CrawlingStatistics

from gevent.pool import Pool
from config import redis_client
import gevent
import redis


#redis_client.flushall()

uf = URLForest()
uf.add_tree('pdf')
uf.add_tree('custom')
#uf.add_tree('zotero')
#uf.add_tree('diff')

ud = URLDataset(redis_client)
# this loads up all the cached URLs we have in redis
ud.feed_to_forest(uf)

stats = CrawlingStatistics()

dumpname = 'crossref.train'
#dumpname = 'pdftest'

spider = Spider(forest=uf, dataset=ud, stats=stats)
spider.add_predictor('pdf', PDFPredictor())
spider.add_predictor('custom', ScraperFullTextPredictor())
#spider.add_predictor('zotero', ZoteroFullTextPredictor())
#spider.add_predictor('diff', P('custom') != (P('zotero') | P('pdf')))

def update_stats(for_greenlet):
    while not for_greenlet.ready():
        gevent.sleep(120)
        stats.log_all()
        stats.write('www/stats_%s.html' % dumpname)

pool = Pool(1)

def urls():
    with codecs.open('data/%s/urls.txt' % dumpname, 'r', 'utf-8') as f:
        for l in f:
            fields = l.strip().split('\t')
            u = fields[0]
            yield u

def crawler():
    for result in pool.imap_unordered(lambda u: spider.predict('custom',u), urls()):
        print "-- final result: %s" % unicode(result)

crawler_greenlet = gevent.Greenlet(crawler)
crawler_greenlet.start()

update_stats(crawler_greenlet)

ud.save('data/%s/dataset.tsv'% dumpname)
uf.save('data/%s/forest.pkl'% dumpname)

