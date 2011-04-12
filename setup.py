from distutils.core import setup

setup(
    name = 'django-mailman',
    version = '0.1',
    packages = ['django_mailman',],
    platforms = ['any'],
    license = 'GNU LGPL v2.1',
    author = 'Bernd Schlapsi',
    author_email = 'brot@gmx.info',
    description = 'Interface to Mailman Web-API',
    long_description = open('README').read(),
    url = 'https://launchpad.net/django-mailman',
)
