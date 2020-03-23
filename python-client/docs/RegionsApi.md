# swagger_client.RegionsApi

All URIs are relative to *https://localhost/api*

Method | HTTP request | Description
------------- | ------------- | -------------
[**read_region_name**](RegionsApi.md#read_region_name) | **GET** /region | Get the local region name


# **read_region_name**
> object read_region_name()

Get the local region name

Read the local region name

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.RegionsApi()

try:
    # Get the local region name
    api_response = api_instance.read_region_name()
    pprint(api_response)
except ApiException as e:
    print("Exception when calling RegionsApi->read_region_name: %s\n" % e)
```

### Parameters
This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

