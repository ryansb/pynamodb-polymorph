import zlib

from pynamodb.attributes import Attribute
from pynamodb.constants import BINARY


class CompressedAttribute(Attribute[bytes]):
    """
    A zlib-compressed binary attribute
    """

    attr_type = BINARY

    def serialize(self, value):
        """
        Returns the compressed binary of the value
        """
        return zlib.compress(value)

    def deserialize(self, value):
        """
        Returns a decoded byte string from a base64 encoded value
        """
        return zlib.decompress(value)
