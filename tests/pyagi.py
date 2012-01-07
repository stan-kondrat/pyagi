"""Tests for ``pyagi.pyagi``."""


from unittest import TestCase

from pyagi.pyagi import AGI


class TestAGI(TestCase):

    def setUp(self):
        self.agi = AGI()

    def test_default_timeout_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_TIMEOUT, int)

    def test_default_record_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_RECORD, int)

    def tearDown(self):
        del self.agi
