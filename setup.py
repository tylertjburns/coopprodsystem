import setuptools

with open('README.md') as f:
    README = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(name='coopprodsystem',
      version='0.4',
      description='Package for Modeling production systems',
      url='https://github.com/tylertjburns/coopprodsystem',
      author='tburns',
      author_email='tyler.tj.burns@gmail.com',
      license='MIT',
      packages=setuptools.find_packages(),
      python_requires=">3.5",
      install_requires=requirements,
      long_description_content_type="text/markdown",
      long_description=README,
      zip_safe=False,
      package_data={
        "assets": ['*.css']
      },
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',

      ])

if __name__ == "__main__":
    print(setuptools.find_packages())