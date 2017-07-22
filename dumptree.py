import codecs

from accesspredict.pdfpredictor import *
from accesspredict.zoteropredictor import *
from accesspredict.scraperpredictor import *
from accesspredict.forest import URLForest
from accesspredict.spider import *
from accesspredict.urldataset import URLDataset

from gevent.pool import Pool
import redis
import sys


client = redis.StrictRedis(host='localhost', port=6379, db=5)

uf = URLForest()
uf.add_tree('pdf')
#uf.add_tree('zotero')
uf.add_tree('custom')
#uf.add_tree('diff')

ud = URLDataset(client)
ud.save('dataset.tsv')

ud.feed_to_forest(uf)

uf.print_as_tree(sys.argv[1])

