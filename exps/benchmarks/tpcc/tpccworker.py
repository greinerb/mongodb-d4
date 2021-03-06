# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Copyright (C) 2012
# Andy Pavlo - http://www.cs.brown.edu/~pavlo/
# Yang Lu - http://www.cs.brown.edu/~yanglu/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# -----------------------------------------------------------------------

import sys
import os
import string
import re
import logging
import traceback
from pprint import pprint, pformat

import constants
from util import *
from api.abstractworker import AbstractWorker
from api.message import *

import drivers
from runtime import *
from runtime import scaleparameters

LOG = logging.getLogger(__name__)

class TpccWorker(AbstractWorker):
    
    def initImpl(self, config, data):
        # HACK: Collapse config into a single dict
        new_config = { }
        for s in config.keys():
            if not s in ['default', self.name]: continue
            for k in config[s].keys():
                new_config[k] = config[s][k]
        config = new_config
        
        ## Create a handle to the target client driver
        config['system'] = "mongodb"
        realpath = os.path.realpath(__file__)
        basedir = os.path.dirname(realpath)
        if not os.path.exists(realpath):
            cwd = os.getcwd()
            basename = os.path.basename(realpath)
            if os.path.exists(os.path.join(cwd, basename)):
                basedir = cwd
        config['ddl'] = os.path.join(basedir, "tpcc.sql")
        
        ## Create our ScaleParameter stuff that we're going to need
        num_warehouses = int(config['warehouses'])
        self.scaleParameters = scaleparameters.makeWithScaleFactor(num_warehouses, config["scalefactor"])
        
        driverClass = self.createDriverClass(config['system'])
        assert driverClass != None, "Failed to find '%s' class" % config['system']
        driver = driverClass(self.conn, config['ddl'])
        assert driver != None, "Failed to create '%s' driver" % config['system']
        driver.loadConfig(config)
        self.driver = driver
        
        self.executor = executor.Executor(self.scaleParameters, stop_on_error=self.stop_on_error)
    ## DEF
    
    def createDriverClass(self, name):
        full_name = "%sDriver" % name.title()
        mod = __import__('drivers.%s' % full_name.lower(), globals(), locals(), [full_name])
        klass = getattr(mod, full_name)
        return klass
    ## DEF
    
    def loadImpl(self, config, channel, data):
        assert self.driver != None
        w_ids = list(data)
        loadItems = (1 in w_ids)
        
        try:
            l = loader.Loader(self.driver, self.scaleParameters, w_ids, loadItems)
            self.driver.loadStart()
            l.execute()
            self.driver.loadFinish()   
        except KeyboardInterrupt:
            return -1
        except (Exception, AssertionError), ex:      
            traceback.print_exc(file = sys.stdout)
            raise
    ## DEF
    
    ## ---------------------------------------------------------------------------
    ## EXECUTION INITIALIZATION
    ## ---------------------------------------------------------------------------
    
    def executeInitImpl(self, config):
        pass
    ## DEF
    
    def next(self, config):
        assert self.executor != None
        return self.executor.doOne()
        
    def executeImpl(self, config, txn, params):
        assert self.driver != None
        assert self.executor != None
        return self.driver.executeTransaction(txn, params)
    ## DEF    
## CLASS