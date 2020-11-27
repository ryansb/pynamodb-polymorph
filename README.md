# PynamoDB Polymorph

This package has utilities that are useful when using PynamoDB with a
single-table (polymorphic) design and overloading Global Secondary Indexes.

Take for example a Publisher class that needs to use a compound key of their
type prefix and their name. If you rely on callers doing the copy in code
there is possibility for them to update the name without also updating the
GSI sort key that contains the name. The `CompoundTemplateAttribute` uses
`string.Template` templating to fill unicode or numeric attributes into a
string template to build keys automatically.

```python
class Publisher(Base, discriminator="Publisher"):
    name = UnicodeAttribute()
    description = UnicodeAttribute(default="")
    gsi1_pk = CopiedDiscriminatorAttribute(source="cls")
    gsi1_sk = CompoundTemplateAttribute(
        template="PUBLISHER#$name",
        attrs=["name"],
    )
```

The template above will take any value in `name` and fill it in to the
template, so `name="Random Book Publishing House"` will become a
`gsi1_sk="PUBLISHER#Random Book Publishing House"`.