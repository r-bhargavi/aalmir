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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_qty_delivered=fields.Float('Total Qty Delivered', compute='total_qty_delivered_sale') 
    total_qty_invoiced=fields.Float('Total Qty Invoiced', compute='total_qty_delivered_sale')
    total_qty=fields.Float('Total Ordered Qty', compute='total_qty_saleline')
    total_invoce_amount=fields.Float('Total Invoice Amount', compute='_compute_total_invoce_amt')
    
    #### send summary report to customer
    @api.multi
    def action_mail_send_summary(self):
        for sale in self:
            ir_model_data = self.env['ir.model.data']
            try:
                template_id =self.env.ref('stock_merge_picking.email_template_for_sale_order_summary')
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict()
            #p_id=self.env.user.partner_id.id
            #partner_ids = [p_id]
            ctx.update({
                'default_model': 'sale.order',
                'default_res_id': sale.id,
                'default_composition_mode': 'comment',
                'default_use_template': bool(template_id),
                'default_template_id': template_id.id, 
                'defaDult_email_ids':sale.employee_email,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True,
               
            })
            return {
                'name' : 'Mail',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    @api.depends('invoice_ids')
    def _compute_total_invoce_amt(self):
        for order in self:
            if order.invoice_ids:
               order.total_invoce_amount=sum(inv.amount_total_signed for inv in order.invoice_ids)
               
    @api.multi
    @api.depends('order_line')
    def total_qty_saleline(self):
        for record in self:
            record.total_qty = sum(line.product_uom_qty for line in record.order_line)
            
    @api.multi
    @api.depends('order_line')
    def total_qty_delivered_sale(self):
        for record in self:
            record.total_qty_delivered = sum(line.qty_delivered for line in record.order_line)
            record.total_qty_invoiced = sum(line.qty_invoiced for line in record.order_line)

    @api.multi
    def open_wizard_qtyincrease(self):
	vals_dict=[]
	for line in self.order_line:
	    if line.product_id.name != 'Deposit Product':
		vals_dict.append((0,0,{'sale_id':self.id,'sale_line_id':line.id,'price_unit':line.price_unit,
					'sale_qty':line.product_uom_qty,'product_id':line.product_id.id}))
	context = self._context.copy()
	context.update({'default_line_one2many':vals_dict,'default_sale_id':self.id})
        form_id= self.env.ref('stock_merge_picking.quantity_increase_form_view').id
	return {
		'name' :'Update Sale order quantity',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'form',
		'res_model': 'sale.order.quantity.increase',
		'view_id': form_id,
		'target': 'new',
		'context': context
                }	
                
    @api.multi
    def open_report_wizard(self):
	vals_dict=[]
	for line in self.order_line:
	    if line.product_id:
		vals_dict.append((0,0,{'sale_id':self.id,'sale_line_id':line.id,
                                 'price_unit':line.price_unit,'qty':line.product_uom_qty,
                                'uom_id':line.product_uom.id,
				'sale_qty':line.product_uom_qty,'product_id':line.product_id.id}))
	context = self._context.copy()
	context.update({'default_report_one2many':vals_dict,'default_sale_id':self.id})
        form_id= self.env.ref('stock_merge_picking.quantity_increase_form_view').id
	return {
		'name' :'Create Report For Approval',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'form',
		'res_model': 'sale.order.quantity.increase',
		'view_id': form_id,
		'target': 'new',
		'context': context
                }

class SaleOrderQuantityIncrease(models.TransientModel):
    _name='sale.order.quantity.increase'
   
    sale_id  = fields.Many2one('sale.order','Sale Order')
    line_one2many = fields.One2many('sale.order.quantity.increase.line','increase_line')
    report_one2many = fields.One2many('sale.order.quantity.increase.line','report_line')
    note = fields.Text('Note')
    doc_name = fields.Char(string='Document Name')
    uploaded_document = fields.Binary(string='uploaded Document',attachment=True)
    print_option=fields.Selection([('delivery','Delivery Order'),('invoice','Invoice'),('both','Both')],string='Print Option')
    delivery_no=fields.Char('Delivery No.')
    invoice_no=fields.Char('Delivery No.')
     
    @api.multi
    def create_report(self):
        for record in self:
             code= self.env['ir.sequence'].next_by_code('sale.order.quantity.increase') or '/'
             if record.print_option == 'delivery':
                record.delivery_no=str(record.sale_id.warehouse_id.code)+'/'+'A'+'/'+str('OUT')+'/'+code
             if record.print_option == 'invoice':  
                record.invoice_no=str('INV')+'/'+'A'+'/'+str(date.today().strftime("%Y"))+'/'+code
             if record.print_option == 'both':
                record.delivery_no=str(record.sale_id.warehouse_id.code)+'/'+'A'+'/'+str('OUT')+'/'+code
                new_code=self.env['ir.sequence'].next_by_code('sale.order.quantity.increase') or '/'
                record.invoice_no=str('INV')+'/'+'A'+'/'+str(date.today().strftime("%Y"))+'/'+new_code
             return self.env['report'].get_action(self, 'stock_merge_picking.report_approve_aalmir_saleorder')
        return False

    @api.multi
    def save(self):
	for res in self:
		body ='Quantity Update : '+' '+'Date:'+str(date.today())
                invoice_val=self.env['account.invoice']	
		for line_wz in res.line_one2many:
		    qty_done=0.0
		    wiz_qty=line_wz.qty
		    if wiz_qty and line_wz.status == 'substract':
		      #CH_N112 add code to check If delivery order is present or not
			do_ids=self.env['stock.picking'].search([('origin','=',self.sale_id.name),('state','in',('done','transit','dispatch','delivered'))])
                        do_ids2=self.env['stock.picking'].search([('sale_id','=',self.sale_id.id),('state','in',('draft','confirmed'))],order="id desc")
                        print"TTTTTTTTTT", do_ids, do_ids2
                        for dos in do_ids2:
		           moves=self.env['stock.move'].search([('picking_id','=',dos.id)],order="id desc" )
		           for move in moves:
	                  	if wiz_qty > 0:
		                     if move.product_id.id == line_wz.product_id.id:
		                             move.product_uom_qty -= wiz_qty
		                             wiz_qty -= move.product_uom_qty 
			#if do_ids:
			#	for picking in do_ids:
			#		for operation in picking.pack_operation_product_ids:
			#			if operation.product_id.id == line_wz.product_id.id:
			#				qty_done += operation.qty_done
		    
		    if line_wz.qty:
			if line_wz.total_qty and qty_done >= line_wz.total_qty:
				raise UserError(_("Sale Order has Delivery order which validate you can not decrease the quantity"))
			line_wz.sale_line_id.product_uom_qty=line_wz.total_qty
			body +='<li> Product : '+str(line_wz.product_id.name)+' from '+str(line_wz.sale_qty)+' To '+str(line_wz.total_qty)+'</li>'
		body +='<li>'+'Reason: '+str(res.note)+'</li>'
		res.sale_id.message_post(body)
	return {'type': 'ir.actions.act_window_close'}


class SaleOrderQuantityIncreaseLine(models.TransientModel):
    _name='sale.order.quantity.increase.line'
	
    @api.multi
    @api.depends('qty','status')
    def _get_total_qty(self):
	for rec in self:
		if rec.status=='add':
			rec.total_qty = rec.sale_qty+ rec.qty
		if rec.status=='substract':
			rec.total_qty = rec.sale_qty - rec.qty

    increase_line = fields.Many2one('sale.order.quantity.increase')
    report_line = fields.Many2one('sale.order.quantity.increase')
    sale_id  = fields.Many2one('sale.order')
    sale_line_id = fields.Many2one('sale.order.line')
    product_id = fields.Many2one('product.product','Product Name') 
    sale_qty = fields.Integer(string='Sale Order Quantity')
    qty = fields.Integer(string='New Quantity')
    uom_id=fields.Many2one('product.uom', 'Unit')
    status = fields.Selection([('add','Add qty'),('substract','Substract qty')],string="Type")
    price_unit=fields.Float('Price Unit', digits=dp.get_precision('Product Price'))
    total_qty = fields.Integer(string='Total Quantity',compute='_get_total_qty')

