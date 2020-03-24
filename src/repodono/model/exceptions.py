class ExecutionNoResultError(TypeError):
    """
    This exception should be raised when execution results in no valid
    result.  It should also be raised when non typed None result is
    returned.
    """
