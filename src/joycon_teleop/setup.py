from setuptools import find_packages, setup

package_name = 'joycon_teleop'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/joycon_teleop']),
        ('share/joycon_teleop', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Roomba Team',
    maintainer_email='roomba@example.com',
    description='Joy-Con teleoperation node for manual Roomba577 control',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joycon_teleop_node = joycon_teleop.joycon_teleop_node:main',
        ],
    },
)
