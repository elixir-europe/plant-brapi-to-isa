import unittest
import isatools
import brapi_to_isa

SERVER = ""
studyID = ""
isatab = ""

class TestConvert(unittest.TestCase):
    """TODO: write tests!! """
    def test_convert(self):
        converted = brapi_to_isa(SERVER, studyID)
        self.assertIs(converted, isatab)


if __name__ == '__main__':
    unittest.main()