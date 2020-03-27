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
    parameter_lmaster = db.relationship(
        'LMaster',
        backref='parameter',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(LMaster.lmaster_id)'
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

class LMaster(db.Model):
    __tablename__ = "lmaster"
    lmaster_id  = db.Column(db.Integer,
                                  primary_key=True)
    lmaster_l2allocationpools = db.relationship(
        'L2AllocationPool',
        backref='lmaster',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(L2AllocationPool.l2allocationpool_id)'
    )
    lmaster_l3cidrs = db.relationship(
        'L3Cidrs',
        backref='lmaster',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(L3Cidrs.l3cidrs_id)'
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
    lmaster_id = db.Column(
        db.Integer, db.ForeignKey('lmaster.lmaster_id'))

    def get_string_allocation_pool(self):
        answer = self.l2allocationpool_first_ip + "-" + self.l2allocationpool_last_ip
        return answer

class L3Cidrs(db.Model):
    __tablename__ = "l3cidrs"
    l3cidrs_id = db.Column(db.Integer,
                                    primary_key=True)
    l3cidrs_cidr = db.Column(db.String(64))
    l3cidrs_site = db.Column(db.String(64))
    lmaster_id = db.Column(
        db.Integer, db.ForeignKey('lmaster.lmaster_id'))

    def get_string_cidr(self):
        answer = self.l3cidrs_cidr
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
    parameter_lmaster = fields.Nested(
        'SLMasterSchema', default=[], many=True)


class ParamsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = Parameter
        sqla_session = db.session
    service = fields.Nested('ParamsServiceSchema', default=None)
    parameter_lmaster = fields.Nested('SLMasterSchema', default=[], many=False)

class ParamsServiceSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    service_id = fields.Int()
    #service_name = fields.Str()
    #service_type = fields.Str()
    #service_global = fields.Str()

class SLMasterSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    lmaster_id  = fields.Int()
    parameter_id = fields.Int()
    lmaster_l2allocationpools = fields.Nested(
        'SL2AllocationPoolSchema', default=[], many=True)
    lmaster_l3cidrs = fields.Nested(
        'SL3CidrsSchema', default=[], many=True)

class LMasterParamsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    parameter_id = fields.Int()
    service_id = fields.Int()

class LMasterSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = LMaster
        sqla_session = db.session
    params = fields.Nested('LMasterParamsSchema', default=None)
    lmaster_l2allocationpools = fields.Nested(
        'SL2AllocationPoolSchema', default=[], many=True)
    lmaster_l3cidrs = fields.Nested(
        'SL3CidrsSchema', default=[], many=True)

class SL2AllocationPoolSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    l2allocationpool_id = fields.Int()
    l2allocationpool_first_ip = fields.String()
    l2allocationpool_last_ip = fields.String()
    l2allocationpool_site = fields.String()
    lmaster_id = fields.Int()

class L2AllocationPoolSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = L2AllocationPool
        sqla_session = db.session
    lmaster = fields.Nested('L2AllocationPoolLMasterSchema', default=None)

class L2AllocationPoolLMasterSchema(ma.ModelSchema):
    parameter_id = fields.Int()
    lmaster_id = fields.Int()

class SL3CidrsSchema(ma.ModelSchema):
    """
    This class exists to get around a recursion issue
    """
    l3cidrs_id = fields.Int()
    l3cidrs_site = fields.String()
    l3cidrs_cidr = fields.String()
    lmaster_id = fields.Int()

class L3CidrsSchema(ma.ModelSchema):
    def __init__(self, **kwargs):
        super().__init__(strict=True, **kwargs)

    class Meta:
        model = L3Cidrs
        sqla_session = db.session
    lmaster = fields.Nested('L3CidrsLMasterSchema', default=None)

class L3CidrsLMasterSchema(ma.ModelSchema):
    parameter_id = fields.Int()
    lmaster_id = fields.Int()

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


