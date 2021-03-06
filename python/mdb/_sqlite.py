# Copyright (c) 2012, 2013 Rich Porter - see LICENSE for further details

import accessor
import json as json_
import message
import os.path
import sqlite3
import sys
import threading

class cursor(object) :
  LAST_SQL='SELECT last_insert_rowid() AS rowid;'
  def __init__(self, connection, factory) :
    connection.row_factory = factory
    self.db = connection.cursor()
  def formatter(self, fmt) :
    return str(fmt).replace('%s', '?')
  def split(self, field) :
    return 'RTRIM('+field+', "-x0123456789abcdef")'
  def _execute(self, *args) :
    self.db.execute(self.formatter(args[0]), *args[1:])
    return self.db.rowcount
  def _executemany(self, *args) :
    self.db.executemany(self.formatter(args[0]), *args[1:])
    return self.db.rowcount

def accessor_factory(cursor, row) :
  'Horrible, horrible hack here. Reverse list as when there are duplicates for fields we want use to 1st'
  return accessor.accessor(reversed([(name[0], row[idx]) for idx, name in enumerate(cursor.description)]))

class connection(object) :
  default_db = 'default.db'
  def connect(self, *args, **kwargs) :
    try :
      self.db = kwargs['db']
    except KeyError:
      self.db = self.default_db
    try :
      instance = sqlite3.connect(self.db)
    except :
      message.warning('Unable to connect. File %(db)s because %(exc)s', db=self.db, exc=sys.exc_info()[0])
    instance.execute('PRAGMA journal_mode=WAL;')
    instance.execute('PRAGMA read_uncommitted = 1;')
    self.instance[self.id()] = instance

  def row_cursor(self) :
    return self.cursor(accessor_factory)

  @classmethod
  def set_default_db(cls, **args) :
    cls.default_db = os.path.join(args.get('root',''), args['db'])

class json :
  @classmethod
  def dump(cls, obj, f) :
    json_.dump(obj, f)
  @classmethod
  def dumps(cls, obj, f) :
    json_.dumps(obj, f)
