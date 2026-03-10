from setuptools import find_packages, setup

package_name = 'roomba_safety'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/roomba_safety']),
        ('share/roomba_safety', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Safety monitor watchdog and emergency stop for Roomba577',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'safety_monitor_node = roomba_safety.safety_monitor_node:main',
        ],
    },
)
