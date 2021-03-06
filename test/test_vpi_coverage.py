# Copyright (c) 2013 Rich Porter - see LICENSE for further details

import coverage
import message
import test
import verilog

# we reuse vpi test
import test_vpi

message.message.verbosity(message.INT_DEBUG)

################################################################################

class test_cvg :
  class coverpoint_sig(coverage.coverpoint) :
    'bits toggle'
    def __init__(self, signal, name=None, parent=None) :
      self.size   = signal.size
      self.bit    = self.add_axis('bit', values=range(0, self.size))
      self.sense  = self.add_axis('sense', true=1, false=0)
      self.fmt    = self.add_axis('fmt', vpiBinStr=0, vpiOctStr=1, vpiHexStr=2, vpiDecStr=3)
      coverage.coverpoint.__init__(self, name=name, parent=parent)

    def define(self, bucket) :
      'set goal'
      # no dont cares or illegals
      bucket.default(goal=10)

    def _define(self, bucket) :
      'An example of more involved goal setting'
      bucket.default(goal=10, dont_care=bucket.axis.fmt=='vpiBinStr')
      # bit will be an integer
      if bucket.axis.fmt == 'vpiDecStr' : 
        bucket.goal += bucket.axis.bit * 10
      # sense will be a string value
      if bucket.axis.sense == 'true' :
        bucket.goal += 1

  class coverpoint_format(coverage.coverpoint) :
    'format x format'
    def __init__(self, signal, name=None, parent=None) :
      self.fmt0 = self.add_axis('fmt0', vpiBinStr=0, vpiOctStr=1, vpiHexStr=2, vpiDecStr=3)
      self.fmt1 = self.add_axis('fmt1', vpiBinStr=0, vpiOctStr=1, vpiHexStr=2, vpiDecStr=3)
      coverage.coverpoint.__init__(self, name=name, parent=parent)

    def define(self, bucket) :
      'set goal'
      # no dont cares or illegals
      bucket.default(goal=10)

  class coverpoint_iterations(coverage.coverpoint) :
    ''
    def __init__(self, signal, name=None, parent=None) :
      self.count = self.add_axis('count', count=0)
      coverage.coverpoint.__init__(self, name=name, parent=parent)

    def define(self, bucket) :
      'set goal'
      # no dont cares or illegals
      bucket.default(goal=100)

################################################################################

class cbClk(test_vpi.cbClk) :
  ITERATIONS=1000
  class assign(test_vpi.cbClk.assign) :
    def __init__(self, size, scope) :
      test_vpi.cbClk.assign.__init__(self, size, scope)
      self.container = coverage.hierarchy(scope.fullname, 'Scope')
      self.cvr_pt0 = test_cvg.coverpoint_sig(self.scope.sig0, name='sig0', parent=self.container)
      self.cursor0 = self.cvr_pt0.cursor()
      self.cvr_pt1 = test_cvg.coverpoint_format(self.scope.sig0, name='sig0 x sig1', parent=self.container)
      self.cursor1 = self.cvr_pt1.cursor()
      self.cvr_pt2 = test_cvg.coverpoint_format(self.scope.sig0, name='sig0 : write fmt x read format', parent=self.container)
      self.cursor2 = self.cvr_pt2.cursor()

    def put(self) :
      sig0 = self.value(self.rand())
      sig1 = self.value()
      self.scope.direct.sig0 = sig0
      self.scope.direct.sig1 = sig1
      self.cursor0(fmt=sig0.__class__.__name__)
      for i in self.cvr_pt0.bit.get_values() :
        self.cursor0(bit=i, sense='true' if sig0[i] else 'false').incr()
      self.cursor1(fmt0=sig0.__class__.__name__, fmt1=sig1.__class__.__name__).incr()
      # use cursor to remember state for get()
      self.cursor2(fmt0=sig0.__class__.__name__)

    def get(self) :
      if not hasattr(self, 'bits') : return
      # cross these choices
      sig0 = self.scope.sig0.get_value(self.choice())
      sig1 = self.scope.sig1.get_value(self.choice())
      # fmt0 state remembered from put() funtion, and increment
      self.cursor2(fmt1=sig0.__class__.__name__).incr()
      self.check(sig0, sig1)

  def fcty(self, *args) :
    'object factory'
    return self.assign(*args)

class test_vpi_coverage(test_vpi.test_vpi) :
  name='test vpi coverage'
  MAX_INSTS=20
  TIMEOUT=1000
  def cb_fcty(self, *args) :
    'object factory'
    return cbClk(*args)

testing = test_vpi_coverage()
