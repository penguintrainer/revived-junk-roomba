from setuptools import find_packages, setup

package_name = 'roomba_driver'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/roomba_driver']),
        ('share/roomba_driver', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Roomba577 serial communication driver node',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'roomba_driver_node = roomba_driver.roomba_driver_node:main',
        ],
    },
)
