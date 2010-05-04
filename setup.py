from distutils.core import setup

setup(name='pyvimex',
      version='1.0',
      description= 'pyvim extension package',
      author='winterTTr',
      author_email='winterTTr@gmail.com',
      url='http://code.google.com/p/pyvim-extension',
      license = 'LGPL' ,
      packages=['pyvimex'],
      package_dir = { 'pyvimex' : 'src' }
      )
