# BRANCHES
**Current HEAD: elixir-europe/plant-brapi-to-isa/reactor**

**WARNING** :  Repository about to be frozen, the reference/working repository will be : https://github.com/ISA-tools/plant-brapi-to-isa

# plant-brapi-to-isa

Code to pull data from BrAPI endpoints and create an [ISA](http://isa-tools.org) representation of the experiments. 

# Docker

This is setup to be used with Docker for easy dependency requirements. You can download and run with a command like:

### Running BrAPI to ISA container without test containers:

```
docker build -t brapi2isa -f Dockerfile .
docker run -it -v outputdir:/outputdir brapi2isa -t <your trial DbId> -e <your endpoint>
```

### Usage for your own endpoint: 

```
docker-compose build && docker-compose run BrAPI2ISA -t <your trial DbId> -e <your endpoint>
```
### Usage for testing:

```
docker-compose build && docker-compose run <>
```
 Where <> can be following values:
- test_trial
- test_study
- test_studies_notrial
- test_pippa


Output will be put into a subfolder `/outputdir`.

# Documentation


 * https://docs.google.com/spreadsheets/d/1SiUVvauhdNSpAfHgds-vQpjAXYs34lFD8wSOZdkyCgY/edit?usp=sharing - MIAPPE spec
 * https://docs.google.com/spreadsheets/d/1RE_lXBFY4FsFcJcPAr-3QTlvKz4azedLob18ONrGZj0/edit?usp=sharing - BrAPI <-> MIAPPE mapping
 * http://docs.brapi.apiary.io/# - BrAPI documentation
 

 # MIAPPE BrAPI2ISA mapping Overview
 ## MIAPPE Investigation
 ISA investigation file from brapi/v1/study/trials.
 ## BRAPI/MIAPPE Study 
 
 ISA investigation file from brapi/v1/study/{id}/
 
 Plant material / MCPD (ie ISA Source): Stored in Study File (s_* files) from brapi/v1/study/{id}/germplasm
 ## MIAPPE Assay
 Stored in the ISATab trait definition file, from brapi/v1/study/{id}/observationVariable 
 
 ## MIAPPE ObservationUnit ie the combination of *treatment x plant material x level*
 ISATab.Sample equals BrAPI/MIAPPE.ObservationUnit. 
ISATab.Sample Treatment * Level * Material Source
Declared in Study files (s_*)

## ISATab Assay
One ISATab Assay file (a_*) by level  
  
 ## MIAPPE Data File
 Flat file allongside ISA files. Listed in ISA Assay File in Raw Data File. One file by level. 
 From brapi/v1/study/{id}/dataLink and brapi/v1/study/{id}/observationUnit transformed to CSV. 
 The issue of creating one ISA Assay per Brapi Observation Level was raised during the biohackathon when you pointed out that could be useful or requested by users. Simply reading BRAPI documentation did not make this obvious.
