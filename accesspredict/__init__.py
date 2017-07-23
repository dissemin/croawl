# -*- encoding: utf-8 -*-
from gevent import monkey
monkey.patch_all(thread=False, select=False)

# for some reason everything breaks down if I do not
# import requests here… (the test coverage gets messed up).
# This is probably due to the interaction between gevent's
# monkey-patching and coverage's black magic)
import requests

# this is just to trick pyflakes into believing that
# we are actually doing something with the requests module.
requests_version = requests.__version__
requests_version += 'hey you'
