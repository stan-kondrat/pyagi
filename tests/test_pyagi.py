"""Tests for ``pyagi.pyagi``."""


from unittest import TestCase

from fudge import patch
from pyagi.pyagi import AGI


class TestAGI(TestCase):

    @patch('sys.stdin')
    def setUp(self, fake_stdin):
        (fake_stdin
            .has_attr(DEFAULT_TIMEOUT=2000)
            .has_attr(DEFAULT_RECORD=20000)
            .provides('readline').returns('agi_test: test\n')
            .next_call().returns('agi_test2: test\n')
            .next_call().returns('\n')
        )
        self.agi = AGI()

    def test_default_timeout_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_TIMEOUT, int)

    def test_default_record_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_RECORD, int)

    def tearDown(self):
        del self.agi
