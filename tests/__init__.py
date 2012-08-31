import unittest

from google.appengine.api import memcache
from google.appengine.ext import testbed


class TestCase(unittest.TestCase):
  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_memcache_stub()
    memcache.flush_all()
    self.testbed.init_datastore_v3_stub()

    self.extendedSetUp()

  def tearDown(self):
    self.extendedTearDown()
    self.testbed.deactivate()

  def extendedTearDown(self):
    # method to be overridden by actual test case
    pass

  def extendedSetUp(self):
    # method to be overridden by actual test case
    pass
