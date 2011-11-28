#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
import pymongo
from pprint import pprint
from ConfigParser import SafeConfigParser

from catalog import *
from util import *

logging.basicConfig(level = logging.INFO,
                    format="%(asctime)s [%(funcName)s:%(lineno)03d] %(levelname)-5s: %(message)s",
                    datefmt="%m-%d-%Y %H:%M:%S",
                    stream = sys.stdout)

## ==============================================
## main
## ==============================================
if __name__ == '__main__':
    aparser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                      description="%s\n%s" % (constants.PROJECT_NAME, constants.PROJECT_URL))
    aparser.add_argument('--config', type=file,
                         help='Path to designer configuration file')
    aparser.add_argument('--host', type=str, default="localhost",
                         help='The hostname of the MongoDB instance containing the sample workload')
    aparser.add_argument('--print-config', action='store_true',
                         help='Print out the default configuration file used by %s' % constants.PROJECT_NAME)
    aparser.add_argument('--debug', action='store_true',
                         help='Enable debug log messages')
    args = vars(aparser.parse_args())

    if args['debug']: logging.getLogger().setLevel(logging.DEBUG)
    if args['print_config']:
        print config.makeDefaultConfig()
        sys.exit(0)
    
    if not args['config']:
        logging.error("Missing configuration file")
        print
        aparser.print_help()
        sys.exit(1)
    logging.debug("Loading configuration file '%s'" % args['config'])
    cparser = SafeConfigParser()
    cparser.read(os.path.realpath(args['config'].name))
    config = config.setDefaultValues(dict(cparser.items(config.KEY)))
    assert config['hostname']
    assert config['port']

    ## Connect to MongoDB and make sure that the databases that we need are there
    conn = pymongo.Connection(config['hostname'], config['port'])
    db_names = conn.database_names()
    
    for key in [ 'schema_db', 'workload_db' ]:
        db_name = config[key]
        if not db_name in db_names:
            raise Exception("The %s database '%s' does not exist" % (key.upper(), db_name))
    ## FOR
    schema_db = conn[config['schema_db']]
    workload_db = conn[config['workload_db']]
    
    ## ----------------------------------------------
    ## STEP 1
    ## Precompute any summarizations and information that we can about the workload
    ## ----------------------------------------------
    schema = catalog.generateCatalogFromDatabase(schema_db)
    print repr(schema)
    
    ## ----------------------------------------------
    ## STEP 2
    ## Generate an initial solution
    ## ----------------------------------------------
    
    ## ----------------------------------------------
    ## STEP 3
    ## Execute the LNS design algorithm
    ## ----------------------------------------------
    
## MAIN