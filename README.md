# BRANCHES
**Current HEAD: elixir-europe/plant-brapi-to-isa**
**WARNING** : Frozen Repository, the reference/working repository is : https://github.com/ISA-tools/plant-brapi-to-isa

# plant-brapi-to-isa

Code to pull data from BrAPI endpoints and create an [ISA](http://isa-tools.org) representation of the experiments. 

Docker
======

This is setup to be used with Docker for easy dependency requirements. You can download and run with a command like:

docker-compose build && docker-compose run --rm conv

Output will be put into a subfolder `out`.

Documentation
=============

 * https://docs.google.com/spreadsheets/d/1SiUVvauhdNSpAfHgds-vQpjAXYs34lFD8wSOZdkyCgY/edit?usp=sharing - MIAPPE spec
 * https://docs.google.com/spreadsheets/d/1RE_lXBFY4FsFcJcPAr-3QTlvKz4azedLob18ONrGZj0/edit?usp=sharing - BrAPI <-> MIAPPE mapping
 * http://docs.brapi.apiary.io/# - BrAPI documentation
