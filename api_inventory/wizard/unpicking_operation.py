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

# Wizard to Un-Pick Batches from PIcking List(Picked Batches)
class unpickBatchesWizard(models.TransientModel):
	_name = "unpick.picked.batches"

	line_ids = fields.One2many('unpick.picked.batches.line','line_id',string="Master Batches")
	pick_id = fields.Many2one('stock.pack.operation', string="Operation")
	picking_id = fields.Many2one('stock.picking', string="Operation")
	qty = fields.Float(string="Quantity",help="Quantity Schedule to Dispatch")
	unit = fields.Many2one('product.uom', string="unit")
	pick_qty = fields.Float(string="Pick Quantity")
	pick_unit = fields.Many2one('product.uom', string="unit")
	unpick_qty = fields.Float(string="Unpick Quantity",compute="_get_Unpick_quantity")
	unpick_unit = fields.Many2one('product.uom', string="unit")
	product_id = fields.Many2one('product.product', string="Product")
	store_id = fields.Many2one('n.warehouse.placed.product', 'Transfer To',help="Transfer to Bin-Location")
	
	@api.model
	@api.depends('line_ids.check')
	def _get_Unpick_quantity(self):
		for rec in self:
			qty=sum([q.qty for q in rec.line_ids if q.check])
			rec.unpick_qty=qty			
	
	@api.multi
	def process(self):
		'''Function to UN-Pick Batches from Picking List
		   Un-Pick Batches move to Transit-In Location'''
		for rec in self:
			if not any([q.check for q in rec.line_ids]):
				raise UserError('Please Select batch to Unpick')
			total_quantity=pkg_capicity=0.0
			rem_batches=[]
			master_batch_name = ''
			transit_id=total_qty_unit=pkg_capicity_unit = pkg_unit=False	
			for line in rec.line_ids:
                                print "line------------------------",line
				if not q.check:
                                    continue
				master_batch_id = line.master_id
				Packaging_type = master_batch_id.packaging
				pkg_capicity_unit = pkg_unit = master_batch_id.packaging.uom_id
				total_qty_unit = master_batch_id.uom_id
				master_batch_name += line.master_id.name+','
				master_batch_id.write({'store_id':rec.store_id.id,
							'picking_id':False,
							'logistic_state':'transit_in'})
				for btch in master_batch_id.batch_id:
					btch.write({'store_id':rec.store_id.id,
							'picking_id':False,
							'logistic_state':'transit_in',
							'batch_history':[(0,0,{'operation':'picking',
				   	'description':'UnPick from Transit-OUT to Transit-IN for Picking-LIST \
				   	 {}'.format(rec.picking_id.id)})]})
					total_quantity += btch.convert_product_qty
					rem_batches.extend([(3,x.id) for x in master_batch_id.batch_id])
				transit_id = line.store_id
                                print "transit_idtransit_id",transit_id,line
			# to update batches in pack Operation
			rec.pick_id.batch_number = rem_batches
			
			body1 ='<ul>Un-Picking Operation for {} </ul>'.format(rec.picking_id.name)
			qty = total_quantity
			packages = len(rem_batches)
			# Remove product from Transit-OUT
			for multi in self.env['store.multi.product.data'].search([
									('store_id','=',transit_id.id),
									('product_id','=',rec.product_id.id),
									('Packaging_type','=',Packaging_type.id)]):
				if qty>0:
					if multi.total_quantity <= qty :
						qty -= multi.total_quantity
						multi.sudo().unlink()
			
					elif multi.total_quantity > qty :
						multi.write({'total_quantity':multi.total_quantity-qty, 
							     'packages':multi.packages - packages})
					     	qty =0.0
			     		else:
						print "ERROR in multi product..."
						err
						raise
				else:
					break
		
			self.env['location.history'].create({'stock_location':transit_id.id,
							'product_id':rec.product_id.id,
							'operation_name':'Send To Transit-IN Due to UnPicking',
							'operation':'do',
							'qty':total_quantity,
							'n_type':'out'})
									
			# search for product Transit -IN location..	according packaging
			store_product=self.env['store.multi.product.data'].search([
							('product_id','=',rec.product_id.id),
						        ('store_id','=',rec.store_id.id),
							('Packaging_type','=',Packaging_type.id)])
							
			body1+='<li>Master Batch :{} </li>'.format(master_batch_name)
			if not store_product: # If product is not found add product
				add_vals={'product_id':rec.product_id.id}
				body1 +="<li>Product add : "+str(rec.product_id.name)+" </li>"
				add_vals.update({'total_quantity':total_quantity})
				add_vals.update({'total_qty_unit':total_qty_unit.id})
				body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
				body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
				add_vals.update({'packages':packages})
				add_vals.update({'pkg_unit':pkg_unit.id})
				add_vals.update({'Packaging_type':Packaging_type.id})
				body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
				rec.store_id.multi_product_ids=[(0,0,add_vals)]	
				rec.store_id.message_post(body1)		
		
			elif store_product: # if found update quantity and packages
				body1 +="<li>Product update qty : "+str(rec.product_id.name)+" </li>"
				store_product.total_quantity += total_quantity
				body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
				store_product.packages += packages
				body1+="<li>Packages updated: "+str(packages)+" </li>"
				transit_id.message_post(body1)
	
			self.env['location.history'].create({'stock_location':transit_id.id,
							'product_id':rec.product_id.id,
							'operation_name':'Du to Un-Pick batches from Picking List',
							'operation':'do',
							'qty':total_quantity,
							'n_type':'in'})
			rec.pick_id.pick_qty -= total_quantity
			
class unpickBatchesLlineWizard(models.TransientModel):
	_name = "unpick.picked.batches.line"

	line_id = fields.Many2one('unpick.picked.batches', string="Line")
	master_id = fields.Many2one('stock.store.master.batch', string="Master Batche")
	qty = fields.Float(string="Quantity")
	qty_unit = fields.Many2one('product.uom', string="unit")
	check = fields.Boolean(string="Select")
	store_id = fields.Many2one('n.warehouse.placed.product', 'Bin-Location')
	
	
