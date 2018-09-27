# -*- coding: utf-8 -*-
# copyright reserved

from datetime import date, datetime,timedelta
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import sys,os
import logging
_logger = logging.getLogger(__name__)
from openerp.exceptions import UserError
    	
class StockPicking(models.Model):
     _inherit='stock.picking' 
    
     ntransfer_type=fields.Selection(selection_add=[('rm_virtual','Raw at Virtual'),('rm_production','RM at Produciton')])
     
     material_request_id=fields.Many2one('mrp.raw.material.request', 'Request No.')
     rm_picking_ids = fields.Many2many('mrp.production.workcenter.line','wo_raw_material_picking_rel',
     			'picking_id','wo_id','Delivery No.',help="Receive Raw Material Delivery no.")
     next_prev_picking_id = fields.Many2many('stock.picking','next_previous_rm_picking_rel',
     			'next_id','prev_id','Delivery No.',help="Shows next and previous delivery number")
     rm_received_emp=fields.Many2one('hr.employee', 'Received By')
     
     '''@api.multi
     def do_transfer(self):
     	error_print=''
     	try:
     	   for rec in self:
	     	reseve_dic={}
	     	data_obj = self.env['ir.model.data']
	    	send_picking1 = data_obj.get_object_reference('api_raw_material', 'send_film_rm_picking')[1]
	    	send_picking2 = data_obj.get_object_reference('api_raw_material', 'send_injection_rm_picking')[1]
	     	if rec.picking_type_id.id in (send_picking1,send_picking2):
	     		product_dic=[]
	     		for operation in rec.pack_operation_product_ids:
	     			product_dic.append(operation.product_id.id)
			for line in rec.move_lines_related:
				if line.product_id.id in product_dic:
					quant= self.env['stock.quant'].search([('reservation_id','=',line.id)])
					if quant:
						reseve_dic.update({line.move_dest_id.id:quant.id})
        	return_val = super(StockPicking, self).do_transfer()
        	if not rec.material_request_id:
        		return return_val
        	else:
        	    if not rec.pack_operation_product_ids:
        	    	error_print='Operation Should not be empty.'
        	    	_logger.error('API-EXCEPTION.. Operation Should not be empty.')
        	    	raise
		    film_raw_picking =data_obj.get_object_reference('api_raw_material', 'receive_film_rm_picking')[1]
		    inj_raw_picking =data_obj.get_object_reference('api_raw_material','receive_injection_rm_picking')[1]
		    if rec.picking_type_id.id in (send_picking1,send_picking2):
    			for line in rec.move_lines_related:
    				if reseve_dic.get(line.move_dest_id.id):
	    				quant=self.env['stock.quant'].search([('id','=',reseve_dic.get(line.move_dest_id.id))])
	    				if quant:
	    					line.move_dest_id.state='assigned'
	    					line.move_dest_id.picking_id.state='assigned'
	    					quant.reservation_id=line.move_dest_id.id
    				
		    elif rec.picking_type_id.id in (film_raw_picking,inj_raw_picking) and rec.material_request_id.request_type != 'extra':
		    	line_ids=[l.id for l in rec.rm_picking_ids ]
		    	for line in rec.rm_picking_ids:
				for res in line.raw_materials_id:
				    if res.next_order_id.id in line_ids:
		    		    	for operation in rec.pack_operation_product_ids:
	    					if operation.product_id.id == res.product_id.id:
	    						res.receive_qty += operation.qty_done if operation.qty_done else operation.product_qty
	    						if (res.requested_qty - operation.qty_done)>0:
	    							res.requested_qty-= operation.qty_done 
    							else:
    								 res.requested_qty =0.0
						 	
					if not rec.pack_operation_product_ids:
						for move in rec.move_lines:
	    						if move.product_id.id == res.product_id.id:
	    							res.receive_qty += move.product_uom_qty
		    						if (res.requested_qty - move.product_uom_qty)>0:
		    							res.requested_qty-= move.product_uom_qty 
	    							else:
	    								 res.requested_qty =0.0

				for shift in line.wo_shift_line:
					pick_id=[pi.id for pi in shift.rec_picking_id] if shift.rec_picking_id else []
					if rec.id in pick_id:
						shift.status='received'
				for shift in line.wo_shift_raw_line:
					pick_id=[pi.id for pi in shift.rec_picking_id] if shift.rec_picking_id else []
					if rec.id in pick_id:
						shift.status='received'
		    		if line.production_id.state=='confirmed':
		    			line.production_id.state='ready'
     	except Exception as err:
     		exc_type, exc_obj, exc_tb = sys.exc_info()
     		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)
    		_logger.error("Exception in stock Transfer -: {} file {}{} line number {}".format(err,fname[0],fname[1],exc_tb.tb_lineno))
		raise UserError("Exception in stock Transfer -: {} contact administrator check log".format(error_print if error_print else err))'''
	
class stockmove(models.Model):
	_inherit='stock.move'
	
	@api.v7
	def _push_apply(self, cr, uid, moves, context=None):
		push_obj = self.pool.get("stock.location.path")
        	for move in moves:
			if not move.move_dest_id and context.get('rm_route'):
				domain = [('location_from_id', '=', move.location_dest_id.id)]
				product=self.pool.get("product.product").browse(cr, uid, context.get('product_id'), context=context)
				#priority goes to the route defined on the product and product category
				route_ids = [x.id for x in product.route_ids + product.categ_id.total_route_ids]
			
				rules = push_obj.search(cr, uid, domain + [('route_id', 'in', route_ids)], order='route_sequence, sequence', context=context)
				if not rules:
				    #then we search on the warehouse if a rule can apply
				    wh_route_ids = []
				    if move.warehouse_id:
					wh_route_ids = [x.id for x in move.warehouse_id.route_ids]
				    elif move.picking_id.picking_type_id.warehouse_id:
					wh_route_ids = [x.id for x in move.picking_id.picking_type_id.warehouse_id.route_ids]
				    if wh_route_ids:
					rules = push_obj.search(cr, uid, domain + [('route_id', 'in', wh_route_ids)], order='route_sequence, sequence', context=context)
			#	    if not rules:
					#if no specialized push rule has been found yet, we try to find a general one (without route)
			#		rules = push_obj.search(cr, uid, domain + [('route_id', '=', False)], order='sequence', context=context)
				if rules:
				    rule = push_obj.browse(cr, uid, rules[0], context=context)
				    # Make sure it is not returning the return
				    if (not move.origin_returned_move_id or move.origin_returned_move_id.location_dest_id.id != rule.location_dest_id.id):
					push_obj._apply(cr, uid, rule, move, context=context)
			else: 
				super(stockmove,self)._push_apply(cr, uid, moves, context=context)

		
		
