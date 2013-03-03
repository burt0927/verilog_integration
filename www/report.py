# Copyright (c) 2012 Rich Porter - see LICENSE for further details

import bottle
import cStringIO
import itertools
import json
import mdb
import message
import os.path
import time

################################################################################

from optparse import OptionParser
parser = OptionParser()
parser.add_option('-p', '--port', default='8080', help='port to serve on')
parser.add_option('-r', '--root', help='root directory for server')
options, values = parser.parse_args()

################################################################################

mdb.db.connection.set_default_db(db=os.path.join(options.root, '../db/mdb.db'))
mdb.mdb('mdb report')

# intercept log messages and redirect to our logger
def bottle_log(msg) :
  message.note(msg.strip())
def wsgi_log(self, format, *args) :
  message.debug(format.strip() % args)

bottle._stderr = bottle_log
from wsgiref.simple_server import WSGIRequestHandler
WSGIRequestHandler.log_message = wsgi_log

# location of static data
static = os.path.join(options.root, 'static')

################################################################################

class serve_something(object) :
  CONTENTTYPE='text/html'
  encapsulate=True
  def __init__(self) :
    self.page = cStringIO.StringIO()

  def __del__(self) :
    self.page.close()
    #database.connecting.database.close_all()

  def div(self) :
    return ' class="tab"'

  def GET(self, **args):
    self.headers()
    elapsed=time.time()
    if self.encapsulate : self.page.write('<div%s>\n' % self.div())
    self.doit(**args)
    elapsed = time.time()-elapsed
    if self.encapsulate : 
      self.page.write('<p class="time" title="Generated in %0.2fs">Generated in %0.2fs</p>' % (elapsed, elapsed))
      self.page.write('</div>\n<b/>\n')
    message.note('page %(page)s served in %(time)0.2fs', page=bottle.request.url, time=elapsed)
    return self.page.getvalue().replace('&', '&amp;')

  def doit(self, inv_id):
    self.serve(inv_id).html(self.page)

  def headers(self):
    bottle.response.content_type = self.CONTENTTYPE

################################################################################

# stolen from python website
class groupby:
    def __init__(self, iterable):
        self.it = iter(iterable)
        self.tgtkey = self.currkey = self.currvalue = object()
        self.keyfunc = lambda x : x.log_id
    def __iter__(self):
        return self
    def __next__(self):
        while self.currkey == self.tgtkey:
            self.currvalue = next(self.it)    # Exit on StopIteration
            self.currkey = self.keyfunc(self.currvalue)
        self.tgtkey = self.currkey
        return (dict(log_id=self.currvalue.log_id, block=self.currvalue.block, activity=self.currvalue.activity, version=self.currvalue.version, description=self.currvalue.description), self._grouper(self.tgtkey))
    next=__next__
    def _grouper(self, tgtkey):
        while self.currkey == tgtkey:
            yield dict(level=self.currvalue.level, severity=self.currvalue.severity, msg=self.currvalue.msg, count=self.currvalue.count)
            self.currvalue = next(self.it)    # Exit on StopIteration
            self.currkey = self.keyfunc(self.currvalue)

class index(serve_something) :
  CONTENTTYPE='application/json'
  encapsulate = False
  def doit(self, variant, start=0, finish=20):
    db   = mdb.db.connection().row_cursor()
    db.execute('SELECT log.*, message.*, COUNT(*) AS count FROM (SELECT * FROM log ORDER BY log_id DESC LIMIT %(start)s, %(finish)s) AS log NATURAL JOIN message GROUP BY log_id, level ORDER By log_id, msg_id, level ASC;' % locals())
    json.dump([{'log' : log, 'msgs' : list(msgs)} for log, msgs in groupby(db.fetchall())], self.page)

################################################################################

@bottle.get('/static/:filename#.*#')
def server_static(filename):
    return bottle.static_file(filename, root=static)

@bottle.route('/')
@bottle.route('/index.html')
def index_html() :
  return bottle.static_file('/index.html', root=static)

urls = (
  ('/index/:variant', index,),
)

for path, cls in urls:
  def serve(_cls) : 
    def fn(**args) : 
      return _cls().GET(**args)
    return fn
  bottle.route(path, name='route_'+cls.__name__)(serve(cls))


################################################################################

bottle.run(port=options.port)

