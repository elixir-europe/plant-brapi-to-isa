from setuptools import setup, find_packages

with open("README.md", 'r') as f:
    long_description = f.read()

with open('requirements.txt', 'r') as f:
    required = f.read().splitlines()


setup(
    name='BrAPI2ISA',
    keywords=["BrAPI", "MIAPPE", "ISA", "Phenotyping", "isa-tab"],
    url='https://github.com/elixir-europe/plant-brapi-to-isa',
    license='BSD-3',
    packages=['.'],
    long_description_content_type='text/markdown',
    long_description=long_description,
    install_requires=[required],
    version='1.0',
    description='Convert BrAPI data to ISA',
    classifiers=[
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': ["brapi2isa=brapi_to_isa:main"]
    }

)
