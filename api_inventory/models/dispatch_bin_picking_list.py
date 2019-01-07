# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, exceptions, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime,date
from urlparse import urljoin
from urllib import urlencode
import re
from dateutil.relativedelta import relativedelta
import math
import sys
import logging
_logger = logging.getLogger(__name__)

def subset_sum_batches(batches, target):
	try:
		partial=[]
		diff=0.0
		for i,start in enumerate(batches):
			if start.convert_product_qty >target:
				continue
			partial=[start]
			remaining=batches[i+1:]
			if sum([q.convert_product_qty for q in partial]) == target: # check if the partial sum is equals to target
				return partial
			for j,next in enumerate(remaining):
		    		partial.append(next)
		    		qty_sum = sum([q.convert_product_qty for q in partial])		
		    		if qty_sum  == target:		# check if the partial sum is equals to target
					return partial
		    		if qty_sum >= target:		# if sum is greater than quantity continue
		    			diff = qty_sum - next.convert_product_qty
		    			partial.pop()
		    			flag=True
		    			if not any([ diff < q.convert_product_qty for q in remaining[j:]]):
						break
			if flag and diff:
				if not any([ diff < q.approve_qty for q in batches[i:]]):
					break
		return []
	except Exception as err:
		exc_type, exc_obj, exc_tb = sys.exc_info()
    		_logger.error("API-EXCEPTION..Exception in Dispatchig of product {} {}".format(err,exc_tb.tb_lineno))
		
class stockPicking(models.Model):
	_inherit = "stock.picking"

     	total_no_pallets=fields.Float('Total Pallets',compute='_get_packaging_count')
     	picking_store = fields.Many2many('store.picking.list','picking_list_sotre_rel','picking_id','store_id',
     			'Bin Location',help="Shows Bin Location for outgoing Products in picking List")
     	
     	# for showing picking batch history in picking list
     	master_batches = fields.One2many('stock.store.master.batch','picking_id','Bin Location',
     			 help="Shows Bin Location for outgoing Products in picking List",domain=[('logistic_state','in',('transit','dispatch'))])
     			 
     	@api.model
     	def create(self,vals):
     		res =super(stockPicking,self).create(vals)
     		if res.location_id.pre_ck:
     			res.ntransfer_type='pre_stock'
     		return res
	
	@api.multi
	def done_bin_picking_operation(self):
		if self.state not in ('partially_available','assigned'):
			raise ValidationError("Picking operation is not in proper state, please contact administrator")
		# alert to check quantity pack operation
		if all(q.pick_qty<=0.0 for q in self.pack_operation_product_ids):
			raise ValidationError("Please pick Some Quantity  to close the picking list.")
			
		self.picking_status = 'r_t_dispatch'
		body = "<ul> <b><li>Picking list is Closed <li></li>	\
				<li>Picked Quantity</li></b>"
		for res in self.pack_operation_product_ids:
#                    patch below line 80,81 added by bhargavi to handle internal tfr issue in qty
                        if res.picking_id.picking_type_code=='internal' and res.picking_id.location_id.actual_location and res.picking_id.location_dest_id.usage == 'production' and res.pick_qt>0.0:
                            res.write({'qty_done':res.pick_qty,'product_qty':res.pick_qty})
			body += '<li>Product : {} <b>{} {}</b></li>'.format(res.product_id.name,\
						res.product_uom_id.name,res.pick_qty)
			#res.qty_done = res.pick_qty
		body += '</ul>'
		self.message_post(body)
		
	@api.multi
	def open_bin_picking_operation(self):
		if self.state not in ('partially_available','assigned'):
			raise ValidationError("Picking operation is not in proper state, please contact administrator")
		self.picking_status='pick_list'
		self.message_post(body="PIcking list is Open again after closing.")
		
	@api.multi
	def open_delivery_order(self):
		form_id = self.env.ref('stock.view_picking_form')
		context=self._context.copy()
		if form_id:
			return {'name' :'Delivery Order',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'stock.picking',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'current',
					'res_id':self.id,
				    }
	
