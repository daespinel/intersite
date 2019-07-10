from config import db, ma
import json
from sqlalchemy.ext.hybrid import hybrid_property


class Service(db.Model):
    __tablename__ = 'service'
    service_id = db.Column(db.Integer,
                           primary_key=True)
    service_name = db.Column(db.String(32))
    service_type = db.Column(db.String(32))
    _service_resources = db.Column(
        'service_resources', db.String(600), default='',  server_default='')
    _service_interconnections = db.Column(
        'service_interconnections', db.String(600), default='',  server_default='')

    @property
    def service_resources(self):
        return [x for x in self._service_resources.split(';')]

    @service_resources.setter
    def service_resources(self, value):
        text = ''
        for element in value:
            text = text + str(element) + ';'
        self._service_resources = text

    @property
    def service_interconnections(self):
        #return [x for x in self._service_interconnections.split(';')]
        return 'joder'

    @service_interconnections.setter
    def service_interconnections(self, value):
        text = ''
        for element in value:
            text = text + str(element) + ';'
        self._service_interconnections = text


class ServiceSchema(ma.ModelSchema):
    class Meta:
        model = Service
        sqla_session = db.session
