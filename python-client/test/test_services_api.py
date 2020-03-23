# coding: utf-8

"""
    Swagger REST Article

    This is the swagger file that goes with our server code  # noqa: E501

    OpenAPI spec version: 1.0.0
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""


from __future__ import absolute_import

import unittest

import swagger_client
from swagger_client.api.services_api import ServicesApi  # noqa: E501
from swagger_client.rest import ApiException


class TestServicesApi(unittest.TestCase):
    """ServicesApi unit test stubs"""

    def setUp(self):
        self.api = swagger_client.api.services_api.ServicesApi()  # noqa: E501

    def tearDown(self):
        pass

    def test_vertical_create_service(self):
        """Test case for vertical_create_service

        Creates an inter-site Service POST  # noqa: E501
        """
        pass

    def test_vertical_delete_service(self):
        """Test case for vertical_delete_service

        Deletes an inter-site Service DELETE  # noqa: E501
        """
        pass

    def test_vertical_read_all_service(self):
        """Test case for vertical_read_all_service

        the inter-site Service mapping structure GET  # noqa: E501
        """
        pass

    def test_vertical_read_one_service(self):
        """Test case for vertical_read_one_service

        Read one inter-site Service GET  # noqa: E501
        """
        pass

    def test_vertical_update_service(self):
        """Test case for vertical_update_service

        Update an already deployed service  # noqa: E501
        """
        pass


if __name__ == '__main__':
    unittest.main()