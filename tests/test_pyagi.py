"""Tests for ``pyagi.pyagi``."""


from signal import getsignal, SIGHUP
from unittest import TestCase

from fudge import patch
from pyagi.pyagi import AGI


class TestAGI(TestCase):

    @patch('sys.stdin')
    def setUp(self, fake_stdin):
        (fake_stdin
            .provides('readline').returns('agi_test: test\n')
            .next_call().returns('agi_test2: test\n')
            .next_call().returns('\n')
        )
        self.agi = AGI()

    def test_init_sets_sighup_signal(self):
        self.assertTrue(hasattr(getsignal(SIGHUP), '__call__'))

    def test_init_sets_env(self):
        self.assertTrue(hasattr(self.agi, 'env'))

    def test_init_sets_env_dict(self):
        self.assertIsInstance(self.agi.env, dict)

    def test_default_record_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_RECORD, int)

    def test_default_timeout_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_TIMEOUT, int)

    def test_get_agi_env_sets_env_attr(self):
        self.assertIsInstance(self.agi.env, dict)

    def test_get_agi_env_sets_vars_from_asterisk(self):
        self.assertEquals(self.agi.env, {'agi_test': 'test', 'agi_test2': 'test'})

    def test_quote_returns_str(self):
        self.assertIsInstance(self.agi._quote('test'), str)

    def test_quote_adds_initial_quote_char(self):
        self.assertTrue(self.agi._quote('test').startswith('"'))

    def test_quote_adds_quote_char_to_end(self):
        self.assertTrue(self.agi._quote('test').endswith('"'))

    def test_quote_returns_expected_value(self):
        self.assertEquals(self.agi._quote('test'), '"test"')

    def test_quote_accepts_ints(self):
        self.assertEquals(self.agi._quote(1), '"1"')

    def tearDown(self):
        del self.agi
