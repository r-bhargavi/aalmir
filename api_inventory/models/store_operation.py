# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta
import math
from urlparse import urljoin
from urllib import urlencode

class locationStockOperation(models.Model):
	_name = "location.stock.operation"
	
	operation_type = fields.Selection([('add','ADD'),('update','Update'),('release','Release'),
					   ('transfer','Transfer'),('capacity','Capicity'),
					   ('split','Split')])
					   
	location_id = fields.Many2one('stock.location','Location')
	stock_location = fields.Many2one('n.warehouse.placed.product','Stock Location')
	new_stock_location = fields.Many2one('n.warehouse.placed.product','New Stock Location')
	product_type = fields.Selection([('single','Single Product'),('multi','Multi Product')],'Product Type',
					related="stock_location.n_location_view.product_type")
					
	product_id = fields.Many2one('product.product', string="Product")
	multi_product_id = fields.Many2one('store.multi.product.data', string="Product")
	unit = fields.Many2one('product.uom','Unit',related="product_id.uom_id",readonly=True)
	qty = fields.Float('Avaiable Quantity',compute='_get_product_qty',help='Available Product Quantity for any operation',store=True)
	storage = fields.Float('Available Capicity',help='Available storage capicity calculate using primary and secondary packaging qty')
	storage_unit = fields.Many2one('product.uom','Unit',related="product_id.uom_id",readonly=True)
	add_qty = fields.Float('Quantity')
	add_unit = fields.Many2one('product.uom','Unit',related="product_id.uom_id",readonly=True)
	
	primary_packaging = fields.Many2one('product.packaging','Packaging')
	check_primary = fields.Boolean(string="check Primary",default=True) # used to hide secondary pkg if product has only primary pkg
	secondary_packaging = fields.Many2one('product.packaging','Secondary Packaging')
	packaging_qty = fields.Char('Pacakges',compute='_get_packaging_qty')
	release_unit = fields.Many2one('product.uom','Release Unit')
	
	new_storage_capicity = fields.Float('New Storage Capacity')
	new_capicity_unit = fields.Many2one('product.uom','Unit',readonly=True)
	previous_storage_capicity = fields.Float('Previous Storage Capacity')
	pre_capicity_unit = fields.Many2one('product.uom','Unit',readonly=True)
	used_storage = fields.Float('Used Storage')
	used_unit = fields.Many2one('product.uom','Unit',readonly=True)
	
	master_batches = fields.Many2many('stock.store.master.batch','store_master_batch_rel','master_id','op_id',
			'Master batches')# Transfer/Release
	
	split_unit = fields.Many2one('product.uom','Unit',compute='_get_product_qty')		
	master_batche = fields.Many2one('stock.store.master.batch',string='Master batches') # spliting
	batches_ids = fields.Many2many('mrp.order.batch.number','store_opration_batch_rel','batch_id','st_op_id',
			'Child batches',help="Used in spliting operation")
			
	@api.multi
	@api.onchange('multi_product_id') # make packaging field empty and add available quantity 
	def onchange_multi_product_qty(self):
		for rec in self:
			if rec.product_type == 'multi':
				rec.primary_packaging=rec.multi_product_id.Packaging_type
				rec.product_id=rec.multi_product_id.product_id.id
				
	#write onchange because it will change the value of storage fields
	@api.multi
	@api.depends('product_id','batches_ids')
	def _get_product_qty(self):
	   if self.operation_type == 'release':  # get available quantity for release operation
		for rec in self:
		    if rec.product_id and not rec.multi_product_id:
		    	qty=0.0
			for line in self.env['n.warehouse.placed.product'].search([('product_id','=',rec.product_id.id),('id','=',rec.stock_location.id)]):
				qty += line.total_quantity    # addition
			for line in self.env['store.multi.product.data'].search([('product_id','=',rec.product_id.id),('store_id.n_location','=',rec.stock_location.id)]):
				qty += line.total_quantity		# addition
			rec.qty=qty

	   elif self.operation_type == 'transfer':  # get available quantity for Transfer operation
		for rec in self:
			if rec.multi_product_id:
				rec.qty=rec.multi_product_id.total_quantity
			else:
				rec.qty = rec.stock_location.total_quantity
	   
	   elif self.operation_type == 'split':  # get available quantity for Transfer operation
		for rec in self:
			if rec.batches_ids:
				rec.qty = sum([ q.convert_product_qty for q in rec.batches_ids])
				rec.split_unit = rec.batches_ids[0].uom_id.id if rec.batches_ids else False
			else:
				rec.qty = 0.0

	@api.multi			#TO make secondary packaging field empty for proper storage quantity calculation
	@api.onchange('primary_packaging')
	def onchange_primary_packaging(self):
		for rec in self:
			if rec.primary_packaging.uom_id:
				data_obj = self.env['ir.model.data']
				uom_id = data_obj.get_object_reference('api_inventory', 'unit_type_data7')
				if uom_id[1] in rec.primary_packaging.uom_id.unit_type._ids:
					rec.check_primary=False
				else:
					rec.check_primary=True
					
	@api.multi		#TO calculate proper storage quantity
	@api.onchange('secondary_packaging','primary_packaging')
	def _get_storage_qty(self):
		for rec in self:
			data_obj = self.env['ir.model.data']
			uom_id = data_obj.get_object_reference('api_inventory', 'unit_type_data7')
			if rec.primary_packaging.uom_id and uom_id[1] in rec.primary_packaging.uom_id.unit_type._ids:
				# if product packaging on pallet
				if self._context.get('add_stock'):
					rec.storage=rec.primary_packaging.qty*rec.stock_location.max_qty
				if self._context.get('update_stock'):
					rec.storage=(rec.stock_location.pkg_capicity-rec.stock_location.packages)
			elif self._context.get('add_stock'):
				if rec.primary_packaging and rec.secondary_packaging:
					storage=rec.primary_packaging.qty*rec.secondary_packaging.qty
					rec.storage=storage*rec.stock_location.max_qty
			elif self._context.get('update_stock'): # update available storage in Update form in packaging unit
				rec.storage=(rec.stock_location.pkg_capicity-rec.stock_location.packages)*int(rec.stock_location.Packaging_type.qty)
							
	@api.multi  # Get packaging Quantity from entered quantity
	@api.onchange('master_batches')
	def _get_packaging_qty(self):
		for rec in self:
		    if rec.add_qty >0.0 and rec.primary_packaging.qty >0.0 and rec.secondary_packaging:
			packaging_qty = str(rec.add_qty/rec.primary_packaging.qty)+" "+str(rec.secondary_packaging.unit_id.name)
			rec.packaging_qty=packaging_qty
    		    elif rec.operation_type=='update':
    		    	if rec.stock_location.Packaging_type.qty:
    		    		if rec.stock_location.pkg_unit.id==rec.stock_location.total_qty_unit.id:
    		    			rec.packaging_qty = str(rec.add_qty)+str(rec.stock_location.pkg_unit.name)
    		    		else:
	    		    		rec.packaging_qty = str(rec.add_qty/rec.stock_location.Packaging_type.qty)+" "+str(rec.stock_location.Packaging_type.uom_id.name)
	    	    elif rec.operation_type=='release':
	    	    	if rec.release_unit and rec.release_unit.id != rec.unit.id:
	    	    		unit_id= rec.stock_location.Packaging_type #self.env['product.packaging'].search([('product_tmpl_id','=',rec.product_id.product_tmpl_id.id),('unit_id','=',rec.unit.id),('uom_id','=',rec.release_unit.id)])
	    	    		qty= unit_id.qty if unit_id else 1
    		    		rec.packaging_qty = str(rec.add_qty*qty)+" "+str(rec.unit.name)
	    		else:
	    			rec.packaging_qty = str(rec.add_qty)+" "+str(rec.unit.name)
	    	    elif rec.operation_type=='transfer':
	    	     	cnt=qty=0
	    	     	unit = rec.multi_product_id.Packaging_type.uom_id if rec.multi_product_id else rec.stock_location.Packaging_type.uom_id if rec.product_id else False
	    	     	if unit and unit.product_type:
	    	     		unit = unit.product_type.name 
    	     		elif unit:
    	     			unit=unit.name
     			else :
     				unit=''
    	     		for mst in rec.master_batches:
    	     			cnt += len(mst.batch_id._ids)
    	     			#for btch in res.batch_id:
				qty +=  mst.total_quantity
			if qty:
				rec.add_qty=qty	
			rec.packaging_qty = str(cnt)+" "+str(unit) if cnt else None
	    	    		
	    			
	@api.multi	 # to check release unit and product unit for packaging quantity counting invisibility
	@api.onchange('release_unit')
	def onhcange_release_unit(self):
		for rec in self:
			if rec.release_unit and rec.release_unit.id != rec.unit.id:
	    	    		unit_id= rec.stock_location.Packaging_type 
	    	    		qty= unit_id.qty if unit_id else 1
    		    		rec.packaging_qty = str(rec.add_qty*qty)+" "+str(rec.unit.name)
	    		else:
	    			rec.packaging_qty = False
				
	@api.model
	def default_get(self, fields):
		'''get context value and update as default fro new html form view in Trasnfer operation '''
		param=self._context.get('params')
    		res = super(locationStockOperation, self).default_get(fields)
    		if param:
    			if param.get('stock_location'):
    				res['stock_location'] = param.get('stock_location')
    				res['operation_type'] = 'transfer'
			if param.get('location_id'):
    				res['location_id'] = param.get('location_id')
			if param.get('product_id') != False:
    				res['product_id'] = param.get('product_id')
		return res
	
	@api.multi
	def save(self):
		n_type=operation_name=body=""
		operation='stk'
		stock_product_id=False
		qty=0
		for res in self.master_batches:
			for btch in res.batch_id:
				qty +=  btch.convert_product_qty if btch.convert_product_qty else btch.approve_qty
		self.add_qty=qty
		if rec.operation_type=='release':
			n_type='out'
			operation_name='Release Quantity from store'
			stock_product_id=self.stock_location.product_id
			unit_id= self.stock_location.Packaging_type
			add_qty=r_pkg=0.0
				
			if self.qty == add_qty:
				body+="<li> <font color='red'>Make Store Empty</font></li>"
				self.stock_location.state = 'empty'
				self.stock_location.product_id = False
				self.stock_location.qty_unit = False
				self.stock_location.pkg_capicity = False
				self.stock_location.pkg_capicity_unit = False
				self.stock_location.packages = False
				self.stock_location.pkg_unit = False
				self.stock_location.Packaging_type = False
			else:
				body+="<ul>Quantity Release From Store"
				body+="<li>Quantity : "+str(add_qty)+(str(self.unit.name))+" </li>"
				self.stock_location.state = 'partial'
    	    			qty= unit_id.qty if unit_id else 1
				self.stock_location.packages -= r_pkg
				body+="<li>Packages : "+str(r_pkg)+str(unit_id.uom_id.name)+" </li></ul>"
			self.stock_location.total_quantity -= add_qty	
				
		if body:
			self.stock_location.message_post(body)		
		self.env['location.history'].create({'stock_location':self.stock_location.id,'n_type':n_type,
					     'product_id':stock_product_id.id,'qty':self.add_qty,
					     'operation':operation,'operation_name':operation_name,})
		return 
		
	@api.multi
	# to update the storage Capicity
	def update_capicity(self):
		for rec in self:
			if rec.new_storage_capicity <=0:
				raise UserError(_('Please Enter Proper Value'))
			if rec.new_storage_capicity < rec.used_storage:
				raise UserError(_('Please Enter Highter Value Than Previous Storage Capicity')) 
			max_qty=rec.stock_location.max_qty if rec.stock_location.max_qty else 1
			pkg_capicity = rec.stock_location.pkg_capicity if rec.stock_location.pkg_capicity else 1
			rec.stock_location.pkg_capicity = (pkg_capicity/max_qty) * rec.new_storage_capicity
			rec.stock_location.max_qty = rec.new_storage_capicity
			rec.stock_location.message_post("<ul><li>Storage Capicity Increase :"+str(rec.new_storage_capicity))
		return 

	@api.multi
	def split_master_batch(self):
		'''Split Selected Master batch to new Batch using child sub bacthes '''
		for rec in self:
			if  rec.master_batche:
				new_id=rec.master_batche.copy()
				if len(rec.master_batche.batch_id) == len(rec.batches_ids):
					raise UsserError('You can not make parent batch Empty')
				for bth in rec.batches_ids:
					bth.master_id=new_id.id
		return True
	
	@api.multi
	def update_html_view(self,view_id,loc_id):		
		view_data='<?xml version="1.0">'
		view_data +='''<form edit="true" string="Bin-Location_view">
			      	<group attrs="{'invisible':[('product_type','!=','multi')]}">
					<field name="multi_product_id"options="{'no_open':True,'no_create':True}"
						 domain="[('store_id','=',stock_location)]"/>
              			</group>
              			<group attrs="{'invisible':[('product_type','=','multi')]}">
					<field name="product_id" attrs="{'readonly':[('product_type','!=','multi')]}"/>
					<field name="product_type" invisible="1"/>
				</group>

				<group col="4">
					<field name="stock_location" readonly="1"/>
					<label for="qty"/>
					<div>
						<field name="qty" nolabel="1" class="oe_inline"/>
						<field name="unit" nolabel="1"  class="oe_inline"/>
					</div>
					<field name="operation_type" invisible="1"/>
					<field name="location_id" invisible="1"/>
				</group>
	
				<group col="4">
					<label for="add_qty" string="Quantity"/>
					<div >
						<field name="add_qty" readonly="1" nolabel="1" class="oe_inline"/>
						<field name="add_unit" readonly="1" nolabel="1"  class="oe_inline"/>
					</div>
					<field name="packaging_qty" string="Packets Quantity" readonly="1" 
						attrs="{'invisible':[('packaging_qty','=',False)]}"/>
				</group>

				<group>
					<field name="master_batches" widget="many2many_tags" string="Transfer Batches" 
						domain="[('product_id','=',product_id),('store_id','=',stock_location)]"
					 	options="{'no_open':True,'no_create':True}"/>
				</group>'''
		
		location_view=self.env['stock.location.view'].search([('location_id','=',loc_id.id),
									('location_type','=','store')])
		view ='<group col="1">'
		if location_view:
		    	view +='<table style="width:100%" border="0"> <tr>'
    			view +='<td style="background-color:white;width:15%;font-size:100%;text-align:center"><b>  Location is Empty </b></td>'
    			view +='<td style="width:5%"></td>'
			view +='<td style="background-color:green;width:17%;font-size:100%;text-align:center"> <font color="white"><b>Fully Occupied</font> </b></td>'
    			view +='<td style="width:5%"> </td>'
    			view +='<td style="background-color:LimeGreen;width:18%;font-size:100%;text-align:center"> <font color="white"><b> Partial Occupied </font> </b></td>'
    			view +='<td style="width:5%"></td>'
    			view += '<td style="background-color:red;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Location under Maintenance </font> </b></td>'
    			view +='<td style="width:5%"></td>'
    			view += '<td style="background-color:black;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Location Not in Use </font> </b></td>'
			view += '</tr></table><p> <p>'
		
		base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		for rec in location_view:
	    	        warehouse=self.env['stock.warehouse'].search([('lot_stock_id','=',rec.location_id.id)],limit=1)
		        if rec and rec.row and rec.column and rec.depth:
		            for r in range(1):
	    			view +='<table style="width:100%" border="1"><tr><td style="background-color:black;" > <font color="white"> '+str(warehouse.name+'/'+rec.location_id.name+'/'+rec.name)+'</font></td></tr> </table>'
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
					    bin_name=str(n_row)+str(n_column)+str(n_depth)
					    url = urljoin(base_url, "/store_view/{}/".format(search_id.id))
					    text_link ='<button name="open_binlocation" string="%s" context={\'bin_id\':%s} type="object"/>'%(bin_name,search_id.id)
					    #text_link = _("""<a href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
					    if search_id.product_id:
			    			if search_id.state=='full':
							view +='<td width="'+str(per)+'%" style="background-color:green;" > <font color="white">'
						else :
							view +='<td width="'+str(per)+'%" style="background-color:LimeGreen;" > <font color="white">'
						view +='<h3 >'+str(text_link)+'</h3>'
						if search_id.product_id:
							view +='<ul><li>['+str(search_id.product_id.default_code)+'] '+str(search_id.product_id.name)+'</li>'
						if search_id.total_quantity:
							view +='<li>'+str(search_id.total_quantity)+str(search_id.total_qty_unit.name)+'</li>'
						if search_id.Packaging_type:
							view +='<li>'+str(search_id.Packaging_type.name)+'</li></ul></font>'
						if search_id.state !='full':
							text_link ='<button name="transfer_validate_operation" string="Place" context={\'bin_id\':%s} type="object" class="btn-primary" />'%(search_id.id)
					     	
					     		view +='<ul>'+text_link+'</ul>'
					    elif search_id.multi_product_ids:
						if search_id.state=='full':
							view +='<td width="'+str(per)+'%" style="background-color:green;" > <font color="white">'
						else :
							view +='<td width="'+str(per)+'%" style="background-color:LimeGreen;" > <font color="white">'
						view +='<h3>'+str(text_link)+'</h3>'
						if search_id.max_qty > 10:
							view +='<table style="width:100%"><tr>'
							td=1
							for store_p1 in search_id.multi_product_ids:
							     if store_p1.product_id:
								view +='<td><ul><li> ['+str(store_p1.product_id.default_code)+'] '+str(store_p1.product_id.name)+'</li>'
							     if store_p1.total_quantity:
								view +='<li>'+str(store_p1.total_quantity)+str(store_p1.total_qty_unit.name)+'</li>'
							     if store_p1.Packaging_type:
								view +='<li>'+str(store_p1.Packaging_type.name)+'</li></td>'
							     if td >4:
							     	view += '</ul></tr><p><tr>'
							     	td=1
							     else:
							     	td+=1
							view +='</tr></table>'
						else:
						     for store_p in search_id.multi_product_ids:
							if store_p.product_id:
								view +='<ul><li>['+str(store_p.product_id.default_code)+'] '+str(store_p.product_id.name)+'</li>'
							if store_p.total_quantity:
								view +='<li>'+str(store_p.total_quantity)+str(store_p.total_qty_unit.name)+'</li>'
							if store_p.Packaging_type:
								view +='<li>'+str(store_p.Packaging_type.name)+'</li></ul><p>'
						view +='</font>'
						if search_id.state !='full':
							text_link ='<button name="transfer_validate_operation" string="Place" context={\'bin_id\':%s} type="object" class="btn-primary"/>'%(search_id.id)
					     	
					     		view +='<ul>'+text_link+'</ul>'
					    elif search_id.state=='maintenance':
						view +='<td width="'+str(per)+'%" style="background-color:red;">'
						view +='<h3>'+str(text_link)+'</h3>'
				
					    elif search_id.state=='no_use':
						view +='<td width="'+str(per)+'%" style="background-color:black;">'
						view +='<ul>'+text_link+'</ul>'
					    else:
						view +='<td width="'+str(per)+'%">'
						view +='<h3>'+str(text_link)+'</h3>'
					     	text_link ='<button name="transfer_validate_operation" string="Place" context={\'bin_id\':%s} type="object" class="btn-primary"/>'%(search_id.id)
					     	
					     	view +='<ul>'+text_link+'</ul>'
					    view +='</td>'
				    view +='</tr>'
				view +='</table><p><p>'
		view_id.sudo().arch_db = view_data + view +'</group></form>'
		
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
	def transfer_validate_operation(self):
		for rec in self:
			if not rec.product_id:
				raise UserError("Please Select product")
			if not rec.master_batches:
				raise UserError("Please Select master Batches")
			
			bin_id=self.env['n.warehouse.placed.product'].search([('id','=',self._context.get('bin_id'))])
			if not bin_id:
				raise UserError("Bin-Location not found")
			elif bin_id.state =='full':
				raise UserError("Bin-Location '{}' is fully accoupied".format(bin_id.name))
			
			if  bin_id.product_type == 'single' and bin_id.product_id.id:
				if bin_id.product_id.id != rec.product_id.id:
					raise UserError("Selected '{}' Bin in only for single product, You can't store different product in this Locaiton".format(bin_id.name))
			
			mst_str=[]
			add_new_qty = 0
			for mst in rec.master_batches:
				add_new_qty += mst.total_quantity
				if mst.store_id.id != rec.stock_location.id:
					raise UserError("Master Batch '{}' is not in current location '{}'".format(mst.name,rec.stock_location.name))
				mst_str.append(mst.name)
			mst_str = ",".join(mst_str)		
			bin_form = self.env.ref('api_inventory.transfer_bin_location_validate_wizard', False)
			context = self._context.copy()
			rec.add_qty = add_new_qty
			context.update({'default_product_id':rec.product_id.id,'default_master_batches':mst_str,
					'default_t_qty':add_new_qty,'default_t_qty_unit':rec.add_unit.id,
					'default_loc_bin_id':rec.stock_location.id,
					'default_dest_bin_id':bin_id.id,'trsf_id':rec.id})
			return {
				    'name':'Transfer Validation',
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'bin.location.validation.wizard',
				    'views': [(bin_form.id, 'form')],
				    'target': 'new',
				    'context':context,
				}
		
	@api.multi
	def bin_transfer_operation(self):
		for rec in self:
			if not rec.product_id:
				raise UserError("Please Select product")
			if not rec.master_batches:
				raise UserError("Please Select master Batches")
			bin_id=self.env['n.warehouse.placed.product'].search([('id','=',self._context.get('bin_id'))])
			if not bin_id:
				raise UserError("Bin-Location not found")
			elif bin_id.state =='full':
				raise UserError("Bin-Location '{}' is fully accoupied".format(bin_id.name))
			
			if  bin_id.product_type == 'single' and bin_id.product_id.id:
				if bin_id.product_id.id != rec.product_id.id:
					raise UserError("Selected '{}' Bin in only for single product, You can't store different product in this Locaiton".format(bin_id.name))
				
		# need to write the code for different packaging of same product
			n_type='out'
			operation_name='Transfer Quantity from store'
			body1="<ul>New Quantity Added in Store</ul>"
			body ="<li>Store Quantity is Transfered To {}</li>".format(bin_id.name)
			operation='transfer'
			
			add_qty = packages = pkg_capicity=0.0
			add_unit = Packaging_type = pkg_capicity_unit=False
			for btch in rec.master_batches:
				btch.store_id=bin_id.id
				add_unit = btch.uom_id
				packages += len(btch.batch_id)
				Packaging_type = btch.packaging
				for child in btch.batch_id:
					add_qty += child.convert_product_qty
					child.write({'store_id':bin_id.id,
					'batch_history':[(0,0,{'operation':'logistics',
				   		'description':'Transfer from Bin-{} To Bin-{}'.format(rec.stock_location.name,bin_id.name)})]})
					
			secondary_pkg = self.env['product.packaging'].search([('pkgtype','=','secondary'),
							('product_tmpl_id','=',rec.product_id.product_tmpl_id.id),
							('unit_id','=',Packaging_type.uom_id.id)],limit=1)
			
			if  rec.stock_location.product_type == 'multi':
				store_product=self.env['store.multi.product.data'].search([
						('product_id','=',rec.product_id.id),
						('store_id','=',rec.stock_location.id),
						('Packaging_type','=',Packaging_type.id)])
				if not store_product :
					raise UserError("Product Not found in '{}', Contact administrator".format(rec.stock_location.name))

				elif len(store_product)>1:
					raise UserError("Multiple Product({}) entry with same packaging found which is not allowed in bin {}, Contact administrator".format(rec.product_id.name,rec.stock_location.name))
				if (store_product.total_quantity - add_qty)<0 :
					raise UserError("Trasnfer Quantity is greater than present batch quantity, Contact administrator")
			## validation code in single product		
			if  bin_id.product_type == 'single':
				if bin_id.state=='full':
					raise UserError("Selected Bin-Location in FULLY Occoupied")
				elif bin_id.state in ('no_use','maintenance',):
					raise UserError("Selected Bin-Location is Not available for storage")
				elif bin_id.state in ('partial','empty',):
					secondary_pkg_qty = secondary_pkg.qty if secondary_pkg else 1
					pkg_capicity =  (Packaging_type.qty * secondary_pkg_qty)*bin_id.max_qty
					if add_qty > pkg_capicity :
						raise UserError("According to your packaging capacity you can store maximun {} {} quantity \n but Your Selected Quantity is {} {}".format(pkg_capicity,Packaging_type.unit_id.name,add_qty,Packaging_type.unit_id.name))
					
			pkg_capicity_unit = Packaging_type.uom_id if secondary_pkg else Packaging_type.unit_id
		# update CURRENT Bin-Location(single product)		
			if  rec.stock_location.product_type == 'single':
				rec.stock_location.total_quantity -= add_qty
				if rec.stock_location.total_quantity <= 0.0 :
					rec.stock_location.write({'state':'empty','product_id':False,
						'total_quantity':0.0,'total_qty_unit':False,'qty_unit':False,
						'pkg_capicity':0.0,'pkg_capicity_unit':False,'packages':0.0,
						'pkg_unit':False,'Packaging_type':False})
					body+="<li> Location makes empty </li>"
				else:
					new_qty = rec.stock_location.total_quantity - add_qty 
					new_pkg = rec.stock_location.packages-packages
					rec.stock_location.write({'state':'partial','total_quantity':new_qty,
								  'packages':new_pkg})
								  
					body+="<li>Quantity Transfered  : "+str(add_qty)+" </li>"
					body+="<li>Packets Transfered  : "+str(packages)+()+" </li>"
					
		# update CURRENT Bin-Location(Multi product)
			elif  rec.stock_location.product_type == 'multi':
				store_product=self.env['store.multi.product.data'].search([
						('product_id','=',rec.product_id.id),
						('store_id','=',rec.stock_location.id),
						('Packaging_type','=',Packaging_type.id)])

				if store_product.total_quantity <= add_qty:
					store_product.unlink()
				else:
					new_qty = store_product.total_quantity - add_qty 
					new_pkg = store_product.packages-packages
					store_product.write({'total_quantity':new_qty,'packages':new_pkg})
					rec.stock_location.state='partial'
					
				if rec.stock_location.multi_product_ids==[]:
					rec.stock_location.state='empty'
				
		# Transfer Quantity in NEW location(Sigle product location)
			if  bin_id.product_type == 'single':
				pkg_qty = secondary_pkg.qty if secondary_pkg else Packaging_type.qty
				pkg_capicity =  pkg_qty * bin_id.max_qty
				if not bin_id.product_id:
					bin_id.product_id = rec.product_id.id
					bin_id.total_qty_unit = add_unit.id
					body1+="<li>Product added  : "+str(rec.product_id.name)+" </li>"
					
					bin_id.pkg_unit = pkg_capicity_unit
					bin_id.Packaging_type = Packaging_type
					body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
					
					bin_id.pkg_capicity = pkg_capicity
					bin_id.pkg_capicity_unit = pkg_capicity_unit
					body1+="<li>Packaging Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
					
				else:
					body1+="<li>Product '{}' Update </li>".format(str(rec.product_id.name))
						
				bin_id.total_quantity += add_qty
				body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"
				
				bin_id.packages += packages if secondary_pkg else pkg_qty
				body1+="<li>Packets Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"
				
				if bin_id.pkg_capicity == bin_id.packages :
					bin_id.state = 'full'
				else:
					bin_id.state = 'partial'
					
		# Transfer Quantity in NEW location(Multi product location)	
			elif  bin_id.product_type == 'multi':
				store_product=self.env['store.multi.product.data'].search([
						('product_id','=',rec.product_id.id),
						('store_id','=',bin_id.id),
						('Packaging_type','=',Packaging_type.id)])
						
				if not store_product:
					add_vals={'product_id':rec.product_id.id}
					body1 +="<li>Product add : "+str(rec.product_id.name)+" </li>"
					
					add_vals.update({'total_quantity':add_qty})
					add_vals.update({'total_qty_unit':add_unit.id})
					body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"
				
					add_vals.update({'pkg_capicity':pkg_capicity})
					add_vals.update({'pkg_capicity_unit':pkg_capicity_unit.id})
					body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
				
					add_vals.update({'pkg_unit':pkg_capicity_unit})
					add_vals.update({'Packaging_type':Packaging_type.id})
					body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
					bin_id.multi_product_ids=[(0,0,add_vals)]
					
				elif store_product:
					body1 +="<li>Product update qty : "+str(rec.product_id.name)+" </li>"
					store_product.total_quantity += add_qty
					body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"
					store_product.pkg_capicity += packages
					body1+="<li>Packag Capicity : "+str(packages)+" "+str(pkg_capicity_unit.name)+" </li>"
					body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
					store_product.packages += packages
					
				#if rec.add_qty == rec.qty:
				#	bin_id.state = 'full'
				#else:
				bin_id.state = 'partial'
				
			self.env['location.history'].create({
					'stock_location':bin_id.id,
					'product_id':rec.product_id.id,
					'operation_name':'Receive Quantity from Store Transfer',
					'operation':'transfer',
					'qty':self.add_qty,
					'n_type':'in'})
					
			self.env['location.history'].create({
					'stock_location':rec.stock_location.id,
					'product_id':rec.product_id.id,
					'operation_name':'Transfer to Other Bin {}'.format(bin_id.name),
					'operation':'transfer',
					'qty':self.add_qty,
					'n_type':'out'})
					
			if body1:
				bin_id.message_post(body1)
			if body:
				rec.stock_location.message_post(body)
				
		rec.master_batches= False
		order_form = self.env.ref('api_inventory.bin_location_trasnfer_form_view', False)
		name='Transfer Quantity In Store To Store'
		context=self._context.copy()
		remove_list=('default_loc_bin_id','default_product_id','default_t_qty_unit','default_dest_bin_id',
				'trsf_id','bin_id','default_master_batches')
		context={ key:context[key] for key in context if key not in remove_list}
		self.update_html_view(order_form,rec.location_id)
		context.update({'default_stock_location':rec.stock_location.id,
				'default_location_id':rec.stock_location.n_location.id,
    				'default_operation_type':'transfer',
    				'default_product_id':rec.product_id.id,})
		if rec.stock_location.product_type=='multi':
                	context.update({'multi_product_operation':True})
        	else:
                	context.update({'product_id':rec.stock_location.product_id.id})
		return {
			    'name':name,
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'form',
			    'res_model': 'location.stock.operation',
			    'views': [(order_form.id, 'form')],
			    'view_id': order_form.id,
			    'target': 'current',
			    'nodestroy' : False,
			    'context':context,
			    'flags': {'form': {'options': {'mode': 'edit'}}},
			 }
		
