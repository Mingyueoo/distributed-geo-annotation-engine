from marshmallow import Schema, fields, validate, validates, ValidationError


class LabelClassSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    color = fields.Str(load_default="#FF0000")
    description = fields.Str(load_default="")
    attributes = fields.List(fields.Dict(), load_default=[])


class LabelSchemaSchema(Schema):
    classes = fields.List(fields.Nested(LabelClassSchema), required=True)
    annotation_types = fields.List(
        fields.Str(validate=validate.OneOf([
            "bbox", "polygon", "point", "polyline",
            "classification", "segmentation_mask"
        ])),
        load_default=["bbox"]
    )
    allow_multiple_labels = fields.Bool(load_default=False)


class DatasetCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(load_default="")
    data_type = fields.Str(
        validate=validate.OneOf([
            "sentinel_optical", "sentinel_sar", "sentinel_radar",
            "climate_simulation", "dem", "multispectral", "hyperspectral", "other"
        ]),
        load_default="other"
    )
    label_schema = fields.Nested(LabelSchemaSchema, load_default=None)
    metadata = fields.Dict(load_default={})


class DatasetUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=200))
    description = fields.Str()
    status = fields.Str(validate=validate.OneOf(["active", "archived", "completed"]))
    label_schema = fields.Nested(LabelSchemaSchema)
    metadata = fields.Dict()


class DatasetQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    data_type = fields.Str()
    status = fields.Str()
    search = fields.Str()
