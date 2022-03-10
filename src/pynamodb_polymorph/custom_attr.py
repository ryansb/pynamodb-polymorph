import typing as t
from datetime import datetime, timezone
from string import Template

import urllib.parse
import ulid
from pynamodb.attributes import NumberAttribute, UnicodeAttribute


class CompoundTemplateAttribute(UnicodeAttribute):
    """Creates a compound STRING attribute out of multiple other attributes from the same model.

    template: A string.Template or a str formatted as a string.Template
    attrs: A list of attribute names to be used in the template string
    """

    def __init__(
        self,
        *args,
        template: t.Union[Template, str],
        attrs: t.List[str],
        **kwargs,
    ):
        self.attrs = attrs
        self.template = (
            template if isinstance(template, Template) else Template(template)
        )
        super().__init__(*args, **kwargs)

    def __get__(self, obj, type_):
        if not obj:
            return self
        return self.template.substitute(
            {x: getattr(obj, x) for x in self.attrs},
        )


class JoinedUnicodeAttribute(UnicodeAttribute):
    """Compound STRING attribute built by joining attributes `attrs` with a chosen separator `sep`.

    `JoinedAttribute(attrs=['org_id', 'user_id'], sep='|') # makes the key `123|456` for org_id=123,user_id=456`

    attrs: A list of attribute names to be used in the key. Either `List[str]` or a comma-separated list of attributes
    sep: A non-empty string to join together
    """

    def __init__(
        self,
        *args,
        attrs: t.Union[str, t.List[str]],
        sep: str = "#",
        **kwargs,
    ):

        self.attrs = (
            tuple(attrs)
            if isinstance(attrs, (list, tuple, set))
            else tuple(i.strip() for i in attrs.split(","))
        )
        self.sep = sep
        super().__init__(*args, **kwargs)

    def __get__(self, obj, type_):
        if obj is None:
            return self
        return self.sep.join(str(getattr(obj, x)) for x in self.attrs)


class EscapedJoinedUnicodeAttribute(JoinedUnicodeAttribute):
    """Compound escaped STRING attribute built by joining attributes `attrs` with a chosen separator `sep`.

    When using user defined input as part of a compound key, this attribute will automatically url encode all or a
    subset of the attributes that make up the compound key.

    `EscapedJoinedAttribute(attrs=['input_email', 'alias'], sep='|', escaped='input_email') # makes the key `helloworld%40example.com|m@pper` for input_email=helloworld@example.com,alias=m@pper`
    `EscapedJoinedAttribute(attrs=['input_email', 'alias'], sep='|') # makes the key `helloworld%40example.com|m%40pper` for input_email=helloworld@example.com,alias=m@pper

    attrs: A list of attribute names to be used in the key. Either `List[str]` or a comma-separated list of attributes
    sep: A non-empty string to join together
    escaped: A list of attribute names to be escaped in the key. Either `List[str]` or a comma-separated list of attributes.
            If no attributes are supplied, all attributes are escaped
    """

    def __init__(
        self,
        *args,
        attrs: t.Union[str, t.List[str]],
        sep: str = "#",
        escaped: t.Optional[t.Union[str, t.List[str]]] = None,
        **kwargs,
    ):
        self.escaped = None
        if escaped:
            self.escaped = (
                tuple(escaped)
                if isinstance(escaped, (list, tuple, set))
                else tuple(i.strip() for i in escaped.split(","))
            )
        super().__init__(*args, attrs=attrs, sep=sep, **kwargs)

    def __get__(self, obj, type_):
        def escape_string(attr, value):
            if not self.escaped or attr in self.escaped:
                return urllib.parse.quote(value)
            return value

        if obj is None:
            return self
        return self.sep.join(escape_string(x, str(getattr(obj, x))) for x in self.attrs)


class ULIDAttribute(UnicodeAttribute):
    """Similar to a UUID, but includes a lexically sortable timestamp.

    Great for use as a range/sort key for time-related items."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, default_for_new=ulid.new, **kwargs)

    def serialize(self, value):
        return value.str

    def deserialize(self, value):
        return ulid.from_str(value)


class IsoDateTime(UnicodeAttribute):
    """ISO-formatted datetime attribute stored with TZ offset. Lexically sortable, defaults to UTC timezone"""

    def serialize(self, value):
        return value.isoformat()

    def deserialize(self, value):
        return datetime.fromisoformat(value)


class UpdatedIsoDateTime(IsoDateTime):
    """Always updates to the latest UTC datetime on write.

    Otherwise this has the same format and usage as IsoDateTime, but is useful
    for updated_at attributes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            # Typing override because our parent class already has a serde for datetime -> str
            default=t.cast(t.Callable[[], str], lambda: datetime.now(tz=timezone.utc)),
            **kwargs,
        )


class SetSizeAttribute(NumberAttribute):
    def __init__(
        self,
        *args,
        source: str,
        **kwargs,
    ):
        self.source = source
        super().__init__(*args, **kwargs)

    def __get__(self, obj, type_):
        return len(getattr(obj, self.source))


def copied_attr_factory(attr_type):
    """Create a new attribute type that mirrors the value of another property.

    Takes any primitive PynamoDB attribute (binary, string, numeric, etc) and copies it under a new name."""

    class CopiedAttribute(attr_type):
        def __init__(
            self,
            *args,
            source: str,
            **kwargs,
        ):
            self.source = source
            super().__init__(*args, **kwargs)

        def __get__(self, obj, type_):
            if obj is None:
                return self
            return getattr(obj, self.source)

    CopiedAttribute.__doc__ = f"""A copy of a {attr_type.__name__}.

    Cannot be set directly and always reads from the supplied `source` property."""
    return CopiedAttribute


class CopiedIntegerAttribute(copied_attr_factory(NumberAttribute)):
    """Copies any attribute that can be coerced to `int`.

    Always coerces values to integer at serialize/deserialize time
    """

    def serialize(self, value):
        return super().serialize(int(value))

    def deserialize(self, value):
        return int(super().deserialize(value))


class CopiedDiscriminatorAttribute(copied_attr_factory(UnicodeAttribute)):
    """Special case of CopiedUnicodeAttribute to cover discriminators"""

    def serialize(self, value):
        if disc := getattr(value, value._discriminator, None):
            return disc._class_map[value]
        return None


CopiedUnicodeAttribute = copied_attr_factory(UnicodeAttribute)
CopiedNumberAttribute = copied_attr_factory(NumberAttribute)
CopiedULIDAttribute = copied_attr_factory(ULIDAttribute)
