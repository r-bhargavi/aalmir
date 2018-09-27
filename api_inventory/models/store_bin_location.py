# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models,tools, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta

class StockWarehouseMain(models.Model):
	_name = "n.warehouse.placed.product"
	_inherit = 'mail.thread'
	_order = "state,n_location_view,n_row,n_column,n_depth"
	
	@api.multi
	@api.depends('pkg_capicity','packages')
	def _get_free_space(self):
		for rec in self:
			if rec.product_type=='single':
				if rec.pkg_capicity and rec.packages:
					rec.n_free_qty = (rec.packages/rec.pkg_capicity)*100
			elif rec.product_type=='multi':
				rec.n_free_qty = sum([i.free_qty for i in rec.multi_product_ids])
				
	@api.multi
	@api.depends('store_batches_ids','reserved_batches_ids')
	def _get_reserve_status(self):
		for rec in self:
			if rec.store_batches_ids and rec.reserved_batches_ids:
				rec.store_status = 'part_rev'
			elif rec.store_batches_ids:
				rec.store_status = 'stored'
			elif rec.reserved_batches_ids:
				rec.store_status = 'reserve'
				
	@api.multi
	def _get_freeqty(self):
		for res in self:
			qty=0.0
			for batch in res.store_batches_ids:
	    			if not batch.picking_id:
	    				if res.product_id.id == batch.product_id.id:
						qty += batch.convert_product_qty
			for batch in res.reserved_batches_ids:
				if not batch.picking_id:
					if res.product_id.id == batch.product_id.id:
						qty += batch.convert_product_qty
			res.free_qty += qty
			
	@api.multi
	@api.depends('n_row','n_column','n_depth')
	def name_generate(self):
	    for record in self:
	    	if record.n_location_view.location_type=='store':
			record.name = str(record.n_location.name)+'-'+str(record.n_location_view.name) +'/'+ str(record.n_row) +'/'+ str(record.n_column) +'/'+ str(record.n_depth)
		else:
			record.name = str(record.n_warehouse.name)+'/'+str(record.n_location.name)+' '+str(record.n_location_view.name)
				
	name= fields.Char('Name',compute="name_generate",store=True)
				
	n_mo_number = fields.Many2one("mrp.production","MO Number")
    	n_po_number = fields.Many2one("purchase.order","PO Number")
    	#n_do_number = fields.Many2one("stock.picking","DO Number")
    	#n_qc_number = fields.Many2one("stock.picking","QC Number")
    	
	n_warehouse = fields.Many2one('stock.warehouse','Warehouse')
	n_location = fields.Many2one('stock.location','Location')
	n_location_view = fields.Many2one('stock.location.view','Storage Name',ondelete='cascade')
	n_row = fields.Char('Row Name')
	n_column =fields.Char('Column Name')
	n_depth =fields.Char('Depth Name')
	
	product_type = fields.Selection([('single','Single Product'),('multi','Multi Product')],'Product Type',
					related="n_location_view.product_type")
	location_type = fields.Selection([('store','Physical Location'),('transit_in','Transit-IN'),
        				  ('transit_out','Transit-OUT')],'Location Type',
        				  related="n_location_view.location_type")
        				  
	product_id = fields.Many2one('product.product', string="Product")
	multi_product_ids =fields.One2many('store.multi.product.data','store_id','Product Details')

	state= fields.Selection([('empty','Empty'),('partial','Partial'),('full','FULL'),
				 ('maintenance','In Maintenance'),('no_use','Not in Use')],default='empty')
	
	store_status= fields.Selection([('stored','stored'),('reserve','Reserved'),
						('part_rev','Partially Reserved'),
						('r_t_dispatch','Read to Dispatch')],
						compute='_get_reserve_status')
						
	max_qty = fields.Float('Storage Capacity',default=0.0,help="Maximum Capacity of Bin to Store Pallets")
	qty_unit = fields.Many2one("product.uom",'Unit')
	
	pkg_capicity = fields.Float('Packages Capacity',default=0.0,help="maximum capacity of storage in packets, \
						 Caucluation based on product packaging")
	pkg_capicity_unit = fields.Many2one("product.uom",'Unit')
	n_free_qty = fields.Float('Free Space(%)',compute="_get_free_space")
	
	Packaging_type = fields.Many2one('product.packaging' ,string="Packaging",copy=True)
	packages = fields.Float('No of Packages',default=0.0,help="Total No. of packets currently in Storage")
	pkg_unit = fields.Many2one("product.uom",'Unit',help="Packages unit")
	
	total_quantity = fields.Float('Total Store Quantity',default=0.0, help="total quantity in product units")
	total_qty_unit = fields.Many2one("product.uom",'Unit')
	free_qty = fields.Float("Free Quantity",compute="_get_freeqty",help="Quantity which is not reseved for any order")
	#lot_numbers = fields.One2many('stock.production.lot','store_id', string="Lot Numbers")
	# API code
	#batches_ids = fields.One2many('picking.lot.store.location','store_id','Store Location')
	#master_batche = fields.Many2one('stock.store.master.batch',string="Master Batch")
	master_batches = fields.One2many('stock.store.master.batch','store_id', string="Master Batches")
	store_batches_ids = fields.One2many('mrp.order.batch.number','store_id','Store Location',
									domain=[('sale_id','=',False)])
	reserved_batches_ids = fields.One2many('mrp.order.batch.number','store_id','Store Location',
									domain=[('sale_id','!=',False)])
	
	image = fields.Binary("Image", attachment=True,
        		help="This field holds the image used as image for the Bin-Location, limited to 1024x1024px.")
	image_medium = fields.Binary("Medium-sized image", attachment=True,
			help="Medium-sized image of the Bin-Location. It is automatically "\
             			"resized as a 128x128px image, with aspect ratio preserved, "\
             	"only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
        #check = fields.Boolean('Select',help="Use field in create picking list")
        company_id = fields.Many2one('res.company', string='Company', required=True,
        	default=lambda self: self.env['res.company']._company_default_get('n.warehouse.placed.product'))
        	
	@api.multi
	def name_get(self):
	    result = []
	    for record in self:
	    	if record.n_location_view.location_type=='store':
			name = str(record.n_location.name)+'-'+str(record.n_location_view.name) +'/'+ str(record.n_row) +'/'+ str(record.n_column) +'/'+ str(record.n_depth)
		else:
			name = str(record.n_warehouse.name)+'/'+str(record.n_location.name)+' '+str(record.n_location_view.name)
		
		result.append((record.id, name))
	    return result
    
    	@api.multi
    	def open_stock_history(self):
    		for rec in self:
    			order_tree = self.env.ref('api_inventory.stock_location_history_action_tree', False)
			return {
			    'name':'History Location Product',
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'tree',
			    'res_model': 'location.history',
			    'views': [(order_tree.id, 'tree')],
			    'view_id': order_tree.id,
			    'domain':[('stock_location','=',rec.id)],
			    'target': 'new',
			 }

    	@api.multi
    	def stock_operation(self):
    	   for rec in self:
    		context = self._context.copy()
	    	if self._context.get('release_stock'):
    			order_form = self.env.ref('api_inventory.remove_stock_location_operation_form', False)
    			name='Release Quantity From Store {}'.format(self.name)
    			context.update({'default_product_id':rec.product_id.id if rec.product_id else False,
				'default_stock_location':rec.id,'default_location_id':rec.n_location.id,
				'default_qty':rec.total_quantity,'default_operation_type':'release'})
    			
    			if name and order_form:	
				return {
				    'name':name,
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'location.stock.operation',
				    'views': [(order_form.id, 'form')],
				    'view_id': order_form.id,
				    'context':context,
				    'target': 'new',
				 }
			 
	    	if self._context.get('transfer_stock'):
    			#order_form = self.env.ref('api_inventory.transfer_stock_location_operation_form', False)
    			order_form = self.env.ref('api_inventory.bin_location_trasnfer_form_view', False)
    			action_id = self.env.ref('api_inventory.location_stock_operation_action', False)
				
    			name='Transfer Quantity Fom Store To Store'
    			self.env['location.stock.operation'].update_html_view(order_form,rec.n_location)
    			
    			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
    			if rec.product_type=='single' and not rec.product_id.id:
    				raise UserError('No Product Found in {} for Transfer Operation'.format(rec.name))
                        record_url = base_url + "/web?#view_type=form&model=location.stock.operation&action={}&stock_location={}&location_id={}".format(action_id.id,rec.id,rec.n_location.id)
                        if rec.product_id.id:
                        	record_url += '&product_id={}'.format(rec.product_id.id)
                        print ";;;;;;;;;;;.....",record_url
			return {
				    'type': 'ir.actions.act_url',
				    'target': 'new',
				    'url': record_url,
			 }
			'''return {
				    'name':name,
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'location.stock.operation',
				    'views': [(order_form.id, 'form')],
				    'view_id': order_form.id,
				    'context':context,
				    'target': 'current',
				    'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
				 }'''
			 
	@api.multi
	def change_storage_capicity(self):
    		context = self._context.copy()
    		unit=self.env['product.uom'].search([('name','=ilike','pallet')],limit=1)
    		packages = (self.pkg_capicity if self.pkg_capicity else 1) / (self.max_qty if self.max_qty else 1)
		context.update({'default_previous_storage_capicity':self.max_qty,
				'default_pre_capicity_unit':unit.id,
				'default_used_storage':float(self.packages)/packages,
				'default_stock_location':self.id,
				'default_new_capicity_unit':unit.id,
				'default_used_unit':unit.id})
		order_form = self.env.ref('api_inventory.update_storage_capicity_operation_form', False)
		return {
			    'name':"Update Storage Capicity",
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'form',
			    'res_model': 'location.stock.operation',
			    'views': [(order_form.id, 'form')],
			    'view_id': order_form.id,
			    'context':context,
			    'target': 'new',
			 }

	@api.model
    	def name_search(self, name, args=None, operator='ilike',limit=100):
    		# used in move to location validation wizard
		if self._context.get('outgoing_wizard'):
			args=[]
        		if self._context.get('product_id'):
        			store=[]
        			if self._context.get('store_id'):
	        			store=self._context.get('store_id')[0][2] if self._context.get('store_id')[0] else []
				wizard=self.env['stock.store.location.wizard'].search([('id','=',self._context.get('wizard_id'))])
				mrp_batches=self.env['mrp.order.batch.number'].search([('product_id','=',self._context.get('product_id')),('store_id','!=',False),('sale_id.name','=',str(wizard.picking.origin))])
				store_ids=list(set([rec.store_id.id for rec in mrp_batches if rec.store_id.id not in store]))
				args=[('id','in',store_ids)]
                		
		# used in transfer to location wizard in store location view
		if self._context.get('operation_store'):
			args=[]
			product_id=False
			if self._context.get('multi_product_id'):
				product_id=self.env['store.multi.product.data'].search([('id','=',self._context.get('multi_product_id'))]).product_id.id
			else:
				product_id= self._context.get('product_id')
			
			if product_id:
        			if self._context.get('store_id'):
                			store = self.search([('state','=','empty')])
                			store += self.search([('id','!=',self._context.get('store_id')),('product_id','=',product_id)])
                			return [(rec.id,str(rec.n_location.name)+'-'+str(rec.n_location_view.name) +'/'+ str(rec.n_row) +'/'+ str(rec.n_column) +'/'+ str(rec.n_depth)) for rec in store ]
        			return []
        		return []
		if self._context.get('picking_list'):
			args=[]
			if self._context.get('product_id') and self._context.get('picking_id'):
				new_batches=self.env['mrp.order.batch.number'].search([('store_id','!=',False),
							('product_id','=',self._context.get('product_id')),
							'|',('picking_id','!=',self._context.get('picking_id')),
							('picking_id','=',False),
							('logistic_state','in',('stored','reserved','r_t_dispatch'))])
				args=[('id','in',[i.store_id.id for i in new_batches])]
        	return super(StockWarehouseMain,self).name_search(name, args, operator=operator,limit=limit)	

	@api.multi
	def operation_on_store(self):
		'''Store Available opeartion like "maintenace","not in use" '''
		if self.state == 'empty' or self._context.get('in_use'):
			if self.product_id or self.multi_product_ids:
				raise Usererror('Please make Empty location to perform operation')
			if self._context.get('maintenance'):
				self.state = 'maintenance'
			elif self._context.get('not_in_use'):
				self.state = 'no_use'
			elif self._context.get('in_use'):
				self.state = 'empty' 
			else:
				raise Userror('Operation is not performerd.')
		else:
			raise Usererror('Please make Empty location to perform operation')

	@api.multi
	def split_opeartion(self):
    		context = self._context.copy()
		context.update({'default_stock_location':self.id,'default_operation_type':'split'})
		order_form = self.env.ref('api_inventory.spliting_master_batch', False)
		return {
			    'name':"Split Master Batches",
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'form',
			    'res_model': 'location.stock.operation',
			    'views': [(order_form.id, 'form')],
			    'view_id': order_form.id,
			    'context':context,
			    'target': 'new',
			 }

        @api.multi
        def write(self,vals):
        	if vals.get('image'):
			vals.update({'image_medium':tools.image_resize_image_medium(vals.get('image'),(256, 128))})
        	return super(StockWarehouseMain,self).write(vals)	
        	
class locationHistory(models.Model):
	_name = "location.history"
	
	stock_location = fields.Many2one('n.warehouse.placed.product','Stock Location')
	product_id = fields.Many2one('product.product', string="Product")
	qty = fields.Float('Quantity')
	operation_name= fields.Char('Discreption')
	operation = fields.Selection([('im','Import'),('mo','Manufacture'),('po','Purchase'),('do','Delivery'),('transfer','Transfer'),('stk','Stock')],string='Operation')
	n_type = fields.Selection([('in','IN'),('out','OUT')],string="Type",default='in')
	
	n_mo_number = fields.Many2one("mrp.production","MO Number")
    	n_po_number = fields.Many2one("purchase.order","PO Number")
    	n_do_number = fields.Many2one("stock.picking","DO Number")
    	n_qc_number = fields.Many2one("stock.picking","QC Number")

class storeMultiProduct(models.Model):
	_name="store.multi.product.data"
	_rec_name="product_id"
	_order ='product_id,total_quantity'

	@api.multi
	@api.depends('pkg_capicity','packages','product_id')
	def _get_free_space(self):
		for rec in self:
			if rec.pkg_capicity>0:
				rec.n_free_qty = (rec.packages/rec.pkg_capicity)*100
		
		pallets = len(rec.store_id.master_batches)
		rem_pallet = rec.store_id.max_qty - pallets
		secondary=self.env['product.packaging'].search([('unit_id','=',rec.Packaging_type.uom_id.id),
					('product_tmpl_id','=',rec.product_id.product_tmpl_id.id),
					('pkgtype','=','secondary')],limit=1)
		if secondary:
			rec.pkg_capicity = secondary.qty * rem_pallet
					
	store_id =fields.Many2one('n.warehouse.placed.product','Store Name')
	product_id = fields.Many2one('product.product', string="Product")
	Packaging_type = fields.Many2one('product.packaging' ,string="Packaging",copy=True)
	
	pkg_capicity = fields.Float('Packages Capacity',compute="_get_free_space",help="maximum capacity of storage in packets, Caucluation based on product packaging")
	pkg_capicity_unit = fields.Many2one("product.uom",'Unit')
	
	free_qty = fields.Float('Free Space(%)',compute="_get_free_space")
	
	packages = fields.Float('No of Packages',compute="_get_batches_details",help="Total No. of packets currently in Storage,Packages Calculate on the Basis on child batches",)
	pkg_unit = fields.Many2one("product.uom",'Unit')
	
	total_quantity = fields.Float('Total Store Quantity',default=0.0, help="total quantity in product units")
	total_qty_unit = fields.Many2one("product.uom",'Unit')
	multi_product_ids =fields.One2many('mrp.order.batch.number','multi_store',string='Batch Details',compute='_get_batches_details')

	@api.model
	def _get_batches_details(self):
		for res in self:
			master_batch_id = self.env['stock.store.master.batch'].search([('store_id','=',res.store_id.id),('product_id','=',res.product_id.id),('packaging','=',res.Packaging_type.id)])._ids
			batches=self.env['mrp.order.batch.number'].search([('store_id','=',res.store_id.id),('product_id','=',res.product_id.id),('master_id','in',master_batch_id)])
			res.multi_product_ids=batches
			res.packages = len(batches)	# update packets quantity
			
			
