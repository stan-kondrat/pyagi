"""Tests for ``pyagi.pyagi``."""


from signal import getsignal, SIGHUP
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

    def test_init_sets_sighup_signal(self):
        self.assertTrue(hasattr(getsignal(SIGHUP), '__call__'))

    def test_default_record_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_RECORD, int)

    def test_default_timeout_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_TIMEOUT, int)

    def test_get_agi_env_sets_env_attr(self):
        self.assertIsInstance(self.agi.env, dict)

    def test_get_agi_env_sets_vars_from_asterisk(self):
        self.assertEquals(self.agi.env, {'agi_test': 'test', 'agi_test2': 'test'})

    def tearDown(self):
        del self.agi
