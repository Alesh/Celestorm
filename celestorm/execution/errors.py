class ExecutionError(Exception):
    """ An error during instruction execution. """


class FinalizationError(Exception):
    """ A critical error during finalization. """


class SynchronizationError(Exception):
    """ A critical error during synchronization. """
