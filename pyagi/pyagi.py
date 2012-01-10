"""An Asterisk AGI library for humans."""


import pprint, re, sys
from signal import signal, SIGHUP
from types import ListType

from exceptions import *


re_code = re.compile(r'(^\d*)\s*(.*)')
re_kv = re.compile(r'(?P<key>\w+)=(?P<value>[^\s]+)\s*(?:\((?P<data>.*)\))*')


class AGI(object):
    """An Asterisk AGI protocol wrapper.

    An instance of this class handles command processing and communication
    between Asterisk and python.

    :attr int DEFAULT_TIMEOUT: The default timeout (in ms) to use for methods
        that take a timeout argument.
    :attr int DEFAULT_RECORD: The default allowed recording time (in ms) to use
        for methods that take a record time argument.
    """
    DEFAULT_RECORD = 20000
    DEFAULT_TIMEOUT = 2000

    def __init__(self):
        signal(SIGHUP, self._handle_sighup)  # handle SIGHUP
        self.env = {}
        self._get_agi_env()

    def _get_agi_env(self):
        """Read in all variables passed to us by Asterisk through STDIN, storing
        these variables in our ``env`` class attribute.

        This works by reading lines from STDIN until we receive a blank line,
        indicating that Asterisk has nothing left to pass us. Each line we read
        is parsed, and stored in a class dictionary, ``env``, for later usage.

        See: http://www.voip-info.org/wiki/view/Asterisk+AGI#AGIExecutionEnvironment
        for more information.
        """
        while True:

            line = sys.stdin.readline().strip()
            if not line:
                break

            # Asterisk passes variables to us in the format:
            #   name: value
            key, data = line.split(':')[0], ':'.join(line.split(':')[1:])
            key = key.strip()
            data = data.strip()

            # Only store the variable and value if the variable name exists. If
            # it is empty, something weird must have happened, so do nothing.
            if key:
                self.env[key] = data

    def _quote(self, string):
        return ''.join(['"', str(string), '"'])

    def _handle_sighup(self, signum, frame):
        """Handle the SIGHUP signal. SIGHUP is sent to us by Asterisk whenever
        the caller hangs up. In this circumstance, we should simply raise an
        ``AGISIGHUPHangup`` exception so the user can deal with it.
        """
        raise AGISIGHUPHangup('Received SIGHUP from Asterisk.')

    def execute(self, command, *args):

        try:
            self.send_command(command, *args)
            return self.get_result()
        except IOError,e:
            if e.errno == 32:
                # Broken Pipe * let us go
                raise AGISIGPIPEHangup("Received SIGPIPE")
            else:
                raise

    def send_command(self, command, *args):
        """Send a command to Asterisk"""
        command = command.strip()
        command = '%s %s' % (command, ' '.join(map(str,args)))
        command = command.strip()
        if command[-1] != '\n':
            command += '\n'
        sys.stdout.write(command)
        sys.stdout.flush()

    def get_result(self, stdin=sys.stdin):
        """Read the result of a command from Asterisk"""
        code = 0
        result = {'result':('','')}
        line = stdin.readline().strip()
        m = re_code.search(line)
        if m:
            code, response = m.groups()
            code = int(code)

        if code == 200:
            for key,value,data in re_kv.findall(response):
                result[key] = (value, data)

                # If user hangs up... we get 'hangup' in the data
                if data == 'hangup':
                    raise AGIResultHangup("User hungup during execution")

                if key == 'result' and value == '-1':
                    raise AGIAppError("Error executing application, or hangup")

            return result
        elif code == 510:
            raise AGIInvalidCommand(response)
        elif code == 520:
            usage = [line]
            line = stdin.readline().strip()
            while line[:3] != '520':
                usage.append(line)
                line = stdin.readline().strip()
            usage.append(line)
            usage = '%s\n' % '\n'.join(usage)
            raise AGIUsageError(usage)
        else:
            raise AGIUnknownError(code, 'Unhandled code or undefined response')

    def _process_digit_list(self, digits):
        if type(digits) == ListType:
            digits = ''.join(map(str, digits))
        return self._quote(digits)

    def answer(self):
        """Answers channel if not already in answer state.

        See: http://www.voip-info.org/wiki/view/answer

        :rtype: int
        :returns: -1 on channel failure, or 0 if successful.
        """
        return self.execute('ANSWER')['result'][0]

    def asyncagi_break(self):
        """Interrupts expected flow of Async AGI commands and returns control
        to previous source (typically, the PBX dialplan).
        """
        pass

    def channel_status(self, channel=''):
        """Returns the status of the specified channel. If no channel name is
        given then returns the status of the current channel.

        See: http://www.voip-info.org/wiki/view/channel+status

        :rtype: int
        :returns: 0 - Channel is down and available.
            1 - Channel is down, but reserved.
            2 - Channel is off hook.
            3 - Digits (or equivalent) have been dialed.
            4 - Line is ringing.
            5 - Remote end is ringing.
            6 - Line is up.
            7 - Line is busy.
        """
        try:
           result = self.execute('CHANNEL STATUS', channel)
        except AGIHangup:
           raise
        except AGIAppError:
           result = {'result': ('-1','')}

        return int(result['result'][0])

    def control_stream_file(self, filename, escape_digits='', skipms=3000, fwd='', rew='', pause=''):
        """Send the given file, allowing playback to be controlled by the given
        digits, if any. Use double quotes for the digits if you wish none to be
        permitted.

        See: http://www.voip-info.org/wiki/view/control+stream+file

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed, or -1 on
            error or if the channel was disconnected.
        """
        escape_digits = self._process_digit_list(escape_digits)
        response = self.execute('CONTROL STREAM FILE', self._quote(filename), escape_digits, self._quote(skipms), self._quote(fwd), self._quote(rew), self._quote(pause))
        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def database_del(self, family, key):
        """Deletes an entry in the Asterisk database for a given family and
        key.

        See: http://www.voip-info.org/wiki/view/database+del

        :rtype: int
        :returns: 1 if successful, 0 otherwise.
        """
        result = self.execute('DATABASE DEL', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to delete from database: family=%s, key=%s' % (family, key))

    def database_deltree(self, family, key=''):
        """Deletes a family or specific keytree within a family in the Asterisk
        database.

        See: http://www.voip-info.org/wiki/view/database+deltree

        :rtype: int
        :returns: 1 if successful, 0 otherwise.
        """
        result = self.execute('DATABASE DELTREE', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to delete tree from database: family=%s, key=%s' % (family, key))

    def database_get(self, family, key):
        """Retrieves an entry in the Asterisk database for a given family and
        key.

        See: http://www.voip-info.org/wiki/view/database+get

        :rtype: str
        :returns: The database entry (if one exists), or an empty string.
        """
        family = '"%s"' % family
        key = '"%s"' % key
        result = self.execute('DATABASE GET', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Key not found in database: family=%s, key=%s' % (family, key))
        elif res == '1':
            return value
        else:
            raise AGIError('Unknown exception for : family=%s, key=%s, result=%s' % (family, key, pprint.pformat(result)))

    def database_put(self, family, key, value):
        """Adds or updates an entry in the Asterisk database for a given
        family, key, and value.

        See: http://www.voip-info.org/wiki/view/database+put

        :rtype: int
        :returns: 1 if successful, 0 otherwise.
        """
        result = self.execute('DATABASE PUT', self._quote(family), self._quote(key), self._quote(value))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to put vaule in databale: family=%s, key=%s, value=%s' % (family, key, value))

    def appexec(self, application, options=''):
        """Executes application with given options.

        See: http://www.voip-info.org/wiki/view/exec

        :rtype: int
        :returns: Whatever the application returns, or -2 on failure to find
            application.

        TODO: Rename this application to exec, to comply with AGI standard.
        """
        result = self.execute('EXEC', application, self._quote(options))
        res = result['result'][0]
        if res == '-2':
            raise AGIAppError('Unable to find application: %s' % application)
        return res

    def get_data(self, filename, timeout=DEFAULT_TIMEOUT, max_digits=255):
        """Stream the given file, and receive DTMF data.

        See: http://www.voip-info.org/wiki/view/get+data

        :rtype: str
        :returns: Digits received from the channel at the other end.
        """
        result = self.execute('GET DATA', filename, timeout, max_digits)
        res, value = result['result']
        return res

    def get_full_variable(self, name, channel = None):
        """Retrieve a channel variable. Understands complex variable names and
        builtin variables, unlike ``get_variable``.

        See: http://www.voip-info.org/wiki/view/get+full+variable

        :rtype: str
        :returns: The variable, or an empty string if the variable doesn't
            exist.
        """
        try:
           if channel:
              result = self.execute('GET FULL VARIABLE', self._quote(name), self._quote(channel))
           else:
              result = self.execute('GET FULL VARIABLE', self._quote(name))

        except AGIResultHangup:
           result = {'result': ('1', 'hangup')}

        res, value = result['result']
        return value

    def get_option(self, filename, escape_digits='', timeout=0):
        """Behaves similar to STREAM FILE but used with a timeout option.

        See: http://www.voip-info.org/wiki/view/get+option
        """
        escape_digits = self._process_digit_list(escape_digits)
        if timeout:
            response = self.execute('GET OPTION', filename, escape_digits, timeout)
        else:
            response = self.execute('GET OPTION', filename, escape_digits)

        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def get_variable(self, name):
        """Get a channel variable.

        See: http://www.voip-info.org/wiki/view/get+variable

        :rtype: str
        :returns: The variable, or an empty string if the variable isn't set.
        """
        try:
           result = self.execute('GET VARIABLE', self._quote(name))
        except AGIResultHangup:
           result = {'result': ('1', 'hangup')}

        res, value = result['result']
        return value

    def gosub(self):
        """Cause the channel to execute the specified dialplan subroutine,
        returning to the dialplan with execution of a Return().
        """
        pass

    def hangup(self, channel=''):
        """Hangs up the specified channel. If no channel name is given, hangs
        up the current channel.

        See: http://www.voip-info.org/wiki/view/hangup
        """
        self.execute('HANGUP', channel)

    def noop(self):
        """Does nothing.

        See: http://www.voip-info.org/wiki/view/noop
        """
        self.execute('NOOP')

    def receive_char(self, timeout=DEFAULT_TIMEOUT):
        """Receives a character of text on a channel. Most channels do not
        support the reception of text.

        See: http://www.voip-info.org/wiki/view/receive+char

        :rtype: int
        :returns: The decimal value of the character if one is received, or 0 if
            the channel does not support text reception. Returns -1 only on
            error/hangup.
        """
        res = self.execute('RECEIVE CHAR', timeout)['result'][0]

        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def receive_text(self):
        """Receives a string of text on a channel. Most channels do not support
        the reception of text.

        See: http://www.voip-info.org/wiki/view/receive+text

        :rtype: str
        :returns: The string received, or an empty string on failure.
        """
        pass

    def record_file(self, filename, format='gsm', escape_digits='#',
            timeout=DEFAULT_RECORD, offset=0, beep='beep'):
        """Record to a file until a given dtmf digit in the sequence is
        received.

        See: http://www.voip-info.org/wiki/view/record+file

        :rtype: int
        :returns: -1 on hangup or error.
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('RECORD FILE', self._quote(filename), format, escape_digits, timeout, offset, beep)['result'][0]
        try:
            return chr(int(res))
        except:
            raise AGIError('Unable to convert result to digit: %s' % res)

    def say_alpha(self, characters, escape_digits=''):
        """Say a given character string, returning early if any of the given
        DTMF digits are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+alpha

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed. Returns -1
            on error/hangup.
        """
        characters = self._process_digit_list(characters)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY ALPHA', characters, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_date(self, seconds, escape_digits=''):
        """Say a given date, returning early if any of the given DTMF digits
        are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+date

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed or -1 on
            error/hangup.
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY DATE', seconds, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_datetime(self, seconds, escape_digits='', format='', zone=''):
        """Say a given time, returning early if any of the given DTMF digits
        are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+datetime

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed or -1 on
            error/hangup.
        """
        escape_digits = self._process_digit_list(escape_digits)
        if format: format = self._quote(format)
        res = self.execute('SAY DATETIME', seconds, escape_digits, format, zone)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_digits(self, digits, escape_digits=''):
        """Say a given digit string, returning early if any of the given DTMF
        digits are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+digits

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed or -1 on
            error/hangup.
        """
        digits = self._process_digit_list(digits)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY DIGITS', digits, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_number(self, number, escape_digits=''):
        """Say a given number, returning early if any of the given DTMF digits
        are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+number

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed or -1 on
            error/hangup.
        """
        number = self._process_digit_list(number)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY NUMBER', number, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_phonetic(self, characters, escape_digits=''):
        """Say a given character string with phonetics, returning early if any
        of the given DTMF digits are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+phonetic

        :rtype: int
        :returns: 0 if playback completes without a digit pressed, the ASCII
            numerical value of the digit if one was pressed, or -1 on
            error/hangup.
        """
        characters = self._process_digit_list(characters)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY PHONETIC', characters, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_time(self, seconds, escape_digits=''):
        """Say a given time, returning early if any of the given DTMF digits
        are received on the channel.

        See: http://www.voip-info.org/wiki/view/say+time

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or the
            ASCII numerical value of the digit if one was pressed or -1 on
            error/hangup.
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY TIME', seconds, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def send_image(self, filename):
        """Sends the given image on a channel. Most channels do not support the
        transmission of images.

        See: http://www.voip-info.org/wiki/view/send+image

        :rtype: int
        :returns: 0 if image is sent, or if the channel does not support image
            transmission. Returns -1 only on error/hangup.

        Image names should not include extensions.
        """
        res = self.execute('SEND IMAGE', filename)['result'][0]
        if res != '0':
            raise AGIAppError('Channel falure on channel %s' % self.env.get('agi_channel','UNKNOWN'))

    def send_text(self, text=''):
        """Sends the given text on a channel. Most channels do not support the
        transmission of text.

        See: http://www.voip-info.org/wiki/view/send+text

        :rtype: int
        :returns: 0 if text is sent, or if the channel does not support text
            transmission. Returns -1 only on error/hangup.
        """
        self.execute('SEND TEXT', self._quote(text))['result'][0]

    def set_autohangup(self, secs):
        """Cause the channel to automatically hangup at time seconds in the
        future. Of course it can be hungup before then as well. Setting to 0
        will cause the autohangup feature to be disabled on this channel.

        See: http://www.voip-info.org/wiki/view/set+autohangup
        """
        self.execute('SET AUTOHANGUP', secs)

    def set_callerid(self, number):
        """Changes the callerid of the current channel.

        See: http://www.voip-info.org/wiki/view/set+callerid
        """
        self.execute('SET CALLERID', number)

    def set_context(self, context):
        """Sets the context for continuation upon exiting the application.

        See: http://www.voip-info.org/wiki/view/set+context
        """
        self.execute('SET CONTEXT', context)

    def set_extension(self, extension):
        """Changes the extension for continuation upon exiting the application.

        See: http://www.voip-info.org/wiki/view/set+extension
        """
        self.execute('SET EXTENSION', extension)

    def set_music(self):
        """Enables/disables the music on hold generator. If class is not
        specified, then the 'default' music on hold class will be used.

        See: http://www.voip-info.org/wiki/view/set+music
        """
        pass

    def set_priority(self, priority):
        """Changes the priority for continuation upon exiting the application.
        The priority must be a valid priority or label.

        See: http://www.voip-info.org/wiki/view/set+priority
        """
        self.execute('set priority', priority)

    def set_variable(self, name, value):
        """Sets a variable to the current channel.

        See: http://www.voip-info.org/wiki/view/set+variable
        """
        self.execute('SET VARIABLE', self._quote(name), self._quote(value))

    def speech_activate_grammar(self):
        """Activates the specified grammar on the speech object."""
        pass

    def speech_create(self):
        """Create a speech object to be used by the other Speech AGI
        commands.
        """
        pass

    def speech_deactivate_grammar(self):
        """Deactivates the specified grammar on the speech object."""
        pass

    def speech_destroy(self):
        """Destroy the speech object created by 'SPEECH CREATE'."""
        pass

    def speech_load_grammar(self):
        """Loads the specified grammar as the specified name."""
        pass

    def speech_recognize(self):
        """Plays back given prompt while listening for speech and dtmf."""
        pass

    def speech_set(self):
        """Set an engine-specific setting."""
        pass

    def speech_unload_grammar(self):
        """Unloads the specified grammar."""
        pass

    def stream_file(self, filename, escape_digits='', sample_offset=0):
        """Send the given file, allowing playback to be interrupted by the
        given digits, if any.

        See: http://www.voip-info.org/wiki/view/stream+file

        :rtype: int
        :returns: 0 if playback completes without a digit being pressed, or
            the ASCII numerical value of the digit if one was pressed, or -1
            on error or if the channel was disconnected.
        """
        escape_digits = self._process_digit_list(escape_digits)
        response = self.execute('STREAM FILE', filename, escape_digits, sample_offset)
        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def tdd_mode(self, mode='off'):
        """Enable/disable TDD transmission/reception on a channel.

        See: http://www.voip-info.org/wiki/view/tdd+mode

        :rtype: int
        :returns: 1 if successful, or 0 if channel is not TDD-capable.
        """
        res = self.execute('TDD MODE', mode)['result'][0]
        if res == '0':
            raise AGIAppError('Channel %s is not TDD-capable')

    def goto_on_exit(self, context='', extension='', priority=''):
        context = context or self.env['agi_context']
        extension = extension or self.env['agi_extension']
        priority = priority or self.env['agi_priority']
        self.set_context(context)
        self.set_extension(extension)
        self.set_priority(priority)

    def verbose(self, message, level=1):
        """Sends message to the console via verbose message system. level is
        the verbose level (1-4).

        See: http://www.voip-info.org/wiki/view/verbose
        """
        self.execute('VERBOSE', self._quote(message), level)

    def wait_for_digit(self, timeout=DEFAULT_TIMEOUT):
        """Waits up to timeout milliseconds for channel to receive a DTMF
        digit.

        See: http://www.voip-info.org/wiki/view/wait+for+digit

        :rtype: chr
        :returns: -1 on channel failure, 0 if no digit is received in the
            timeout, or the numerical value of the ASCII of the digit if one is
            received. Use -1 for the timeout value if you desire the call to
            block indefinitely.
        """
        res = self.execute('WAIT FOR DIGIT', timeout)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except ValueError:
                raise AGIError('Unable to convert result to digit: %s' % res)
