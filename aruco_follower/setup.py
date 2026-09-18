from setuptools import find_packages, setup

package_name = 'aruco_follower'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'flask', 'requests'],
    zip_safe=True,
    maintainer='Antor Mondal',
    maintainer_email='antor.mondal2002@gmail.com',
    description='ArUco marker detection and marker-following of autonomous mobile robot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'aruco_detector = aruco_follower.aruco_detector:main',
            'marker_follower = aruco_follower.marker_follower:main',
            'set_target_marker = aruco_follower.set_target_marker:main',
            'web_target_commander = aruco_follower.web_target_commander:main',
        ],
    },
)
