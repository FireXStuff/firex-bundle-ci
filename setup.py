from setuptools import setup

setup(name='firex-bundle-ci',
      version='0.1.',
      description='FireX CI services',
      url='https://github.com/FireXStuff/firex-bundle-ci.git',
      author='Core FireX Team',
      author_email='firex-dev@gmail.com',
      license='BSD-3-Clause',
      packages=['firex_bundle_ci'],
      zip_safe=True,
      install_requires=[
          "firexapp",
	  "lxml",
	  "xunitmerge",
      ],)
