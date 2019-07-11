from config import db, ma
import json
from sqlalchemy.ext.hybrid import hybrid_property


class Service(db.Model):
    __tablename__ = 'service'
    service_id = db.Column(db.Integer,
                           primary_key=True)
    service_name = db.Column(db.String(32))
    service_type = db.Column(db.String(32))
    service_resources = db.relationship(
        'Resource',
        backref='service',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(Resource.id)'
    )
    service_interconnections = db.relationship(
        'Interconnexion',
        backref='service',
        cascade='all, delete, delete-orphan',
        single_parent=True,
        order_by='desc(Interconnexion.id)'
    )
    #_service_resources = db.Column(
    #    'service_resources', db.String(600), default='',  server_default='')
    #_service_interconnections = db.Column(
    #    'service_interconnections', db.String(600), default='',  server_default='')

    def __init__(self,name,typo,resources,interconnections):
        self.service_name = name
        self.service_type = typo
        self.set_service_resources(resources)
        self.set_service_interconnections(interconnections)

    #@property
    def get_service_resources(self):
        response = [x for x in self._service_resources.split(';')]
        return 'response'

    #@service_resources.setter
    def set_service_resources(self, value):
        text = ''
        for element in value:
            text = text + str(element) + ';'
        self._service_resources = text

    #@property
    def get_service_interconnections(self):
        #return [x for x in self._service_interconnections.split(';')]
        return self.service_name

    #@service_interconnections.setter
    def set_service_interconnections(self, value):
        text = ''
        for element in value:
            text = text + str(element) + ';'
        self._service_interconnections = text

class Resource(db.Model):
    __tablename__ = "resource"
    resource_id = db.Column(db.Integer,
                           primary_key=True)
    resource_region = db.Column(db.String(32))
    resource_uuid = db.Column(db.String(32))

class Interconnexion(db.Model):
    __tablename__ = "interconnexion"
    interconnexion_id = db.Column(db.Integer,
                           primary_key=True)
    interconnexion_uuid = db.Column(db.String(32))

class ServiceSchema(ma.ModelSchema):
    class Meta:
        model = Service
        sqla_session = db.session
