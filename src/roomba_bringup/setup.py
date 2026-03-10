import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'roomba_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/roomba_bringup']),
        ('share/roomba_bringup', ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Launch files and configuration for Roomba577 multi-mode cleaning system',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)
