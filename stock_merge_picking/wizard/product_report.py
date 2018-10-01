# -*- coding: utf-8 -*-
from openerp import models, fields, api,_
from openerp import tools
from datetime import datetime, date,time, timedelta
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare, float_round
from openerp.exceptions import UserError
from urlparse import urljoin
import openerp.addons.decimal_precision as dp
from urllib import urlencode

class IrActionsReportXml(models.Model):
    _inherit = 'ir.actions.report.xml'

    report_type = fields.Selection(selection_add=[("xlsx", "xlsx")])

class ProductReport(models.TransientModel):
    _name='product.report'
   
    partner_id  = fields.Many2one('res.partner','Customer')
    product_ids=fields.Many2many('product.product','wiz_pro_rel','wiz_product_rel', string='Product')
    date_from=fields.Datetime('From Date')
    date_to=fields.Datetime('To Date')
    product_line=fields.One2many('product.report.line','report_id')
    filter_option=fields.Selection([('customer','Customer Wise'),('product','Product Wise'),('lpo',' LPO Number Wise')],string='Filter By')
    filter_by=fields.Selection([('customer','Customer Wise Invoice Report '),('all','All Customer Invoice Report '),('submission','Invoice Submission Report'),('sale','Sale Summary Report'),('running_sale','Running Sale Orders')],string='Filter By')
    lpo_id=fields.Many2many('customer.upload.doc','lpo_wiz_rel','lpo_rel_wiz', string='LPO Number')
    sale_ids=fields.Many2many('sale.order','sale_wiz_rel','rel_sale_wiz',string='Sale Order')
    invoice_status=fields.Selection([('draft','Draft Invoice'),('open','Validate Invoice'),('paid','Paid Invoice'),('all','All Invoice')],string='Invoice Status')
    product_status=fields.Selection([('sale','Sale Order Wise'),('delivery','Deivery Order Wise'),('invoice','Invoice Wise ')],string='Search Status')
    report_type=fields.Selection([('summary','Summary Report'),('detail','Detail Report')],string='Report  Type')
    total_delivered=fields.Float('Total Delivered',compute='cal_qty')
    total_ordered=fields.Float('Total Ordered', compute='cal_qty')
    total_invoiced=fields.Float('Total Invoiced', compute='cal_qty')
    total_remaining=fields.Float('Total Remaining', compute='cal_qty')
    total_amount=fields.Float('Total Amount', compute='cal_qty')
    lpo_id_inv=fields.Many2many('customer.upload.doc','lpo_wiz_rel','lpo_rel_wiz',string='LPO Number')
    report_company_id=fields.Many2one('res.company','Company Name', default=lambda self: self.env['res.company']._company_default_get('product.report'))

    @api.multi
    @api.depends('product_line.qty_delivered','product_line.qty_ordered')
    def  cal_qty(self):
         for record in self:
             record.total_delivered=sum(line.qty_delivered for line in  record.product_line)
             record.total_ordered=sum(line.qty_ordered for line in  record.product_line)
             record.total_invoiced=sum(line.qty_invoiced for line in  record.product_line)
             record.total_remaining=sum(line.qty_remaining for line in  record.product_line)
             record.total_amount=sum(line.total_amount for line in  record.product_line)

    @api.multi
    def export_xls(self):
	self.summary_value()
        report_name=model=''
        if self._context.get('product'):
           report_name='export_sale_xls.sale_report_xls.xlsx'
           model='sale.order.line'
        if self._context.get('invoice'):
           report_name='export_invoice_xls.invoice_report_xls.xlsx'
           model='account.invoice'
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = model
        datas['form'] = self.read()[0]
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': report_name,
                    'datas': datas,
                    'name': 'Summary Details'
                   }
    @api.multi
    def print_report(self):
        for record in self:
	    record.summary_value()
            if self._context.get('product'):
               return self.env['report'].get_action(self, 'stock_merge_picking.report_product_wise')
            if self._context.get('invoice') and self.filter_by !='sale':
               return self.env['report'].get_action(self, 'stock_merge_picking.report_invoice_wise')
            if self.filter_by =='sale':
               res=self.env['report'].get_action(self.sale_ids, 'stock_merge_picking.report_summary_aalmir_saleorder')
               return res
        return False

    @api.multi
    @api.onchange('product_ids')
    def onchange_product_id(self):
	for rec in self:
		if rec.product_ids:
			rec.summary_value()
		else:
			rec.product_line=[(6,0,[])]

    @api.multi
    def summary_value(self):
       val=[]
       product_id=[]
       domain=[]
       all_partners_and_children = {}
       all_partner_ids = []
       for record in self:
	   record.product_line=[(6,0,[])]
           if record.partner_id:
              for partner in record.partner_id:
                  all_partners_and_children[partner] =self.pool.get('res.partner').search(self._cr, self._uid,[('id', 'child_of', record.partner_id.id)])
                  all_partner_ids += all_partners_and_children[partner]
           #if record.product_ids and record.filter_option == 'product' and self._context.get('product'):
           if record.partner_id and record.filter_option == 'product' and self._context.get('product'):
              record.lpo_id=False
	      if not record.product_ids and record.partner_id:
		pricelist=self.env['product.pricelist'].search([('customer','=',record.partner_id.id)])
		for prl in pricelist:
                     for customer_p in prl.cus_products:
                         product_id.append(customer_p.product_id.id)
		#record.product_ids=[(6,0,product_id)]
              for product in record.product_ids:
                  product_id.append(product.id)
		
              if record.product_status =='sale':
                 if record.date_from and record.date_to:
                    domain +=[('order_id.date_order','>=',record.date_from),('order_id.date_order','<=',record.date_to )]
                 domain +=[('order_partner_id','in',all_partner_ids),('product_id','in',product_id),('order_id.state','in',('sale','done'))]
                 domain +=[('order_id.state','in',('sale','done'))]
                 sale_line=self.env['sale.order.line'].search(domain)
                 if sale_line:
                    for line in sale_line:
		          val.append(({'sale_id':line.order_id.id,
		          'delivery_ids':[(6, 0, [x.id for x in  line.order_id.picking_ids])],
		          'invoice_ids':[(6, 0, [x.id for x in  line.order_id.invoice_ids])],
		          'lpo_number':line.order_id.sale_lpo_number,
		          'order_date':line.order_id.date_order,'price_unit':line.price_unit,
		          'qty_delivered':line.qty_delivered,'qty_ordered':line.product_uom_qty,
		          'qty_invoiced':line.qty_invoiced,'product_uom':line.product_uom.id,
		          'product_id':line.product_id.id}))
                    record.product_line=val
                 
              if record.product_status =='invoice':
                 if record.date_from and record.date_to:
                    domain +=[('invoice_id.date_invoice','>=',record.date_from),('invoice_id.date_invoice','<=',record.date_to )]
                 domain +=['|',('invoice_id.partner_id.parent_id','in',all_partner_ids),('invoice_id.partner_id','in',all_partner_ids)]
                 domain +=[('product_id','in',product_id),('invoice_id.state','in',('open','paid'))]
                 invoice_line=self.env['account.invoice.line'].search(domain)
                 final_qty=0.0
                 vals=[]
                 if invoice_line:
                    print"LLLLLLLLLLLLLLLLL",invoice_line,product_id
                    for line in invoice_line:
                        val.append(({'sale_id':line.invoice_id.sale_id.id,
                                  'qty_invoiced':line.quantity,
                                  'product_uom':line.uom_id.id,
                                  'order_date':line.invoice_id.date_invoice,
                                  'price_unit':line.price_unit,
                                  'product_id':line.product_id.id,
                                  'lpo_number':line.invoice_id.sale_id.sale_lpo_number,
                                  'invoice_ids':[(4, line.invoice_id.id)]
                                  })) 
                    if record.report_type == 'summary':
		            import itertools as it
		            keyfunc = lambda x: x['product_id']
		            print"Yyyyyyyyyyyyyy",vals
		            groups = it.groupby(sorted(val, key=keyfunc), keyfunc)
		            product=[{'product_id':k, 'qty':sum(x['qty_invoiced'] for x in g),} for k, g in groups]
		            for ln in product:
		                for line in invoice_line:
		                    if ln['product_id'] == line.product_id.id:
		                       val.append(({'sale_id':line.invoice_id.sale_id.id,
		                          'qty_invoiced':ln['qty'],
		                          'product_uom':line.uom_id.id,
		                          'order_date':line.invoice_id.date_invoice,
		                          'price_unit':line.price_unit,
		                          'product_id':line.product_id.id,
		                          'lpo_number':line.invoice_id.sale_id.sale_lpo_number,
		                          }))
		            final_val1=list({v['product_id']:v for v in val}.values())
		            record.product_line=final_val1
                    else:
                         record.product_line=val
              if record.product_status =='delivery':
                 if record.date_from and record.date_to:
                    domain +=[('picking_id.delivery_date','>=',record.date_from),('picking_id.delivery_date','<=',record.date_to )]
                 domain +=['|',('picking_id.partner_id.parent_id','in',all_partner_ids),('picking_id.partner_id','in',all_partner_ids)]
                 domain +=[('product_id','in',product_id),('picking_id.state','=','delivered')]
                 print"DOOOOOOOOOOOo",domain
                 operation_ids=self.env['stock.pack.operation'].search(domain) 
                 vals=[]
                 print"%%%%%%%%%%%%% delivery_ids",operation_ids
                 if operation_ids:
                    for operation in operation_ids:
                        vals.append(({'product_id':operation.product_id.id,  
                                    'qty':operation.qty_done }))
                        val.append((0,0,{'sale_id':operation.picking_id.sale_id.id,
                                  'qty_delivered':operation.qty_done,
                                  'product_uom':operation.product_uom_id.id,
                                  'order_date':operation.picking_id.delivery_date,
                                  'price_unit':operation.n_sale_order_line.price_unit,
                                  'product_id':operation.product_id.id,
                                  'lpo_number':operation.picking_id.sale_id.sale_lpo_number,
                                  'qty_ordered':operation.n_sale_order_line.product_uom_qty,
                                  'delivery_ids':[(4, operation.picking_id.id)],
                                  'invoice_ids':[(6, 0, [x.id for x in  operation.picking_id.invoice_ids])],
                                  }))
                    if record.report_type == 'summary':
                       cr = self.env.cr
                       val1=[]
                       import itertools as it
                       keyfunc = lambda x: x['product_id']
                       print"Yyyyyyyyyyyyyy",vals
                       groups = it.groupby(sorted(vals, key=keyfunc), keyfunc)
                       product=[{'product_id':k, 'qty':sum(x['qty'] for x in g),} for k, g in groups]
                       print"KLLLLLLLLLLL",product
                       for ln in product:
                           for operation in operation_ids:
                               if ln['product_id'] == operation.product_id.id: 
                                   cr.execute('SELECT sum(product_uom_qty) FROM sale_order_line where product_id=%s and order_id=%s', (operation.product_id.id,operation.picking_id.sale_id.id))
                                   qty_check=cr.fetchone()[0]
                                   cr.execute('SELECT sum(qty_delivered) FROM sale_order_line where product_id=%s and order_id=%s', (operation.product_id.id,operation.picking_id.sale_id.id))
                                   qty_done=cr.fetchone()[0]
                                   cr.execute('SELECT sum(qty_invoiced) FROM sale_order_line where product_id=%s and order_id=%s', (operation.product_id.id,operation.picking_id.sale_id.id))
                                   qty_invoiced=cr.fetchone()[0]
                                   val1.append(({'sale_id':operation.picking_id.sale_id.id,
                                      'qty_delivered':qty_done,
                                      'delivery_ids':[(6, 0, [x.id for x in  operation.picking_id.sale_id.picking_ids])],
                                       'invoice_ids':[(6, 0, [x.id for x in  operation.picking_id.sale_id.invoice_ids])],
                                      'product_uom':operation.product_uom_id.id,
                                      'order_date':operation.picking_id.delivery_date,
                                      'price_unit':operation.n_sale_order_line.price_unit,
                                      'product_id':operation.product_id.id,
                                      'lpo_number':operation.picking_id.sale_id.sale_lpo_number,
                                      'qty_ordered':qty_check,
                                      'qty_invoiced':qty_invoiced
                                  }))                   
                       final_val1=list({v['product_id']:v for v in val1}.values())
                       print"VVVVVVVVVVVVVV",val1 , final_val1        
                       record.product_line=final_val1
                    else:
                        record.product_line=val
                 print"DDDDDDDDDDDDD",operation_ids
           elif record.filter_option == 'customer' and  self._context.get('product'):
                print"yyyyyyyyyyyyyvimslsh"
                domain +=[('partner_id','in',all_partner_ids),('state','in',('sale','done'))]
                if record.date_from and record.date_to:
                   domain +=[('date_order','>=',record.date_from),('date_order','<=',record.date_to )]
                sale_ids =self.env['sale.order'].search(domain)
                if sale_ids:
                  for sale in sale_ids:
                     val.append((0,0,{'sale_id':sale.id, 'order_date':sale.date_order,
                                    'delivery_ids':[(6, 0, [x.id for x in  sale.picking_ids])],
                                    'invoice_ids':[(6, 0, [x.id for x in  sale.invoice_ids])],
                                    'lpo_number':sale.sale_lpo_number,
                                    'qty_delivered':sale.total_qty_delivered,
                                    'qty_invoiced':sale.total_qty_invoiced,
                                    'qty_ordered':sale.total_qty,
                                    }))
                  record.product_line=val
                
           elif record.filter_option == 'lpo' and self._context.get('product'):
                lpo_ids=[]
                record.partner_id=False
                record.product_ids=False
                if record.lpo_id:
                   for lpo in record.lpo_id:
                       lpo_ids.append(lpo.id)
                   docs=self.env['customer.upload.doc'].search([('id','in',lpo_ids)])
                   if docs:
                      val=[]
                      for doc in docs:
                          for line in doc.sale_id_lpo.order_line:
                              val.append((0,0,{'sale_id':doc.sale_id_lpo.id,
                                    'delivery_ids':[(6, 0, [x.id for x in  doc.sale_id_lpo.picking_ids])],
                                    'invoice_ids':[(6, 0, [x.id for x in  doc.sale_id_lpo.invoice_ids])],
                                    'lpo_number':doc.sale_id_lpo.sale_lpo_number,
                                    'order_date':line.order_id.date_order,'price_unit':line.price_unit,
                                    'qty_delivered':line.qty_delivered,'qty_ordered':line.product_uom_qty,
                                    'qty_invoiced':line.qty_invoiced,'product_uom':line.product_uom.id,
                                    'product_id':line.product_id.id
                                    }))
                      record.product_line=val
                   else:
                      record.product_line=val

       return { "type": "ir.actions.do_nothing",}
    
