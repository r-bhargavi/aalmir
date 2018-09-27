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

class stock_return_picking(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    #reverse_type=fields.Selection([('child_batches','Child Batches'), 
    #				     ('master_batches', 'Master Batches'),
    #				     ('new_batches','New Batches'),
    #				     #('both','Child&Master Batches')
    #				     ], string="Reverse Type")
    
    #master_ids = fields.Many2many('picking.lot.store.location','master_batch_return_history','wiz_id','btch_id','Master Batches')
   # batche_ids = fields.Many2many('picking.lot.store.location.batches','child_batch_return_history','wiz_id','btch_id','Child Batches')
   # batch_exist = fields.Boolean('Exist',default=False)
    				     				     
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if self._context and self._context.get('active_ids', False):
            if len(self._context.get('active_ids')) > 1:
                raise UserError(_("You may only return one picking at a time!"))
        #res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = self._context and self._context.get('active_id', False) or self._context.get('new_active_id', False) or False
        uom_obj = self.env['product.uom']
        pick_obj = self.env['stock.picking']
        pick = pick_obj.browse(record_id)
        quant_obj = self.env['stock.quant']
        chained_move_exist = False
        res={}
        if pick:
            if pick.state not in ('done','delivered'):
                raise UserError(_("You may only return pickings that are Done or Delivered"))

            for move in pick.move_lines:
                if move.scrapped:
                    continue
                if move.move_dest_id:
                    chained_move_exist = True
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quant_search = quant_obj.search([('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)])
                for quant in quant_search:
			if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        	qty += quant.qty
                qty = uom_obj._compute_qty(move.product_id.uom_id.id, qty, move.product_uom.id)
                result1.append((0, 0, {'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id}))

            if len(result1) == 0:
                raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': chained_move_exist})
            if 'parent_location_id' in fields and pick.location_id.usage == 'internal':
                res.update({'parent_location_id':pick.picking_type_id.warehouse_id and pick.picking_type_id.warehouse_id.view_location_id.id or pick.location_id.location_id.id})
            if 'original_location_id' in fields:
                res.update({'original_location_id': pick.location_id.id})
            if 'location_id' in fields:
                res.update({'location_id': pick.location_id.id})
            '''if pick.store_ids:
            	batche_ids=[]
            	for line in pick.store_ids:
            		batche_ids.extend(line.batches_ids._ids)
            		print "111111111111111,,,,,,",line.batches_ids._ids
    		print "222222222222222222222,,,,,,",line.batches_ids._ids
    		print "---------------------",pick.store_ids._ids
            	res.update({'master_ids':[(6,0,pick.store_ids._ids)],
            		    'batch_exist':True,
            		    'batche_ids':[(6,0,batche_ids)],
            			})'''
        return res

'''# history of picking and location				    
class pickinglotstore(models.TransientModel):
	_name="picking.lot.store.location"
	
	picking_id = fields.Many2one('stock.picking','Move name')
	product_id = fields.Many2one('product.product','Product Name')
	master_id = fields.Many2one('stock.store.master.batch','Master Batch')
	quantity = fields.Float('Quantity')
	unit_id = fields.Many2one('product.uom',"Unit")
     	
class pickinglotstoreBatches(models.TransientModel):
	_name="picking.lot.store.location.batches"
	
	history_id = fields.Many2one('picking.lot.store.location','History')
	product_id = fields.Many2one('product.product','Product Name')
	store_id = fields.Many2one('n.warehouse.placed.product','Store Name')
	quantity = fields.Float('Quantity')
	unit_id = fields.Many2one('product.uom',"Unit")
	lot_number = fields.Many2one('stock.production.lot','Lot Number')
	batch_number = fields.Many2one('mrp.order.batch.number','Batch Number')
	is_return = fields.Boolean('Return',default=False)
	date_return = fields.Datetime('Return Date')'''


