# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
setup(
    name='app',
    version="1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["flask","flask_login","datetime","itertools","pytz","jsonschema","flask_wtf"],
)
