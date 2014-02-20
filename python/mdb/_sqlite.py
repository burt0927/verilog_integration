# Copyright (c) 2012, 2013 Rich Porter - see LICENSE for further details

import accessor
import message
import os.path
import sqlite3
import sys
import threading

class cursor(object) :
  def __init__(self, connection, factory) :
    connection.row_factory = factory

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
    self.instance[threading.current_thread()] = instance

  def row_cursor(self) :
    return self.cursor(accessor_factory)

  @classmethod
  def set_default_db(cls, **args) :
    cls.default_db = os.path.join(args.get('root',''), args['db'])

