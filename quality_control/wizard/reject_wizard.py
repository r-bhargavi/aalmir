# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api, exceptions, _
import logging
import math
from openerp.exceptions import UserError
import sys
_logger = logging.getLogger(__name__)


class QualityRejectDoc(models.TransientModel):
    """This wizard is used to show rejection note."""
    
    @api.model
    def default_get(self, fields):
    	res = super(QualityRejectDoc, self).default_get(fields)
    	active_id = self._context.get('active_id')
    	if active_id:
    		res.update({'quality_line_id': active_id})
    	return res
		
    _name = 'quality.reject.qty'
    
    quality_line_id = fields.Many2one("quality.checking.line",'Quality Line',readonly=True)
    approve_line_one2many = fields.One2many('quality.reject.line.qty','line_id1','Batches Line')
    line_one2many = fields.One2many('quality.reject.line.qty','line_id2','Batches Line')
    reject_resion=fields.Many2many('quality.reject.reason','wizard_mrp_batch_reject_resion_rel','wizard_id',
        			   'resion_id',string='Reject Reason')

    @api.multi
    def action_process(self):
    	error_str=''
    	try:
		for res in self:
			reason=[]
			for reson in res.reject_resion:
				reason.append((4,reson.id))
			state1=state2=False
			vals={'product_id':res.quality_line_id.product_id.id if res.quality_line_id.product_id else False,
				'uom_id':res.quality_line_id.uom_id.id if res.quality_line_id.uom_id else False,
				'reject_uom':res.quality_line_id.uom_id.id if res.quality_line_id.uom_id else False,
				'approve_uom':res.quality_line_id.uom_id.id if res.quality_line_id.uom_id else False,
			  	'quality_line_id':res.quality_line_id.id,
			  	'quality_id':res.quality_line_id.quality_id.id,}
		  	batches_ids=[]
		  	quantity=approve_qty=0.0
		  	picking=False
	    		for line in res.quality_line_id.batch_ids:
	    			print "jjjjjjjjj",line.reject_resion
				if line.check_type =='reject':
					line.reject_resion=reason
					line.reject_qty = line.product_qty
					state=state1='reject'
					line.qty_unit_id = res.quality_line_id.uom_id.id
					reason=[]
					for reson in line.reject_resion:
						reason.append((4,reson.id))
			    		batches_ids.append((0,0,{'product_id':res.quality_line_id.product_id.id,
			    					'uom_id':res.quality_line_id.uom_id.id,
			    					'lot_id':res.quality_line_id.lot_id.id,
			    					'quantity':line.product_qty,
			    					'avail_quantity':line.product_qty,
			    					'main_batches':line.id,
			    					'state':'draft',
			    					'line_id':res.quality_line_id.id,
			    					'reject_resion':reason,
			    					'quality_id':res.quality_line_id.quality_id.id,}))
    					quantity += line.product_qty
		    		elif line.check_type !='reject':
		    			print "mmmmmmmmmm..",line.convert_product_qty
		    			state2='approve'
					line.approve_qty = line.product_qty
					approve_qty += line.convert_product_qty
					line.reject_resion=[]
					picking=True
					line.qty_unit_id = res.quality_line_id.uom_id.id
					line.logistic_state ='ready'
			
			if picking and approve_qty:
				if not res.quality_line_id.quality_id.picking_id:
					error_str='Related Transfer is not found, Please contact with Administrator'
					raise
				elif res.quality_line_id.quality_id.picking_id.state in ('done','cancel'):
					error_str='Related Transfer is in Done State, Please contact with Administrator'
					raise
				
				if not res.quality_line_id.quality_id.picking_id.pack_operation_product_ids:
					error_str='operation in picking is not proper'
					raise
				for pack in res.quality_line_id.quality_id.picking_id.pack_operation_product_ids:
					if pack.product_id.id == res.quality_line_id.product_id.id:
						pack.qty_done = approve_qty
				res.quality_line_id.quality_id.picking_id.do_new_transfer()# calling picking def
				wiz_immediate_id=self.env['stock.immediate.transfer'].search([('pick_id','=',res.quality_line_id.quality_id.picking_id.id)],order='id desc',limit=1)
		 	    	if wiz_immediate_id:
		 	    		wiz_immediate_id.process()
		 	    	else:	
			    		wiz_backorder_id=self.env['stock.backorder.confirmation'].search([('pick_id','=',res.quality_line_id.quality_id.picking_id.id)],order='id desc',limit=1)
			    		wiz_backorder_id.process()
	    	    		res.quality_line_id.quality_id.picking_id = self.env['stock.picking'].search([('backorder_id', '=', res.quality_line_id.quality_id.picking_id.id)],limit=1).id
    	    		else:
    	    			if not approve_qty:
    	    				error_str='Qty not found for transfer'
    	    			if not picking:
    	    				error_str = "picking not found"
				raise
					
			res.quality_line_id.state='partial' if state1 and state2  else state2 if state2 else state1
			if state1=='reject':
				vals.update({'quantity':quantity ,'qty_available':quantity,'reject_qty':quantity,
				    'rejected_batches_line':batches_ids,
				    'state':state,'move_status':'in_mo' if state=='reject' else False,})
				create_id=self.env['quality.checking.line.history'].create(vals)
			
	except Exception as err:
		if error_str:
			_logger.error(error_str)
   			raise UserError(error_str)
		else:
    			exc_type, exc_obj, exc_tb = sys.exc_info()
	    		_logger.error("API-EXCEPTION..Exception in Quality Checking {} {}".format(err,exc_tb.tb_lineno))
	    		raise UserError("API-EXCEPTION..Exception in Quality Checking {} {}".format(err,exc_tb.tb_lineno))
	return True

class QualityRejectDocline(models.TransientModel):
    """This wizard is used to show rejection note."""
    
    _name = 'quality.reject.line.qty'
    
    line_id1 = fields.Many2one('quality.reject.qty','Batches')  
    line_id2 = fields.Many2one('quality.reject.qty','Batches')  
    batches = fields.Char('Approve Batches')
    check_bool = fields.Boolean('check')
   
