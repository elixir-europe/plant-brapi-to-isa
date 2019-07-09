from setuptools import setup

setup(
    name='BrAPI2ISA',
    url='https://github.com/elixir-europe/plant-brapi-to-isa',
    packages=['.'],
    install_requires=open('requirements.txt').read().splitlines(),
    version='0.1',
    description='Convert BrAPI data to ISA',
    long_description=open('README.md').read(),
)
