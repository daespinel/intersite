# coding: utf-8

"""
    Swagger REST Article

    This is the swagger file that goes with our server code  # noqa: E501

    OpenAPI spec version: 1.0.0
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""


import pprint
import re  # noqa: F401

import six


class Service(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'type': 'str',
        'name': 'str',
        'resources': 'list[str]'
    }

    attribute_map = {
        'type': 'type',
        'name': 'name',
        'resources': 'resources'
    }

    def __init__(self, type=None, name=None, resources=None):  # noqa: E501
        """Service - a model defined in Swagger"""  # noqa: E501

        self._type = None
        self._name = None
        self._resources = None
        self.discriminator = None

        if type is not None:
            self.type = type
        if name is not None:
            self.name = name
        if resources is not None:
            self.resources = resources

    @property
    def type(self):
        """Gets the type of this Service.  # noqa: E501

        Type of inter-site service  # noqa: E501

        :return: The type of this Service.  # noqa: E501
        :rtype: str
        """
        return self._type

    @type.setter
    def type(self, type):
        """Sets the type of this Service.

        Type of inter-site service  # noqa: E501

        :param type: The type of this Service.  # noqa: E501
        :type: str
        """

        self._type = type

    @property
    def name(self):
        """Gets the name of this Service.  # noqa: E501

        Name of the inter-site service  # noqa: E501

        :return: The name of this Service.  # noqa: E501
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """Sets the name of this Service.

        Name of the inter-site service  # noqa: E501

        :param name: The name of this Service.  # noqa: E501
        :type: str
        """

        self._name = name

    @property
    def resources(self):
        """Gets the resources of this Service.  # noqa: E501


        :return: The resources of this Service.  # noqa: E501
        :rtype: list[str]
        """
        return self._resources

    @resources.setter
    def resources(self, resources):
        """Sets the resources of this Service.


        :param resources: The resources of this Service.  # noqa: E501
        :type: list[str]
        """

        self._resources = resources

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(Service, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, Service):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other