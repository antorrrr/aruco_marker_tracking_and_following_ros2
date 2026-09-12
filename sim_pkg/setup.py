from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'sim_pkg'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))
        ),
        (
            os.path.join('share', package_name, 'models'),
            glob(os.path.join('models', '*'))
        ),
        (
            os.path.join('share', package_name, 'description'),
            glob(os.path.join('description', '*'))
        ),
        (
            os.path.join('share', package_name, 'worlds'),
            glob(os.path.join('worlds', '*'))
        ),
        (
            os.path.join('share', package_name, 'params'),
            glob(os.path.join('params', '*'))
        ),
        (
            os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*'))
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='antor',
    maintainer_email='',
    description='',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)