# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
from openerp import tools
from datetime import datetime, date, timedelta
import math
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import json

class PurchaseRequestData(models.Model):
    _name = 'user.purchase.request'
    _inherit = ['mail.thread']

    name=fields.Char('Purchase Request No.')
    product_details=fields.One2many('user.purchase.request.line','order_id','Product Details') 
    date_planned=fields.Datetime('Schedule Date', default=fields.Datetime.now)
    supplier = fields.Many2one('res.partner',string='Supplier')  
    state = fields.Selection([('draft','Draft'),('sent','Sent'),('in_purchase','In Purchase'),('received','Received')],'Status', default='draft')
 
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('user.purchase.request')
        result = super(PurchaseRequestData, self).create(vals)
        return result

    @api.multi
    def make_procurment(self):
    	for record in self:
           rq_data=self.env['stock.purchase.request']
           for line in record.product_details:
		   if line.product_id:
			   reqst_search=rq_data.search([('product_id','=',line.product_id.id ), ('p_state','in',('draft','requisition'))], limit=1)
			   if reqst_search:
				  line=self.env['stock.purchase.request.line'].create({'product_id':line.product_id.id,
				          'qty':line.qty, 'uom_id':line.uom_id.id, 'supplier':line.supplier.id,
                                           'description':line.description,'user_pr_id':record.id,
				           'required_date':line.date_planned,'purchase_request_id':reqst_search.id})
				  body='<b>Purchase Request Sent From '+str(self.env.user.name) +' </b>'
				  body +='<ul><li> Purchase Request No. : '+str(reqst_search.name) +'</li></ul>'
                                  body +='<ul><li>User Purchase Request No. : '+str(record.name) +'</li></ul>'
				  body +='<ul><li> Product Name : '+str(reqst_search.product_id.name) +'</li></ul>'
                                  body +='<ul><li> qty : '+str(line.qty) +str(line.uom_id.name)+'</li></ul>'
				  body +='<ul><li> Requested By  : '+str(self.env.user.name) +'</li></ul>'
				  body +='<ul><li> Requested Date  : '+str(date.today()) +'</li></ul>'
				  line.product_id.message_post(body=body)
				  line.product_id.product_tmpl_id.message_post(body=body)
				  reqst_search.message_post(body=body)
                                  record.message_post(body=body)
			   else:
				  request=rq_data.create({'product_id':line.product_id.id })
				  body='<b>Purchase Request Sent From '+str(self.env.user.name) +' </b>'
				  body +='<ul><li> Purchase Request No. : '+str(request.name) +'</li></ul>'
                                  body +='<ul><li>User Purchase Request No. : '+str(record.name) +'</li></ul>'
				  body +='<ul><li> Product Name : '+str(request.product_id.name) +'</li></ul>'
                                  body +='<ul><li> qty : '+str(line.qty) +str(line.uom_id.name)+'</li></ul>'
				  body +='<ul><li> Requested By  : '+str(self.env.user.name) +'</li></ul>'
				  body +='<ul><li> Requested Date  : '+str(date.today()) +'</li></ul>'
				  line.product_id.message_post(body=body)
				  line.product_id.product_tmpl_id.message_post(body=body)
				  request.message_post(body=body)
                                  record.message_post(body=body)
				  if request:
				     line=self.env['stock.purchase.request.line'].create({'product_id':line.product_id.id,
				            'supplier':line.supplier.id,'user_pr_id':record.id,
                                           'qty':line.qty, 'uom_id':line.uom_id.id, 
                                            'description':line.description,
				            'required_date':line.date_planned,'purchase_request_id':request.id}) 
			   record.state='sent'	   
        
class PurchaseRequestDataLine(models.Model):
    _name = 'user.purchase.request.line'
    

    @api.model
    def supplier_name(self):
        return self._context.get('supplier') if self._context.get('supplier') else False

    @api.multi
    @api.onchange('product_id')
    def unit_name(self):
        for record in self:
            if record.product_id:
               record.uom_id=record.product_id.uom_id
            else:
               record.uom_id=False

    order_id=fields.Many2one('user.purchase.request', string='Request No.')
    product_id=fields.Many2one('product.product', string='Product Name') 
    description = fields.Char('Description')  
    qty=fields.Float('Qty')
    uom_id=fields.Many2one('product.uom', string="Unit")
    
    date_planned=fields.Datetime('Schedule Date', default=fields.Datetime.now)
    supplier = fields.Many2one('res.partner',string='Supplier', default=supplier_name)
        
