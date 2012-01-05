class AGIException(Exception): pass
class AGIError(AGIException): pass

class AGIUnknownError(AGIError): pass

class AGIAppError(AGIError): pass

# there are several different types of hangups we can detect
# they all are derrived from AGIHangup
class AGIHangup(AGIAppError): pass
class AGISIGHUPHangup(AGIHangup): pass
class AGISIGPIPEHangup(AGIHangup): pass
class AGIResultHangup(AGIHangup): pass

class AGIDBError(AGIAppError): pass

class AGIUsageError(AGIError): pass
class AGIInvalidCommand(AGIError): pass
