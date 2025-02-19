from celestorm.encoding.errors import SignError
from .instruction import Instruction, OID

try:
    from nacl.exceptions import BadSignatureError
    from nacl.signing import SigningKey, VerifyKey

    from .package import Package as PurePackage

    SIGNING_SUPPORTED = True


    # Add sign/verify to the instruction package

    class Package(PurePackage):

        def sign(self, key: SigningKey) -> 'Package':
            """ Sings package """
            if not self.digest:
                raise SignError("Digest not specified; cannot sign")
            if self.signature:
                raise SignError("Package already signed")
            signed = key.sign(self.digest)
            return Package((self[0] | 0b10000000).to_bytes() + self[1:] + signed.signature)

        def verify(self, key: VerifyKey) -> bool:
            """ Verifies sing of package """
            if not self.signature:
                raise SignError("Package isn't signed")
            try:
                key.verify(self.digest, self.signature)
                return True
            except BadSignatureError:
                return False

except ImportError:
    SIGNING_SUPPORTED = False

    from .package import Package
