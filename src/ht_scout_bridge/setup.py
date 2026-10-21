from setuptools import setup
from glob import glob
setup(name='ht_scout_bridge', version='0.1.0', packages=['ht_scout_bridge'],
      data_files=[('share/ament_index/resource_index/packages',['resource/ht_scout_bridge']),
                  ('share/ht_scout_bridge',['package.xml']),
                  ('share/ht_scout_bridge/config',glob('config/*.yaml')),
                  ('share/ht_scout_bridge/launch',glob('launch/*.launch.py'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='HT project maintainers',maintainer_email='noreply@example.com',
      description='Calibrated Scout inputs for HT exploration',license='BSD-3-Clause',
      entry_points={'console_scripts':['scout_inputs = ht_scout_bridge.node:main',
                                       'check_scout_calibration = ht_scout_bridge.geometry:main']})
