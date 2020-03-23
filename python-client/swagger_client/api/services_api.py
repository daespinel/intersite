# coding: utf-8

"""
    Swagger REST Article

    This is the swagger file that goes with our server code  # noqa: E501

    OpenAPI spec version: 1.0.0
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""


from __future__ import absolute_import

import re  # noqa: F401

# python 2 and python 3 compatibility library
import six

from swagger_client.api_client import ApiClient


class ServicesApi(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    Ref: https://github.com/swagger-api/swagger-codegen
    """

    def __init__(self, api_client=None):
        if api_client is None:
            api_client = ApiClient()
        self.api_client = api_client

    def vertical_create_service(self, service, **kwargs):  # noqa: E501
        """Creates an inter-site Service POST  # noqa: E501

        Create an inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_create_service(service, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param Service service: data for inter-service creation (required)
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.vertical_create_service_with_http_info(service, **kwargs)  # noqa: E501
        else:
            (data) = self.vertical_create_service_with_http_info(service, **kwargs)  # noqa: E501
            return data

    def vertical_create_service_with_http_info(self, service, **kwargs):  # noqa: E501
        """Creates an inter-site Service POST  # noqa: E501

        Create an inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_create_service_with_http_info(service, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param Service service: data for inter-service creation (required)
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['service']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method vertical_create_service" % key
                )
            params[key] = val
        del params['kwargs']
        # verify the required parameter 'service' is set
        if ('service' not in params or
                params['service'] is None):
            raise ValueError("Missing the required parameter `service` when calling `vertical_create_service`")  # noqa: E501

        collection_formats = {}

        path_params = {}

        query_params = []

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        if 'service' in params:
            body_params = params['service']
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.api_client.select_header_content_type(  # noqa: E501
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/intersite-vertical', 'POST',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='object',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def vertical_delete_service(self, global_id, **kwargs):  # noqa: E501
        """Deletes an inter-site Service DELETE  # noqa: E501

        Deletes an inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_delete_service(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: Id of the service to delete (required)
        :return: None
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.vertical_delete_service_with_http_info(global_id, **kwargs)  # noqa: E501
        else:
            (data) = self.vertical_delete_service_with_http_info(global_id, **kwargs)  # noqa: E501
            return data

    def vertical_delete_service_with_http_info(self, global_id, **kwargs):  # noqa: E501
        """Deletes an inter-site Service DELETE  # noqa: E501

        Deletes an inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_delete_service_with_http_info(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: Id of the service to delete (required)
        :return: None
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['global_id']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method vertical_delete_service" % key
                )
            params[key] = val
        del params['kwargs']
        # verify the required parameter 'global_id' is set
        if ('global_id' not in params or
                params['global_id'] is None):
            raise ValueError("Missing the required parameter `global_id` when calling `vertical_delete_service`")  # noqa: E501

        collection_formats = {}

        path_params = {}
        if 'global_id' in params:
            path_params['global_id'] = params['global_id']  # noqa: E501

        query_params = []

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.api_client.select_header_content_type(  # noqa: E501
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/intersite-vertical/{global_id}', 'DELETE',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type=None,  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def vertical_read_all_service(self, **kwargs):  # noqa: E501
        """the inter-site Service mapping structure GET  # noqa: E501

        Read the list of inter-site services  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_read_all_service(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :return: list[InlineResponse200]
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.vertical_read_all_service_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.vertical_read_all_service_with_http_info(**kwargs)  # noqa: E501
            return data

    def vertical_read_all_service_with_http_info(self, **kwargs):  # noqa: E501
        """the inter-site Service mapping structure GET  # noqa: E501

        Read the list of inter-site services  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_read_all_service_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :return: list[InlineResponse200]
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = []  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method vertical_read_all_service" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.api_client.select_header_content_type(  # noqa: E501
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/intersite-vertical', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='list[InlineResponse200]',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def vertical_read_one_service(self, global_id, **kwargs):  # noqa: E501
        """Read one inter-site Service GET  # noqa: E501

        Read one inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_read_one_service(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: (required)
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.vertical_read_one_service_with_http_info(global_id, **kwargs)  # noqa: E501
        else:
            (data) = self.vertical_read_one_service_with_http_info(global_id, **kwargs)  # noqa: E501
            return data

    def vertical_read_one_service_with_http_info(self, global_id, **kwargs):  # noqa: E501
        """Read one inter-site Service GET  # noqa: E501

        Read one inter-site service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_read_one_service_with_http_info(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: (required)
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['global_id']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method vertical_read_one_service" % key
                )
            params[key] = val
        del params['kwargs']
        # verify the required parameter 'global_id' is set
        if ('global_id' not in params or
                params['global_id'] is None):
            raise ValueError("Missing the required parameter `global_id` when calling `vertical_read_one_service`")  # noqa: E501

        collection_formats = {}

        path_params = {}
        if 'global_id' in params:
            path_params['global_id'] = params['global_id']  # noqa: E501

        query_params = []

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.api_client.select_header_content_type(  # noqa: E501
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/intersite-vertical/{global_id}', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='object',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def vertical_update_service(self, global_id, **kwargs):  # noqa: E501
        """Update an already deployed service  # noqa: E501

        Update an already deployed service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_update_service(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: Global ID of the service to update (required)
        :param Service1 service:
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.vertical_update_service_with_http_info(global_id, **kwargs)  # noqa: E501
        else:
            (data) = self.vertical_update_service_with_http_info(global_id, **kwargs)  # noqa: E501
            return data

    def vertical_update_service_with_http_info(self, global_id, **kwargs):  # noqa: E501
        """Update an already deployed service  # noqa: E501

        Update an already deployed service  # noqa: E501
        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.vertical_update_service_with_http_info(global_id, async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str global_id: Global ID of the service to update (required)
        :param Service1 service:
        :return: object
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['global_id', 'service']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method vertical_update_service" % key
                )
            params[key] = val
        del params['kwargs']
        # verify the required parameter 'global_id' is set
        if ('global_id' not in params or
                params['global_id'] is None):
            raise ValueError("Missing the required parameter `global_id` when calling `vertical_update_service`")  # noqa: E501

        collection_formats = {}

        path_params = {}
        if 'global_id' in params:
            path_params['global_id'] = params['global_id']  # noqa: E501

        query_params = []

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        if 'service' in params:
            body_params = params['service']
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # HTTP header `Content-Type`
        header_params['Content-Type'] = self.api_client.select_header_content_type(  # noqa: E501
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/intersite-vertical/{global_id}', 'PUT',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='object',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)
