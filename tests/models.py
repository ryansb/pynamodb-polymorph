from datetime import datetime
from typing import Optional

from pynamodb.attributes import (
    DiscriminatorAttribute,
    NumberAttribute,
    TTLAttribute,
    UnicodeAttribute,
    UnicodeSetAttribute,
)
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex
from pynamodb.models import Model

from pynamodb_polymorph import (
    CompoundTemplateAttribute,
    CopiedDiscriminatorAttribute,
    CopiedIntegerAttribute,
    CopiedULIDAttribute,
    CopiedUnicodeAttribute,
    SetSizeAttribute,
    ULIDAttribute,
)


class GSI1(GlobalSecondaryIndex):
    class Meta:
        index_name = "gsi1"
        projection = AllProjection()
        billing_mode = "PAY_PER_REQUEST"

    gsi1_pk = UnicodeAttribute(hash_key=True)
    gsi1_sk = UnicodeAttribute(range_key=True)


class GSI2(GlobalSecondaryIndex):
    class Meta:
        index_name = "gsi2"
        projection = AllProjection()
        billing_mode = "PAY_PER_REQUEST"

    gsi2_pk = UnicodeAttribute(hash_key=True)
    gsi2_sk = NumberAttribute(range_key=True)


class Base(Model):
    class Meta:
        table_name = "appstore"
        region = "us-west-2"
        billing_mode = "PAY_PER_REQUEST"

    pk = CompoundTemplateAttribute(
        hash_key=True,
        template="$type_#$ulid",
        attrs=["type_", "ulid"],
    )
    ulid = ULIDAttribute()
    cls = DiscriminatorAttribute(attr_name="__type")
    ttl = TTLAttribute(null=True)
    gsi1 = GSI1()
    gsi2 = GSI2()

    @property
    def type_(self):
        return self.__class__.__name__.upper()

    @property
    def created_at(self) -> Optional[datetime]:
        """Based on a ULID `pk`, extract an aware datetime"""
        if ts := getattr(self.pk, "timestamp", None):
            return ts().datetime
        if ts := getattr(self.ulid, "timestamp", None):
            return ts().datetime


class FooModel(Base, discriminator="Foo"):
    foo = UnicodeAttribute()
    gsi1_pk = UnicodeAttribute(default="FOO")
    gsi1_sk = CopiedUnicodeAttribute(source="foo")


class BarModel(Base, discriminator="Bar"):
    compound = CompoundTemplateAttribute(
        template="BAR#$pk#$bar",
        attrs=["pk", "bar"],
    )
    pk = UnicodeAttribute()
    bar = UnicodeAttribute()


class Publisher(Base, discriminator="Publisher"):
    name = UnicodeAttribute()
    description = UnicodeAttribute(default="")
    gsi1_pk = CopiedDiscriminatorAttribute(source="cls")
    gsi1_sk = CompoundTemplateAttribute(
        template="PUBLISHER#$name",
        attrs=["name"],
    )


class Review(Base, discriminator="Review"):
    app = UnicodeAttribute()
    reviewer_email = UnicodeAttribute()
    reviewer_name = UnicodeAttribute()
    stars = NumberAttribute()
    gsi1_pk = CompoundTemplateAttribute(
        template="REVIEW#$reviewer_email",
        attrs=["reviewer_email"],
    )
    gsi1_sk = CopiedUnicodeAttribute(source="app")
    gsi2_pk = CompoundTemplateAttribute(
        template="REVIEW#$app",
        attrs=["app"],
    )
    gsi2_sk = CopiedIntegerAttribute(source="ulid")


class App(Base, discriminator="App"):
    pk = CopiedUnicodeAttribute(source="uri")
    title = UnicodeAttribute()
    publisher = UnicodeAttribute()
    uri = UnicodeAttribute()
    downloads = NumberAttribute(default_for_new=0)
    gsi1_pk = CopiedUnicodeAttribute(source="publisher")
    gsi1_sk = CopiedULIDAttribute(source="ulid")


class Order(Base, discriminator="Order"):
    email = UnicodeAttribute()
    items = UnicodeSetAttribute()
    size = SetSizeAttribute(source="items")
    gsi1_pk = CompoundTemplateAttribute(
        template="ORDER#$email",
        attrs=["email"],
    )
    gsi1_sk = CopiedULIDAttribute(source="ulid")
    gsi2_pk = CompoundTemplateAttribute(
        template="BYSIZE#$size",
        attrs=["size"],
    )
    gsi2_sk = CopiedIntegerAttribute(source="ulid")
