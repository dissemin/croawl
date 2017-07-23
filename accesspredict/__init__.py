# -*- encoding: utf-8 -*-
import requests
from gevent import monkey
monkey.patch_all(thread=False, select=False)

