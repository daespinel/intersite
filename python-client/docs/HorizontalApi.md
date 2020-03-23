# swagger_client.HorizontalApi

All URIs are relative to *https://localhost/api*

Method | HTTP request | Description
------------- | ------------- | -------------
[**horizontal_create_service**](HorizontalApi.md#horizontal_create_service) | **POST** /intersite-horizontal | Horizontal request to create an inter-site Service POST
[**horizontal_delete_service**](HorizontalApi.md#horizontal_delete_service) | **DELETE** /intersite-horizontal/{global_id} | Deletes an inter-site Service DELETE
[**horizontal_read_parameters**](HorizontalApi.md#horizontal_read_parameters) | **GET** /intersite-horizontal/{global_id} | Read the local cidr of an inter-site Service
[**horizontal_update_service**](HorizontalApi.md#horizontal_update_service) | **PUT** /intersite-horizontal/{global_id} | Update an already deployed service


# **horizontal_create_service**
> horizontal_create_service(service)

Horizontal request to create an inter-site Service POST

Horizontal request to create an inter-site Service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.HorizontalApi()
service = swagger_client.Service2() # Service2 | data for inter-site creation

try:
    # Horizontal request to create an inter-site Service POST
    api_instance.horizontal_create_service(service)
except ApiException as e:
    print("Exception when calling HorizontalApi->horizontal_create_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **service** | [**Service2**](Service2.md)| data for inter-site creation | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **horizontal_delete_service**
> horizontal_delete_service(global_id)

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
api_instance = swagger_client.HorizontalApi()
global_id = 'global_id_example' # str | Id of the service to delete

try:
    # Deletes an inter-site Service DELETE
    api_instance.horizontal_delete_service(global_id)
except ApiException as e:
    print("Exception when calling HorizontalApi->horizontal_delete_service: %s\n" % e)
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

# **horizontal_read_parameters**
> object horizontal_read_parameters(global_id)

Read the local cidr of an inter-site Service

Read one inter-site service

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.HorizontalApi()
global_id = 'global_id_example' # str | 

try:
    # Read the local cidr of an inter-site Service
    api_response = api_instance.horizontal_read_parameters(global_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling HorizontalApi->horizontal_read_parameters: %s\n" % e)
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

# **horizontal_update_service**
> object horizontal_update_service(global_id, service=service)

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
api_instance = swagger_client.HorizontalApi()
global_id = 'global_id_example' # str | Global ID of the service to update
service = swagger_client.Service3() # Service3 |  (optional)

try:
    # Update an already deployed service
    api_response = api_instance.horizontal_update_service(global_id, service=service)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling HorizontalApi->horizontal_update_service: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **global_id** | **str**| Global ID of the service to update | 
 **service** | [**Service3**](Service3.md)|  | [optional] 

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

