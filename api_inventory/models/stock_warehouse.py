# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, exceptions, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta

class stockWarehouse(models.Model):
    _inherit = "stock.warehouse"
 
    move_type_id = fields.Many2one('stock.picking.type', 'Pre-Stock Picking')
    #wh_move_stock_loc_id = fields.Many2one('stock.location', 'Store Location',help="this location is used for Move to Stock storage location in warehouse")
    user_rel = fields.Many2many('res.users','warehouse_user_operation_rel','warehouse_id','user_id','Store Operators',help="select operator to perform bin-location operations \n1. Transfer to bin-location \n2. Pick for dispatch")
    
    '''@api.model
    def create(self,vals):
    	location_obj=self.env['stock.location']
    	push_obj=self.env['stock.location.path']
    	warehouse=super(stockWarehouse,self).create(vals)
    	if warehouse.reception_steps == 'three_steps':	
	    	location_vals={'name': 'Pre-Stock Location',
		        	'usage': 'internal',
		        	'location_id': warehouse.lot_stock_id.location_id.id,
		        	'active': True,
		        	'company_id' : warehouse.company_id.id,
		        	'pre_ck':True}
	    	location_id = location_obj.create(location_vals)
	    	warehouse.wh_move_stock_loc_id=location_id.id
	    	warehouse.lot_stock_id.actual_location = True
    		push_name=str(warehouse.code)+': Pre-Stock -> Stock'
    		data_obj = self.env['ir.model.data']
    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
    		if mo_route:
    			stock_qc_route=push_obj.search([('route_id','=',mo_route),('active','=',False),
    						('location_from_id','=',warehouse.wh_qc_stock_loc_id.id),
    						('picking_type_id','=',warehouse.qc_type_id.id)])
    			if stock_qc_route:
    				stock_qc_route.location_dest_id=warehouse.wh_move_stock_loc_id.id
			else:
				push_name=str(warehouse.code)+': Quality Control -> Pre-Stock'
				push_obj.create({'name':push_name,'route_id':mo_route,
    						'location_from_id':warehouse.wh_qc_stock_loc_id.id,    							'location_dest_id':warehouse.wh_move_stock_loc_id.id,
    						'picking_type_id':warehouse.qc_type_id.id})
    						
    			move_route=push_obj.search([('route_id','=',mo_route),
			    			('location_from_id','=',warehouse.wh_move_stock_loc_id.id),
			    			('picking_type_id','=',warehouse.move_type_id.id)])
    			if not move_route:
    				push_obj.create({'name':push_name,'route_id':mo_route,
    						'location_from_id':warehouse.wh_move_stock_loc_id.id,    							'location_dest_id':warehouse.lot_stock_id.id,
    						'picking_type_id':warehouse.move_type_id.id})
    	return warehouse'''
    
    @api.v7
    def create_sequences_and_picking_types(self,cr,uid,warehouse,context):
    	super(stockWarehouse,self).create_sequences_and_picking_types(cr,uid,warehouse,context)
    	seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        #create new sequences
        int_seq_id = seq_obj.create(cr, uid, {'name': warehouse.name + _(' Sequence Pre-Stock'), 'prefix': warehouse.code + '/P-INT/', 'padding': 5}, context=context)
       
        #order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
    	move_type = picking_type_obj.create(cr,uid,vals={
			    'name': _('Move In Locations'),
			    'warehouse_id': warehouse.id,
			    'code': 'internal',
			    'use_create_lots': False,
			    'use_existing_lots': True,
			    'sequence_id': int_seq_id,
			    'default_location_src_id': warehouse.wh_input_stock_loc_id.id,
			    'default_location_dest_id': warehouse.lot_stock_id.id,
			    'active':warehouse.reception_steps=='three_steps',
			    'sequence': max_sequence + 2,
			    'color': warehouse.int_type_id.color},context=context)
    	return super(stockWarehouse, self).write(cr, uid, warehouse.id, vals={'move_type_id':move_type}, context=context)
		
    @api.multi
    def write(self,vals):
    	for warehouse in self:
    	    push_obj=self.env['stock.location.path'] 
    	    move_type_id=warehouse.move_type_id
    	    if not move_type_id:
    	    	seq_obj = self.env['ir.sequence']
        	picking_type_obj = self.env['stock.picking.type']
        	#create new sequences
        	int_seq_id = seq_obj.search([('name','=',str(warehouse.name + _(' Sequence Pre-Stock'))),('prefix','=',str(warehouse.code + '/P-INT/'))])
       		if not int_seq_id :
       			int_seq_id = seq_obj.create(cr, uid, {'name': warehouse.name + _(' Sequence Pre-Stock'), 'prefix': warehouse.code + '/P-INT/', 'padding': 5}, context=context)
        	#order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        	max_sequence = picking_type_obj.search_read([],['sequence'], order='sequence desc')
        	max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
        	
    		move_type_id = picking_type_obj.create({
					    'name': _('Move In Locations'),
					    'warehouse_id': warehouse.id,
					    'code': 'internal',
					    'use_create_lots': False,
					    'use_existing_lots': True,
					    'sequence_id': int_seq_id.id,
					    'default_location_src_id': warehouse.wh_input_stock_loc_id.id,
					    'default_location_dest_id': warehouse.lot_stock_id.id,
					    'sequence': max_sequence + 2,
					    'color': warehouse.int_type_id.color,
					    'active':False})
	    	vals.update({'move_type_id':move_type_id.id})
	    	
    	    if vals.get('reception_steps') and vals.get('reception_steps')=='two_steps' :
    	    	wh_input_stock_loc_id=warehouse.wh_input_stock_loc_id
    	    	location_obj=self.env['stock.location']
    	    	location_obj.sudo().browse(wh_input_stock_loc_id.id).write({'pre_ck': True})
	    	location_obj.sudo().browse(warehouse.lot_stock_id.id).write({'actual_location': True})
	    	
	    	            # code for Update push method in routes  
    		'''push_name=str(warehouse.code)+': Pre-Stock Location -> Stock'
    		data_obj = self.env['ir.model.data']
    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
    		if mo_route:
    			# check push rule for Quality to Store if found Then update push dest_id
    			stock_qc_route=push_obj.search([('route_id','=',mo_route),('active','=',False),
    						('location_from_id','=',warehouse.wh_qc_stock_loc_id.id),
    						('picking_type_id','=',warehouse.qc_type_id.id)])
    			if stock_qc_route:
    				stock_qc_route.location_dest_id=wh_move_stock_loc_id.id
    			# check push rule for pre-stock to Store if not Then Create
    			stock_move_route=push_obj.search([('route_id','=',mo_route),
    						('location_from_id','=',wh_move_stock_loc_id.id),
    						('picking_type_id','=',move_type_id.id)])
    			if not stock_move_route:
    				push_obj.create({'name':push_name,'route_id':mo_route,
    						'location_from_id':wh_move_stock_loc_id.id, 								'location_dest_id':warehouse.lot_stock_id.id,
    						'picking_type_id':move_type_id.id if move_type_id else False})
			else:
				stock_move_route.active=True'''
	    	move_type_id.active=True
    	    elif vals.get('reception_steps') and vals.get('reception_steps') not in ('three_steps','two_steps'):
			data_obj = self.env['ir.model.data']
	    		mo_route = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
	    		if mo_route:
	    			move_route=push_obj.search([('route_id','=',mo_route),('location_from_id','=',warehouse.wh_input_stock_loc_id.id),('picking_type_id','=',warehouse.move_type_id.id)])
				if move_route:
					move_route.active=False
	print "lllllllll...",vals,self.move_type_id.active
	return super(stockWarehouse,self).write(vals)

    @api.multi
    def switch_location(self,warehouse, new_reception_step=False, new_delivery_step=False):
    	super(stockWarehouse,self).switch_location(warehouse, new_reception_step=new_reception_step, new_delivery_step=new_delivery_step)
        location_obj = self.env['stock.location']
        new_reception_step = new_reception_step or warehouse.reception_steps
        if warehouse.reception_steps != new_reception_step:
            #if not self._location_used(warehouse.wh_move_stock_loc_id.id, warehouse):
            #    warehouse.wh_move_stock_loc_id.active=False
            if new_reception_step == 'two_steps':
		if warehouse.move_type_id:
			warehouse.move_type_id.active= True
		if warehouse.wh_input_stock_loc_id:
			warehouse.wh_input_stock_loc_id.active=True
            else:
		if warehouse.move_type_id:
			warehouse.move_type_id.active= False
		if warehouse.wh_input_stock_loc_id:
			warehouse.wh_input_stock_loc_id.active=False
        return True

class stockPickingType(models.Model):
	_inherit ='stock.picking.type'
	
	@api.multi
	def write(self,vals):
		print "++++----",self,vals
		return super(stockPickingType,self).write(vals)
		
