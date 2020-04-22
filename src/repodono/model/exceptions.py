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


class MappingReferenceError(Exception):
    """
    Used to indicate a reference error for a given resource.
    """

    # XXX this really should be KeyError, but because how the system
    # currently also leverages this in the mapping, it **can't** be so
    # as it would then be swallowed.
    #
    # The issue is that all the internal base Mapping classes will need
    # to be revalidated such that this version would correctly cascade
    # down to where it is needed.
