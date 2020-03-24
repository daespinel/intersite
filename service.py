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
    parameter_local_resource = db.Column(db.String(64))
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
    resource_cidr = db.Column(db.String(64))
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id'))


class Interconnexion(db.Model):
    __tablename__ = "interconnexion"
    interconnexion_id = db.Column(db.Integer,
                                  primary_key=True)
    interconnexion_uuid = db.Column(db.String(64))
    service_id = db.Column(db.Integer, db.ForeignKey('service.service_id'))
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.resource_id'))
    resource = db.relationship('Resource')

class L2Master(db.Model):
    __tablename__ = "l2master"
    l2master_id  = db.Column(db.Integer,
                                  primary_key=True)
    l2master_l2allocationpools = db.relationship(
        'L2AllocationPool',
        backref='l2master',
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

    def get_string_allocation_pool(self):
        answer = self.l2allocationpool_first_ip + "-" + self.l2allocationpool_last_ip
        return answer


# Service schemas for model read and write
# Service associated schema
class ServiceSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Service
        sqla_session = db.session
    service_params = fields.Nested(
        'SParamsSchema', default=[], many=True)
    service_resources = fields.Nested(
        'SResourcesSchema', default=[], many=True)
    service_interconnections = fields.Nested(
        'SInterconnectionsSchema', default=[], many=True)

# Parameter associated schemas
class SParamsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    parameter_id = fields.Int()
    service_id = fields.Int()
    parameter_allocation_pool = fields.Str()
    parameter_local_cidr = fields.Str()
    parameter_local_resource = fields.Str()
    parameter_ipv = fields.Str()
    parameter_master = fields.Str()
    parameter_master_auth = fields.Str()
    parameter_l2master = fields.Nested(
        'SL2MasterSchema', default=[], many=True)


class ParamsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Parameter
        sqla_session = db.session
    service = fields.Nested('ParamsServiceSchema', default=None)
    parameter_l2master = fields.Nested('SL2MasterSchema', default=[], many=False)

class ParamsServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    #service_name = fields.Str()
    #service_type = fields.Str()
    #service_global = fields.Str()

class SL2MasterSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    l2master_id  = fields.Int()
    parameter_id = fields.Int()
    l2master_l2allocationpools = fields.Nested(
        'SL2AllocationPoolSchema', default=[], many=True)

class L2MasterParamsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    parameter_id = fields.Int()
    service_id = fields.Int()

class L2MasterSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = L2Master
        sqla_session = db.session
    params = fields.Nested('L2MasterParamsSchema', default=None)
    l2master_l2allocationpools = fields.Nested(
        'SL2AllocationPoolSchema', default=[], many=True)

class SL2AllocationPoolSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    l2allocationpool_id = fields.Int()
    l2allocationpool_first_ip = fields.String()
    l2allocationpool_last_ip = fields.String()
    l2allocationpool_site = fields.String()
    l2master_id = fields.Int()

class L2AllocationPoolSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = L2AllocationPool
        sqla_session = db.session
    l2master = fields.Nested('L2AllocationPoolL2MasterSchema', default=None)

class L2AllocationPoolL2MasterSchema(ma.ModelSchema):
    parameter_id = fields.Int()
    l2master_id = fields.Int()

# Resources associated schemas
class SResourcesSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    resource_id = fields.Int()
    service_id = fields.Int()
    resource_region = fields.Str()
    resource_uuid = fields.Str()
    resource_cidr = fields.Str()


class ResourcesSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Resource
        sqla_session = db.session
    service = fields.Nested('ResourcesServiceSchema', default=None)


class ResourcesServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    #service_name = fields.Str()
    #service_type = fields.Str()
    #service_global = fields.Str()

# Interconnection associated schemas
class SInterconnectionsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    interconnexion_id = fields.Int()
    service_id = fields.Int()
    resource_id = fields.Int()
    interconnexion_uuid = fields.Str()


class InterconnectionsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Interconnexion
        sqla_session = db.session
    service = fields.Nested(
        'InterconnectionsServiceSchema', default=None)


class InterconnectionsServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    resource_id = fields.Int()
    #service_name = fields.Str()
    #service_type = fields.Str()
    #service_global = fields.Str()


