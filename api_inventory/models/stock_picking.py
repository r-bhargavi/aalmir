# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, exceptions, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime,date
import re
from dateutil.relativedelta import relativedelta
import math
import sys
import logging
_logger = logging.getLogger(__name__)
import os
import base64

def subset_sum_batches(batches, target):
	try:
		partial=[]
		diff=0.0
		for i,start in enumerate(batches):
			partial=[start]
			partial_sum = sum([q.convert_product_qty for q in partial])
			if partial_sum == target: # check if the partial sum is equals to target
				return partial
				
			flag=False
			ntarget = target - partial_sum
			if all([ q.convert_product_qty > ntarget for q in batches[i+1:]]):
				continue
			remaining=[x for x in batches[i+1:] if x.convert_product_qty<=ntarget ]
			for j,next in enumerate(remaining):
				# existing qty + new batch Quantity
				partial_sum += next.convert_product_qty
		    		if target == partial_sum :# check if the partial sum is equals to target
		    			partial.append(next)
					return partial
		    		elif target > partial_sum:	# if sum is greater than quantity continue
		    			diff = qty_sum - target
		    			partial_sum -= next.convert_product_qty
		    			nremaining = batches[j+1:]
	    				if all([ q.convert_product_qty>diff for q in nremaining]):
						break
				else:
					partial.append(next)
		return []
	except Exception as err:
		exc_type, exc_obj, exc_tb = sys.exc_info()
    		_logger.error("API-EXCEPTION..Exception in batches counting {} {}".format(err,exc_tb.tb_lineno))
				
class stockPicking(models.Model):
	_inherit = "stock.picking"
        
        pick_ref=fields.Many2one('stock.picking', string='Pick Ref')
     	store_ids = fields.One2many('picking.lot.store.location','picking_id','Store Location')
     	ntransfer_type = fields.Selection(selection_add=[('pre_stock','Move To Stock'),
     							('manufacturing','Manufacturing Transfer'),
							('invt_loss','Inventory'),
							('sen_to_produciton','Send To Production')])
     	
     	@api.model
     	def create(self,vals):
     		if vals.get('location_id') and vals.get('location_dest_id'):
     			if vals.get('location_id') == vals.get('location_dest_id'):
     				raise UserError('You are trying to do Internal Transfer in Same-Location')
     				
     		res =super(stockPicking,self).create(vals)
     		if res.location_id.pre_ck and res.location_dest_id.actual_location:
     			res.ntransfer_type='pre_stock'
			res.term_of_delivery=False
		if res.location_id.usage == 'inventory':
			res.ntransfer_type='invt_loss'
		if res.picking_type_code == 'outgoing':
			res.ntransfer_type='develiry'
				
		if res.picking_type_id.code == 'internal':
			res.report_name='Internal Transfer'
		elif res.picking_type_id.code == 'incoming':
			if res.ntransfer_type == 'do_return' :
				res.report_name='Goods Return Note'
			else:
				res.ntransfer_type='receipt'
				res.report_name='Receipt Order'
		if res.ntransfer_type == 'manufacturing':
			res.report_name='Production Transfer'
     		return res
     	
     	@api.multi
     	def write(self,vals):
     		for res in self:
			if vals.get('location_id') and vals.get('location_dest_id'):
	     			if vals.get('location_id') == vals.get('location_dest_id'):
	     				raise UserError('You are trying to do Internal Transfer in Same-Location')
			elif vals.get('location_id') and res.location_dest_id:
	     			if vals.get('location_id') == res.location_dest_id.id:
	     				raise UserError('You are trying to do Internal Transfer in Same-Location')
			elif vals.get('location_dest_id') and res.location_id:
	     			if res.location_id.id == vals.get('location_dest_id'):
	     				raise UserError('You are trying to do Internal Transfer in Same-Location')
     		return super(stockPicking,self).write(vals)
   
     	#Dispatch button click >>>>>inherited method	
	@api.multi
	def action_first_validation(self):
		'''Function to open the dispatch Wizard'''
		for rec in self:
			if rec.picking_status !='r_t_dispatch':
				raise UserError('Please Close Picking List to Dispatch this Order.')
				
			if rec.picking_type_id.code=='outgoing':  
				data=[]
				wizard_id=self.env['stock.store.location.wizard'].search([('picking','=',self.id)])
				wizard_id.unlink()
				# call method to get picked master batch data
				data=self._get_bacthes(rec.origin)
				location_view = self.env['stock.location.view'].search([
									('location_type','=','transit_out'),
									('location_id','=',rec.location_id.id)])
				location_dest = self.env['n.warehouse.placed.product'].search([
									('n_location_view','=',location_view.id)])
				vals={'picking':rec.id,'status':'dispatch', 
					'wizard_line':data,'locations':location_dest.id}
				res_id=self.env['stock.store.location.wizard'].create(vals)
				if res_id:
					form_id = self.env.ref('api_inventory.store_locations_form_view_wizard_outgoing')
					return {
						'name' :'Dispatch Products',
						'type': 'ir.actions.act_window',
						'view_type': 'form',
						'view_mode': 'form',
						'res_model': 'stock.store.location.wizard',
						'views': [(form_id.id, 'form')],
						'view_id': form_id.id,
						'target': 'new',
						'res_id':res_id.id,
					    }
		return super(stockPicking,self).action_first_validation_data()
     		
	@api.multi
	def _get_bacthes(self,origin):
		'''Calculate batches for dispatching from Transit-OUT '''
		for res in self:
			data=[]
			for operation in res.pack_operation_product_ids:
				#batch_id=self.env['mrp.order.batch.number'].search([('sale_id','=',res.sale_id.id),
				#	('product_id','=',operation.product_id.id),('store_id','!=',False),
				#	('logistic_state','=','transit'),('picking_id','=',res.id),
				#	],order="id asc")
				batch_id=operation.batch_number
				
				master_batches=[]
				to_do= operation.qty_done if operation.qty_done else operation.product_qty
				qty_unit=operation.product_uom_id.id
				pick_qty=0.0
				for b_qty in batch_id:
					if b_qty.master_id.id not in master_batches:
						master_batches.append(b_qty.master_id.id)
						pick_qty += b_qty.master_id.total_quantity
					qty_unit=b_qty.qty_unit_id.id
				
				data.append((0,0,{'product_id':operation.product_id.id,'to_do_qty':to_do,
						'to_do_unit':qty_unit,
						'pick_qty':pick_qty,
						'packaging':operation.packaging_id.id,
						'pack_id':operation.id,
						'master_batches':[(6,0,master_batches)],}))
			return data			

