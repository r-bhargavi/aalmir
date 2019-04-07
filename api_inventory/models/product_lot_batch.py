# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#CH03 add on_change to change base currency and converted currency

from openerp import api, fields, models, _
from openerp import fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta

class stockproductionlot(models.Model):
	_inherit = 'stock.production.lot'	
	store_id = fields.Many2one('n.warehouse.placed.product', 'Bin-Location')
        picking_id=fields.Many2one('stock.picking')

    	@api.model
    	def name_search(self, name, args=None, operator='ilike',limit=100):
        	if self._context.get('picking_origin'):
        		picking=self.env['stock.picking'].search([('id','=',self._context.get('picking_origin'))],limit=1)
                        if self._context.get('batch_no'):
                           lot_ids=self.search([('picking_id','=',picking.id)])
                           return [(rec.id,rec.name) for rec in lot_ids]
        		lots=[]
        		if self._context.get('lot_id'):
        			lots=self._context.get('lot_id')[0][2] if self._context.get('lot_id')[0] else []
                	mo_ids=self.env['mrp.production'].search([('name','=',picking.origin)],limit=1)
                	batches=self.env['mrp.order.batch.number'].search([('store_id','=',False),('logistic_state','=','ready'),('production_id','=',mo_ids.id)])
                	lot_id=self.search([('production_id','=',mo_ids.id)])
                	if lot_id:
                		args= [('id','in',[rec.lot_id.id for rec in batches if rec.lot_id.id not in lots])]
                	else:	
        			return []
        	return super(stockproductionlot,self).name_search(name, args, operator=operator,limit=limit)

class stockMasterBatch(models.Model):
	'''This Table is used to store the master batches 
	  this master batches are according to secondary pakckaging(mostly 1-pallet==1-master batch) '''
	  
	_name = 'stock.store.master.batch'	
	
	@api.model
	def default_company(self):
		return self.env.user.company_id or False
		
	name = fields.Char('Number',copy=False)	#master batch number
	store_id = fields.Many2one('n.warehouse.placed.product', 'Bin-Location',copy=True)
	location_id = fields.Many2one('stock.location', 'Stock Location',copy=True)
        lot_id = fields.Many2one('stock.production.lot', 'Lot Number',compute='_get_batches_data')
        batch_id = fields.One2many('mrp.order.batch.number','master_id', 'Batches Number',copy=False)
        check = fields.Boolean('Check')
        product_id=fields.Many2one('product.product')
        picking_id=fields.Many2one('stock.picking')
        packaging = fields.Many2one('product.packaging' ,string="Packaging",copy=True)
        #                                added by bhargavi store true

        total_quantity = fields.Float('Total Quantity',compute='_get_batches_data',store=True)
        total_quantity_dup = fields.Float('Total Quantity DUp')
        uom_id=fields.Many2one('product.uom',compute='_get_batches_data',store=True)
        #                                added by bhargavi

	logistic_state = fields.Selection([('draft','Draft'),('ready','Ready'),('transit_in','Transit-IN'),
    				('stored','In Store'),('reserved','Reserved'),('r_t_dispatch', 'Ready To Dispatch'),
    				('transit', 'Transit-OUT'),('dispatch','Dispatched'),('returned','Return'),
    				('done','Done')],string='Logistic Status',default='draft',readonly=True)
    	company_id=fields.Many2one('res.company',default=default_company)
    	
    	@api.model
    	def create(self,vals):
	    	name=self.env['ir.sequence'].next_by_code('master.batch')
	    	vals.update({'name':name})
	    	return super(stockMasterBatch,self).create(vals)
    	
    	@api.multi
    	def _get_batches_data(self):
                print "_get_batches_data_get_batches_data"
		for res in self:
                        print "resresresresresres",res
			qty=0
			uom=False
			lot_id=False
			#date = False
			for rec in res.batch_id:
				qty +=rec.convert_product_qty
				uom=rec.uom_id.id	
				lot_id = rec.lot_id.id
				#date = rec.produce_qty_date
                        res.total_quantity = qty
                        res.uom_id = uom
                        res.lot_id = lot_id
			#res.inventory_date = date

 				
class MrpWorkorderBatchNo(models.Model):
	_inherit='mrp.order.batch.number'
	
	@api.model
	def default_company(self):
		return self.env.user.company_id or False
		
	company_id=fields.Many2one('res.company',default=default_company)
    	store_id = fields.Many2one('n.warehouse.placed.product', 'Bin-Location')
	picking_id=fields.Many2one('stock.picking',string='Delivery Order',help="") # use in quality picking and delivery picking
	multi_store=fields.Many2one('store.multi.product.data',string="Multi Store",help='Store Multi Store Product view')
	master_id = fields.Many2one('stock.store.master.batch', 'Master Batch')
	
	batch_history=fields.One2many('mrp.order.batch.number.history','batch_id',string="Batch History")

	
        _sql_constraints = [('name_unique', 'unique(name)', 'Batch-Number already exists.')]
	pack_id = fields.Many2one('stock.pack.operation', 'Operation') 
	
    	@api.model
    	def name_search(self, name, args=None, operator='ilike',limit=100):
        	if self._context.get('store_wizard'):
        		args=[]
        		if not self._context.get('lot_id'):
        			return []
			max_qty = self._context.get('max_qty')
			batch=()
			if self._context.get('batch'):
        			batch +=tuple(self._context.get('batch')[0][2]) if self._context.get('batch')[0] else ()
        			max_qty -= len(batch)
        			if not max_qty:
					return []
        		material=self.search([('store_id','=',False),('approve_qty','>',0),
        					('logistic_state','=','ready'),
        					('id','not in',batch),
        					('lot_id','in',self._context.get('lot_id')[0][2])])
			
        		args=[('id','in',tuple([rec.id for rec in material if rec.id not in batch]))]
        	return super(MrpWorkorderBatchNo,self).name_search(name, args, operator=operator,limit=limit)
 
 #####Not in use
     	@api.multi
    	def pick_batch(self):
		self.logistic_state='transit'
		return { 
        		"type": "ir.actions.do_nothing",}

    	@api.multi
    	def unpick_batch(self):
   		self.logistic_state='r_t_dispatch'
   		return { 
        		"type": "set_scrollTop",}
####<<<	
	@api.multi
	def split_mrp_batch(self):
		form_id = self.env.ref('api_inventory.mrp_batch_spit_wizard')
		context=self._context.copy()
		ids=self.search([('name','ilike',self.name)])
        	new_number = self.name+str('_{}'.format(len(ids)))
		context.update({'default_product_id':self.product_id.id,'default_qty_unit':self.uom_id.id,
			'default_qty':self.convert_product_qty,'default_batch_id':self.id,
			'default_new_number':new_number})
		return {
			'name' :'Split Batch',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mrp.batch.split.wizard',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'context':context,
		    }
		
class MrpWorkorderBatchNoHistory(models.Model):
	''' This table is to store batch operation history
	 '''
	_name='mrp.order.batch.number.history'
	
    	batch_id = fields.Many2one('mrp.order.batch.number', 'Batch Number')
	description = fields.Char('Description')
	operation = fields.Selection([('production','Production'),('logistics','Logistics'),('import','Import'),
				('placing','Placing In BIn'),('quality','Quality checking'),('split','Split'),
    				('picking','Picking Store'),('dispatch','Dispatched'),('delivered','Delivered'),
    				('returned','Return'),('reserve','Reserved'),('unreserve','UnReserved'),
    				('draft','Draft')],string='Operation',default='draft',readonly=True)


