class ExecutionError(Exception):
    """ Non-critical execution error. """


class ExecutionCritical(Exception):
    """ Critical execution error. """
