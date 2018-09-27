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
import openerp.addons.decimal_precision as dp

# Conformation wizard To Product batch in Production
class productionBatchesProduce(models.TransientModel):
	_name = "production.batches.produce"

	product_id = fields.Many2one('product.product', string="Product")
	pick_id = fields.Many2one('stock.pack.operation', string="Operation")
	qty = fields.Float(string="Quantity")
	qty_unit = fields.Many2one('product.uom', string="unit")
	date = fields.Datetime(string="Produce Date",required=True)
	employee_name=fields.Many2one('hr.employee',string='Operators Name',required=True)
	document_ids = fields.Many2many('ir.attachment','batches_produce_wiz_attachment_rel','wiz_id','doc_id','Documents')
	remark=fields.Text('Remark')
	produce_batches = fields.Many2many('mrp.order.batch.number','batches_produce_wizard_rel',
				'batch_id','wiz_id','Documents')
	
	@api.onchange('produce_batches')
	def _get_quantity(self):
		for rec in self:
			qty=sum([q.product_qty for q in rec.produce_batches])
			rec.qty=qty
			
	@api.multi
	def produce_batch(self):
		for line in self.produce_batches:
			vals={'produce_bool':True,'print_bool':False}
			if self.employee_name:
				vals.update({'employee_name':self.employee_name.name})
			if self.document_ids:
				vals.update({'document':[(4,i.id) for i in self.document_ids]})
			if self.remark:
				vals.update({'remark':self.remark})
			if self.date:
				vals.update({'produce_qty_date':self.date})
			line.write(vals)
			line.batch_history=[(0,0,{'operation':'production','description':
				'Produce by {} on {} Quantity {} '.format(self.employee_name.name,str(self.date),line.product_qty)})]
			if self.pick_id:
				self.pick_id.qty_done = sum([q.product_qty for q in self.pick_id.produce_batches if q.produce_bool])

# Wizard to Split batch
class mrpBatchSplitWizard(models.TransientModel):
	_name = "mrp.batch.split.wizard"

	product_id = fields.Many2one('product.product', string="Product")
	batch_id = fields.Many2one('mrp.order.batch.number', string="Batch Number")
	qty = fields.Float(string="Quantity",digits=dp.get_precision('Product Unit of Measure'))
	qty_unit = fields.Many2one('product.uom', string="unit")
	split_qty = fields.Float(string="Split Quantity")
	new_number=fields.Text('New Number')
	
	@api.multi
	def split_batch(self):
		if not self.batch_id:
			raise UserError('Please Select batch to Split')
		if not self.batch_id.store_id:
			raise UserError("You can split only Stock batches")
			
		if self.qty < self.split_qty:
			raise UserError("Please Enter Split quantity less than Batch Quanitty")
		if self.qty <=0:
			raise UserError("you can't Split Batch which quantity is 0")
		
		ids=self.env['mrp.order.batch.number'].search([('name','ilike',self.batch_id.name)])
        	new_number = self.batch_id.name+str('_{}'.format(len(ids)))
		new_id=self.batch_id.copy({'product_qty':self.split_qty,'approve_qty':self.split_qty,
					'name':new_number})
		self.batch_id.product_qty -= self.split_qty
		self.batch_id.approve_qty -= self.split_qty 
		self.batch_id.batch_history = [(0,0,{'operation':'split','description':'Split batch to {} with qty {}'.format(new_id.name,self.split_qty)})]
		if self.batch_id:
			if self.batch_id.store_id.location_type=='store':
				self.batch_id.store_id.packages +=1
		new_id.batch_history = [(0,0,{'operation':'split','description':'Split batch from {} with qty {}'.format(self.batch_id.name,self.split_qty)})]

