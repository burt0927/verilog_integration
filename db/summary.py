# Copyright (c) 2013 Rich Porter - see LICENSE for further details

import database
import mdb
import message
import os.path

################################################################################

parser = message.reportOptionParser()
parser.add_option('-r', '--regression', action='store_true', help='is regression')
options, values = parser.parse_args()

################################################################################

mdb.db.connection.set_default_db(db=os.path.join(options.root, '../db/mdb.db'))
message.message.summary(False)

for log_id in map(int, values) :
  results = database.rgr().result(log_id, options.regression)
  result = results.summary(True)
  for test in results :
    (message.warning if test.status.status != 'PASS' else message.note)("[%(log_id)d, %(status)s] %(reason)s", log_id=test.log.log_id, **test.status)
  if result.passes != result.total :
    msg = message.error
  else :
    msg = message.information
  msg('%(total)d %(tests)s, %(passes)d pass, %(fails)d fail', tests='test' if result.total == 1 else 'tests', **result)
