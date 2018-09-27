# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api,_
import math
from datetime import datetime
from datetime import datetime, date, time, timedelta
from openerp.exceptions import UserError
import sys
import logging
_logger = logging.getLogger(__name__)
import os


# Conformation wizard in Bin-Bin Transfer
class binLocationValidationWizard(models.TransientModel):
	_name = "bin.location.validation.wizard"

	product_id = fields.Many2one('product.product', string="Product")
	master_batches = fields.Char('Master Batches')
	t_qty = fields.Float(string="Quantity")
	t_qty_unit = fields.Many2one('product.uom', string="unit")
	
	dest_bin_id = fields.Many2one('n.warehouse.placed.product',string='New Bin-Location')
	loc_bin_id  = fields.Many2one('n.warehouse.placed.product',string='Current Bin-Location')
	
	@api.multi
	def transfer_process(self):
		if self._context.get('trsf_id'):
			transfer_id=self.env['location.stock.operation'].search([('id','=',self._context.get('trsf_id'))])
			if transfer_id:
				return transfer_id.bin_transfer_operation()
		else:
		 	raise UserError('Error in Transfer...')
		
	#@api.multi
	#def cancel_process(self):
	#	return True
		
