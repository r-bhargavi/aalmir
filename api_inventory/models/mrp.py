# -*- coding: utf-8 -*-
# copyright reserved

from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp 
from datetime import datetime, date, time, timedelta

class MrpProduction(models.Model):
    _inherit='mrp.production'
   
    @api.model
    def default_get(self,fields):
        rec = super(MrpProduction,self).default_get(fields)
        if rec.get('product_id'):
		product_id=self.env['product.product'].search([('id','=',rec.get('product_id'))])
		if product_id:
			if not product_id.product_tmpl_id.check_quality:
				if rec.get('sale_id'):
					dest_id=self.env['sale.order'].search([('id','=',rec.get('sale_id'))])
					if dest_id:
						rec.update({'location_dest_id': dest_id.warehouse_id.wh_input_stock_loc_id.id})
				else:
					dest_id=self.env['stock.location'].search([('pre_ck','=',True)],order='id asc' ,limit=1)
					if dest_id:
						rec.update({'location_dest_id' : dest_id.id})
	return rec

    @api.multi
    def action_produce(self, production_qty, production_mode, wiz=False):
    	production_id = self._context.get('active_id') if self._context.get('active_id') else self.id
    	lot_id = self._context.get('lot_id') if self._context.get('lot_id') else False
    	picking_id=False
    	for move in self.move_created_ids:
    		picking_id=move.move_dest_id.picking_id.id

    	for rec in self:
    	    r_qty=0.0
    	    if rec.sale_line:
			qty=0.0
			n_qty=float(production_qty)
			extra_qty=float(rec.sale_line.n_extra_qty)
			status_list=[]
			for line in self.env['reserve.history'].search([('sale_line','=',rec.sale_line.id)]):
				if line.n_status in ('release','cancel','dispatch','delivered') :
					qty -= float(line.res_qty)
				if line.n_status in ('reserve','r_t_dispatch') :
					qty += float(line.res_qty)

			if rec.location_dest_id.pre_ck:	# if destination location is Pre stock location to inventory
				search_id=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')],limit=1) ## add status
				if search_id:
				    self.env['sale.order.line'].sudo().browse(rec.sale_line.id).write({'n_status_rel':[(4,search_id.id)]})
				if wiz.batch_ids:
           				for batch in wiz.batch_ids:
		               			batch.logistic_state='ready'
		               			batch.approve_qty = batch.convert_product_qty
		               			
			if rec.sale_line.product_uom_qty <= (rec.n_produce_qty):
				n_qty = float(rec.sale_line.product_uom_qty - qty)
				extra_qty += float(rec.n_produce_qty - rec.sale_line.product_uom_qty)
			    
			# if destination is Direct stock or Pre-Stock
			if not rec.location_dest_id.quality_ck_loc and not rec.location_dest_id.pre_ck: 
				search_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1) ## add status
				if search_id:
					status_list.append((4,search_id.id))
				vals={'product_id':self.product_id.id,'res_qty':n_qty,
					'n_status':'reserve','n_reserve_Type':'mo',
					'res_date':date.today(),'sale_line':rec.sale_line.id}
				if n_qty>0.0:
					ids=self.env['reserve.history'].create(vals)
				self.env['sale.order.line'].sudo().browse(rec.sale_line.id).write({
								'reserved_qty':(qty+n_qty),
								'n_extra_qty':extra_qty,
								'n_status_rel':status_list})
            
    	return super(MrpProduction, self).action_produce(production_qty, production_mode, wiz)
    	
    	

