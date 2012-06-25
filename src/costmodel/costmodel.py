# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Copyright (C) 2012
# Andy Pavlo - http://www.cs.brown.edu/~pavlo/
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

from __future__ import division
import sys
import json
import logging
import math
import random

'''
Cost Model object

Used to evaluate the "goodness" of a design in respect to a particular workload. The 
Cost Model uses Network Cost, Disk Cost, and Skew Cost functions (in addition to some
configurable coefficients) to determine the overall cost for a given design/workload
combination

workload : Workload abstraction class

config {
    'weight_network' : Network cost coefficient,
    'weight_disk' : Disk cost coefficient,
    'weight_skew' : Skew cost coefficient,
    'nodes' : Number of nodes in the Mongo DB instance,
    'max_memory' : Amount of memory per node in MB,
    'address_size' : Amount of memory required to index 1 document,
    'skew_intervals' : Number of intervals over which to calculate the skew costs
}

statistics {
    'collections' : {
        'collection_name' : {
            'fields' : {
                'field_name' : {
                    'query_use_count' : Number of queries in which this field appears in the predicate,
                    'cardinality' : Number of distinct values,
                    'selectivity' : Cardinalty / Tuple Count
                }
            },
            'tuple_count' : Number of tuples in the collection,
            'workload_queries' : Number of queries in the workload that target this collection,
            'workload_percent' : Percentage of queries in the workload that target this collection,
            'avg_doc_size' : The average number of kilobytes per document in this collection,
            'max_pages' : The maximum number of pages required to scan the collection
        },
    },
    'total_queries' : total number of queries in the workload??,
  }
'''
class CostModel(object):
    
    def __init__(self, workload, config, statistics = {}) :
        self.workload = workload
        self.weight_network = config['weight_network']
        self.weight_disk = config['weight_disk']
        self.weight_skew = config['weight_skew']
        self.nodes = config['nodes']
        self.stats = statistics
        self.rg = random.Random()
        self.rg.seed('cost model coolness')
        # Convert MB to KB
        self.max_memory = config['max_memory'] * 1024 * 1024 * self.nodes
        self.skew_segments = config['skew_intervals'] - 1
        self.address_size = config['address_size'] / 4
    ## end def ##
    
    def overallCost(self, design) :
        cost = 0
        cost += self.weight_network * self.networkCost(design)
        cost += self.weight_disk * self.diskCost(design)
        cost += self.weight_skew * self.skewCost(design)
        return cost / (self.weight_network + self.weight_disk + self.weight_skew)
    ## end def ##
    
    def networkCost(self, design) :
        cost, queries = self.partialNetworkCost(design, self.workload)
        return cost
    ## end def ##
    
    '''
    Estimate the Disk Cost for a design and a workload
    - Best case, every query is satisfied by main memory
    - Worst case, every query requires a full collection
    '''
    def diskCost(self, design):
        worst_case = 0
        cost = 0
        # 1. estimate index memory requirements
        index_memory = self.getIndexSize(design)
        if index_memory > self.max_memory :
            return 10000000000000
        
        # 2. approximate the number of documents per collection in the working set
        working_set = self.estimateWorkingSets(design, self.max_memory - index_memory)
        
        # 3. Iterate over workload, foreach query:
        for s in self.workload:
            for q in s.queries :
                # is the collection in the design - if not ignore
                if design.hasCollection(q.collection) == False :
                    break
                
                # Does this depend on the type of query? (insert vs update vs delete vs select)
                multiplier = 1
                if q.type == 'insert' :
                    multiplier = 2
                    max_pages = 1
                    min_pages = 1
                    pass
                else :
                    if q.type == 'update' or q.type == 'delete' :
                        multiplier = 2
                    ## end if ##
                    
                    # How many pages for the queries tuples?
                    max_pages = self.stats[q.collection]['max_pages']
                    min_pages = max_pages
                    
                    # Is the entire collection in the working set?
                    if working_set[q.collection] >= 100 :
                        min_pages = 0
                    
                    # Does this query hit an index?
                    elif design.hasIndex(q.collection, list(q.predicates)) :
                        min_pages = 0
                    else :
                        # Does this query hit the working set?
                        ws_hit = self.rg.randint(1, 100)
                        if ws_hit <= working_set[q.collection] :
                            min_pages = 0
                ## end if ##
                    
                cost += min_pages        
                worst_case += max_pages
        if worst_case == 0 :
            return 0
        else :
            return cost / worst_case
    ## end def ##
    
    def skewCost(self, design):
        segment_costs = []
        segments = []
        if self.workload.length > 0 :
            start = self.workload.sessions[0].startTime
            end = self.workload.sessions[self.workload.length - 1].endTime
        else :
            return 0
            
        # Divide the workload up into segments for skew analysis
        offset = (end - start) / self.skew_segments
        timer = start + offset
        i = 0
        wl_seg = self.workload.factory()
        for s in self.workload.sessions :
            if s.endTime > timer :
                i += 1
                timer += offset
                segments.append(wl_seg)
                wl_seg = self.workload.factory()
            wl_seg.addSession(s)
        segments.append(wl_seg)
        
        # Calculate the network cost for each segment for skew analysis
        for i in range(0, len(segments)) :
            segment_costs.append(self.partialNetworkCost(design, segments[i]))
        
        # Determine overall skew cost as a function of the distribution of the
        # segment network costs
        sum_of_query_counts = 0
        sum_intervals = 0
        for i in range(0, len(segments)) :
            skew = 1 - segment_costs[i][0]
            sum_intervals += skew * segment_costs[i][1]
            sum_of_query_counts += segment_costs[i][1]
        
        if sum_of_query_counts == 0 :
            return 0
        else :
            return sum_intervals / sum_of_query_counts
        
    def partialNetworkCost(self, design, wrkld_sgmnt) :
        worst_case = 0
        result = 0
        stat_collections = list(self.stats)
        query_count = 0
        for s in wrkld_sgmnt.sessions :
            previous_query = None
            for q in s.queries :
                # Check to see if the queried collection exists in the design's 
                # de-normalization scheme
                if design.hasCollection(q.collection) :
                    process = False
                    parent_col = design.getParentCollection(q.collection)
                    if previous_query == None :
                        process = True
                    elif parent_col == q.collection :
                        process = True
                    elif previous_query.type <> 'select' or q.type <> 'select' :
                        process = True
                    elif previous_query.collection <> parent_col :
                        process = True
                    if process == True :
                        worst_case += self.nodes
                        query_count += 1
                        if q.type == 'insert' :
                            result += 1
                        else :
                            # Network costs of SELECT, UPDATE, DELETE queries are based off
                            # of using the sharding key in the predicate
                            if len(q.predicates) > 0 :
                                scan = True
                                query_type = None
                                for k,v in q.predicates.iteritems() :
                                    if design.inShardKeyPattern(q.collection, k) :
                                        scan = False
                                        query_type = v
                                if scan == False :
                                    # Query uses shard key... need to determine if this is an
                                    # equality predicate or a range type
                                    if query_type == 'equality' :
                                        result += 0.0
                                    else :
                                        nodes = self.guessNodes(design, q.collection, k)
                                        result += nodes
                                else :
                                    result += self.nodes
                            else :
                                result += self.nodes
                    else :
                        # query does not need to be processed
                        pass
                else :
                    # Collection is not in design.. don't count query
                    pass
                previous_query = q
        if worst_case == 0 :
            cost = 0
        else :
            cost = result / worst_case
        return (cost, query_count)
        
    '''
    Serve as a stand-in for the EXPLAIN function referenced in the paper?
    
    How do we use the statistics to determine the selectivity of this particular
    attribute and thus determine the number of nodes required to answer the query?
    '''
    def guessNodes(self, design, collection, key) : 
        return math.ceil(self.stats[collection]['fields'][key]['selectivity'] * self.nodes)
        
    '''
    Estimate the amount of memory required by the indexes of a given design
    '''
    def getIndexSize(self, design) :
        memory = 0
        for col in design.getCollections() :
            # Add a hit for the index on '_id' attribute for each collection
            memory += self.stats[col]['tuple_count'] * self.stats[col]['avg_doc_size']
            
            # Process other indexes for this collection in the design
            for index in design.getIndexesForCollection(col) :
                memory += self.stats[col]['tuple_count'] * self.address_size * len(index)
        return memory
        
    '''
    Estimate the percentage of a collection that will fit in working set space
    '''
    def estimateWorkingSets(self, design, capacity) :
        working_set_counts = {}
        leftovers = {}
        buffer = 0
        needs_memory = []
        
        # create tuples of workload percentage, collection for sorting
        sorting_pairs = []
        for col in design.getCollections() :
            sorting_pairs.append((self.stats[col]['workload_percent'], col))
        sorting_pairs.sort(reverse=True)
        
        # iterate over sorted tuples to process in descending order of usage
        for pair in sorting_pairs :
            memory_available = capacity * pair[0]
            memory_needed = self.stats[pair[1]]['avg_doc_size'] * self.stats[pair[1]]['tuple_count']
            
            # is there leftover memory that can be put in a buffer for other collections?
            if memory_needed <= memory_available :
                working_set_counts[pair[1]] = 100
                buffer += memory_available - memory_needed
            else :
                col_percent = memory_available / memory_needed
                still_needs = 1.0 - col_percent
                working_set_counts[pair[1]] = math.ceil(col_percent * 100)
                needs_memory.append((still_needs, pair[1]))
        
        '''
        This is where the problem is... Need to rethink how I am doing this.
        '''
        for pair in needs_memory :
            memory_available = buffer
            memory_needed = (1 - (working_set_counts[pair[1]] / 100)) * self.stats[pair[1]]['avg_doc_size'] * self.stats[pair[1]]['tuple_count']
            
            if memory_needed <= memory_available :
                working_set_counts[pair[1]] = 100
                buffer = memory_available - memory_needed
            else :   
                if memory_available > 0 :
                    col_percent = memory_available / memory_needed
                    working_set_counts[pair[1]] += col_percent * 100
        return working_set_counts
    ## end def ##
## end class ##