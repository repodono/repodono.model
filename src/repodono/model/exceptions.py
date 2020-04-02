class ExecutionError(Exception):
    """
    Used to indicate a generic execution error.
    """


class ExecutionRejectError(ExecutionError):
    """
    This exception may be raised when an execution was rejected.
    """


class ExecutionNoResultError(ExecutionError, TypeError):
    """
    This exception should be raised when execution results in no valid
    result.  It should also be raised when non typed None result is
    returned.
    """


class ExecutionTimeoutError(ExecutionError):
    """
    This exception may be raised to indicate that an execution has ran
    out of time (or otherwise timed out).
    """