# show picking list form with product quantity to dispatch on clicking PICKING LIST In delivery order
	@api.multi
	def show_picking_list(self):
		data={'name' :'Select Bin-Location',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'stock.picking',
				
				'target': 'current',
				'res_id':self.id,
			    }
		form_id = self.env.ref('api_inventory.store_picking_list_batch_form_view')
		context=self._context.copy()		    
		if self.picking_type_code=='internal':
			if self.location_dest_id.actual_location and self.location_id.actual_location:
				data.update({'views': [(form_id.id, 'form')],
						'view_id': form_id.id,})
				return data
			if self.location_id.actual_location and  self.location_dest_id.usage == 'production':
				data.update({'views': [(form_id.id, 'form')],
						'view_id': form_id.id,})
				return data
		if self.picking_type_code=='outgoing':  
			data.update({'views': [(form_id.id, 'form')],
					'view_id': form_id.id,})
			return data

	# call from dispatch wizard
	@api.multi
	def action_first_validation_data(self):
	    try:
		sale_status_line=self.env['sale.order.line.status']
		for pick in self:
		    if not pick.dispatch_date:
			    pick.dispatch_date=datetime.today()
		    # call default method for stock picking/location wizard
		    pick.do_new_transfer()
		    if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
		    	wiz_id = self.env['stock.immediate.transfer'].search([('pick_id','=',pick.id)],order='id desc',limit=1)
		    	if wiz_id:
		    		wiz_id.process()
	    	    else:
	    		wiz_id = self.env['stock.backorder.confirmation'].search([('pick_id','=',pick.id)],order='id desc',limit=1)
	    		if wiz_id:
		    		wiz_id._process()
		    		
		    backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', pick.id)])
		    if len(backorder_pick)>1:
		    	 raise UserError('More backorder found, Please contact with administrator')
		    
		    #if backorder_pick and backorder_pick.state in ('assigned','partially_available'):
			#backorder_pick.picking_status='pick_list'
		    #selif backorder_pick:
		    #backorder_pick.picking_status='draft'
				
		    for line in pick.pack_operation_product_ids:
		        # add product in sale order line  when delivered qty is greater than order qty
			if line.n_sale_order_line:
			#CH_N062 UPdate status in reserve history >>>
				for resr in line.n_sale_order_line.res_ids:
					if resr.picking_id.id==pick.id:
						if resr.n_status=='r_t_dispatch':
							if (resr.res_qty-line.qty_done)>0:
								default_dic={'res_qty':(resr.res_qty-line.qty_done),
									     'picking_id':backorder_pick.id,
									     'n_status':'release',
									     'n_reserve_Type':'do'}
								n_resr=resr.copy(default=default_dic)
							resr.write({'res_qty':line.qty_done,'n_status':'dispatch'})
							break
			#CH_N062<<<<<<<<<<<<
				if (line.n_sale_order_line.reserved_qty-line.qty_done)>=0:
					line.n_sale_order_line.reserved_qty -= line.qty_done
				else:
					line.n_sale_order_line.reserved_qty=0.0
				if line.n_sale_order_line.product_uom_qty <= line.n_sale_order_line.qty_delivered:
					status_list = []
					search_id=sale_status_line.search([('n_string','=','dispatch')],limit=1)
					if search_id:
						status_list.append((4,search_id.id))
					new_id=sale_status_line.search([('n_string','in',
							('r_t_dispatch','partial_dispatch','force_reserve'))])
					if new_id:
						status_list.extend([(3,i.id) for i in new_id])
					line.n_sale_order_line.write({'n_status_rel':status_list})
					n_type='full'
					
				else:
					status_list = []
					search_id = sale_status_line.search([('n_string','=','partial_dispatch')],limit=1)
					if search_id:
						status_list.append((4,search_id.id))
					new_id=sale_status_line.search([('n_string','=','r_t_dispatch')],limit=1)
					if new_id:
						status_list.append((3,new_id.id))
					if status_list:
						line.n_sale_order_line.write({'n_status_rel':status_list})
					n_type='partial'

				exist_rec=self.env['mrp.delivery.date'].search([('n_picking_id','=',pick.id),
							('n_line_id1','=',line.n_sale_order_line.id),
							('n_status','=','r_t_dispatch')],limit=1)
				if not exist_rec:
					self.env['mrp.delivery.date'].create({'n_dispatch_date_d':date.today(),
								'n_status':'dispatch','n_picking_id':pick.id,
								'n_line_id1':line.n_sale_order_line.id,'n_type':'partial'})
				else:
					self.env['schedule.delivery.date.history'].create({
									'n_nextdate':date.today(),
									'n_status':'dispatch',
									'n_picking_id':line.picking_id.id,
									'n_line_id':line.n_sale_order_line.id,
									'delivery_id':exist_rec.id})
					exist_rec.write({'n_status':'dispatch','n_dispatch_date_d':date.today()})
				line.n_sale_order_line._get_schedule_date()
				
		    delivery_data={}
		    for line in pick.pack_operation_product_ids:
		        # add product in sale order line  when delivered qty is greater than order qty
			if line.n_sale_order_line:
		    		line.n_sale_order_line._get_schedule_date()
		    		if line.product_id.type !='product':
		    			continue
	   			delivery_data[line.n_sale_order_line.id] = delivery_data[line.n_sale_order_line.id] +line.qty_done  if delivery_data.get(line.n_sale_order_line.id) else line.qty_done
	   			
    		    # update picking_list status
		    pick.picking_status='dispatch'
		    # Validate Invoice if it in open state
		    if pick.sale_id.auto_invoice and pick.invoice_ids:
		    	body=''
		    	invoice_data={}
		    	for invoice in pick.invoice_ids:
	    			for inv in invoice.invoice_line_ids:
	    				if inv.product_id.type !='product':
		    				continue
					for so_line in inv.sale_line_ids:
						invoice_data[so_line.id] = invoice_data[so_line.id] + inv.quantity  if invoice_data.get(so_line.id) else inv.quantity
			
			equal = greater = less = False		
			for do_prd in delivery_data:
				if not invoice_data.get(do_prd,False):
					line_ids = self.env['sale.order.line'].search([('id','=',do_prd)])
					raise UserError("Product '{}' was not in Invoice".format(line_ids.product_id.name))
				if delivery_data.get(do_prd) == invoice_data.get(do_prd):
					equal=True
				elif delivery_data.get(do_prd) > invoice_data.get(do_prd):
					greater=True
				elif delivery_data.get(do_prd) < invoice_data.get(do_prd):
					less=True
				
			for invoice in pick.invoice_ids:
		    		if invoice.state=='draft' and equal:
		    			invoice.signal_workflow('invoice_open')
		    			body +='<li> <b>{}</b> validate</li>'.format(invoice.number)
	    			elif invoice.state in ('paid','cancel','open'):
	    				pass
		    		else:
		    			raise UserError('Your Invoice quantity in not matching with delivered quantity , Please Contact with Sales-Support or modify invoice related to this delivery order.')	
    			if body:
				pick.message_post(body)
				
		# Send Mail Dispatch Quantity
		    if pick.picking_type_code=='outgoing':  
                        temp_id = self.env.ref('api_inventory.email_template_for_dispatch_done')
                        if temp_id:
                   		recipient_partners=[]
				group = self.env['res.groups'].search([('name', '=', 'Delivery Email')])
				user_obj = self.env['res.users'].browse(self.env.uid)
				for recipient in group.users:
					if recipient.login != user_obj.login:
						if recipient.login != pick.sale_id.user_id.login:
							recipient_partners.append(recipient.login)

				body ='<li>Delivery Order No: '+str(pick.name)+'</li>'
				if pick.min_date:
					body +='<li>Schedule Date: '+str(pick.min_date)+'</li>'
				body +='<li>Sale order: '+str(pick.sale_id.name)+'</li>'
				body +='<li>Customer Name:  '  +str(pick.partner_id.name)+'</li>'
				body +='<li>Dispatched Date:  ' +str(pick.dispatch_date if pick.dispatch_date else '')+'</li>'
				body +='<li> Please Find the attachment for Dispatched Documents</li>'

				attch_ids=[i.id for i in pick.dispatch_doc]
				report_obj = self.env['report']
				attch_obj = self.env['ir.attachment']
				if pick.invoice_ids:
					for inv in pick.invoice_ids:
						data=report_obj.get_pdf(inv,'gt_order_mgnt.report_invoice_aalmir')
						rep_name='Invoice:'+str(inv.number)+'.pdf'
						attachment_data = {
								'name': rep_name,
								'datas_fname': rep_name,
								'datas': base64.encodestring(data),
								'type':'binary'
								  }
						attch_ids.append(attch_obj.create(attachment_data).id)
				attachment_ids=[(6,0,attch_ids)]
				temp_id.write({'body_html': body, 'email_cc':",".join(set(recipient_partners)), 'email_to':self.sale_id.user_id.login,'email_from': user_obj.login,'attachment_ids':attachment_ids})

				if temp_id and temp_id.email_to:
					temp_id.send_mail(self.id)
		return True	
	    except Exception as err:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		_logger.error("API-EXCEPTION Dispatch\n action_first_validation_data {} {}".format(err,exc_tb.tb_lineno))
		raise UserError("API-EXCEPTION..{}".format(err))	
	
	@api.multi
	def do_new_transfer(self):
		'''Add validation on Validate button in stock picking \
		  for data coming form inventory loss and \
		  When quantity move form INput to Stock Location.'''
	    	for res in self:
	    		try:
    			    if res.location_id.usage in ('inventory','production') or res.picking_type_code =='incoming':
    			    	if not res.pack_operation_product_ids:
		    			raise ValueError("Please Make some Operations.")
    			    	
				for rec in res.pack_operation_product_ids:
					if rec.product_id.type != 'product':
						# to Create Batches for only Stockable Product
						continue
					if not rec.packaging_id and rec.qty_done:
						raise ValueError("Packaging of Product [{}]{} is not defined".format(rec.product_id.default_code,rec.product_id.name))
					if rec.qty_done > rec.product_qty and not res.ntransfer_type =='manufacturing':
						if res.purchase_id and not res.purchase_id.allow_extra:
							raise ValueError("Done Quantity Should be less than or \
								equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
						elif not res.purchase_id:
							raise ValueError("Done Quantity Should be less than or \
								equal to Product Quantity")
						
				if not res.location_dest_id.pre_ck:
					raise ValueError("Please Select Only Input Location To move quantity")
				
				#from Production >>> INput Location (Production)
				if not self._context.get('production_batches') and res.picking_type_code =='internal' and res.ntransfer_type =='manufacturing' and res.location_id.usage == 'production':
					product_data = []
					for operation in res.pack_operation_product_ids:
						new_batches=[q.id for q in operation.produce_batches if (q.product_qty>0 and q.produce_bool)]
						if not new_batches:
							raise ValueError("Please Produce Batches First")
						if operation.product_id.type != 'product':
							raise UserError('You can select only Stockable Product to \
									 generate batches')
						
						operation_qty = operation.qty_done if operation.qty_done else operation.product_qty
						product_data.append((0,0,{'product_id':operation.product_id.id,
									'qty_done':operation_qty,
									'qty_unit':operation.product_uom_id.id,
									'pack_id':operation.id,
									'batch_ids':[(6,0,new_batches)],
									'btch_unit':operation.packaging_id.uom_id.id,}))
		
					wizard_id=self.env['stock.store.location.wizard'].search([
									('picking','=',res.id)])
					wizard_id.unlink()
					vals={'picking':res.id,'wizard_product_line':product_data}
					res_id=self.env['stock.store.location.wizard'].create(vals)
					form_id = self.env.ref('api_inventory.production_batches_selection_form_view_wizard')
					return {
						'name' :'Select Batches For Transfer to Logistics',
						'type': 'ir.actions.act_window',
						'view_type': 'form',
						'view_mode': 'form',
						'res_model': 'stock.store.location.wizard',
						'views': [(form_id.id, 'form')],
						'view_id': form_id.id,
						'target': 'new',
						'res_id':res_id.id,
					    }
					    
    			    if (res.picking_type_id.code=='internal' and res.location_id.pre_ck and res.location_dest_id.actual_location):
    			    	product_data = []
    			    	flag = False
    			    	# Move to stock does not allow to transfer extra quantity
    			    	if all(x.qty_done == x.product_qty for x in res.pack_operation_product_ids):
    			    		flag =True
				for operation in res.pack_operation_product_ids:
					if not operation.packaging_id and operation.qty_done:
						raise ValueError("Packaging of Product [{}]{} is not defined".format(operation.product_id.default_code,operation.product_id.name))
					elif not operation.secondary_pack and operation.qty_done :
                                            secondary_pack=self.env['product.packaging'].search([('product_tmpl_id','=',operation.product_id.product_tmpl_id.id),('pkgtype','=','secondary')])
                                            print "secondary_packsecondary_pack",secondary_pack
                                            if secondary_pack:
                                                operation.write({'secondary_pack':secondary_pack.id})
#						if not 'store' in operation.packaging_id.uom_id.unit_type.mapped('string') and operation.qty_done :
#							raise ValueError("Secondary Packaging of product '[{}]{}' not  defined".format(operation.product_id.default_code,operation.product_id.name))
					if operation.qty_done > operation.product_qty:
						#if res.purchase_id and not res.purchase_id.allow_extra:
						#	raise ValueError("Done Quantity Should be less than or \
						#		equal to Product Quantity \n If You want to receive Extra Please contact Purchase Manager to Set Allow Extra in Purchase Order")
						#elif not res.purchase_id:
						raise ValueError("Done Quantity Should be less than or \
								equal to Product Quantity")
					if flag:
						operation.qty = 0.0
							
    			    if res.picking_type_code=='internal':
    			    	# Warehose to Warehouse tarnsfer
    			    	# INternal Location transfer(Production)
				if res.location_id.actual_location and (res.location_dest_id.actual_location or res.location_dest_id.usage == 'production'):
					if not res.pack_operation_product_ids:
    			    			raise ValueError("Please First Make some Operations. On Clicking \
    			    					'Mark as ToDo'")
    			    					
    					if res.picking_status !='r_t_dispatch':
						raise UserError('Please Close Picking List to transfer this Product Quantity.')
					data=[]
					wizard_id=self.env['stock.store.location.wizard'].search([('picking','=',self.id)])
					wizard_id.unlink()
					# call method to get picked master batch data
					data=self._get_bacthes(res.origin)
					location_view = self.env['stock.location.view'].search([
									('location_type','=','transit_out'),
									('location_id','=',res.location_id.id)])
					location_id = self.env['n.warehouse.placed.product'].search([
									('n_location_view','=',location_view.id)])
					vals={'picking':res.id,'wizard_line':data,'locations':location_id.id}
					if res.location_dest_id.actual_location:		
					#Transfer Warehouse
						location_dest_view = self.env['stock.location.view'].search([
									('location_type','=','transit_in'),
									('location_id','=',res.location_dest_id.id)])
						location_dest_id = self.env['n.warehouse.placed.product'].search([
									('n_location_view','=',location_dest_view.id)])
									
						vals.update({'status':'dispatch','store_dest_id':location_dest_id.id})
					if res.location_dest_id.usage == 'production':
						vals.update({'status':'int_production'})
					res_id=self.env['stock.store.location.wizard'].create(vals)
					if res_id:
						form_id = self.env.ref('api_inventory.store_locations_form_view_wizard_outgoing')
						return {
							'name' :'Transfer Products',
							'type': 'ir.actions.act_window',
							'view_type': 'form',
							'view_mode': 'form',
							'res_model': 'stock.store.location.wizard',
							'views': [(form_id.id, 'form')],
							'view_id': form_id.id,
							'target': 'new',
							'res_id':res_id.id,
						    }
	    		except Exception as err:
				exc_type, exc_obj, exc_tb = sys.exc_info()
    				_logger.error("API-EXCEPTION. In move To Transfer {} {}".format(repr(err),exc_tb.tb_lineno))
    				raise UserError(err)
    				
    			# In case of receive Extra quantity
		    	if (res.location_id.usage in ('inventory','production') or res.picking_type_code =='incoming') and all(x.qty_done >= x.product_qty for x in res.pack_operation_product_ids):
		    		product_data = []
		    	    	for operation in res.pack_operation_product_ids:
					product_data.append((0,0,{'product_id':operation.product_id.id,
						'qty_done':operation.qty_done,
						'qty_unit':operation.product_uom_id.id,
						'pack_id':operation.id,
						'max_batches':math.ceil(operation.qty_done/operation.packaging_id.qty),
						'btch_unit':operation.packaging_id.uom_id.id,}))
		
				wizard_id=self.env['stock.store.location.wizard'].search([
						('picking','=',res.id)])
				wizard_id.unlink()
				vals={'picking':res.id,'wizard_product_line':product_data}

				res_id=self.env['stock.store.location.wizard'].create(vals)
				form_id = self.env.ref('api_inventory.inventory_loss_batches_form_view_wizard')
				return {
					'name' :'Generate Batches for Purchased Product',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'stock.store.location.wizard',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'new',
					'res_id':res_id.id,
				    }
	    		return super(stockPicking,self).do_new_transfer()

   ##call on make to do
	@api.multi
	def action_confirm(self):
		'''inherite method to show alert on Make To Do in internal tarnsfer from  invnetory loss(manufacturing Transfers)'''
		for res in self:
			try:
    			    if res.location_id.usage =='inventory':
				if not res.location_dest_id.pre_ck:
					raise ValueError("Please Select Only Input-Location To move quantity from Inventory Loss")
    			    if res.location_id.usage=='production':
				if not res.location_dest_id.pre_ck:
					raise ValueError("Please Select Only Input-Location To move Produced quantity")
    			    if res.location_id.usage=='supplier':
				if not res.location_dest_id.pre_ck:
					raise ValueError("Please Select Only Input-Location To move Purchase Quantity")	
					
		    	except Exception as err:
				exc_type, exc_obj, exc_tb = sys.exc_info()
    				_logger.error("API-EXCEPTION. in Transfer Quantity {} {}".format(repr(err),exc_tb.tb_lineno))
    				raise UserError(err)
			result = super(stockPicking,self).action_confirm()
                        pick_id=self.search([('origin','=',res.name)])
                        print "pick_idpick_id",pick_id,res.id
                        if pick_id:
                            pick_id.write({'pick_ref':res.id})
                            res.write({'pick_ref':pick_id.id})
			if res.location_id.usage in ('inventory','production') and res.location_dest_id.pre_ck and res.ntransfer_type=='manufacturing' and not res.backorder_id:
				batch_obj = self.env['mrp.order.batch.number']
				batch_history_obj = self.env['mrp.order.batch.number.history']
				for move in res.move_lines_related:
					if res.origin:
						product_req_id=self.env['n.manufacturing.request'].search([
										('name','=',res.origin)])
						if product_req_id:
							move.production_req=[(4,product_req_id.id)]
							product_req_id.n_state='manufacture'
						else:
							raise UserError('Production Request is not found of name {}'.format(res.origin))
				for line in res.pack_operation_product_ids:
					if not line.packaging_id:
						raise UserError("Please define Primary Packaging for product '{}' ".format(line.product_id.name))
					max_qty	= line.packaging_id.qty
					qty = line.product_qty
					batches=[]
					seq=1
					while qty > 0:
   						n_qty = qty if max_qty > qty else max_qty
						ids=batch_obj.create({
								'product_id':line.product_id.id,
							 	'approve_qty':n_qty,'product_qty':n_qty,
							 	'uom_id':line.product_uom_id.id,
								'qty_unit_id':line.product_uom_id.id,
								'produce_qty_date':datetime.now(),
								'name':'{}{}'.format(res.origin,str(seq).zfill(4)),
								'picking_id':res.id,
								'request_state':'done','logistic_state':'draft'})
						batches.append(ids.id)
						batch_history_obj.create({'batch_id':ids.id,'operation':'production',
						   'description':'New Batch create in Production {}'.format(res.name)})
						qty -= n_qty
						seq +=1
					line.inprocess_batches=[(6,0,batches)]
			return result

	@api.multi
	def reverse_from_dispatch(self):			
		''' Click by Manager To reverse from the Ready_To_Dispatch state to previous state 
			All Pick Quantity is revert to Transit-IN. Area'''
		for rec in self:
			if rec.picking_type_code == 'outgoing' and rec.sale_id:
        			for operation in rec.pack_operation_product_ids:
					search_id=self.env['mrp.order.batch.number'].search([
								('store_id','!=',False),
								('logistic_state','=','r_t_dispatch'),
								('picking_id','=',rec.id),
								('product_id','=',operation.product_id.id)],order='id')
					if search_id:
						master_id=[]
						for batch in search_id:
							batch.logistic_state = 'reserved' 
							if batch.master_id not in master_id:
								master_id.append(batch.master_id)
								
						for mst in master_id:
							mst.logistic_state= 'reserved'
        			#if rec.master_batches:
				#	for master in rec.master_batches:
				#		master.picking_id=False
			return super(stockPicking,self).reverse_from_dispatch()
			
   ## call on validate in outgoing
	@api.multi
	def send_to_dispatch(self):
		'''Function to update child batches from Reserved/Transit_in To Ready_to_dispatch '''
		for rec in self:
			order_batch_obj = self.env['mrp.order.batch.number']
			if rec.picking_type_code == 'outgoing' and rec.sale_id:
                		for operation in rec.pack_operation_product_ids:
					if operation.qty_done and operation.product_qty < operation.qty_done:
                				raise UserError('Please Enter Done quantity is euqal product quantity')
        				
        				result_batches=[]
        				quantity = operation.qty_done or operation.product_qty
        				packets = int(quantity / operation.packaging_id.qty)
        				# Check for reserved Qty FUll packaging
					full_rev=order_batch_obj.search([('product_id','=',operation.product_id.id),
								('convert_product_qty','=',operation.packaging_id.qty),
								('store_id','!=',False),
								('logistic_state','=','reserved'),
								('picking_id','=',rec.id)],
								order='id',limit=packets)
				 	
			 		quantity -= sum([ rev.convert_product_qty for rev in full_rev])
			 		result_batches = [i for i in full_rev]
				 	if quantity:
				 		# Check for reserved Qty Loose packaging
				 		loose_rev=order_batch_obj.search([
				 				('product_id','=',operation.product_id.id),
								('convert_product_qty','<',operation.packaging_id.qty),
								('store_id','!=',False),
								('logistic_state','=','reserved'),
								('picking_id','=',rec.id)],
								order='id')
						loose_qty = sum([ rev.convert_product_qty for rev in loose_rev])
						if quantity < loose_qty:	
				 			numbers=[srch for srch in loose_rev]
							extra_btch = subset_sum_batches(numbers,quantity)
							if extra_btch:
								result_batches.extend(extra_btch)
								quantity = 0.0
							else:
								Error = "There are no group of Batches found for product [{}]{} with referance to remaining loose Packaging Quantity {}".format(operation.product_id.default_code,operation.product_id.name,quantity)
								_logger.error("API-EXCEPTION..Exception in batches counting {}".format(Error))
								raise UserError(Error)
								
						else:
							quantity -= loose_qty 
							result_batches.extend([j for j in loose_rev])
						
				 	if quantity and quantity > operation.packaging_id.qty:
				 		packets = int(quantity / operation.packaging_id.qty)
				 		# Check for New Batches FUll packaging
						new_batches=order_batch_obj.search([
							('convert_product_qty','=',operation.packaging_id.qty),
							('store_id','!=',False),('picking_id','=',False),
							('logistic_state','in',('transit_in','stored')),
							('product_id','=',operation.product_id.id)],
							order='id',limit=packets)
						quantity -= sum([ n.convert_product_qty for n in new_batches])
						result_batches.extend([j for j in new_batches])
					
				 	if quantity:
				 		# Check for New Batches Loose packaging
						search_id=order_batch_obj.search([
								('convert_product_qty','<',operation.packaging_id.qty),
								('store_id','!=',False),
								('logistic_state','in',('transit_in','stored')),
								('picking_id','=',False),
								('product_id','=',operation.product_id.id)],order='id')
						if search_id:
							numbers=[srch for srch in search_id]
							extra_btch = subset_sum_batches(numbers,quantity)
							if extra_btch:
								result_batches.extend(extra_btch)
							else:
								error="Logistics Dispatch some of system reserved  batches of product [{}]{} in other Delivery Order,\n Now there is no loose batch packaging available in system according to quantity {} \n,If you found loose packaging of Product you can Unreserve and Reserve again. OR contact administrator".format(
						operation.product_id.default_code,operation.product_id.name,quantity)
								_logger.error("API-EXCEPTION..Exception in batches counting {}".format(error))
								raise UserError(error)
					master_id=[]
					optn_qty = operation.qty_done or operation.product_qty
					for batch in result_batches:
						batch.logistic_state = 'r_t_dispatch'
						batch.picking_id = rec.id
						if batch.master_id not in master_id:
							master_id.append(batch.master_id)
						optn_qty -= batch.convert_product_qty
						if optn_qty<=0.0:
							break
							
					for mst in master_id:
						mst.picking_id = rec.id
						mst.logistic_state='r_t_dispatch'
								
		return super(stockPicking,self).send_to_dispatch()

   ## call on validate in outgoing
	@api.multi
	def import_product_data(self):
		'''Function to  import product in manufacturing transfer '''
		for rec in self:
			#pass
			#if rec.ntransfer_type=='manufacturing':  
			form_id = self.env.ref('api_inventory.product_import_manufacturing_transfer')
			if form_id:
				return {'name' :'Import Manufacturong Transfer',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'product.store.data.import',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'new',
					'context':{'default_picking_id':rec.id},
				    }
    # SEND Delivery Alert  mail
	@api.multi
	def action_second_validation(self):
		super(stockPicking,self).action_second_validation()
		temp_id = self.env.ref('api_inventory.email_template_for_delivery_done')
                if temp_id:
                        recipient_partners=''
	       		group = self.env['res.groups'].search([('name', '=', 'Delivery Email')])
	       		user_obj = self.env['res.users'].browse(self.env.uid)
	       		for recipient in group.users:
       				if recipient.login != user_obj.partner_id.email:
		    	   		recipient_partners += ","+str(recipient.login) if recipient_partners else str(recipient.login)
		    	if recipient_partners:
                                body ='<li>Delivery Order No: '+str(self.name)+'</li>'
                                body +='<li>Customer Name:  '  +str(self.partner_id.name)+'</li>'
                                body +='<li>Delivered Date:  ' +str(self.delivery_date)+'</li>'
		       	        body +='<li> Please Find the attachment for Delivery Documents</li>'
		               
		       		body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'stock.picking',self.id, context=self._context)
		       		attch=([(6,0,[i.id for i in self.delivery_doc])])
		       		temp_id.write({'body_html': body_html,'email_cc':recipient_partners, 'email_to':self.sale_id.user_id.login,'email_from': user_obj.partner_id.email,'attachment_ids':attch})
		       		if temp_id and temp_id.email_to:
		       			temp_id.send_mail(self.id)
                return True

				    
	# reassign batches on recompute in picking operation.		        	
	@api.multi
	def do_prepare_partial(self):
		result=super(stockPicking,self).do_prepare_partial()
		for rec in self:
			if rec.ntransfer_type =='manufacturing':
				for operation in rec.pack_operation_product_ids:
					operation.batch_recompute()
	
	@api.multi
	def print_quotation(self):
		return self.env['report'].get_action(self, 'api_inventory.report_workorder_batch_number_barcode')

	@api.v7
	def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
		# inherite this move to add origin in case of Extra quantity move is created and assign to next chain stock picking.
		res = super(stockPicking,self)._prepare_values_extra_move(cr, uid, op,product,remaining_qty,context)
		if 'Extra' in res.get('name',''):
			origin = ''
			for m in op.linked_move_operation_ids:
			    if m.move_id.procurement_id:
				origin = m.move_id.origin
				break
			
			res.update({'origin':origin or op.picking_id.origin})
		return res
			
