class EncodingError(Exception):
    """ A general encoding error. """


class SerializeError(EncodingError):
    """ An error during instruction serialization into a package. """


class DeserializeError(EncodingError):
    """ An error during instruction package deserialization. """


class SignError(EncodingError):
    """ An error during an unsuccessful attempt to sign the instruction package. """


class VerifyError(EncodingError):
    """ An error due to a violation of the instruction package's integrity. """
