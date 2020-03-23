# swagger_client.ServicesApi

All URIs are relative to *https://localhost/api*

Method | HTTP request | Description
------------- | ------------- | -------------
[**vertical_create_service**](ServicesApi.md#vertical_create_service) | **POST** /intersite-vertical | Creates an inter-site Service POST
[**vertical_delete_service**](ServicesApi.md#vertical_delete_service) | **DELETE** /intersite-vertical/{global_id} | Deletes an inter-site Service DELETE
[**vertical_read_all_service**](ServicesApi.md#vertical_read_all_service) | **GET** /intersite-vertical | the inter-site Service mapping structure GET
[**vertical_read_one_service**](ServicesApi.md#vertical_read_one_service) | **GET** /intersite-vertical/{global_id} | Read one inter-site Service GET
[**vertical_update_service**](ServicesApi.md#vertical_update_service) | **PUT** /intersite-vertical/{global_id} | Update an already deployed service


# **vertical_create_service**
> object vertical_create_service(service)

Creates an inter-site Service POST

Create an inter-site service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ServicesApi()
service = swagger_client.Service() # Service | data for inter-service creation

try:
    # Creates an inter-site Service POST
    api_response = api_instance.vertical_create_service(service)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ServicesApi->vertical_create_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service** | [**Service**](Service.md)| data for inter-service creation | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **vertical_delete_service**
> vertical_delete_service(global_id)

Deletes an inter-site Service DELETE

Deletes an inter-site service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ServicesApi()
global_id = 'global_id_example' # str | Id of the service to delete

try:
    # Deletes an inter-site Service DELETE
    api_instance.vertical_delete_service(global_id)
except ApiException as e:
    print("Exception when calling ServicesApi->vertical_delete_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **global_id** | **str**| Id of the service to delete | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **vertical_read_all_service**
> list[InlineResponse200] vertical_read_all_service()

the inter-site Service mapping structure GET

Read the list of inter-site services

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ServicesApi()

try:
    # the inter-site Service mapping structure GET
    api_response = api_instance.vertical_read_all_service()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ServicesApi->vertical_read_all_service: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

[**list[InlineResponse200]**](InlineResponse200.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **vertical_read_one_service**
> object vertical_read_one_service(global_id)

Read one inter-site Service GET

Read one inter-site service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ServicesApi()
global_id = 'global_id_example' # str | 

try:
    # Read one inter-site Service GET
    api_response = api_instance.vertical_read_one_service(global_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ServicesApi->vertical_read_one_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **global_id** | **str**|  | 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **vertical_update_service**
> object vertical_update_service(global_id, service=service)

Update an already deployed service

Update an already deployed service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.ServicesApi()
global_id = 'global_id_example' # str | Global ID of the service to update
service = swagger_client.Service1() # Service1 |  (optional)

try:
    # Update an already deployed service
    api_response = api_instance.vertical_update_service(global_id, service=service)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling ServicesApi->vertical_update_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **global_id** | **str**| Global ID of the service to update | 
 **service** | [**Service1**](Service1.md)|  | [optional] 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

