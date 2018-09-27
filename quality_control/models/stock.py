# -*- coding: utf-8 -*-
# copyright reserved

from datetime import date, datetime,timedelta
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError

class stockPicking(osv.osv):
    _inherit='stock.picking'
        	
    @api.model
    def create(self,vals):
    	res =super(stockPicking,self).create(vals)
    	if res.location_id.quality_ck_loc:
    		res.ntransfer_type='quality'
    	return res
    	
    	
class stock_move(osv.osv):
    _inherit='stock.move'
    
 #CH_N111 add code to get seperate Quality Check for each MO
    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, context=None):
        """Try to assign the moves to an existing picking
        that has not been reserved yet and has the same
        procurement group, locations and picking type  (moves should already have them identical)
         Otherwise, create a new picking to assign them to.
        """
        move = self.browse(cr, uid, move_ids, context=context)[0]
        pick_obj = self.pool.get("stock.picking")
	#picks =pick_obj.search(cr,uid,[('origin','=',move.origin)])
	#if not picks:
	print "lllllllllll,,,,----------------",move.origin
	picks = pick_obj.search(cr, uid, [('origin','=',move.origin),
				('group_id', '=', move.group_id.id),
				('location_id', '=', move.location_id.id),
				('location_dest_id', '=', move.location_dest_id.id),
				('picking_type_id', '=', move.picking_type_id.id),
				('printed', '=', False),
                		('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], 
				limit=1, context=context)
	'''if not picks:
		picks = pick_obj.search(cr, uid, [
				('group_id', '=', move.group_id.id),
				('location_id', '=', move.location_id.id),
				('location_dest_id', '=', move.location_dest_id.id),
				('picking_type_id', '=', move.picking_type_id.id),
				('printed', '=', False),
                		('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], 
				limit=1, context=context)'''
		
        if picks:
            pick = picks[0]
        else:
            values = self._prepare_picking_assign(cr, uid, move, context=context)
            pick = pick_obj.create(cr, uid, values, context=context)
        return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)
 
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
class stocklocation(models.Model):
    _inherit = "stock.location"
	
    quality_ck_loc = fields.Boolean("Is Quality Location",help='If you check this then the location is used for Quality Check Location', default=False) # used in MRP or PO for send finished product in location for Quality check
   
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('production_loc'):
        	if self._context.get('product_id'):
        		product=self.env['product.product'].search([('id','=',self._context.get('product_id'))])
			if self._context.get('sale_id') and product.check_quality:
				sale=self.env['sale.order'].search([('id','=',self._context.get('sale_id'))])
				if sale and sale.warehouse_id:
					flag=True
					for ar in args:
						if ar[0] and ar[0]=='id':
							ar[2].append(sale.warehouse_id.wh_qc_stock_loc_id.id)
							flag=False
					if flag:
						args.extend([('id','in',[sale.warehouse_id.wh_qc_stock_loc_id.id])])
        return super(stocklocation,self).name_search(name, args, operator=operator, limit=limit)


class stockWarehouse(models.Model):
    _inherit = "stock.warehouse"
 
    qc_type_id = fields.Many2one('stock.picking.type', 'Quality Check')
    quality_control_check = fields.Many2many('stock.location.route','warehoues_route_quality_relation',
    		'warehouse_id','route_id', 'Quality Check',help="select the roues on which quality control is used")
    
    @api.model
    def create(self,vals):
    	location_obj=self.env['stock.location']
    	push_obj=self.env['stock.location.path']
    	warehouse=super(stockWarehouse,self).create(vals)
    	warehouse.wh_qc_stock_loc_id.quality_ck_loc=True
    	# code for add push method in routes
    	if warehouse.reception_steps=='three_steps':
    		push_name=str(warehouse.code)+': Quality Control -> Stock'
    		data_obj = self.env['ir.model.data']
    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
    		if mo_route:
    			quality_route=push_obj.search([('route_id','=',mo_route),
			    			('location_from_id','=',warehouse.wh_qc_stock_loc_id.id),
			    			('picking_type_id','=',warehouse.qc_type_id.id)])
    			if not quality_route:
    				push_obj.create({'name':push_name,'route_id':mo_route,
    						'location_from_id':warehouse.wh_qc_stock_loc_id.id,    							'location_dest_id':warehouse.lot_stock_id.id,
    						'picking_type_id':warehouse.qc_type_id.id})
	return warehouse

    @api.v7
    def create_sequences_and_picking_types(self,cr,uid,warehouse,context):
    	super(stockWarehouse,self).create_sequences_and_picking_types(cr,uid,warehouse,context)
    	seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        #create new sequences
        int_seq_id = seq_obj.create(cr, uid, {'name': warehouse.name + _(' Sequence quality'), 'prefix': warehouse.code + '/QC/', 'padding': 5}, context=context)
       
        #order the picking types with a sequence 
        max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
    	quality_type = picking_type_obj.create(cr,uid,vals={
					    'name': _('Quality Check'),
					    'warehouse_id': warehouse.id,
					    'code': 'internal',
					    'use_create_lots': False,
					    'use_existing_lots': True,
					    'sequence_id': int_seq_id,
					    'default_location_src_id': warehouse.wh_output_stock_loc_id.id,
					    'default_location_dest_id': warehouse.lot_stock_id.id,
					    'sequence': max_sequence + 2,
					    'active':warehouse.reception_steps=='three_steps',
					    'color': warehouse.int_type_id.color},context=context)
    	return super(stockWarehouse, self).write(cr, uid, warehouse.id, vals={'qc_type_id':quality_type}, context=context)
	
    @api.multi
    def write(self,vals):
    	for warehouse in self:
    	    warehouse.wh_qc_stock_loc_id.quality_ck_loc=True
    	    active=True if vals.get('reception_steps') == 'three_steps' else False
    	    wh_qc_type_id=warehouse.qc_type_id
    	    if not wh_qc_type_id:
    	    	seq_obj = self.env['ir.sequence']
        	picking_type_obj = self.env['stock.picking.type']
        	#create new sequences
        	int_seq_id = seq_obj.create({'name': warehouse.name + _(' Sequence quality'), 'prefix': warehouse.code + '/QC/', 'padding': 5})
       
        	#order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        	max_sequence = picking_type_obj.search_read([],['sequence'], order='sequence desc')
        	max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
        	
    	    	quality_type = picking_type_obj.create({
						    'name': _('Quality Check'),
						    'warehouse_id': warehouse.id,
						    'code': 'internal',
						    'use_create_lots': False,
						    'use_existing_lots': True,
						    'sequence_id': int_seq_id.id,
						    'default_location_src_id': warehouse.wh_output_stock_loc_id.id,
						    'default_location_dest_id': warehouse.lot_stock_id.id,
						    'sequence': max_sequence + 2,
						    'active':active,
						    'color': warehouse.int_type_id.color})
	        wh_qc_type_id=quality_type
	    	vals.update({'qc_type_id':quality_type.id})
	    if vals.get('code') or vals.get('name'):
	    	name = warehouse.name
	    	if vals.get('name'):
                    name = vals.get('name', warehouse.name)
    		if warehouse.out_type_id:
                    warehouse.qc_type_id.sequence_id.write({'name': name + _(' Sequence quality'), 'prefix': vals.get('code', warehouse.code) + '/QC/'})
            
            # code for Update push method in routes  
            push_obj=self.env['stock.location.path']   
	    if vals.get('reception_steps')=='three_steps':
    		push_name=str(warehouse.code)+': Quality -> Pre-Stock Location'
    		data_obj = self.env['ir.model.data']
    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
    		if mo_route:
    			quality_route=push_obj.search([('route_id','=',mo_route),('active','=',False),
    						('location_from_id','=',warehouse.wh_qc_stock_loc_id.id),
    						('picking_type_id','=',warehouse.qc_type_id.id)])
    			if not quality_route:
    				push_obj.create({'name':push_name,'route_id':mo_route,
    						'location_from_id':warehouse.wh_qc_stock_loc_id.id, 							'location_dest_id':warehouse.lot_stock_id.id,
    						'picking_type_id':wh_qc_type_id.id})
			else:
				quality_route.active=True
	    elif vals.get('reception_steps') and vals.get('reception_steps') !='three_steps':
		data_obj = self.env['ir.model.data']
    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
    		if mo_route:
    			quality_route=push_obj.search([('route_id','=',mo_route),
    							('location_from_id','=',warehouse.wh_qc_stock_loc_id.id),
    							('picking_type_id','=',warehouse.qc_type_id.id)])
			if quality_route:
				quality_route.active=False
	return super(stockWarehouse,self).write(vals)
	
    @api.multi
    def switch_location(self,warehouse, new_reception_step=False, new_delivery_step=False):
    	super(stockWarehouse,self).switch_location(warehouse, new_reception_step=new_reception_step, new_delivery_step=new_delivery_step)
        location_obj = self.env['stock.location']
        new_reception_step = new_reception_step or warehouse.reception_steps
        if warehouse.reception_steps != new_reception_step:
        	if new_reception_step == 'three_steps':
        		if warehouse.qc_type_id:
        			warehouse.qc_type_id.active= True
        		if warehouse.wh_qc_stock_loc_id:
        			warehouse.wh_qc_stock_loc_id.active= True
        	else:
        		if warehouse.qc_type_id:
        			warehouse.qc_type_id.active= False
			if warehouse.wh_qc_stock_loc_id:
				warehouse.wh_qc_stock_loc_id.active=False
        return True
        
        
