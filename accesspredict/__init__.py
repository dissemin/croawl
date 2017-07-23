# -*- encoding: utf-8 -*-
from gevent import monkey
monkey.patch_all(thread=False, select=False)

