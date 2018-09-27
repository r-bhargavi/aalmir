# -*- coding: utf-8 -*-
from openerp import models, fields, api,_
from openerp import tools
from datetime import datetime, date, timedelta,time
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare, float_round
from openerp.exceptions import UserError
from urlparse import urljoin
from urllib import urlencode
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class SaleOrderLpo(models.TransientModel):
    _name='sale.order.lpo'
     
    lpo_line=fields.One2many('sale.order.lpo.line','lpo_id')
    sale_id=fields.Many2one('sale.order')

    @api.multi
    def add_lpo(self):
        for record in self:
            sale=self.env['sale.order'].search([('id','=',self._context.get('sale_id'))])
            stock=self.env['stock.picking'].search(['|',('sale_id','=',sale.id),('origin','=',sale.name)])
            invoices=self.env['account.invoice'].search([('origin','=',sale.name)])
            if invoices:
               for invoice in invoices:
                   for line in invoice.invoice_line_ids:
                       for rec in record.lpo_line:
                           if rec.product_id.id == line.product_id.id:
                              line.lpo_documents= rec.lpo_documents
            if stock:
               for stk in stock:
                   for operation in stk.pack_operation_product_ids:
                       for rec in record.lpo_line:
                           if rec.product_id.id == operation.product_id.id:
                              operation.lpo_documents= rec.lpo_documents
            for rec in record.lpo_line:
                line=self.env['sale.order.line'].search([('id','=',rec.lind_id.id),('order_id','=',sale.id)])
                if line:
                   line.lpo_documents= rec.lpo_documents

class SaleOrderLpoLine(models.TransientModel):
    _name='sale.order.lpo.line'
     
    lpo_id=fields.Many2one('sale.order.lpo')
    lind_id=fields.Many2one('sale.order.line')
    product_id=fields.Many2one('product.product', string='Product')
    lpo_documents=fields.Many2many('customer.upload.doc', string='LPO Documents')
    
    
