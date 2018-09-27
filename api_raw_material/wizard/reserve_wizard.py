# -*- coding: utf-8 -*-
# copyright reserved

from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from urlparse import urljoin
from urllib import urlencode
import json

class rawMaterialWizard(models.TransientModel):
    _name = "raw.material.reserve.release"
    
    product_id = fields.Many2one("product.product", "Product")
    line_id = fields.Many2one("mrp.raw.material.request.line", "Product")
    avl_qty = fields.Float('Available Qty ',)	
    avl_uom=fields.Many2one('product.uom', string="Unit")
    
    total_qty_reserve = fields.Float('Total Qty to Reserve') 
    uom_id2=fields.Many2one('product.uom', string="Unit")
    
    reserve_qty = fields.Float('Reserve qty')
    reserve_uom=fields.Many2one('product.uom', string="Unit")
    
    res_qty = fields.Float('Available Reserve Qty ')
    release_qty = fields.Float('Release Qty')
    release_uom=fields.Many2one('product.uom', string="Unit")   	
    
    @api.multi
    def reserve(self):
    	for res in self:
    		if round(res.reserve_qty,2) > round(res.avl_qty,2):
    			raise UserError('You cannot reserve more than available quantity. !')
		if round(res.reserve_qty,2) > round(res.total_qty_reserve,2):
    			raise UserError('You cannot reserve more than Total Quantity to reserve!')
		if res.reserve_qty <= 0:
			raise UserError('Please Enter proper Quantity to reserve')
			
    		res.line_id.reserve_qty += res.reserve_qty
    		res.line_id.pending_qty -= res.reserve_qty
    		self.env['reserve.history'].create({'rm_line_id':res.line_id.id,'product_id':res.product_id.id,
    			'res_qty':res.reserve_qty,'n_status':'reserve','n_reserve_Type':'so',
    			'n_avl_qty':res.avl_qty,'n_total_avl_qty':res.total_qty_reserve})
    		body="Raw Material Quantity is Reserved"
    		body += "<li> Product : {}".format(str(res.product_id.name))
    		body += str("<li> Quantity : {} {}".format(str(res.reserve_qty),str(res.reserve_uom.name)))
		res.line_id.material_request_id.message_post(body=body)
		if round(res.line_id.reserve_qty,2) == round(res.line_id.qty,2):
			res.line_id.reserve_status='reserve'
			res.line_id.rm_type='stock'
		else:
			res.line_id.reserve_status='approve'
	return True
    		
    @api.multi
    def release(self):
    	for res in self:
    		if round(res.release_qty,2) > round(res.res_qty,2):
    			raise UserError('You cannot Release more than available quantity. !')
		if res.release_qty <= 0:
			raise UserError('Please Enter proper Quantity to Release')
			
    		res.line_id.reserve_qty -= res.release_qty
    		res.line_id.pending_qty += res.release_qty
    		self.env['reserve.history'].create({'rm_line_id':res.line_id.id,'product_id':res.product_id.id,
    			'res_qty':res.release_qty,'n_status':'release','n_avl_qty':res.res_qty})
    			
		body="Raw Material Quantity is Released"
    		body+="<li> Product : {}".format(res.product_id.name)
    		body+="<li> Quantity : {} {}".format(res.release_qty,res.release_uom.name)
		res.line_id.material_request_id.message_post(body=body)
		
		if res.line_id.reserve_qty == res.line_id.qty:
			res.line_id.reserve_status='reserve'
		else:
			res.line_id.reserve_status='approve'
			
	return True
    		
    		
    		
