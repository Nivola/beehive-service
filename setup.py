#!/usr/bin/env python
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2023 CSI-Piemonte

from sys import version_info
from setuptools import setup
from setuptools.command.install import install as _install


class install(_install):
    def pre_install_script(self):
        pass

    def post_install_script(self):
        pass

    def run(self):
        self.pre_install_script()

        _install.run(self)

        self.post_install_script()


def load_requires():
    with open("./MANIFEST.md") as f:
        requires = f.read()
    return requires


def load_version():
    with open("./beehive_service/VERSION") as f:
        version = f.read()
    return version


if __name__ == "__main__":
    version = load_version()
    setup(
        name="beehive_service",
        version=version,
        description="Nivola service package",
        long_description="Nivola service package",
        author="CSI Piemonte",
        author_email="nivola.engineering@csi.it",
        license="EUPL-1.2",
        url="",
        scripts=[],
        packages=[
            "beehive_service",
            "beehive_service.controller",
            "beehive_service.dao",
            "beehive_service.db_script",
            "beehive_service.db_script.procedure",
            "beehive_service.entity",
            "beehive_service.event",
            "beehive_service.model",
            "beehive_service.plugins",
            "beehive_service.plugins.appengineservice",
            "beehive_service.plugins.appengineservice.views",
            "beehive_service.plugins.computeservice",
            "beehive_service.plugins.computeservice.views",
            "beehive_service.plugins.databaseservice",
            "beehive_service.plugins.databaseservice.entity",
            "beehive_service.plugins.databaseservice.views",
            "beehive_service.plugins.dummy",
            "beehive_service.plugins.loggingservice",
            "beehive_service.plugins.loggingservice.views",
            "beehive_service.plugins.monitoringservice",
            "beehive_service.plugins.monitoringservice.views",
            "beehive_service.plugins.storageservice",
            "beehive_service.plugins.storageservice.views",
            "beehive_service.server",
            "beehive_service.task",
            "beehive_service.task_v2",
            "beehive_service.views",
        ],
        namespace_packages=[],
        py_modules=[
            "beehive_service.__init__",
            "beehive_service.model",
            "beehive_service.mod",
            "beehive_service.service_util",
        ],
        classifiers=[
            "Development Status :: %s" % version,
            "Programming Language :: Python",
        ],
        entry_points={},
        data_files=[],
        package_data={"beehive_service": ["VERSION"]},
        install_requires=load_requires(),
        dependency_links=[],
        zip_safe=True,
        cmdclass={"install": install},
        keywords="",
        python_requires="",
        obsoletes=[],
    )
