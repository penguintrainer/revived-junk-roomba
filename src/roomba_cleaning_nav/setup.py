from setuptools import setup
from glob import glob
import os

package_name = 'roomba_cleaning_nav'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='user@example.com',
    description='ROS2 packages for Roomba 577 cleaning and navigation',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'roomba_driver = roomba_cleaning_nav.roomba_driver_node:main',
            'teleop_node = roomba_cleaning_nav.teleop_node:main',
            'navigation_node = roomba_cleaning_nav.navigation_node:main',
            'cleaning_node = roomba_cleaning_nav.cleaning_node:main',
        ],
    },
)
