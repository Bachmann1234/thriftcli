# Copyright Notice:
# Copyright 2017, Fitbit, Inc.
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup


def make_version_unique(version):
    if version.exact:
        return version.format_with('{tag}+{time:%s}')
    else:
        return version.format_with('{tag}.post{distance}+{time:%s}')


config = {
    'name': 'thriftcli',
    'description': 'Thrift CLI',
    'author': 'Neel Virdy',
    'packages': ['thriftcli'],
    'entry_points': {
        'console_scripts': ['thriftcli = thriftcli.thrift_cli:main']
    },
    'install_requires': ['kazoo', 'mock', 'thrift', 'twitter.common.rpc', 'coverage'],
    'requires': ['kazoo', 'mock', 'thrift', 'twitter.common.rpc', 'coverage'],
    'use_scm_version': {'version_scheme': make_version_unique},
    'setup_requires': ['setuptools_scm']
}

setup(**config)
