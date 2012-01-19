"""Tests for ``pyagi.pyagi``."""


from signal import getsignal, SIGHUP
from unittest import TestCase

from fudge import patch, test, Fake
from pyagi.exceptions import AGISIGHUPHangup
from pyagi.pyagi import AGI


class TestAGI(TestCase):
    """Base test case for all AGI class tests. This class provides a simple
    setUp method that mocks stdin. This reduces our code complexity across all
    of our test cases.
    """
    @patch('sys.stdin')
    def setUp(self, fake_stdin):
        (fake_stdin
            .provides('readline').returns('agi_test: test\n')
            .next_call().returns('agi_test2: test\n')
            .next_call().returns('\n')
        )
        self.agi = AGI()

    def tearDown(self):
        del self.agi


class TestAttributes(TestAGI):
    """Tests all AGI class attributes."""
    def test_default_record_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_RECORD, int)

    def test_default_timeout_is_int(self):
        self.assertIsInstance(self.agi.DEFAULT_TIMEOUT, int)


class TestInit(TestAGI):
    """Tests the __init__ method."""
    def test_init_sets_sighup_signal(self):
        self.assertTrue(hasattr(getsignal(SIGHUP), '__call__'))

    def test_init_sets_env(self):
        self.assertTrue(hasattr(self.agi, 'env'))

    def test_init_sets_env_dict(self):
        self.assertIsInstance(self.agi.env, dict)


class TestGetAGIEnv(TestAGI):
    """Tests the _get_agi_env method."""
    def test_get_agi_env_sets_env_attr(self):
        self.assertIsInstance(self.agi.env, dict)

    def test_get_agi_env_sets_vars_from_asterisk(self):
        self.assertEquals(self.agi.env, {'agi_test': 'test', 'agi_test2': 'test'})


class TestQuote(TestAGI):
    """Tests the _quote method."""
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


class TestHandleSighup(TestAGI):
    """Tests the _handle_sighup method."""
    def test_handle_sighup_raises_exception(self):
        self.assertRaises(AGISIGHUPHangup, self.agi._handle_sighup, 1, 2)


class TestExecute(TestAGI):
    """Tests the execute method."""

    @test
    def test_execute_calls_command(self):
        self.agi.send_command = (Fake('pyagi.pyagi.AGI.send_command')
                .is_callable())
        self.agi.get_result = (Fake('pyagi.pyagi.AGI.get_result')
                .is_callable()
                .returns(True))

        self.agi.execute('NoOp')
