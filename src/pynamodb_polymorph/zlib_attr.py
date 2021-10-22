import base64
import zlib

from pynamodb.attributes import Attribute
from pynamodb.constants import BINARY


class CompressedAttribute(Attribute[bytes]):
    """
    A zlib-compressed binary attribute
    """

    attr_type = BINARY

    def serialize(self, value: str) -> str:
        """
        Returns the compressed binary of the value
        """
        return base64.b64encode(zlib.compress(value.encode("utf-8"))).decode("utf-8")

    def deserialize(self, value: bytes) -> str:
        """
        Returns a decoded byte string from a base64 encoded value
        """
        return zlib.decompress(base64.b64decode(value)).decode("utf-8")
