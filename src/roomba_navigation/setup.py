from setuptools import find_packages, setup

package_name = 'roomba_navigation'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/roomba_navigation']),
        ('share/roomba_navigation', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Autonomous boustrophedon coverage planning with Nav2 integration for Roomba577',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'coverage_planner_node = roomba_navigation.coverage_planner_node:main',
        ],
    },
)
