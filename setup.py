import setuptools


def long_description():
    with open('README.md', 'r') as file:
        return file.read()


setuptools.setup(
    name='aiofastforward',
    version='0.0.3',
    author='Michal Charemza',
    author_email='michal@charemza.name',
    description='Fast-forward time in asyncio Python by patching loop.time, loop.call_later, loop.call_at, and asyncio.sleep',
    long_description=long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/michalc/aiofastfoward',
    py_modules=[
        'aiofastforward',
    ],
    python_requires='>=3.5.1',
    test_suite='test',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: AsyncIO',
    ],
)