class stockPackOPeration(models.Model):
	_inherit="stock.pack.operation"
	
	batch_number = fields.Many2many('mrp.order.batch.number','pack_operation_batch_rel','pack_id','batch_id','Batch Number',copy=False) # To store History of Production Batches and Batches Data in Inventory Loss
	
	inprocess_batches = fields.One2many('mrp.order.batch.number','pack_id','In-Production Batches',domain=[('produce_bool','=',False)], copy=False) # add field to show NEW Batches created in Production
	produce_batches = fields.One2many('mrp.order.batch.number','pack_id','Produced Batches',copy=False ,domain=[('produce_bool','=',True)]) # add field to show Produced Batches from production	
	print_selection = fields.Many2one('print.selection.value','Selection',copy=False)
	
	@api.multi
	def batch_recompute(self):
		''' Search existing batches '''
		if self.picking_id.ntransfer_type =='manufacturing':
			if not self.state =='assigned':
				raise UserError('You can\'t Create Batch ,Operation is not in Proper State')
				
			batch_obj=self.env['mrp.order.batch.number'].search([('picking_id','=',self.picking_id.id),('logistic_state','=','draft'),('product_id','=',self.product_id.id)])
			self.inprocess_batches=[(6,0,batch_obj._ids)]
		return {'type':'ir.actions.do_nothing'}
	
	@api.multi
	def produce_batch(self):
		for rec in self:
			rec.calculate()
			if self._context.get('produce'):
				if not any([ x.print_bool==True for x in rec.produce_batches ]):
					raise UserError('Please Select Batches to Produce.')
			else:
				if not any([ x.print_bool==True for x in rec.inprocess_batches ]):
					raise UserError('Please Select Batches to Produce.')
			form_id = self.env.ref('api_inventory.transfer_batch_production_wizard')
			if form_id:
				batch_ids=[]
				if self._context.get('produce'):
					batch_ids = [ q.id for q in rec.produce_batches if q.print_bool]
				else:
					batch_ids = [ q.id for q in rec.inprocess_batches if q.print_bool]
				qty=sum([ q.product_qty for q in rec.inprocess_batches if q.print_bool])
				return {'name' :'Production batches Produce',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'production.batches.produce',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'new',
					'context':{'default_product_id':rec.product_id.id,
						'default_qty':qty,
						'default_pick_id':rec.id,'default_qty_unit':rec.product_uom_id.id,
						'default_produce_batches':[(6,0,batch_ids)]},
				    }
			
	@api.multi
	def batch_create(self):
		'''Create new batches '''
		if self.picking_id.state !='assigned':
			raise UserError('You can\'t Create Batch ,Operation is not in Proper State')
		
		if self.picking_id.ntransfer_type !='manufacturing':
			raise UserError('You are not in proper operation to create batches(only for manufacturing)')
	
		seq=len(self.inprocess_batches)+len(self.produce_batches)
		bth_name = '{}{}'.format(self.picking_id.origin,str(seq).zfill(4))
		while True:
			if self.env['mrp.order.batch.number'].search([('name','=',str(bth_name))]):
				seq +=1
				bth_name = '{}{}'.format(self.picking_id.origin,str(seq).zfill(4))
				continue
			else:
				break
				
		for line in self.inprocess_batches:
			if not line.produce_bool:
				new_id = line.copy(default={'name':bth_name})
				break
				
		self.pack_qty = len(self.inprocess_batches)+len(self.produce_batches)
		return {'type':'ir.actions.do_nothing'}
		
	@api.multi
	def print_batches(self):
		self.calculate()
		return self.env['report'].get_action(self, 'api_inventory.production_batch_number_print')

	@api.multi
	def print_batches_details(self):
		self.calculate()
		return self.env['report'].get_action(self, 'api_inventory.production_batch_details_print')
        
        @api.multi
        def calculate(self):
        	if not self.print_selection:
        		raise UserError('Please Select Print Selection')
        		
		if self.print_selection.value == 'clr':
			self.produce_batches.write({'print_bool':False})
			self.inprocess_batches.write({'print_bool':False})
		
		if self.print_selection.value == 'any':
		   	pass
		
		if self.print_selection.value == 'all':
			if self._context.get('produce'):
				self.produce_batches.write({'print_bool':True})
				self.inprocess_batches.write({'print_bool':False})		
			else:
				self.inprocess_batches.write({'print_bool':True})
				self.produce_batches.write({'print_bool':False})	
			 
		if self.print_selection.value == 'from':
			flag=False
			if self._context.get('produce'):
				self.inprocess_batches.write({'print_bool':False})		
				for rec in self.produce_batches:
					if rec.print_bool:
						flag=True
					if flag:
						rec.print_bool=True
			else:
				self.produce_batches.write({'print_bool':False})
				for rec in self.inprocess_batches:
					if rec.print_bool:
						flag=True
					if flag:
						rec.print_bool=True
					
		if self.print_selection.value == 'to':
			flag=False
			if self._context.get('produce'):
				self.inprocess_batches.write({'print_bool':False})
				for rec in self.produce_batches:
					if rec.print_bool:
						flag=True
					rec.print_bool=True
					if flag:
						break
			else:
				self.produce_batches.write({'print_bool':False})
				for rec in self.inprocess_batches:
					if rec.print_bool:
						flag=True
					rec.print_bool=True
					if flag:
						break
						
        	if self.print_selection.value == 'range':
        		ids=False
        		flag=flag1=False
        		if self._context.get('produce'):
        			self.inprocess_batches.write({'print_bool':False})
        			if len([ x for x in self.produce_batches if x.print_bool==True])<2:
					raise UserError('Please Select Two  Record')	
				for rec in self.produce_batches:
					if rec.print_bool and not ids:
						flag=True
						ids=rec.id
					if rec.print_bool and ids!=rec.id:
						flag1=True
					if flag:
						rec.print_bool=True
					if flag1:
						break
        		else:
				self.produce_batches.write({'print_bool':False})
				if len([ x for x in self.inprocess_batches if x.print_bool==True])<2:
					raise UserError('Please Select Two  Record')	
				for rec in self.inprocess_batches:
					if rec.print_bool and not ids:
						flag=True
						ids=rec.id
					if rec.print_bool and ids!=rec.id:
						flag1=True
					if flag:
						rec.print_bool=True
					if flag1:
						break
		return {'type':'ir.actions.do_nothing'}
		
