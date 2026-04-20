from marshmallow import Schema, fields, validate, validates, ValidationError, pre_load


ANNOTATION_TYPES = ["bbox", "polygon", "point", "polyline", "classification", "segmentation_mask"]
ANNOTATION_STATUSES = ["pending", "approved", "rejected", "needs_review"]


class GeometrySchema(Schema):
    type = fields.Str(required=True)
    coordinates = fields.Raw()
    rle = fields.Raw()  # Run-length encoding for masks
    bitmap = fields.Raw()  # Raw bitmap for masks


class AnnotationCreateSchema(Schema):
    annotation_type = fields.Str(
        required=True,
        validate=validate.OneOf(ANNOTATION_TYPES)
    )
    label = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    label_id = fields.Str(load_default=None)
    confidence = fields.Float(load_default=1.0, validate=validate.Range(min=0.0, max=1.0))
    geometry = fields.Dict(required=True)
    attributes = fields.Dict(load_default={})
    band_specific = fields.Bool(load_default=False)
    band_index = fields.Int(load_default=None)
    time_step = fields.Int(load_default=None)

    @validates("geometry")
    def validate_geometry(self, value):
        if not isinstance(value, dict):
            raise ValidationError("Geometry must be a JSON object")
        if "type" not in value:
            raise ValidationError("Geometry must have a 'type' field")


class AnnotationUpdateSchema(Schema):
    label = fields.Str(validate=validate.Length(min=1, max=200))
    confidence = fields.Float(validate=validate.Range(min=0.0, max=1.0))
    geometry = fields.Dict()
    attributes = fields.Dict()
    status = fields.Str(validate=validate.OneOf(ANNOTATION_STATUSES))
    review_comment = fields.Str()


class AnnotationBulkCreateSchema(Schema):
    annotations = fields.List(fields.Nested(AnnotationCreateSchema), required=True)


class AnnotationQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=50, validate=validate.Range(min=1, max=200))
    label = fields.Str()
    annotation_type = fields.Str(validate=validate.OneOf(ANNOTATION_TYPES))
    status = fields.Str(validate=validate.OneOf(ANNOTATION_STATUSES))
    is_ai_generated = fields.Bool()
    user_id = fields.Int()