class ProductReportLine(models.TransientModel):
    _name='product.report.line'

    report_id = fields.Many2one('product.report')
    order_date=fields.Datetime('Date')
    product_id=fields.Many2one('product.product',string='Product')
    sale_id  = fields.Many2one('sale.order', string='Sale No.')
    delivery_ids=fields.Many2many('stock.picking' ,'wiz_pro_stock','wiz_stock_pro_rel',string='Delivery No.')
    invoice_ids=fields.Many2many('account.invoice' ,'wiz_pro_invoice','wiz_invoice_pro_rel',
                                 string='Invoice No.')
    lpo_number=fields.Char('LPO Number') 
    qty_ordered=fields.Float('Ordered Qty')
    qty_delivered=fields.Float('Delivered Qty')
    qty_invoiced=fields.Float('Invoiced Qty')
    price_unit=fields.Float('Unit Price',digits=dp.get_precision('Product Price'))
    product_uom=fields.Many2one('product.uom',string='Unit')
    qty_remaining=fields.Float('Remaining Qty', compute='remain_qty')
    total_amount=fields.Float('Total amount', compute='amount_total')

    @api.multi
    @api.depends('qty_delivered','price_unit')
    def amount_total(self):
        for record in self:
            if record.price_unit and record.qty_delivered:
               record.total_amount=record.price_unit * record.qty_delivered
            if record.report_id.product_status == 'invoice':
                  record.total_amount=record.price_unit * record.qty_invoiced
            if record.report_id.filter_option == 'lpo':
                  record.total_amount=record.price_unit * record.qty_ordered
    
    @api.multi
    @api.depends('qty_ordered','qty_delivered')
    def remain_qty(self):
        for record in self:
            if record.qty_ordered:
               record.qty_remaining=record.qty_ordered -record.qty_delivered
            else:
               record.qty_remaining=0.0

