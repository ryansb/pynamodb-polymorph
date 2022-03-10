import timeit
import urllib.parse
from datetime import datetime, timedelta, timezone
from textwrap import dedent

import pytest
import ulid
from faker import Faker

import models


def test_compound_key_from_discriminator():
    f = models.Publisher(name="RyanSB")
    as_record = f.serialize()
    assert as_record["gsi1_pk"]
    assert as_record["gsi1_pk"]["S"]
    assert as_record["gsi1_pk"]["S"] == "Publisher"
    assert as_record["gsi1_sk"]["S"] == "PUBLISHER#RyanSB"


def test_item_calculated():
    b = models.BarModel(pk="prim", bar="hello")
    record = b.serialize()
    print(record)
    assert record["bar"]["S"] == b.bar
    assert record["compound"]["S"] == b.compound
    assert record["compound"]["S"] == "BAR#prim#hello"
    b.deserialize(
        {
            "bar": {"S": "Buzz!"},
            "pk": {"S": "Fizz"},
            "compound": {"S": "Hello#World!"},
        }
    )
    assert "BAR#Fizz#Buzz!" == b.compound


def test_foo():
    f = models.FooModel(foo="hello")
    print(f.serialize())
    assert ulid.from_str(f.serialize()["ulid"]["S"])
    assert ulid.from_str(f.serialize()["pk"]["S"].split("#")[-1])
    assert f.serialize()["__type"]["S"] == "Foo"


def test_joined_attr():
    f = models.Review(
        app="Annoyed Birds",
        stars=5,
        reviewer_email="someone@test.com",
        reviewer_name="Some One",
    )
    print(f.serialize())
    assert ulid.from_str(f.serialize()["ulid"]["S"])
    assert ulid.from_str(f.serialize()["pk"]["S"].split("#")[-1])
    assert f.serialize()["__type"]["S"] == "Review"
    assert f.serialize()["gsi1_pk"]["S"] == "REVIEW#someone@test.com"


def test_escaped_joined_attr():
    invited_email = "helloworld@example.com"
    inviter_email = "other@example.com"

    f = models.UserInvite(inviter_email=inviter_email, invited_email=invited_email)
    print(f.serialize())
    assert (
        f.compound_all_escaped
        == f"USERINVITE#{urllib.parse.quote(invited_email)}#{urllib.parse.quote(inviter_email)}"
    )
    assert (
        f.compound_single_escaped
        == f"USERINVITE#{urllib.parse.quote(invited_email)}#{inviter_email}"
    )


def test_created_at():
    f = models.FooModel(foo="hello")
    now = datetime.now(tz=timezone.utc)
    assert timedelta(seconds=-1) < now - f.created_at < timedelta(seconds=1)


def test_date_formats():
    setup = dedent(
        """
        from datetime import datetime, timezone
        import pynamodb_polymorph
        from pynamodb.attributes import UTCDateTimeAttribute

        dt = UTCDateTimeAttribute()
        now = datetime.now(tz=timezone.utc)
        utc_now_fmt = UTCDateTimeAttribute().serialize(datetime.now(tz=timezone.utc))
        iso_dt = pynamodb_polymorph.IsoDateTime()
        iso_now_fmt = iso_dt.serialize(now)"""
    )
    RUNS = 10000
    pdb_serialize = timeit.timeit("dt.serialize(now)", setup=setup, number=RUNS)
    iso_serialize = timeit.timeit("iso_dt.serialize(now)", setup=setup, number=RUNS)
    pdb_deserialize = timeit.timeit(
        "dt.deserialize(utc_now_fmt)", setup=setup, number=RUNS
    )
    iso_deserialize = timeit.timeit(
        "iso_dt.deserialize(iso_now_fmt)", setup=setup, number=RUNS
    )
    print("Average per loop serialize", pdb_serialize / RUNS)
    print("Average per loop deserialize", pdb_deserialize / RUNS)
    print("Average per iso loop serialize", iso_serialize / RUNS)
    print("Average per iso loop deserialize", iso_deserialize / RUNS)

    assert (iso_serialize / RUNS) * 3 < (
        pdb_serialize / RUNS
    ), "our custom ISO-based serialization is at least 3x faster than pynamodb's UTCDateTime attribute"
    assert (iso_deserialize / RUNS) * 3 < (
        pdb_deserialize / RUNS
    ), "our custom ISO-based deserialization is at least 3x faster than pynamodb's UTCDateTime attribute"
