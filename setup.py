from setuptools import setup, find_packages


setup(
    name='oedipus',
    version='0.1',
    description='Nicer, chainable API for Sphinx search',
    long_description=open('README.rst').read(),
    author='Erik Rose',
    author_email='erik@mozilla.com',
    license='BSD',
    packages=find_packages(exclude=['ez_setup']),
    url='http://github.com/erikrose/oedipus',
    include_package_data=True,
    zip_safe=False,
    # TODO: Is the canonical sphinxapi compatible? We made some changes in
    # SUMO.
    tests_require=['nose', 'fudge'],
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'],
)
