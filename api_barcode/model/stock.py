from openerp.addons import decimal_precision as dp
from openerp import models, fields, api,_
import time
import datetime
from datetime import datetime
from datetime import datetime, date, time, timedelta
from urlparse import urljoin
from urllib import urlencode
from time import gmtime, strftime
import math
from openerp.exceptions import UserError, ValidationError
import sys
import logging
_logger = logging.getLogger(__name__)
import os
import re


def ean_checksum(eancode):
    """returns the checksum of an ean string of length 13, returns -1 if the string has the wrong length"""
    if len(eancode) != 13:
        return -1
    oddsum = 0
    evensum = 0
    eanvalue = eancode
    reversevalue = eanvalue[::-1]
    finalean = reversevalue[1:]

    for i in range(len(finalean)):
        if i % 2 == 0:
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
    total = (oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10.0)) % 10
    return check

def generate_ean(ean):
    """Creates and returns a valid ean13 from an invalid one"""
    if not ean:
        return "0000000000000"
    ean = re.sub("[A-Za-z]", "0", ean)
    ean = re.sub("[^0-9]", "", ean)
    ean = ean[:13]
    if len(ean) < 13:
        ean = ean + '0' * (13 - len(ean))
    return ean[:-1] + str(ean_checksum(ean))

class StockWarehouseMain(models.Model):
	_inherit='n.warehouse.placed.product'
	
	#ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
    	barcode=fields.Char('Barcode')
        barcode_copy=fields.Char('Barcode Number', related='barcode')
	
        @api.model
        def create(self, vals):
		res = super(StockWarehouseMain, self).create(vals)
		ean = generate_ean(str(res.id))
		res.barcode = ean
		return res
        	