class stocpackOperation(models.Model):
	_inherit = "stock.pack.operation"
	
	pick_qty=fields.Float('Picked qty')
	
	@api.multi
	def bin_picking_operation(self):
		picking_list=self.env['store.picking.list']
		for res in self:
			if res.picking_id.picking_status !='pick_list':
				raise ValidationError("Picking List is Closed, Please Open it to perform picking operation.")
			if res.pick_qty == res.qty_done:
				raise ValidationError("You already Pick FULL Quantity Batches\n If you want to PICK Another Batch, Please UnPIck Some Batches")
			picking_list=picking_list.search([('picking_id','=',res.picking_id.id),
									('product_id','=',res.product_id.id),
									('pick_id','=',res.id)],limit=1)
			
			quantity = res.qty_done if res.qty_done else res.product_qty
			if not picking_list:
				strategy=self.env['product.removal'].search([('method','=','reserve')])
				picking_list=picking_list.create({'picking_id':res.picking_id.id,
						'product_id':res.product_id.id,
						'dispatch_qty': quantity,
						'dispatch_unit':res.product_uom_id.id,
						'removel_strategy':strategy.id if strategy else False,
						'pick_id':res.id,
						})
			else:
				picking_list.dispatch_qty = quantity
				if not picking_list.pick_id:
					picking_list.pick_id=res.id
					
			form_id = self.env.ref('api_inventory.bin_picking_list_html_form_view')
			#context = self._context.copy()
			#context.update({'html_view':True})
			if form_id:
				picking_list._create_html_view(form_id)
				return {'name' :'Batches To Pick from Bin-Location',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'store.picking.list',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'current',
					'res_id':picking_list.id,
					#'context':context,
					'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
				    }

	@api.multi
	def unpick_operation(self):
		for res in self:
			if res.picking_id.picking_status !='pick_list':
				raise ValidationError("Picking List is Closed, Please Open it to \
										Perform Un-Picking  Operation.")
			if res.pick_qty == 0:
				raise ValidationError("Don't have Quantity to Un-PICK Quantity.")
			
			quantity = res.qty_done if res.qty_done else res.product_qty
			context = self._context.copy()
			new_data=[]
			
			transit_id = self.env['n.warehouse.placed.product'].search([
								('n_location','=',res.picking_id.location_id.id),
								('location_type','=','transit_in')])
			for line in res.picking_id.master_batches:
				if line.product_id.id == res.product_id.id:
					new_data.append((0,0,{'store_id':line.store_id.id,
								'product_id':line.product_id.id,
								'master_id': line.id,
								'qty':line.total_quantity,
								'qty_unit':line.uom_id.id}))
			context.update({'default_line_ids':new_data,'default_pick_id':res.id,
					'default_picking_id':res.picking_id.id,'default_product_id':res.product_id.id,
					'default_qty':quantity,'default_unit':res.product_uom_id.id,
					'default_pick_qty':res.pick_qty,'default_pick_unit':res.product_uom_id.id,
					'default_unpick_unit':res.product_uom_id.id,
					'default_store_id':transit_id.id,})		
			form_id = self.env.ref('api_inventory.unpick_batch_wizard')
			if form_id:
				return {'name' :'Un-PICK Mater Batches',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'unpick.picked.batches',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'new',
					'context':context,
					'flags': {'form': {'action_buttons': False, 'options': {'mode': 'edit'}}},
				    }
	    
	@api.multi
	def autopick_operation(self):
		'''Pick Quantity automatically'''
		for rec in self:
			master_id = self.env['stock.store.master.batch'].search([('product_id','=',rec.product_id.id),
		    						('logistic_state','=','r_t_dispatch')])
			pick_qty = 0.0
			if not master_id:
				raise ValidationError("There is no reserved master batch available to PICK. OR \n \
						Quantity is not available in stock. OR \n \
						Logistic Person dispatch Master batch in Other delivery Order.\n \
						Please Do manual Picking Operation ")
			else:
			   for mast in master_id:
				if mast.logistic_state == 'transit':
					raise UserError("Master Batch '{}' is already Transfered to Transit-OUT Area".format(mast.name))
			
				store_id=self.env['n.warehouse.placed.product'].search([('id','=',mast.store_id.id)])
				location_view = self.env['stock.location.view'].search([('location_type','=','transit_out'),('location_id','=',store_id.n_location.id)])
				transit_id = self.env['n.warehouse.placed.product'].search([('n_location_view','=',location_view.id)])
				total_quantity=0.0
				for res in store_id:
					if not  all ([x.logistic_state=='r_t_dispatch' and x.picking_id.id==rec.picking_id.id for x in mast.batch_id ]):
						continue
					qty=pkg_capicity=0.0
					product_id = rec.product_id
					Packaging_type = mast.packaging
					pkg_capicity_unit = pkg_unit = mast.packaging.uom_id
					total_qty_unit = mast.uom_id
				
					mast.write({'store_id':transit_id.id,
								'picking_id':rec.picking_id.id,
								'logistic_state':'transit'})
								
					for btch in mast.batch_id:
						btch.write({'store_id':transit_id.id,
								'picking_id':rec.picking_id.id,
								'logistic_state':'transit',
								'batch_history':[(0,0,{'operation':'picking',
					   'description':'Pick from Bin Location {}'.format(store_id.name)})]})
						qty += btch.convert_product_qty
						pick_qty += btch.convert_product_qty
					# to update batches in pack Operation
					rec.batch_number = [(4,x.id) for x in mast.batch_id]
					total_quantity = qty
					packages = len(mast.batch_id._ids)
					body1 ='<ul>Picking Operation for {} </ul>'.format(rec.picking_id.name)
					if res.product_type == 'single': ## do operation for Single product
						pkg_capicity_unit = res.pkg_capicity_unit
						pkg_unit = res.pkg_unit
						if total_quantity < res.total_quantity:
							res.write({'state':'partial','total_quantity':res.total_quantity-total_quantity,
							'packages':float(res.packages)-float(packages)})
						elif total_quantity == res.total_quantity:
							res.write({'state':'empty','product_id':False,'total_quantity':0.0,
								'total_qty_unit':False,'qty_unit':False,'pkg_capicity':0.0,
								'pkg_capicity_unit':False,'packages':0.0,'pkg_unit':False,
								'Packaging_type':False})
						else:
							print "ERROR in selecting..."
							raise
			
					else:
						# do operation for multi product
						for multi in self.env['store.multi.product.data'].search([
										('store_id','=',res.id),
										('product_id','=',product_id.id),
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
		
					self.env['location.history'].create({'stock_location':res.id,
									'product_id':product_id.id,
									'operation_name':'Send To Transit-OUT for Dispatch',
									'operation':'do',
									'qty':total_quantity,
									'n_type':'out'})
										
					# search for product Transit -OUT location..	according packagig
					store_product=self.env['store.multi.product.data'].search([
									('product_id','=',product_id.id),
									('store_id','=',transit_id.id),
									('Packaging_type','=',Packaging_type.id)])
								
					body1+='<li>Master Batch :{} </li>'.format(mast.name)
					if not store_product: # If product is not found add product
						transit_id.state='partial'
						add_vals={'product_id':product_id}
						body1 +="<li>Product add : "+str(product_id.name)+" </li>"
						add_vals.update({'total_quantity':total_quantity})
						add_vals.update({'total_qty_unit':total_qty_unit.id})
						body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
						body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
						add_vals.update({'packages':packages})
						add_vals.update({'pkg_unit':pkg_unit.id})
						add_vals.update({'Packaging_type':Packaging_type.id})
						body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
						transit_id.multi_product_ids=[(0,0,add_vals)]	
						transit_id.message_post(body1)		
			
					elif store_product: # if found update quantity and packages
						body1 +="<li>Product update qty : "+str(product_id.name)+" </li>"
						store_product.total_quantity += total_quantity
						body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
						#store_product.pkg_capicity += pkg_capicity
						#body1+="<li>Package Capicity updated: "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
						store_product.packages += packages
						body1+="<li>Packages updated: "+str(packages)+" </li>"
						transit_id.message_post(body1)
		
					self.env['location.history'].create({'stock_location':transit_id.id,
									'product_id':product_id.id,
									'operation_name':'for Dispatch',
									'operation':'do',
									'qty':total_quantity,
									'n_type':'in'})	
			if not 	pick_qty:
				raise ValidationError("There is no Full reserved master batch available to PICK. \n \
						Please Do manual Picking Operation ")
						
			rec.pick_qty += pick_qty
		
class storePikcingList(models.Model):
	_name = "store.picking.list"

#	store_name = fields.Many2one('n.warehouse.placed.product','Bin Location')
	product_id = fields.Many2one('product.product', string="Product")
	pick_full = fields.Boolean( string="Pick Full?")
	picking_id = fields.Many2one('stock.picking', string="Stock Picking")
     	status = fields.Selection([('draft','draft'),('partial','Partial Pick'),('pick','Fully Pick')],default='draft')
     	pick_id = fields.Many2one('stock.pack.operation', string="Operation")
     	
	@api.multi
	def show_picking_list(self):
		form_id = self.env.ref('api_inventory.store_picking_list_batch_form_view')
		context=self._context.copy()
		if form_id:
			return {'name' :'Picking List',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'stock.picking',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'current',
					'res_id':self.picking_id.id,
				    }
	@api.multi
	def process_selected(self):
            if not any([q.pick_full for q in self.env['store.picking.list'].search([('pick_full','=',True)])]):
                raise UserError('Please Select batch to Process Fully!!')
            batches_selected=self.env['store.picking.list'].search([('pick_full','=',True)])
            print "batches_selectedbatches_selected",batches_selected
	dispatch_qty = fields.Float('To Dispatch Qty',help="Quantity set to Dispatch by Sales Support")		
	dispatch_unit = fields.Many2one('product.uom','Unit')
	qty_pick = fields.Float('Picked Quantity',compute="_get_quantity_data",help="Quantity is Picked by Store Operator")
	pickunit = fields.Many2one('product.uom',compute="_get_quantity_data")
	qty_to_pick = fields.Float('Remaining to Pick',compute="_get_quantity_data",help="Remaining Quantity to Picked by Store Operator")
	pick_unit = fields.Many2one('product.uom',compute="_get_quantity_data")
	removel_strategy = fields.Many2one('product.removal',string="Picking Strategy")
	
	@api.multi
	def open_binlocation(self):
		for rec in self:
			bin_form = self.env.ref('api_inventory.product_stock_location_from', False)
			bin_id = self._context.get('bin_id')
			context=self._context.copy()
			context.update({'transfer_wizard':True})
			if bin_form and bin_id:
				return {
				    'name':'Bin-Location',
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'n.warehouse.placed.product',
				    'views': [(bin_form.id, 'form')],
				    'res_id': bin_id,
				    'target': 'new',
				    'context':context,
					}
					
	@api.multi
	def _get_quantity_data(self):
		for res in self:
			#batches = self.env['mrp.order.batch.number'].search([('product_id','=',res.product_id.id),
			#						     ('picking_id','=',res.picking_id.id),
			#						     ('logistic_state','=','transit')])
		        
			pick_qty=0.0
			for batch in res.pick_id.batch_number:
				if batch.convert_product_qty:
					pick_qty += batch.convert_product_qty
					
			res.qty_pick = pick_qty
			res.qty_to_pick = res.dispatch_qty - pick_qty
			res.pickunit = res.dispatch_unit
			res.pick_unit = res.dispatch_unit
			
	@api.multi
	#@api.onchange('removel_strategy')
	def _create_html_view(self,view_id):
		'''Generate Bin-Location view '''
		for res in self:
		    view_data='<?xml version="1.0">'
		    view_data +=''' <form string="Picking List">
				<header>
					<button name="show_picking_list" class="btn-primary" string="Picking List" type="object"/>
					<button name="process_selected" class="btn-primary" string="Process Selected" type="object"/>
		    			<field name="status" widget="statusbar"/>
				</header>
			    	<group col="4">
				            <field name="product_id" readonly="1"/>
					    <label for="dispatch_qty"/>
					    <div>
					    	<field name="dispatch_qty"  class="oe_inline" readonly="1"/>
					    	<field name="dispatch_unit" class="oe_inline" readonly="1"/>
					    </div>
                                            <field name="picking_id" readonly="1"  context="{'form_view_ref':'api_invnetory.store_picking_list_batch_form_view'}"/>
					    <label for="qty_to_pick"/>
					    <div>
					    	<field name="qty_to_pick" class="oe_inline" readonly="1"/>
					    	<field name="pick_unit" class="oe_inline" readonly="1"/>
					    </div>
					    <label for="qty_pick"/>
					    <div>
					    	<field name="qty_pick" class="oe_inline" readonly="1"/>
					    	<field name="pickunit" class="oe_inline" readonly="1"/>
					    </div>
				    </group>'''
		            
		    view ='<group col="1">'
		    warehouse,location_view,master_list=[],[],[]
		    
		    pick_qty = res.qty_to_pick
		    orer_by='id'
		    if res.removel_strategy.method == 'fifo':
		    	orer_by='produce_qty_date'
		    elif res.removel_strategy.method == 'lifo':
		    	orer_by='produce_qty_date desc'
		    	
		    batch_ids=self.env['mrp.order.batch.number'].search([('product_id','=',res.product_id.id),
		    			('logistic_state','in',('stored','reserved','r_t_dispatch','transit_in')),
		    			('picking_id','=',res.picking_id.id),
		    			('company_id','=',res.picking_id.company_id.id)],order=orer_by)
		    if not batch_ids:
		    	batch_ids=self.env['mrp.order.batch.number'].search([('product_id','=',res.product_id.id),
		    			('logistic_state','in',('stored','reserved','r_t_dispatch','transit_in')),
		    			('company_id','=',res.picking_id.company_id.id)
		    			],order=orer_by)
		    for i in batch_ids:
		    	if i.store_id.n_warehouse.id not in warehouse:
		    		warehouse.append(i.store_id.n_warehouse.id)
	    		if i.store_id.n_location_view not in location_view:
	    			if self.picking_id.location_id.id == i.store_id.n_location.id:
			    		location_view.append(i.store_id.n_location_view)
	    		if pick_qty > 0:
	    			pick_qty -= i.convert_product_qty
	    			if i.master_id.id not in master_list:
	    				master_list.append(i.master_id.id)
	    				
		    location_view.sort()
		    if location_view:
		    	view +='<table style="width:100%" border="0"> <tr>'
    			view +='<td style="background-color:white;width:12%;font-size:100%;text-align:center"><b>Empty Location </b></td>'
    			view +='<td style="width:3%"></td>'
    			view +='<td style="background-color:silver;width:14%;font-size:100%;text-align:center"><b> Occupied Location </b></td>'
    			view +='<td style="width:3%"></td>'
    			if res.removel_strategy.method == 'reserve':
    				view +='<td style="background-color:green;width:15%;font-size:100%;text-align:center"> <font color="white"><b>Reserved Quantity</font> </b></td>'
			else:
    				view +='<td style="background-color:green;width:15%;font-size:100%;text-align:center"> <font color="white"><b> Quantity To Pick </font> </b></td>'
    			view +='<td style="width:3%"> </td>'
    			view +='<td style="background-color:LimeGreen;width:15%;font-size:100%;text-align:center"> <font color="white"><b> Extra Quantity </font> </b></td>'
    			view +='<td style="width:3%"></td>'
    			view += '<td style="background-color:red;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Under Maintenance </font> </b></td>'
    			view +='<td style="width:3%"></td>'
    			view += '<td style="background-color:black;width:14%;font-size:100%;text-align:center"> <font color="white"><b>  Out of Use </font> </b></td>'
			view += '</tr></table><p> <p>'
		    else:
                        print "self._contextself._contextself._context",self._context
		    	if self._context.get('picking_view'):
		    		raise ValidationError("Quantity of product '{}' is not found in any location of '{}'  warehouse ".format(res.product_id.name,res.picking_id.picking_type_id.warehouse_id.name))
		
		    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		    for rec in location_view:
	    	        warehouse=self.env['stock.warehouse'].search([('lot_stock_id','=',rec.location_id.id)],limit=1)
		        if rec and rec.row and rec.column and rec.depth:
		            for r in range(1):
	    			view +='<table style="width:100%" border="1"><tr><td style="background-color:gray;" > <font style="font-weight: bold;font-size: 15px;color:white">   '+str(warehouse.name+'/'+rec.location_id.name+'/'+rec.name)+'</font></td></tr> </table>'
	    			view +='<table style="width:100%" border="1"><tr>'
	    			view += '<td style="width:2%"></td>'
	    			per=98/rec.depth
				for d in range(rec.depth):
					view += '<td style="width:'+str(per)+'"%;text-align:center"> <b>Depth - '+str(d+1)+'</b></td>'
				view += '</tr></table><p><p>'
			
		            for row in range(rec.row):
	    			view +='<b><li>Row '+str(row+1)+' - '+str(rec.name)+' </li></b><p><p>\
		    			<table style="width:100%" border="1">'
				n_row=0
				if rec.row_name.str_id == 'ASL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'ACL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'NUM':
					n_row=int(rec.r_series)+row
				elif rec.row_name.str_id == 'ROM':
					n_row=rec.int_to_roman(row+1)
		
				for column in range(rec.column):
				    view +='<tr>'
				    n_column=0
				    if rec.column_name.str_id == 'ASL':
						n_column=chr(ord(rec.c_series)+column)
				    elif rec.column_name.str_id == 'ACL':
						n_column=chr(ord(rec.c_series)+column)
				    elif rec.column_name.str_id == 'NUM':
						n_column=int(rec.c_series)+column
				    elif rec.column_name.str_id == 'ROM':
						n_column=rec.int_to_roman(column+1)
			
				    view +='<td width=2% align="center"> <font color="black"> <h4>'+str(n_column)+'</h4></td>'
				    for depth in range(rec.depth):
					n_depth=0
					if rec.depth_name.str_id == 'ASL':
						n_depth=chr(ord(rec.d_series)+depth)
					elif rec.depth_name.str_id == 'ACL':
						n_depth=chr(ord(rec.d_series)+depth)
					elif rec.depth_name.str_id == 'NUM':
						n_depth=int(rec.d_series)+depth
					elif rec.depth_name.str_id == 'ROM':
						n_depth=rec.int_to_roman(depth+1)
		
					search_id=self.env['n.warehouse.placed.product'].search([
							('n_warehouse','=',warehouse.id),
							('n_location','=',rec.location_id.id),
							('n_location_view','=',rec.id),
							('n_row','=',str(n_row)),
							('n_column','=',str(n_column)),
							('n_depth','=',str(n_depth)),
							('max_qty','=',rec.storage_capacity)])
					per=98.0/rec.depth
					if search_id:
					    url = urljoin(base_url, "/store_view/{}/".format(search_id.id))
					    bin_name=str(n_row)+str(n_column)+str(n_depth)
					    text_link = _("""<a href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
					    #text_link ='<button name="open_binlocation" string="%s" context={\'bin_id\':%s} type="object"/>'%(bin_name,search_id.id)
					    if search_id.state in ('full','partial'):
						flag=view1=reserved=False
						for store_p1 in search_id.master_batches:
						   	if store_p1.product_id.id == self.product_id.id:
						   		flag=True
						   		view1 ='<ul> ['+str(store_p1.product_id.default_code)+'] '+str(store_p1.product_id.name)+'</ul>'
						   		break
				   		if flag:
						    view +='<td width="'+str(per)+'%" > '
						    view +='<h3>'+str(text_link)+'</h3>'
						    view +=view1+'<table style="width:100%"><tr>'
						    td=1
						    for store_p1 in search_id.master_batches:
						   	if store_p1.product_id.id == self.product_id.id:
						   	     pkg_unit=''
						   	     pkg = store_p1.packaging
						   	     if pkg.uom_id.product_type:
						   	     	pkg_unit=pkg.uom_id.product_type.name
						   	     else:
						   	     	pkg_unit=pkg.uom_id.name
						   	     if store_p1.logistic_state in ('reserved','r_t_dispatch') and res.removel_strategy.method == 'reserve' and store_p1.id  in master_list:
							     	view +='<td style="background-color:green;"><font color="white"><ul><li><b>'+str(store_p1.name)+'</b></li>'
						     	     elif res.removel_strategy.method == 'fifo' and store_p1.id  in master_list:
							     	view +='<td style="background-color:green;"><font color="white"><ul><li><b>'+str(store_p1.name)+'</b></li>'
							     elif res.removel_strategy.method == 'lifo' and store_p1.id  in master_list:
							     	view +='<td style="background-color:green;"><font color="white"><ul><li><b>'+str(store_p1.name)+'</b></li>'
						   	     else:
					     			view +='<td style="background-color:LimeGreen;"><font color="white"><ul><li><b>'+str(store_p1.name)+'</b></li>'
							     view +='<li>'+str(len(store_p1.batch_id._ids))+str(pkg_unit)+'</li>'
                                                             view +='<li>'+str(store_p1.total_quantity)+str(store_p1.uom_id.name)+'</li>'
							     text_link ='<button name="pick_operation" string="SPLIT" context={\'master_id\':%s,\'bin_id\':%s} type="object" class="btn-primary"/>'%(store_p1.id,search_id.id)
                                                             pick_full_view='<field name="pick_full"/>'
                                                             view +='</ul><ul>'+text_link+'</ul>'
							     text_link_pfb ='<button name="process_full_batches" string="Pick Full Batch" context={\'master_id\':%s,\'bin_id\':%s} type="object" class="btn-primary"/>'%(store_p1.id,search_id.id)
							     view +='<ul>'+text_link_pfb+'</ul>'
                                                             view +='</ul><ul>'+pick_full_view+'</ul></font></td>'
                                                             
                                                                                                    
							     if td >4:
							     	view += '</tr><p><tr>'
							     	td=1
							     else:
							     	td+=1
							     	
						    view +='</tr></table>'
				    		else:
				    			view +='<td  style="background-color:silver;" width="'+str(per)+'%">'
							view +='<h3>'+str(text_link)+'</h3>'
						
					    elif search_id.state=='maintenance':
						view +='<td width="'+str(per)+'%" style="background-color:red;">'
						view +='<h3>'+str(text_link)+'</h3>'
				
					    elif search_id.state=='no_use':
						view +='<td width="'+str(per)+'%" style="background-color:black;">'
						view +='<h3>'+str(text_link)+'</h3>'
					    else:
						view +='<td width="'+str(per)+'%"> <h3>'+str(text_link)+'</h3>'
					    view +='</td>'
				    view +='</tr>'
				view +='</table><p><p>'
		    view_id.sudo().arch_db = view_data + view +'</group></form>'
			
	@api.model
	def fields_view_get(self, view_id=None, view_type='form', toolbar=False):
		data =super(storePikcingList, self).fields_view_get(view_id, view_type, toolbar=toolbar)
        	return data
        
        @api.multi
        @api.onchange('removel_strategy')
        def calculate_view(self):
        	for rec in self:
			form_id = self.env.ref('api_inventory.bin_picking_list_html_form_view')
			if form_id:
				self._create_html_view(form_id)
				return {'name' :'Batches To Pick from Bin-Location',
					'type': 'ir.actions.client',
					'tag': 'reload',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'store.picking.list',
					#'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'current',
					#'res_id':rec.id,
					'nodestroy' : True,
					'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
				    }
        @api.multi
	def process_full_batches(self):
            return self.with_context(call_fom_full_batch=True).pick_operation()
            
            
	@api.multi
	def pick_operation(self):
		'''Pick Button from Bin View to show confirmation wizard'''
		if not self._context.get('master_id') and not self._context.get('bin_id'):
			raise UserError("Record's are not found..!")
			
		for rec in self:
			master_batch_id = self.env['stock.store.master.batch'].search([('id','=',self._context.get('master_id'))],limit=1)
			if master_batch_id.logistic_state == 'transit':
				raise UserError("Master Batch '{}' is already Transfered to Transit-OUT Area".format(master_batch_id.name))
			
			bin_id = self.env['n.warehouse.placed.product'].search([('id','=',self._context.get('bin_id'))])
			dest_id = self.env['n.warehouse.placed.product'].search([
							('n_location','=',bin_id.n_location.id),
							('n_location_view.location_type','=','transit_out')])
			if not dest_id:
				raise UserError("Transit-OUT Area is not found")
			form_id = self.env.ref('api_inventory.store_pick_confirm_wizard')
			context=self._context.copy()
			context.update({'default_picking_id':self.picking_id.id,'default_product_id':self.product_id.id,
					'default_loc_bin_id':bin_id.id,'default_dest_bin_id':dest_id.id,
					'default_pick_list':self.id,'default_master_batch':master_batch_id.id,
					'default_t_qty':master_batch_id.total_quantity,
					'default_picked_qty':self.qty_to_pick,
					'default_operation_type':'split_tk',
					'default_t_qty_unit':master_batch_id.uom_id.name})
			if master_batch_id.total_quantity > rec.qty_to_pick:
                            
				context.update({'default_qty_warning':True})
                        if self._context.get('call_fom_full_batch',False):
                            add_vals={}
                            add_vals.update({'picking_id':self.picking_id.id,'product_id':self.product_id.id,
					'loc_bin_id':bin_id.id,'dest_bin_id':dest_id.id,
					'pick_list':self.id,'master_batch':master_batch_id.id,
					't_qty':master_batch_id.total_quantity,
					'picked_qty':master_batch_id.total_quantity,
					'operation_type':'keep',
                                        't_qty_unit':master_batch_id.uom_id.id})
                            wiz_id=self.env['store.pick.confirm.wizard'].create(add_vals)
                            return wiz_id.process_picking()

			if form_id:
				return {'name' :'Pick Confirmation',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'store.pick.confirm.wizard',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'context':context,
					'target': 'new',
				    }
			#return rec.pick_operation_process()
	
	@api.multi
	def pick_operation_process(self):
		'''Bin PIcking Confirmtion Wizard process '''
		if not self._context.get('master_id') and not self._context.get('bin_id'):
			return False
		for rec in self:
			master_batch_id = self.env['stock.store.master.batch'].search([('id','=',self._context.get('master_id'))],limit=1)
			if master_batch_id.logistic_state == 'transit':
				raise UserError("Master Batch '{}' is already Transfered to Transit-OUT Area".format(master_batch_id.name))
			
			store_id=self.env['n.warehouse.placed.product'].search([('id','=',self._context.get('bin_id'))])
			location_view = self.env['stock.location.view'].search([('location_type','=','transit_out'),('location_id','=',store_id.n_location.id)])
			transit_id = self.env['n.warehouse.placed.product'].search([('n_location_view','=',location_view.id)])
			total_quantity=0.0
			for res in store_id:
				qty=pkg_capicity=0.0
				product_id = master_batch_id.product_id
				Packaging_type = master_batch_id.packaging
				pkg_capicity_unit = pkg_unit = master_batch_id.packaging.uom_id
				total_qty_unit = master_batch_id.uom_id
				
				master_batch_id.write({'store_id':transit_id.id,
							'picking_id':rec.picking_id.id,
							'logistic_state':'transit'})
				#for btch in master_batch_id.batch_id:
				master_batch_id.batch_id.write({'store_id':transit_id.id,
							'picking_id':rec.picking_id.id,
							'logistic_state':'transit',
							'batch_history':[(0,0,{'operation':'picking',
				   'description':'Pick from Bin Location {}'.format(store_id.name)})]})
					#qty += btch.convert_product_qty
				# to update batches in pack Operation
				rec.pick_id.batch_number = [(4,x.id) for x in master_batch_id.batch_id]
				total_quantity = sum([x.convert_product_qty for x in master_batch_id.batch_id ])
				packages = len(master_batch_id.batch_id._ids)
				body1 ='<ul>Picking Operation for {} </ul>'.format(rec.picking_id.name)
				if res.product_type == 'single': ## do operation for Single product
					pkg_capicity_unit = res.pkg_capicity_unit
					pkg_unit = res.pkg_unit
					if total_quantity < res.total_quantity:
						res.write({'state':'partial','total_quantity':res.total_quantity-total_quantity,
						'packages':float(res.packages)-float(packages)})
					elif total_quantity == res.total_quantity:
						res.write({'state':'empty','product_id':False,'total_quantity':0.0,
							'total_qty_unit':False,'qty_unit':False,'pkg_capicity':0.0,
							'pkg_capicity_unit':False,'packages':0.0,'pkg_unit':False,
							'Packaging_type':False})
					else:
						print "ERROR in selecting..."
						raise
			
				else:
					# do operation for multi product
					for multi in self.env['store.multi.product.data'].search([
									('store_id','=',res.id),
									('product_id','=',product_id.id),
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
		
				self.env['location.history'].create({'stock_location':res.id,
								'product_id':product_id.id,
								'operation_name':'Send To Transit-OUT for Dispatch',
								'operation':'do',
								'qty':total_quantity,
								'n_type':'out'})
										
				# search for product Transit -OUT location..	according packagig
				store_product=self.env['store.multi.product.data'].search([
								('product_id','=',product_id.id),
							        ('store_id','=',transit_id.id),
								('Packaging_type','=',Packaging_type.id)])
								
				body1+='<li>Master Batch :{} </li>'.format(master_batch_id.name)
				if not store_product: # If product is not found add product
					transit_id.state='partial'
					add_vals={'product_id':product_id}
					body1 +="<li>Product add : "+str(product_id.name)+" </li>"
					add_vals.update({'total_quantity':total_quantity})
					add_vals.update({'total_qty_unit':total_qty_unit.id})
					body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
					body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
					add_vals.update({'packages':packages})
					add_vals.update({'pkg_unit':pkg_unit.id})
					add_vals.update({'Packaging_type':Packaging_type.id})
					body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
					transit_id.multi_product_ids=[(0,0,add_vals)]	
					transit_id.message_post(body1)		
			
				elif store_product: # if found update quantity and packages
					body1 +="<li>Product update qty : "+str(product_id.name)+" </li>"
					store_product.total_quantity += total_quantity
					body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
					#store_product.pkg_capicity += pkg_capicity
					#body1+="<li>Package Capicity updated: "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
					store_product.packages += packages
					body1+="<li>Packages updated: "+str(packages)+" </li>"
					transit_id.message_post(body1)
		
				self.env['location.history'].create({'stock_location':transit_id.id,
								'product_id':product_id.id,
								'operation_name':'for Dispatch',
								'operation':'do',
								'qty':total_quantity,
								'n_type':'in'})

			# Update Quantity in Stock Pack Operation
			rec.pick_id.pick_qty = sum([x.convert_product_qty for x in rec.pick_id.batch_number])
			print "pick_operation_process",rec.dispatch_qty,rec.qty_pick
			if rec.dispatch_qty == rec.qty_pick:
                                print "rec.picking_id.idrec.picking_id.id",rec.picking_id.id
				rec.status='pick'
		    		form_id = self.env.ref('api_inventory.store_picking_list_batch_form_view')
                                print "form_idform_idform_id",form_id
				return {'name' :'Store Picking List',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'stock.picking',
					'views': [(form_id.id, 'form')],
					'view_id': form_id.id,
					'target': 'current',
					'res_id':rec.picking_id.id,
				    }
				    
		self.status='partial'	
    		form_id = self.env.ref('api_inventory.bin_picking_list_html_form_view')
		if form_id:
			self._create_html_view(form_id)
			return {
				'name' :'Batches To Pick from Bin-Location',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'store.picking.list',
				'views': [(form_id.id, 'form')],
				'view_id': form_id.id,
				'target': 'current',
				'res_id':self.id,
				'nodestroy' : False,
				'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
				}
                                