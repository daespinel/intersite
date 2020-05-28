[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green)](https://www.apache.org/licenses/LICENSE-2.0)
![python](https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue)
[![Build Status](https://travis-ci.org/daespinel/intersite.svg?branch=master)](https://travis-ci.com/github/daespinel/intersite)

# DIMINET DIstributed Module for Inter-site NETworking services deployement

DIMINET is a a distributed/decentralized module for inter-site networking services capable to interconnect independent networking resources in an automatized and transparent manner. Layer 2 network extensions and Layer 3 routing functionss are two main implementation tasks. This first proof-of-concept of the proposed solution has been implemented besides the networking service of Open-stack, Neutron. One important planned feature of our proposed system is the generalization to other cloud services. So the collaboration between independent systems can reuse and extend based on this building block.

While this project is independent of Neutron networking API service, it acts as an plugin deployed on the same networking node of Neutron, such add-on service will be very useful to manage and utilize independent geo-distributed networking resources for services like network slicing.

This is an incremental effort based on OpenStack Networking services and its existing APIs. 


## Installation

Git clone this repository with the following command:

```bash
git clone https://github.com/daespinel/intersite.git`
cd intersite
```

Create a virtual environment.

```bash
virtualenv -p python3 venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Configuration

Diminet require you to configure a simple configuration located in `config/services.conf` file:

```bash
[DEFAULT]
# IP address of the Host where also the local Neutron server is located
host = <HOST_IP>
# Region Name of the local region deployment in order to autehnticate to the local Keystone service
region_name = <REGION_NAME>
# User info to authenticate against Keystone
username = <USER_NAME>
password = <USER_PASSWORD>
project = <PROJECT_NAME>
# Keystone authentication URL
auth utl = http://<AUTH_URL>/identity/v3
```

## Launch

Once the previous steps have been done, the DIMINET server is executed with the following command:

```bash
python app.py
```

The user can access the `<HOST_IP>:7575` url to access the GUI. As the server has been implemented using Flask and Swagger frameworks, it proposes a documented API in `<HOST_IP>:7575/api/ui/` .

## Proposed services

DIMINET proposes two services, each one requiring to provide different informations:

### Layer 2 extension service

As it names indicates, this service provides an extension of a Layer 2 network (in Neutron, a network object with its subnetwork) to be extended to remote sites. The user needs to provide:

```bash
# Local region name with the Neutron network uuid that will be extended
# eg., "RegionOne,3b8360e6-e29a-4063-a8bc-7bbd0785d08b", the network has a CIDR 10.0.0.0/24
<LOCAL_REGION_NAME>,<NEUTRON_NETWORK_UUID>
# A list of remote sites where the network will be extended
# "RegionTwo","RegionThree","RegionFour"
<REMOTE_REGION_ONE>,<REMOTE_REGION_TWO>,<REMOTE_REGION_THREE>
```

### Layer 3 routing extension

This service provides a logical router among several existing and independent resources (networks and their subnetworks) deployed in different sites.

```bash
# Local region name with the Neutron network uuid
# eg., "RegionOne,3b8360e6-e29a-4063-a8bc-7bbd0785d08b", the network has a CIDR 10.0.0.0/24
"<LOCAL_REGION_NAME>,<NEUTRON_NETWORK_UUID>"
# A list of remote sites where the network will be extended
# "RegionTwo,c58089b1-c083-4532-9d7d-85d531097a62",
# "RegionThree,3feae7ca-e66c-4006-aced-5f3a819c91f6", the network has a CIDR 10.0.1.0/24
# "RegionFour,5861e31f-074d-4f0b-a091-de569e5108fa", the network has a CIDR 10.0.2.0/24
"<REMOTE_REGION_ONE>,<NEUTRON_NETWORK_UUID>","<REMOTE_REGION_TWO>,<NEUTRON_NETWORK_UUID>","<REMOTE_REGION_THREE>,<NEUTRON_NETWORK_UUID>"
```

