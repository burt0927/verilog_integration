# Copyright (c) 2012, 2013 Rich Porter - see LICENSE for further details

import message
import os
import Queue
import socket
import threading
from accessor import *

class activityBlockVersion :
  def __init__(self, **kwargs) :
    self.activity = kwargs.get('activity', None)
    self.block    = kwargs.get('block', None)
    self.version  = kwargs.get('version', self.get_version())

  def get_version(self) :
    import subprocess
    try :
      return subprocess.check_output(['git', 'log', '-1', '--format=%h']).strip()
    except :
      return 'Not available'

class mdbDefault(dict) :
  'Pull some attributes from the enviroment'
  __env = None
  def __init__(self) :
    if self.__env is None :
      MDB=os.environ.get('MDB', [])
      if MDB :
        self.__env = map(lambda x : x.split('='), MDB.split(','))
        self.update(self.__env)
      else :
        self.__env = []
  def __getattr__(self, attr) :
    return self.get(attr, None)

################################################################################

class _cursor(object) :
  ident=0
  debug=False
  def __init__(self, connection, factory) :
    self.connection = connection
    self.db = self.connection.cursor()
    self.dump = open(self.filename(), 'w') if self.debug else None
    if self.dump :
      import inspect, pprint
      pprint.pprint(inspect.stack(), stream=self.dump)

  def commit(self) :
    self.connection.commit()

  def execute(self, *args) :
    if self.dump :
      self.dump.write('%08x : ' % id(self.db) + ' << '.join(map(str, args)) + '\n')
    return self.db.execute(*args)

  def __getattr__(self, attr) :
    return getattr(self.db, attr)

  def __iter__(self) :
    return self.db

  def __enter__(self) :
    return self.db

  def __exit__(self, type, value, traceback): 
    self.connection.commit()
    self.db.close()

  def __del__(self) :
    if self.dump :
      self.dump.close()

  @classmethod
  def filename(cls) :
    name, cls.ident = 'sql_%d' % cls.ident, cls.ident + 1
    return name

class _connection(object) :
  instance = dict()

  def __init__(self, *args, **kwargs) :
    'pools connections on per thread basis'
    if threading.current_thread() not in self.instance :
      self.connect(*args, **kwargs)

  def cursor(self, *args) :
    return cursor(self.instance[threading.current_thread()], *args)

try :
  import _mysql as db
except ImportError :
  import _sqlite as db

class cursor(_cursor, db.cursor) :
  impl = db
  def __init__(self, connection, factory=None) :
    db.cursor.__init__(self, connection, factory)
    _cursor.__init__(self, connection, factory)

class connection(_connection, db.connection) :
  impl = db

################################################################################

class mdb(object) :
  queue_limit = 10
  instances = []
  atexit = False
  class repeatingTimer(threading._Timer) :
    def run(self):
      while not self.finished.is_set():
        self.finished.wait(self.interval)
        self.function(*self.args, **self.kwargs)
    def running(self) :
      return not self.finished.is_set()

  def __init__(self, description='none given', test=None, root=None, parent=None, level=message.ERROR, **kwargs) :
    self.commit_level = level
    self.abv = activityBlockVersion(**kwargs)
    self.queue = Queue.Queue()
    # init default filter
    self.filter_fn = self.filter
    self.root = root or mdbDefault().root
    self.parent = parent or mdbDefault().parent
    # create log entry for this run
    self.log_id = self.log(os.getuid(), socket.gethostname(), self.abv, self.root, self.parent, description, test)
    # install callbacks
    message.emit_cbs.add('mdb emit', 1, self.add, None)
    message.terminate_cbs.add('mdb terminate', 20, self.finalize, self.finalize)
    # flush queue every half second
    self.timer = self.repeatingTimer(0.5, self.flush)
    self.timer.start()
    # add to list of instances
    self.instances.append(self)
    message.debug('hello ...')

  def filter(self, cb_id, level, filename) :
    'do not store messages less important that INFORMATION by default'
    return level < message.INFORMATION

  def finalize(self, *args) :
    'set test status & clean up'
    if self.timer.running() :
      message.debug('... bye')
      self.timer.cancel()
    self.flush()
    self.status()

  def add(self, cb_id, when, level, severity, tag, filename, line, msg) :
    # option to ignore certain messages
    if self.filter_fn(cb_id, level, filename) :
      return
    # add to queue, take copy of filename and msg
    self.queue.put([cb_id, accessor(tv_sec=when.tv_sec, tv_nsec=when.tv_nsec), level, severity, tag and tag.ident, tag and tag.subident, str(filename), line, str(msg)])
    # flush to db if this message has high severity or there are a number of outstanding messages
    if level >= self.commit_level or self.queue.qsize() >= self.queue_limit :
      self.flush()

  def get_root(self) :
    return self.root or self.log_id
  def is_root(self) :
    return self.root is None

  @classmethod
  def finalize_all(cls) :
    for instance in cls.instances :
      instance.finalize()

  @classmethod
  def cursor(cls) :
    return connection().cursor()

  def get_sema(self) :
    if not hasattr(self, 'semaphore') :
      self.semaphore = threading.Semaphore()
    return self.semaphore

  def flush(self) :
    semaphore = self.get_sema()
    semaphore.acquire()
    with self.cursor() as cursor :
      def insert(cb_id, when, level, severity, ident, subident, filename, line, msg) :
        cursor.execute('INSERT INTO message (log_id, level, severity, date, ident, subident, filename, line, msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', (self.log_id, level, severity, when.tv_sec, ident, subident, filename, line, msg))
      try :
        while (1) :
          insert(*self.queue.get(False))
      except Queue.Empty :
        pass # done
    semaphore.release()

  def log(self, uid, hostname, abv, root, parent, description, test) :
    'create entry in log table'
    with self.cursor() as db :
      db.execute('INSERT INTO log (uid, root, parent, activity, block, version, description, test, hostname) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', (uid, root, parent, abv.activity, abv.block, abv.version, description, test, hostname))
      return db.lastrowid

  def status(self) :
    'update status at end'
    with self.cursor() as cursor :
      cursor.execute('UPDATE log SET status = ? WHERE log_id = ?;', (int(message.message.status().flag), self.log_id))

# short cut
finalize_all = mdb.finalize_all
