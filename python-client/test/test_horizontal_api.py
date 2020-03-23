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
from swagger_client.api.horizontal_api import HorizontalApi  # noqa: E501
from swagger_client.rest import ApiException


class TestHorizontalApi(unittest.TestCase):
    """HorizontalApi unit test stubs"""

    def setUp(self):
        self.api = swagger_client.api.horizontal_api.HorizontalApi()  # noqa: E501

    def tearDown(self):
        pass

    def test_horizontal_create_service(self):
        """Test case for horizontal_create_service

        Horizontal request to create an inter-site Service POST  # noqa: E501
        """
        pass

    def test_horizontal_delete_service(self):
        """Test case for horizontal_delete_service

        Deletes an inter-site Service DELETE  # noqa: E501
        """
        pass

    def test_horizontal_read_parameters(self):
        """Test case for horizontal_read_parameters

        Read the local cidr of an inter-site Service  # noqa: E501
        """
        pass

    def test_horizontal_update_service(self):
        """Test case for horizontal_update_service

        Update an already deployed service  # noqa: E501
        """
        pass


if __name__ == '__main__':
    unittest.main()