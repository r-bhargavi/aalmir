# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api,_
import math
from datetime import datetime
from datetime import datetime, date, time, timedelta
from openerp.exceptions import UserError
from urlparse import urljoin
from urllib import urlencode
import math
import sys
import logging
_logger = logging.getLogger(__name__)


class PickConfirmWizard(models.TransientModel):
    """Show Wizard on pick button in picking list Graph View"""
    
    _name = 'store.pick.confirm.wizard'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    product_id = fields.Many2one('product.product', string='Product')
    pick_list = fields.Many2one('store.picking.list', string='Picking')
    operation_type = fields.Selection([('keep','Select Full Master Batch'),
    					('split','Split Master Batch (Pick Existing Master Batch)'),
    					('split_tk','Split Master Batch (Pick New Master Batch)')],
    			default='keep',string='Operation Type')
    new_batch_number = fields.Char('New Master-Batch',help="Split Current Master Batch and after split New-batch keep in Bin-Location")
    
    master_batch = fields.Many2one('stock.store.master.batch','Master Batch',help="Master Batch is Transfered to Transit -OUT Area")
    t_qty = fields.Float(string="Quantity",help="In Current Batch")
    picked_qty = fields.Float(string="Qty To Pick",help="Maximum Quantity remaining to Pick")
    t_qty_unit = fields.Many2one('product.uom', string="unit")
	
    loc_bin_id  = fields.Many2one('n.warehouse.placed.product',string='Current Bin-Location')
    dest_bin_id = fields.Many2one('n.warehouse.placed.product',string='New Bin-Location')
    qty_warning = fields.Boolean('Hide',default=False)
    child_ids = fields.Many2many('mrp.order.batch.number','picking_confirm_batches_id','wiz_id','batch_id',string='Child batches',help="Selected batches Transfer to New Master Batch")
    #quantity = fields.Float(string="Quantity",help="Quantity of selcted Batches, Transfer to New Master Batch")
    
    @api.model
    def default_get(self, fields):
        result= super(PickConfirmWizard, self).default_get(fields)
        sequence = self.env['ir.sequence'].search([('code','=','master.batch')])
        next= sequence.get_next_char(sequence.number_next_actual)
	if next:
            result.update({'new_batch_number':next})
        return result
        
    #@api.onchange('child_ids')
    #def child_batch_onchange(self):
    #	for  rec in self:
    #		qty = sum([q.convert_product_qty for q  in rec.child_ids])
    #		rec.quantity= qty if qty else 0
    		
    @api.multi
    def process_picking(self):
	 for rec in self:
	 	if not self._context.get('master_id') and not self._context.get('bin_id'):
			raise UserError("Master Batch/Bin-Location are not founded..!")
		
		if rec.operation_type=='keep':
			if rec.pick_list.qty_pick + rec.t_qty > rec.pick_list.dispatch_qty:
				raise UserError("You are not allow to pick extra quantity")
				
		elif rec.operation_type=='split':
			qty =sum([line.convert_product_qty for line in rec.child_ids])
			if rec.pick_list.qty_pick + (rec.t_qty-qty) > rec.pick_list.dispatch_qty:
				raise UserError("You are not allow to pick extra quantity")
				
		elif rec.operation_type=='split_tk':
			qty =sum([line.convert_product_qty for line in rec.child_ids])
			if rec.pick_list.qty_pick + qty > rec.pick_list.dispatch_qty:
				raise UserError("You are not allow to pick extra quantity")
						
		if not rec.master_batch:
			raise UserError("Master Batch is not found..!")
	#Split Selected Master batch to new Batch using child sub bacthes
		context=self._context.copy()
		if rec.operation_type in ('split','split_tk') :
			if  not rec.child_ids:
				raise UserError("Please Select child Batches to split the master batch..!")
				
			if  rec.master_batch:
				new_id=rec.master_batch.copy()
				#for bth in rec.child_ids:
				rec.child_ids.write({'master_id':new_id.id})
				if rec.operation_type == 'split_tk' :
					context.update({'master_id':new_id.id})
		context.pop('picking_view',None)
	 	return rec.pick_list.with_context(context).pick_operation_process()
	 	 

    @api.model
    def cancel_process(self, fields):
        return True
         
