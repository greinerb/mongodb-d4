
import unittest
import os
import sys

basedir = os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.join(basedir, "../../src"))
sys.path.append(os.path.join(basedir, "../../src/search"))
sys.path.append(os.path.join(basedir, "../"))

from util import configutil
from util import constants

from tpcctestcase import TPCCTestCase
from ConfigParser import RawConfigParser
from search.designer import Designer
from search import Design
from designcandidates import DesignCandidates
from initialdesigner import InitialDesigner
from lnsdesigner import LNSDesigner
from costmodel import CostModel
from tpcc import constants as tpccConstants
from search import bbsearch

LNS_RUN_TIME = 2 * 60 * 60 # seconds

class FindExpectedDesign(TPCCTestCase):
    """
        Try to see if the existing cost model could generate the best desgin we
        expected
    """
    def setUp(self):
        TPCCTestCase.setUp(self)

        config = RawConfigParser()
        configutil.setDefaultValues(config)

        self.designer = Designer(config, self.metadata_db, self.dataset_db)
        self.dc = self.designer.generateDesignCandidates(self.collections, self.workload)
        self.assertIsNotNone(self.dc)
        
        # Make sure that we don't have any invalid candidate keys
        for col_name in self.collections.iterkeys():
            for index_keys in self.dc.indexKeys[col_name]:
                for key in index_keys:
                    assert not key.startswith(constants.REPLACE_KEY_DOLLAR_PREFIX), \
                        "Unexpected candidate key '%s.%s'" % (col_name, key)
        ## FOR
        
    ## DEF

    def outtestfindExpectedDesign(self):
        """Perform the actual search for a design"""
        # Generate all the design candidates
        # Instantiate cost model
        cmConfig = {
            'weight_network': 4,
            'weight_disk':    1,
            'weight_skew':    1,
            'nodes':          10,
            'max_memory':     1024,
            'skew_intervals': 10,
            'address_size':   64,
            'window_size':    500
        }
        cm = CostModel(self.collections, self.workload, cmConfig)

        initialDesign = InitialDesigner(self.collections, self.workload, None).generate()
        upper_bound = cm.overallCost(initialDesign)
        print "init solution: ", initialDesign
        print "init solution cost: ", upper_bound
        collectionNames = [c for c in self.collections]
        
        dc = self.dc.getCandidates(collectionNames)
        print "candidates: ", dc
        ln = LNSDesigner(self.collections, \
                        self.dc, \
                        self.workload, \
                        None, \
                        cm, \
                        initialDesign, \
                        upper_bound, \
                        LNS_RUN_TIME)
        solution = ln.solve()
        print "Best cost: ", ln.bestCost
        print "solution: ", solution
    ## DEF
    
if __name__ == '__main__':
    unittest.main()
## MAIN
