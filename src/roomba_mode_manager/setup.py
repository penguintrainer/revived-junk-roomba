from setuptools import find_packages, setup

package_name = 'roomba_mode_manager'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/roomba_mode_manager']),
        ('share/roomba_mode_manager', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Driving mode state machine and cmd_vel multiplexer for Roomba577',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mode_manager_node = roomba_mode_manager.mode_manager_node:main',
        ],
    },
)
