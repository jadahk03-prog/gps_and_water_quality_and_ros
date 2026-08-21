from setuptools import find_packages, setup

package_name = 'ros_led'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Miguel Angel Gonzalez Rodriguez',
    maintainer_email='miguel_gonzalezr@ieee.org',
    description='ROS 2 nodes for water-quality sensors and GPS on Arduino UNO Q.',
    license='BSD 3-Clause',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "water_quality = ros_led.water_quality:main",
            "led = ros_led.led:main",
            "gps = ros_led.gps:main",
        ],
    },
)
