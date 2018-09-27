
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

class Saleorder(models.Model):
	_inherit='sale.order'
	ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
    	barcode=fields.Char('Barcode',copy=False)
        barcode_copy=fields.Char('Barcode Number', related='barcode')
        
class Stockpicking(models.Model):
	_inherit='stock.picking'
	ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
	barcode=fields.Char('Barcode',copy=False)
	barcode_copy=fields.Char('Barcode Number', related='barcode')

class MrpOrderBatchNumber(models.Model):
	_inherit='mrp.order.batch.number'
	ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
	barcode=fields.Char('Barcode',copy=False)

class AccountInvoice(models.Model):
	_inherit='account.invoice'
	ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
	barcode=fields.Char('Barcode',copy=False)


class Mrprpoduction(models.Model):

	_inherit='mrp.production'
	ean_sequence_id= fields.Many2one('ir.sequence', 'Ean Sequence')
	barcode=fields.Char('Barcode',copy=False)
	barcode_copy=fields.Char('Barcode Number', related='barcode')
            
            
