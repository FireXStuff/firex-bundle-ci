import versioneer
from setuptools import setup

setup(name='firex-bundle-ci',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description='FireX CI services',
      url='https://github.com/FireXStuff/firex-bundle-ci.git',
      author='Core FireX Team',
      author_email='firex-dev@gmail.com',
      license='BSD-3-Clause',
      packages=['firex_bundle_ci'],
      zip_safe=True,
      install_requires=[
          "firexapp",
          "firex-keeper",
          "lxml",
          "xunitmerge",
          "unittest-xml-reporting"
      ],
      entry_points={'firex.bundles': 'firex-bundle-ci = firex_bundle_ci'},
      )
