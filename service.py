from config import db, ma
import json
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow import fields


class Service(db.Model):
    __tablename__ = 'service'
    service_id = db.Column(db.Integer,
                           primary_key=True)
    service_name = db.Column(db.String(32))
    service_type = db.Column(db.String(32))
    service_global = db.Column(db.String(64))
    service_params = db.Column(db.String(64))
    service_resources = db.relationship(
        'Resource',
        backref='service',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(Resource.resource_id)'
    )
    service_interconnections = db.relationship(
        'Interconnexion',
        backref='service',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(Interconnexion.interconnexion_id)'
    )


class Resource(db.Model):
    __tablename__ = "resource"
    resource_id = db.Column(db.Integer,
                            primary_key=True)
    resource_region = db.Column(db.String(64))
    resource_uuid = db.Column(db.String(64))
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id'))


class Interconnexion(db.Model):
    __tablename__ = "interconnexion"
    interconnexion_id = db.Column(db.Integer,
                                  primary_key=True)
    interconnexion_uuid = db.Column(db.String(64))
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id'))


class ServiceSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Service
        sqla_session = db.session
    service_resources = fields.Nested(
        'SServiceResourcesSchema', default=[], many=True)
    service_interconnections = fields.Nested(
        'SServiceInterconnectionsSchema', default=[], many=True)


class SServiceResourcesSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    resource_id = fields.Int()
    service_id = fields.Int()
    resource_region = fields.Str()
    resource_uuid = fields.Str()


class ServiceResourcesSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Resource
        sqla_session = db.session
    service = fields.Nested('ServiceResourcesServiceSchema', default=None)


class ServiceResourcesServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    service_name = fields.Str()
    service_type = fields.Str()
    service_global = fields.Str()
    service_params = fields.Str()


class SServiceInterconnectionsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    interconnexion_id = fields.Int()
    service_id = fields.Int()
    interconnexion_uuid = fields.Str()


class ServiceInterconnectionsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Interconnexion
        sqla_session = db.session
    service = fields.Nested(
        'ServiceInterconnectionsServiceSchema', default=None)


class ServiceInterconnectionsServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    service_name = fields.Str()
    service_type = fields.Str()
    service_global = fields.Str()
    service_params = fields.Str()
