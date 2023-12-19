# beehive-service
__beehive-service__ is the project that contains the service component of the nivola cmp platform.

All code is written using python and support versions 3.7.x>

For more information refer to the [nivola](https://github.com/Nivola/nivola) project

## Overview

*beehive service* expose an API by which a final user may interact with the Nivola  Cloud Management Platform cmp.
When the method requires the interaction with same provider it wraps the invocations of *beehive resource* methods and 
sometimes it may orchestrate different calls.
When the method requires some authentication and authorization it wraps the invocations of *beehive auth* methods.

### Data model
In order to organize consumers and accounts for costs incurred, the legal entities using the platform are identified by 
the **Organization** entity.
Each **Organization** is in turn divided into **Division** (there is always one by default), while one or more 
**Accounts** can be associated with a **Division**.

When created an **Account** is empty and has no services activated within it is just authorization concept.
The **Account**  configuration is created by means of enabling capabilities (**AccountCapability**).

An **AccountCapability** is enabled set of services are created inside the Account.
Each Capability is designed in order do provide a consistent set of services which existence is needed by target services:
eg. in order to create a ComputeInstance service the Account must contain one ComputeService, at least one ComputeImage,
at least one **ComputeVpc** etc.

By enabling an **AccountCapability**, many **ServiceInstance** may be created in an **Account** in a single operation.
One **Account** may have many **AccountCapability** enabled and associated with it.

The **ServiceInstance** is entity that describe the business services such as the *ComputeInstance*, *DatabaseInstance*, 
etc that can be created inside an **Account**.

Each **ServiceInstance** has one **ServiceDefinition**.
The **ServiceDefinition** entity contains the template configuration required in order to create an **ServiceInstance**.

Each **ServiceDefinition** has one **ServiceType**.
The **ServiceType** entity identify the plug-in which contains the logics in order to manage the **ServiceInstance**

All the ServiceDefinitions are organized into catalogues by means of the **ServiceCatalog** entity.

## Installing

### Install requirements
First of all you have to install some package:

```
$ sudo apt-get install gcc
$ sudo apt-get install -y python-dev libldap2-dev libsasl2-dev libssl-dev
```

At this point create a virtualenv

```
$ python3 -m venv /tmp/py3-test-env
$ source /tmp/py3-test-env/bin/activate
$ pip3 install wheel
```

### Install python packages

public packages:

```
$ pip3 install -U git+https://github.com/Nivola/beehive-service.git
```


## Contributing
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning
We use Semantic Versioning for versioning. (https://semver.org)

## Authors
See the list of contributors who participated in this project in the file AUTHORS.md contained in each specific project.

## Copyright
CSI Piemonte - 2018-2022

Regione Piemonte - 2020-2022

## License
See the *LICENSE.txt file contained in each specific project for details.

## Community site (Optional)
At https://www.nivolapiemonte.it/ could find all the informations about the project.
