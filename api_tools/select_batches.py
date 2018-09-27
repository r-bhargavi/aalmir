from openerp import fields, models ,api, _,SUPERUSER_ID
from openerp.exceptions import UserError, ValidationError
import logging
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp
import math
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
import json
import numpy as np

def subset_sum_batches1(batches, target, partial=[]):
    qty_sum = sum([q.approve_qty for q in partial])	
    if qty_sum  == target:		# check if the partial sum is equals to target
    	print "equal....",qty_sum ,target
	return partial
    if qty_sum >= target:		# if sum is greater than quantity continue
    	print "max....",qty_sum ,target
	return  False	
    for i in range(len(batches)):
	n = batches[i]
	remaining = batches[i+1:]
	qty_sum_q = sum([q.approve_qty for q in partial+[n]])	# check if sum of next record is not going beyond
	print "...RRR",i,len(batches),qty_sum_q,target
	if qty_sum_q > target:
		diff = target - qty_sum
		if not any([ diff < q.approve_qty for q in remaining]):
			break
	result_batches=subset_sum_batches(remaining, target, partial+[n])
	if result_batches:
		return result_batches
		
    if qty_sum > target:
    	diff = target - qty_sum
    	if not any([ diff < q.approve_qty for q in batches]):
		return False
    return False
    
def subset_sum_batches(batches, target):
	try:
		partial=[]
		diff=0.0
		for i,start in enumerate(batches):
			partial=[start]
			remaining=batches[i+1:]
			for j,next in enumerate(remaining):
		    		partial.append(next)
		    		qty_sum = sum([q.approve_qty for q in partial])		
		    		if qty_sum  == target:		# check if the partial sum is equals to target
					return partial
		    		if qty_sum >= target:		# if sum is greater than quantity continue
		    			diff = qty_sum - next.approve_qty
		    			partial.pop()
		    			flag=True
		    			if not any([ diff < q.approve_qty for q in remaining[j:]]):
						break
			if flag and diff:
				if not any([ diff < q.approve_qty for q in batches[i:]]):
					break
		return False
	except :
		pass

