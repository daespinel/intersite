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
    service_params = db.relationship(
        'Parameter',
        backref='service',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(Parameter.parameter_id)'
    )
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


class Parameter(db.Model):
    __tablename__ = "parameter"
    parameter_id = db.Column(db.Integer,
                             primary_key=True)
    parameter_allocation_pool = db.Column(db.String(64))
    parameter_local_cidr = db.Column(db.String(64))
    parameter_ipv = db.Column(db.String(64))
    parameter_master = db.Column(db.String(64))
    parameter_master_auth = db.Column(db.String(64))
    parameter_l2master = db.relationship(
        'L2Master',
        backref='parameter',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(L2Master.l2master_id)'
    )
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id'))


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


class L2Master(db.Model):
    __tablename__ = "l2master"
    l2master_id  = db.Column(db.Integer,
                                  primary_key=True)
    l2master_l2allocationpools = db.relationship(
        'L2AllocationPool',
        backref='L2Master',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(L2AllocationPool.l2allocationpool_id)'
    )
    parameter_id = db.Column(
        db.Integer, db.ForeignKey('parameter.parameter_id'))


class L2AllocationPool(db.Model):
    __tablename__ = "l2allocationpool"
    l2allocationpool_id = db.Column(db.Integer,
                                    primary_key=True)
    l2allocationpool_first_ip = db.Column(db.String(64))
    l2allocationpool_last_ip = db.Column(db.String(64))
    l2allocationpool_site = db.Column(db.String(64))
    l2master_id = db.Column(
        db.Integer, db.ForeignKey('l2master.l2master_id'))


# Service schemas for model read and write

class ServiceSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Service
        sqla_session = db.session
    service_params = fields.Nested(
        'SServiceParamsSchema', default=[], many=False)
    service_resources = fields.Nested(
        'SServiceResourcesSchema', default=[], many=True)
    service_interconnections = fields.Nested(
        'SServiceInterconnectionsSchema', default=[], many=True)


class SServiceParamsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    parameter_id = fields.Int()
    service_id = fields.Int()
    parameter_allocation_pool = fields.Str()
    parameter_local_cidr = fields.Str()
    parameter_ipv = fields.Str()
    parameter_master = fields.Str()
    parameter_master_auth = fields.Str()
    parameter_l2master = fields.Nested(
        'SParamsL2MasterSchema', default=[], many=False)


class ServiceParamsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Parameter
        sqla_session = db.session
    service = fields.Nested('ServiceParamsServiceSchema', default=None)


class ServiceParamsServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    service_name = fields.Str()
    service_type = fields.Str()
    service_global = fields.Str()


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


