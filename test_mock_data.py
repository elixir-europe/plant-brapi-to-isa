# Minimal study information
# TODO: add more than one study
mock_study = {
    "studyDbId": "1001",
    "studyName": "Study 1",
    "startDate": "2013-01-01",
    "endDate": "2014-01-01",
    "studyType": "Yield study",
    "location": {"altitude": 828,
                 "countryCode": "PER", "countryName": "Peru",
                 "latitude": -11.1274995803833, "longitude": -75.35639190673828,
                 "name": "Location 1"},
}

# Minimal trials
# TODO: add more than one trial
mock_trials = [
    {
        "trialName": "Peru Yield Trial 1",
        "studies": [mock_study]
    },
]

mock_germplasms = [
    {
        "germplasmName": "Name001"
    },
    {
        "germplasmName": "Name002"
    },
]
mock_variables = [
    {
        "observationVariableDbId": "MO_123:100002",
        "name": "Plant height",
        "ontologyDbId": "MO_123",
        "ontologyName": "Ontology.org",
        "crop": "maize",
        "growthStage": "1",
        "date": "2018-11-14",

        "method": {
            "methodDbId": "m1",
            "name": "Tape Measure",
            "description": "Standard rolled measuring tape",
            "formula": "a^2 + b^2 = c^2",
            "reference": "google.com",
            "class": "Numeric",
        },
        "scale": {
            "scaleDbId": "s1",
            "dataType": "Numerical",
            "decimalPlaces": 1,
            "name": "Centimeter",
            "validValues": {
                "categories": [],
                "max": 99999,
                "min": 0
            },
            "xref": "xref",
        },
        "trait": {
            "traitDbId": "t1",
            "name": "Plant Height",
            "class": "Numeric",
            "entity": "entity",
            "attribute": "plant height",
            "description": "plant height",
            "xref": "xref",
        },
    },
    {
        "observationVariableDbId": "MO_123:100003",
        "name": "Carotenoid",
        "ontologyDbId": "MO_123",
        "ontologyName": "Ontology.org",
        "crop": "maize",
        "date": "2018-11-14",
        "growthStage": "1",
        "method": {
            "methodDbId": "m3",
            "name": "Standard Color Palette",
            "formula": "NA",
            "description": "Comparing sample color to standard color palette",
            "reference": "google.com",
            "class": "Categorical",
        },
        "scale": {
            "scaleDbId": "s3",
            "name": "Color",
            "validValues": {
                "categories": [
                    "dark red",
                    "red",
                    "dark blue",
                    "blue",
                    "black"
                ],
                "max": 0,
                "min": 0
            },
            "dataType": "Categorical",
            "xref": "xref",
        },
        "trait": {
            "traitDbId": "t3",
            "name": "Leaf Color",
            "description": "color of leaf sample",
            "class": "Categorical",
            "attribute": "leaf color",
            "entity": "entity",
            "xref": "xref",
        },
    },
    {
        "observationVariableDbId": "MO_123:100005",
        "name": "Root color",
        "ontologyDbId": "MO_123",
        "ontologyName": "Ontology.org",
        "crop": "maize",
        "date": "2018-11-14",
        "defaultValue": "10",
        "growthStage": "1",
        "method": {
            "methodDbId": "m3",
            "name": "Standard Color Palette",
            "description": "Comparing sample color to standard color palette",
            "formula": "NA",
            "reference": "google.com",
            "class": "Categorical",
        },
        "scale": {
            "scaleDbId": "s3",
            "name": "Color",
            "dataType": "Categorical",
            "validValues": {
                "categories": [
                    "dark red",
                    "red",
                    "dark blue",
                    "blue",
                    "black"
                ],
                "max": 0,
                "min": 0
            },
            "xref": "xref",
        },
        "trait": {
            "traitDbId": "t4",
            "name": "Root Color",
            "class": "Categorical",
            "entity": "entity",
            "attribute": "root color",
            "description": "color of root sample",
            "xref": "xref",
        },
    },
    {
        "observationVariableDbId": "MO_123:100006",
        "name": "Virus severity",
        "ontologyDbId": "MO_123",
        "ontologyName": "Ontology.org",
        "crop": "maize",
        "date": "2018-11-14",
        "growthStage": "1",
        "method": {
            "methodDbId": "m4",
            "name": "Image analysis",
            "description": "Image analysis of sample photo",
            "class": "Percentage",
            "formula": "Bobs Color Threshold Tool",
            "reference": "https://bobsimageanalysis.com"
        },
        "scale": {
            "scaleDbId": "s4",
            "name": "Percentage",
            "dataType": "Percentage",
            "validValues": {
                "categories": [],
                "max": 100,
                "min": 0
            },
            "xref": "xref",
        },
        "trait": {
            "traitDbId": "t5",
            "name": "Virus severity",
            "description": "Percentage of contaminated sample",
            "class": "Percentage",
            "attribute": "Virus severity",
            "entity": "entity",
            "xref": "xref",
        },
    },
]
mock_observation_units = [
    {
        "observationUnitDbId": "1",
        "observationUnitName": "Plot 1",
        "germplasmName": mock_germplasms[0]["germplasmName"],
        "observations": [
          {
            "collector": "A. Technician",
            "observationTimeStamp": "2013-06-14T22:03:51Z",
            "observationVariableDbId": mock_variables[0]['observationVariableDbId'],
            "observationVariableName": mock_variables[0]['name'],
            "value": "1.2"
          },
          {
            "collector": "A. Technician",
            "observationTimeStamp": "2013-06-14T22:04:51Z",
            "observationVariableDbId": mock_variables[1]['observationVariableDbId'],
            "observationVariableName": mock_variables[1]['name'],
            "value": "4.5"
          }
        ],
    },
    {
        "observationUnitDbId": "3",
        "observationUnitName": "Plot 2",
        "germplasmName": mock_germplasms[1]["germplasmName"],
        "observations": [
          {
            "collector": "A. Technician",
            "observationTimeStamp": "2013-06-14T22:07:51Z",
            "observationVariableDbId": mock_variables[2]['observationVariableDbId'],
            "observationVariableName": mock_variables[2]['name'],
            "value": "2.1"
          },
          {
            "collector": "A. Technician",
            "observationTimeStamp": "2013-06-14T22:08:51Z",
            "observationVariableDbId": mock_variables[3]['observationVariableDbId'],
            "observationVariableName": mock_variables[3]['name'],
            "value": "dark blue"
          }
        ],
    },
]


def mock_brapi_results(results, total_pages):
    return {"metadata": {"pagination": {"totalPages": total_pages}},
            "result": {"data": results}}


def mock_brapi_result(result):
    return {"metadata": {}, "result": result}
