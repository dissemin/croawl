# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from collections import defaultdict
from datetime import datetime
import json

def readfile(fname):
    with open(fname, 'r') as f:
        return f.read()

stats_html_header = readfile('html/stats/header.html')
stats_html_footer = readfile('html/stats/footer.html')

class CrawlingStatistics(object):
    """
    An object holding statistics about the current crawl
    """

    def __init__(self):
        self.keys = []
        self.lines = defaultdict(list)
        self.accu = defaultdict(int)
        self.start = datetime.utcnow()

    def add_key(self, key):
        if not ':' in key:
            raise ValueError('invalid name, needs a ":"')
        if not key in self.keys:
            self.keys.append(key)

    def increment(self, name, nb=1):
        if name not in self.keys:
            raise ValueError('unknown name')
        self.accu[name] += nb

    def log_all(self):
        elapsed = datetime.utcnow() - self.start
        print "////////// logging "
        for key in self.keys:
            val = self.accu[key]
            self.lines[key].append([elapsed.seconds/60.0, val])
        self.accu.clear()

    def write(self, fname):
        self.nbplots = 0
        self.output = stats_html_header

        groups = defaultdict(list)
        for name, values in self.lines.items():
            parts = name.split(':')
            if len(parts) < 2:
                print "skipping %s" % name
                continue
            groups[parts[0]].append(name)

        for group, contents in groups.items():
            self.plot(contents, group)
        with open(fname, 'w') as f:
            f.write(self.output + stats_html_footer)

    def _generate_json(self, name):
        second_part = name.split(':')[1]
        return {
            'type': 'line',
            'showInLegend': 'true',
            'legendText': second_part,
            'dataPoints': [
                {'x':x,'y':y}
                for x, y in self.lines[name]
            ],
        }

    def plot(self, names, title=''):
        self.nbplots += 1
        data = [
            self._generate_json(name)
            for name in names
        ]
        self.output += """
        <script>
        $(function(){
        var chart%d = new CanvasJS.Chart("chart%d",
        {
            title:{
            text: "%s"
            },
            data: %s
        });

        chart%d.render();
        });
        </script>
        <div style="height:400px;width:600px;" id="chart%d"></div>
        """ % (self.nbplots, self.nbplots, title, json.dumps(data), self.nbplots, self.nbplots)



