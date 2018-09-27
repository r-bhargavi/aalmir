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
    
    ntransfer_type=fields.Selection(selection_add=[('quality','Quality Check')])
        	
    @api.model
    def create(self,vals):
    	res =super(stockPicking,self).create(vals)
    	if res.location_id.quality_ck_loc:
    		res.ntransfer_type='quality'
    	return res
    	
    @api.multi
    def do_transfer(self):			#change to do_new_transfer
        return_val = super(StockPicking, self).do_transfer() 
        invoice_val=self.env['account.invoice']
        account_line=self.env['account.invoice.line']
        journal_id = invoice_val.default_get(['journal_id'])['journal_id']
        invoice_picking_ids = []
        for res in self:
		if rec.picking_type_id.code == 'incoming' and rec.purchase_id:
			lot_id = self._context.get('lot_id') if self._context.get('lot_id') else False
			picking_id=user=False
			for move in self.move_created_ids:
				picking_id=move.move_dest_id.picking_id.id

			for rec in self:
			    responsible=self.env['res.groups'].sudo().search([('category_id.name', '=', 'Quality control')],limit=1)
			    b_lst=[]
			    for recipient in responsible.users:
			    	user=recipient.id
			    
			    if rec.sale_line:
				if rec.location_dest_id.quality_ck_loc:	# if destination location is quality check 
					search_id=self.env['sale.order.line.status'].search([('n_string','=','quality_check')],limit=1) ## add status
					if search_id:
					    self.env['sale.order.line'].sudo().browse(rec.sale_line.id).write({'n_status_rel':[(4,search_id.id)]})
					    
			    if rec.product_id.product_tmpl_id.check_quality and wiz:
			    	    if wiz.batch_ids:
			   		for batch in wiz.batch_ids:
					       b_lst.append((4,batch.id))
				    # Check if record is already exist or not
			       	    search_id=self.env['quality.checking'].search([('source','=',rec.purchase_id.name)])
			    	    if not search_id:
			    	    	#self.env['stock.picking'].sudo().browse(picking_id).write({'packaging':rec.n_packaging.id})
			    		vals={'source':rec.purchase_id.name,'product_id':rec.product_id.id,'purchase_id':rec.purchase_id.id,'picking_id':picking_id,
			    			'quality_line':[(0,0,{'name':rec.name,'quantity':production_qty,'mo_state':rec.state,
			    				'product_id':rec.product_id.id,'uom_id':rec.product_uom.id,'lot_id':lot_id,
							'state':'available','n_type':'new','batch_ids':b_lst, 'mrp_id':production_id
							})],'uom_id':rec.product_uom.id,'user':user}
			    		self.env['quality.checking'].create(vals)
				    else:
				    	# check if Lot number is already exist or not
				    	search_line_id=self.env['quality.checking.line'].search([('lot_id','=',lot_id)],limit=1)
				    	if not search_line_id:
				    		vals={'quality_line':[(0,0,{'name':rec.name,'quantity':production_qty,
			    					'mo_state':rec.state,'product_id':rec.product_id.id,
				    				'uom_id':rec.product_uom.id,'lot_id':lot_id,
				    				'state':'available','n_type':'new','batch_ids':b_lst,
				    				 'mrp_id':production_id})]}
			    			if production_qty:
					    		search_id.write(vals)
					    		
			    		else:
			    			# if Exist then update state and quantity
			    			search_line_id.quantity += production_qty
			    			search_line_id.state = 'available'
        return return_val         
        