# history of picking and location				    
class pickinglotstore(models.Model):
	'''Store History of Stock picking batch wise '''
	_name="picking.lot.store.location"
	
	picking_id = fields.Many2one('stock.picking','Move name')
	product_id = fields.Many2one('product.product','Product Name')
	store_id = fields.Many2one('n.warehouse.placed.product','Store Name')
	master_id = fields.Many2one('stock.store.master.batch','Master Batch')
	quantity = fields.Float('Quantity')
	unit_id = fields.Many2one('product.uom',"Unit")
	#lot_number = fields.Many2one('stock.production.lot','Lot Number')
	#batch_number = fields.Many2one('mrp.order.batch.number','Batch Number')
     	batches_ids = fields.One2many('picking.lot.store.location.batches','history_id','Dispatch Batches')
     	
class pickinglotstoreBatches(models.Model):
	_name="picking.lot.store.location.batches"
	
	history_id = fields.Many2one('picking.lot.store.location','History')
	product_id = fields.Many2one('product.product','Product Name')
	store_id = fields.Many2one('n.warehouse.placed.product','Store Name')
	quantity = fields.Float('Quantity')
	unit_id = fields.Many2one('product.uom',"Unit")
	lot_number = fields.Many2one('stock.production.lot','Lot Number')
	batch_number = fields.Many2one('mrp.order.batch.number','Batch Number')
	is_return = fields.Boolean('Return',default=False)
	date_return = fields.Datetime('Return Date')
	

class printSelectionValues(models.Model):
	_name="print.selection.value"
	
	name = fields.Char('Name')
	value = fields.Char('Value')
	description = fields.Char('Description')
	active = fields.Boolean('Active')
	print_type = fields.Selection([('delivery','Delivery')], string="Type")


