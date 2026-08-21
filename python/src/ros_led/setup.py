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
    description='ROS 2 Jazzy running in a container on the Arduino UNO Q to control the onboard LED via an RPC bridge between the Qualcomm MPU (Linux) and the STM32 microcontroller. A ROS 2 node subscribes to a boolean topic and triggers an RPC call to the MCU, enabling end-to-end ROS-native LED control on the UNO Q.',
    license='BSD 3-Clause',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            "led = ros_led.led:main",
            "gps = ros_led.gps:main",
        ],
    },
)
