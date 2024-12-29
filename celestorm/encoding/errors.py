from celestorm.errors import ExecutionError


class EncodingError(ExecutionError):
    """ Common encoding error. """


class SerializeError(EncodingError):
    """ Raises when serialization fails. """


class DeserializeError(EncodingError):
    """ Raises when deserialization fails. """


class VerifyError(EncodingError):
    """ Raises when instruction package verification failed. """
