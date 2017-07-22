import codecs

from accesspredict.pdfpredictor import *
from accesspredict.zoteropredictor import *
from accesspredict.scraperpredictor import *
from accesspredict.forest import URLForest
from accesspredict.spider import *
from accesspredict.urldataset import URLDataset

from gevent.pool import Pool
from config import redis_client
import sys


uf = URLForest()
uf.add_tree('pdf')
#uf.add_tree('zotero')
uf.add_tree('custom')
#uf.add_tree('diff')

ud = URLDataset(redis_client)

ud.feed_to_forest(uf)

uf.print_as_tree(sys.argv[1])

