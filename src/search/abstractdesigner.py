# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Copyright (C) 2012 by Brown University
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

import logging
from threading import Thread

LOG = logging.getLogger(__name__)

## ==============================================
## Abstract Designer
## ==============================================
class AbstractDesigner(Thread):
    
    def __init__(self, collections, workload, config):
        Thread.__init__(self)
        assert isinstance(collections, dict)
        assert not workload is None
        #assert not config is None
        
        self.collections = collections
        self.workload = workload
        self.config = config
        self.debug = LOG.isEnabledFor(logging.DEBUG)
    ## DEF
        
    def generate(self):
        raise NotImplementedError("Unimplemented %s.generate()" % self.__init__.im_class)
    
    def run(self):
        pass
## CLASS