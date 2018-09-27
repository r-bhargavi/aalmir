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
import math

##  Show wizards on quantity transfer from inventory loss  >> INput Location
##  Show wizards on quantity transfer from INput Location >> Stock (Transit Location)

##  Show wizards on quantity transfer from Production >> INput Location (Manufacturing Dashboard)

class stock_immediate_transfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    @api.multi
    def process(self):
    	self.ensure_one()
    	#from INput_location >> Stock(Transit IN)
	if self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.pre_ck and self.pick_id.location_dest_id.actual_location:   
		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			#if not operation.qty_done:
			#	continue
			if not operation.packaging_id :
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
				
			elif not operation.secondary_pack:
				if not 'store' in operation.packaging_id.uom_id.unit_type.mapped('string'):
					raise UserError("Secondary Packaging of product '{}' not  defined".format(operation.product_id.name))
					
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or \
								equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id}))
		
		wizard_id=self.env['stock.store.location.wizard'].search([('picking','=',self.pick_id.id)])
						
		wizard_id.unlink()
		bin_id= self.env['stock.location.view'].search([
				('location_id','=',self.pick_id.location_dest_id.id),
				('location_type','=','transit_in')],limit=1)
		bin_location_id=self.env['n.warehouse.placed.product'].search([('n_location_view','=',bin_id.id)])

		data=self.env['stock.backorder.confirmation']._get_bacthes(self.pick_id)
		vals={'picking':self.pick_id.id,'wizard_line':data,'locations':bin_location_id.id,
			'wizard_product_line':product_data,'immediate_tra':self.id}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.incomming_batches_form_view_wizard')
		return {
			'name' :'Generate Master Batches',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
		    
        #from  INventry loss/Purchase  >> INput_location (Purchase /Inventory Loss)
        elif (self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.usage == 'inventory' and self.pick_id.ntransfer_type !='manufacturing') or (self.pick_id.picking_type_code =='incoming') :
    		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			#if not operation.qty_done:
			#	continue
			if operation.product_id.type != 'product':
				# to Create Batches for only Stockable Product
				continue
						
			if not operation.packaging_id:
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or \
								equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id,
						'pack_id':operation.id,
						'max_batches':math.ceil(operation_qty/operation.packaging_id.qty),
						'btch_unit':operation.packaging_id.uom_id.id,}))
		
		wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',self.pick_id.id)])
		wizard_id.unlink()
		vals={'picking':self.pick_id.id,'wizard_product_line':product_data,'immediate_tra':self.id}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.inventory_loss_batches_form_view_wizard')
		return {
			'name' :'Generate Full Quantity Batches for Purchased Product',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
		    
	else:	    
		# If still in draft => confirm and assign
		if self.pick_id.state == 'draft':
		    self.pick_id.action_confirm()
		    if self.pick_id.state != 'assigned':
		        self.pick_id.action_assign()
		        if self.pick_id.state != 'assigned':
		            raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
		for pack in self.pick_id.pack_operation_ids:
		    if pack.product_qty > 0:
		        pack.write({'qty_done': pack.product_qty})
		    else:
		        pack.unlink()
		self.pick_id.do_transfer()

class stock_backorder_confirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'
    
    @api.multi
    def process(self):
        self.ensure_one()
        ##from INput_location >> Stock(Transit IN)
        if self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.pre_ck and self.pick_id.location_dest_id.actual_location:
    		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			if not operation.qty_done:
				continue
			if operation.product_id.type != 'product':
				# to Create Batches for only Stockable Product
				continue
				
			if not operation.packaging_id:
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
			elif not operation.secondary_pack:
				if not 'store' in operation.packaging_id.uom_id.unit_type.mapped('string'):
					raise UserError("Secondary Packaging of product '{}' not  defined".format(operation.product_id.name))
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity. \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id}))
		
		wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',self.pick_id.id)])
		wizard_id.unlink()
		bin_id= self.env['stock.location.view'].search([
				('location_id','=',self.pick_id.location_dest_id.id),
				('location_type','=','transit_in')],limit=1)
		bin_location_id=self.env['n.warehouse.placed.product'].search([
				('n_location_view','=',bin_id.id)])

		data=self._get_bacthes(self.pick_id)
		vals={'picking':self.pick_id.id,'wizard_line':data,'locations':bin_location_id.id,
			'wizard_product_line':product_data,'back_order_id':self.id,'backorder':False}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.incomming_batches_form_view_wizard')
		return {
			'name' :'Generate Master Batches',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
		    
        elif (self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.usage == 'inventory' and self.pick_id.ntransfer_type !='manufacturing') or self.pick_id.picking_type_code=='incoming':
    		## Record in Purchase or INventory loss
    		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			if not operation.qty_done:
				continue
			if operation.product_id.type != 'product':
				# to Create Batches for only Stockable Product
				continue
				
			if not operation.packaging_id:
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or \
								equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id,
						'pack_id':operation.id,
						'max_batches':math.ceil(operation_qty/operation.packaging_id.qty),
						'btch_unit':operation.packaging_id.uom_id.id,}))

		wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',self.pick_id.id)])
		wizard_id.unlink()
		vals={'picking':self.pick_id.id,'wizard_product_line':product_data,
			'back_order_id':self.id,'backorder':False}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.inventory_loss_batches_form_view_wizard')
		return {
			'name' :'Generate Batches',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
        else:
        	self._process()

    @api.multi
    def process_cancel_backorder(self):
        self.ensure_one()
        # Send to Warehouse
        if self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.pre_ck and self.pick_id.location_dest_id.actual_location:
    		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			if not operation.qty_done:
				continue
			if operation.product_id.type != 'product':
				#to Create Batches for only Stockable Product
				continue
				
			if not operation.packaging_id:
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
			elif not operation.secondary_pack:
				if not 'store' in operation.packaging_id.uom_id.unit_type.mapped('string'):
					raise UserError("Secondary Packaging of product '{}' not  defined".format(operation.product_id.name))
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or \
								equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id}))
		
		wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',self.pick_id.id)])
		wizard_id.unlink()
		bin_id= self.env['stock.location.view'].search([
				('location_id','=',self.pick_id.location_dest_id.id),
				('location_type','=','transit_in')],limit=1)
		bin_location_id=self.env['n.warehouse.placed.product'].search([
				('n_location_view','=',bin_id.id)])

		data=self._get_bacthes(self.pick_id)
		vals={'picking':self.pick_id.id,'wizard_line':data,'locations':bin_location_id.id,
			'wizard_product_line':product_data,'back_order_id':self.id,'backorder':True}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.incomming_batches_form_view_wizard')
		return {
			'name' :'Generate Master Batches',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
	# send to INput	    
	elif (self.pick_id.picking_type_code =='internal' and self.pick_id.location_id.usage == 'inventory' and self.pick_id.ntransfer_type !='manufacturing') or self.pick_id.picking_type_code=='incoming':
    		product_data = []
		for operation in self.pick_id.pack_operation_product_ids:
			if operation.product_id.type != 'product':
				# to Create Batches for only Stockable Product
				continue
			if not operation.qty_done:
				continue
			if not operation.packaging_id:
				raise UserError("Packaging of product '{}' not found".format(operation.product_id.name))
			if operation.qty_done > operation.product_qty:
				if self.pick_id.purchase_id and not self.pick_id.purchase_id.allow_extra:
					raise UserError("Done Quantity Should be less than or \
							equal to Product Quantity \n If You want to receive Extra, \
						 Please contact Purchase Manager to Set Allow Extra in Purchase Order")
				elif not self.pick_id.purchase_id:
					raise UserError("Done Quantity Should be less than or equal to Product Quantity")
			operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
			product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation_qty,
						'qty_unit':operation.product_uom_id.id,
						'pack_id':operation.id,
						'max_batches':math.ceil(operation_qty/operation.packaging_id.qty),
						'btch_unit':operation.packaging_id.uom_id.id,}))
		
		wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',self.pick_id.id)])
		wizard_id.unlink()
		vals={'picking':self.pick_id.id,'wizard_product_line':product_data,
			'back_order_id':self.id,'backorder':True}

		res_id=self.env['stock.store.location.wizard'].create(vals)
		form_id = self.env.ref('api_inventory.inventory_loss_batches_form_view_wizard')
		return {
			'name' :'Generate Batches',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'stock.store.location.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'res_id':res_id.id,
		    }
     	else:
        	self._process(cancel_backorder=True)

    @api.model
    def _get_bacthes(self,pick_id):
    	''' This method is used to get batches for master Batches in wizard on validation in Move_to_Store picking '''
    	data=[]
    	picking_obj = self.env['stock.picking']
    	mrp_id=self.env['mrp.production'].search([('name','=',pick_id.origin)],limit=1)
    	purchase=self.env['purchase.order'].search([('name','=',pick_id.origin)],limit=1)
    	sequence = self.env['ir.sequence'].search([('code','=','master.batch')])
    	operation_obj = self.env['stock.pack.operation']
    	batches_obj=self.env['mrp.order.batch.number']
	    	
    	try:
	    	picking_id=picking_obj.search([('name','=',pick_id.origin)],limit=1) # check if picking is in chain operation and quantity comes from inventory loss
	    	next= sequence.get_next_char(sequence.number_next_actual)
	    	
	    	if purchase or not picking_id:
		    	for move in pick_id.move_lines_related:
			    	move_id=self.env['stock.move'].search([('move_dest_id','=',move.id),('state','=','done')])
			    	if move_id.picking_id:
				    	picking_id = move_id.picking_id
				    	break
	    	for res in pick_id.pack_operation_product_ids:
	    		if res.product_id.type != 'product':
				# to Create Master Batches for only Stockable Product
				continue
				
			pckg_qty=res.pallet_no if res.secondary_pack else 1
			lots,batches=(),()
			btch=0
			# if Product Quantity is comes from Purchase/inventory Loss(Add Quantity)/Production
			n_picking = picking_id
			if picking_id:
				if picking_id.state !='done':
					raise ValueError('Previous Chain Operation is not performed Please Complete That Operation')
				back_id=picking_id.id
				while True:
					new_id=picking_obj.search([('backorder_id','=',back_id),('state','=','done')])
					if not new_id:
						break
					n_picking +=new_id
					back_id = new_id.id
				batches_ids=()
				operation = operation_obj.search([('product_id','=',res.product_id.id),
								  ('picking_id','in',n_picking._ids)])
				for op in operation:
					batches_ids += (op.batch_number._ids)
					if not op.batch_number:
						batches_ids += (op.produce_batches._ids)
				search_batches=batches_obj.search([('logistic_state','=','ready'),
						('store_id','=',False),('product_id','=',res.product_id.id),
						('product_qty','>',0),('id','in',batches_ids)],order="id")
				max_pallet=res.total_pallet_qty
				for batch in search_batches:
					batches += (batch.id,)
					if batch.lot_id.id not in lots:
						lots += (batch.lot_id.id,)
					pckg_qty -= 1
					btch += 1
					if pckg_qty <= 0 or btch == res.pack_qty:
						data.append((0,0,{'product_id':res.product_id.id,'master_batch':next,
						'max_qty':res.pallet_no if res.secondary_pack else 1,
						'batch_qty':len(batches),
						'packaging':res.packaging_id.id,'sec_packaging':res.secondary_pack.id,
						'lot_ids':[(6,0,lots)],'batch_ids':[(6,0,batches)]}))
						next=next[:4]+str(int(next[4:])+1).zfill(5)
						pckg_qty=res.pallet_no if res.secondary_pack else 1
						lots,batches=(),()
						max_pallet -= 1
					if max_pallet <=0:
						break

			# Quantity Comes from Manufacturing process
			elif mrp_id:
				bacthes_ids=batches_obj.search([('production_id','=',mrp_id.id),
								('logistic_state','=','ready'),
								('store_id','=',False),('product_qty','>',0),
								('id','not in',tuple(completed_ids))])
				for batch in bacthes_ids:
					batches.append(batch.id)
					completed_ids.append(batch.id)
					lots.append(batch.lot_id.id)
					btch +=1
					if btch >= pckg_qty:
						break
					
	except Exception as error:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		_logger.error("API-EXCEPTION. Calculate master Batches data {} {} {}".format(repr(error),fname,exc_tb.tb_lineno))
		raise UserError("API-EXCEPTION. {} Contact Administrator and check Log".format(error))
	return tuple(data)


