
import json
import pySBOLx
import unittest

from xplan_to_sbol.ConversionUtil import *
from xplan_to_sbol.xplanParser.XplanDataParser import XplanDataParser

import xplan_to_sbol.__main__ as xbol
from sbol import *

''' 
    This module is used to test data generated from xplan to sbol for the yeastGates challenge problem.
	
    author(s) : Tramy Nguyen
''' 

class TestYeastGates(unittest.TestCase):

    """ 
    This class will perform unit testing on the yeastGates example that was generated by xplan2sbol converter.
	
    There are two options to run this module from the xplan_to_sbol directory:
    1. Run module as a standalone: python -m unittest tests/Test_yeastGates.py
    2. Run this module as a test suite : python tests/SBOLTestSuite.py
    
    """
    
    @classmethod
    def setUpClass(cls):
        print("Running " + cls.__name__)
        yeastGates_json = 'example/xplan/yeastGates-Q0-v2.json'		
        yeastGates_sbol = 'example/sbol/yeastGates-Q0-v2.xml'
        om_path = 'example/om/om-2.0.rdf'
		
        cls.sbolDoc = Document()
        cls.sbolDoc.read(yeastGates_sbol)
		
        with open(yeastGates_json) as jsonFile:
            jsonData = json.load(jsonFile)
            cls.converted_sbol =  xbol.convert_xplan_to_sbol(jsonData, SBOLNamespace.HTTPS_HS, om_path, True)
            cls.xplan_data = XplanDataParser(jsonData)

    def test_totalIds(self):
        expected_ids = set(range(0, 12))
        actual_ids = set()
        for step_obj in self.xplan_data.get_stepsList():
            actual_ids.add(step_obj.get_id())
        self.assertEqual(expected_ids, actual_ids)
             	
		
    def test_SBOLFiles_diff(self):
        outputFile = 'example/sbol/convertedResult.xml'
        self.converted_sbol.write(outputFile)

        actual_sbol = Document()
        actual_sbol.read(outputFile)
        
        actual_sbol.identity = "yeastGates-Q0-v2_conversionDocument"
        self.sbolDoc.identity = 'yeastGates-Q0-v2_goldenDocument'
        sbolDiff_res = self.sbolDoc.compare(actual_sbol)
        self.assertTrue(sbolDiff_res == 1)
		
if __name__ == '__main__':
	unittest.main()