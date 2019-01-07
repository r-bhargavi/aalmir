# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models ,api, _
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
import json
import logging
_logger = logging.getLogger(__name__)

class SaleOrderTrialForm(models.Model):
    _name='sale.order.trial.form'

    name=fields.Char('Trial Form Name')
    sale_id=fields.Many2one('sale.order',)
    note=fields.Text('Note')
    button_hide=fields.Boolean(default=False)
    product_id=fields.Many2one('product.product', string='Product Name')
    trial_sale_id=fields.Many2one('sale.order', string='Trial Sale order Number')
    product_description=fields.Text('Product Description')
    
    @api.multi
    def save(self):
        self.button_hide=True
        return {'type': 'ir.actions.act_window_close'}
        
class SaleOrderInvoice(models.Model):
    _name='custom.saleorder.invoice'

    line_id=fields.One2many('sale.order.line','sale_invoice_id')
    sale_id=fields.Many2one('sale.order')
    invoice_due_date=fields.Datetime('Invoice Due Date',default=fields.Datetime.now)
    qty_exceed=fields.Boolean('Qty Exceed' , compute='qty_exceed_value')
    qty_exceed1=fields.Boolean('Qty Exceed' , compute='qty_exceed_value')
    invoice_policy=fields.Selection([('delivery', 'Invoice Based On Each Delivery'),('quantity', 'Invoice Based On Delivered Qty'),('manual',' Manual Invoice')],string='Invoice Policy')
    delivery_ids=fields.Many2many('stock.picking')
    
    @api.multi
    @api.depends('line_id.product_uom_qty', 'line_id.qty_invoiced')
    def qty_exceed_value(self):
        for record in self:
            for line in record.line_id:
                if line.product_uom_qty:
                   if line.product_uom_qty < line.qty_invoiced: 
                      record.qty_exceed=True
                if line.product_uom_qty and line.mk_invoice_qty:
                   if  ((line.product_uom_qty - line.qty_invoiced) < line.mk_invoice_qty ):
                       record.qty_exceed1=True
                       
    @api.multi
    def create_invoice_wizard(self):
        for record in self:
            main_invoice=self.env['account.invoice']
            invoice_form = self.env.ref('account.invoice_form', False)
	    context = self._context.copy()
            invoice_val=self.env['account.invoice']
            order_line=self.env['sale.order.line']
            total_invoice=invoice_val.search([('sale_id','=', self.sale_id.id)])
            journal_id = invoice_val.default_get(['journal_id'])['journal_id']
            account_line=self.env['account.invoice.line']
            lpo=[]
            doc=self.env['customer.upload.doc'].search([('sale_id_lpo','=',record.sale_id.id)])
            if doc:
               for doc_id in doc:
                   lpo.append((4,doc_id.id))
            invoice_vals={'partner_id':record.sale_id.partner_id.id,
                         'partner_invoice_id':record.sale_id.partner_invoice_id.id,
                        'name': record.sale_id.name,  
                        'origin': record.sale_id.name,
                        'type': 'out_invoice','journal_id': journal_id,
                        'document_id':lpo,
                        'n_lpo_receipt_date':record.sale_id.lpo_receipt_date,
                        'n_lpo_issue_date':record.sale_id.lpo_issue_date,
                        'n_lpo_document':record.sale_id.lpo_document,
                        'currency_id':record.sale_id.n_quotation_currency_id.id,
                        'user_id': record.sale_id.user_id.id,    
                        'team_id': record.sale_id.team_id.id,
                        'sale_id':record.sale_id.id,
                       'account_id': record.sale_id.partner_invoice_id.property_account_receivable_id.id,
                       'payment_term_id': record.sale_id.payment_term_id.id,
                       'fiscal_position_id': record.sale_id.fiscal_position_id.id or  record.sale_id.partner_invoice_id.property_account_position_id.id,
                       'invoice_due_date':record.invoice_due_date
                     }
            ## Create Invoice based on each delivered qty
            if record.delivery_ids and record.invoice_policy =='quantity':
               qty_invoice =main_invoice.create(invoice_vals)
               vals=[]
               for delivery in record.delivery_ids:
                   delivery.invoice_done=True
                   delivery.invoice_ids=[(6, 0, [qty_invoice.id])]
                   for operation in delivery.pack_operation_product_ids:
                       for line in record.sale_id.order_line:
                           if line.product_id.id == operation.product_id.id: 
                              vals.append(({'product_id':operation.product_id.id,  
                                    'qty':operation.qty_done }))
	       import itertools as it
	       keyfunc = lambda x: x['product_id']
	       groups = it.groupby(sorted(vals, key=keyfunc), keyfunc)
               product=[{'product_id':k, 'qty':sum(x['qty'] for x in g)} for k, g in groups]
               for line in record.sale_id.order_line:
                   for ln in product:
                       if ln['product_id'] == line.product_id.id:
                          if (line.product_uom_qty - line.qty_invoiced) < ln['qty']:
                              raise UserError('Your Invoice Is completed According to your Order qty.')
                          inv_line=account_line.create({'invoice_id':qty_invoice.id,
                                 'product_id':line.product_id.id, 'lpo_documents':line.lpo_documents,
                                'quantity':ln['qty'],'uom_id':line.product_uom.id, 
                                'name':line.product_id.name, 'price_unit':line.price_unit,
                                'account_id':line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id})
                          inv_line.write({'sale_line_ids': [(6, 0, [line.id])],
                              'invoice_line_tax_ids': [(6, 0, [x.id for x in  line.tax_id])]}) 
               qty_invoice.compute_taxes()   
               qty_invoice.picking_ids=[(6, 0, [x.id for x in record.delivery_ids])]
               record.delivery_ids=False
               record.invoice_policy ='manual'
               break
            ## create invoice based on deliveries 
            if record.delivery_ids and record.invoice_policy =='delivery':
               val_inv=val_del=[]
               for delivery in record.delivery_ids:
                   delivery.invoice_done=True
		   if invoice_vals.get('message_follower_ids'):
			invoice_vals.pop('message_follower_ids')
                   each_invoice =main_invoice.create(invoice_vals)
                   delivery.invoice_ids=[(6, 0, [x.id for x in each_invoice])]
                   each_invoice.picking_ids=[(6, 0, [x.id for x in delivery])]
                   for operation in delivery.pack_operation_product_ids:
                       for line in record.sale_id.order_line:
                               if operation.product_id.id ==line.product_id.id:
                                   if (line.product_uom_qty - line.qty_invoiced) < operation.qty_done:
                                        raise UserError('Your Invoice Is completed According to your Order qty.')                       
                                   else:
		                        inv_line=account_line.create({'invoice_id':each_invoice.id,

		                          'product_id':operation.product_id.id,
                                          'lpo_documents':line.lpo_documents,
		                          'quantity':operation.qty_done,
                                          'uom_id':operation.product_uom_id.id, 
		                          'name':operation.product_id.name,
                                          'price_unit':operation.n_sale_order_price,
		                          'account_id': operation.product_id.property_account_income_id.id or operation.product_id.categ_id.property_account_income_categ_id.id})
		                  	inv_line.write({'sale_line_ids': [(6, 0, [line.id])],
		                         'invoice_line_tax_ids': [(6, 0, [x.id for x in  line.tax_id])]})
                   each_invoice.compute_taxes()

               record.delivery_ids=False
               record.invoice_policy ='manual'
               break
            ## create invoice based on Manual Qty
            if record.line_id and record.invoice_policy =='manual':
               if sum(l.mk_invoice_qty for l in record.line_id) == 0.0: #line.mk_invoice_qty ==
                  raise UserError('Your Invoice Qty Should be always greater than 0.0')
               invoice =main_invoice.create(invoice_vals)
               for line in record.line_id:
                    if (line.product_uom_qty - line.qty_invoiced) < line.mk_invoice_qty:
                        raise UserError('Your Invoice Is completed According to your Order qty.')
                    account = line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id
                    if line.mk_invoice_qty > 0.0:
                       inv_line=account_line.create({'invoice_id':invoice.id,
                                   'product_id':line.product_id.id,
                                   'lpo_documents':line.lpo_documents,
                                   'quantity':line.mk_invoice_qty,'uom_id':line.product_uom.id, 
                                   'name':line.name, 'price_unit':line.price_unit,
                                   'account_id': account})
                       inv_line.write({'sale_line_ids': [(6, 0, [line.id])],
                                       'invoice_line_tax_ids': [(6, 0, [x.id for x in  line.tax_id])]})
                    line.write({'mk_invoice_qty':0.0})
               invoice.compute_taxes()
   	       '''return {
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'form',
			    'res_model': 'account.invoice',
			    'views': [(invoice_form.id, 'form')],
			    'view_id': invoice_form.id,
			    'res_id':invoice.id,
			    'target': 'current',
		       }'''
                               
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self,fields):
        rec = super(SaleOrder, self).default_get(fields)
	obj = self.env['sale.order'].browse(self._context.get('active_id'))
	if self._context.get('n_ctx'):
        	rec.update({'invoice_status':'no'})
        return rec

    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
    	'''Inherite Method to show only Delivery/Return in Sale Order'''
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            order.delivery_count = len(order.picking_ids.filtered(lambda x: x.picking_type_code in ('outgoing','incoming')))

    @api.multi
    def action_view_delivery(self):
        '''Inherite Method to add Filter of incoming/outgoing to show only Delivery/Return in Sale Order '''
        action = self.env.ref('stock.action_picking_tree_all')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        pick_ids = sum([order.picking_ids.ids for order in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"])]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result
        
    @api.multi
    def saleOrder_Trailform(self):
        order_form = self.env.ref('gt_order_mgnt.view_sale_order_trial_form', False)
        context = self._context.copy()
        line=self.order_line.search([('product_id.name','!=','Deposit Product'),('order_id','=',self.id)],limit=1)
        context.update({'default_sale_id':self.id, 'default_product_id':line.product_id.id, 'default_product_description':line.name,
                         'default_trial_sale_id':self.sale_trail_id.id})
        return {
            'name':'Sale Order Trial Form',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.trial.form',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,}
	    
    @api.multi
    def total_qty_data(self):
        for record in self:
		
		total_pr=total_po=total_mo=total_mo_pr_qty=total_inv=total_inv_pay=total_del=total_resrv=0.0
		pr_request=self.env['n.manufacturing.request'].search([('n_sale_line','=',record.id),('n_state','!=','cancel')])
		po=self.env['purchase.order'].search([('sale_id','=',record.id),('state','=','purchase')])
		te=self.env['purchase.requisition'].search([('origin','=',record.name),('state','!=','cancel')])
		delivery=self.env['stock.picking'].search([('origin','=',record.name),('state','=','delivered')])
		invoice=self.env['account.invoice'].search([('sale_id','=',record.id),('state','in',('open','paid', 'draft'))])
		mo=self.env['mrp.production'].search([('sale_id','=',record.id),('state','!=','cancel')])
		if record.order_line:
			for line in record.order_line:
				total_resrv += line.reserved_qty
			record.total_reserved_qty=total_resrv
		if invoice:
			for inv in invoice:
			   if inv.state in ('open', 'paid'):
			      d = json.loads(inv.payments_widget) 
			      if d:
				 for payment in d['content']:
				    if inv.type=='out_refund':
				    	total_inv_pay -= payment['amount']
				    else:
					total_inv_pay += payment['amount']
			   to_currency=record.report_currency_id if record.report_currency_id else record.n_quotation_currency_id
			   if inv.type=='out_refund':
			   	total_inv  -= inv.currency_id.compute(inv.amount_total,to_currency)   #CH_N103 add convert currency 
			   else:
				total_inv  += inv.currency_id.compute(inv.amount_total,to_currency)   #CH_N103 add convert currency 
			record.invoice_val = str(record.invoice_count) +'('+str(total_inv_pay)+'/'+str(total_inv) +')'
			record.total_invoice_amt= total_inv
		if not record.is_reception:
		    if pr_request:
		       for pr_qty in pr_request:
		  		total_pr += pr_qty.n_order_qty
		       record.total_pr_qty=total_pr

		    if mo:
		       for mrp in mo:
		           total_mo +=mrp.n_request_qty
		           for move in mrp.move_created_ids2:
		               total_mo_pr_qty += move.product_uom_qty
		       record.total_mo_qty=str(str(total_mo_pr_qty) +'/'+str(total_mo))

		    if po:
		       for line in po:
		           for ln in line.order_line:
		               total_po +=ln.product_qty
		       record.total_po_qty= total_po  

		    if te:
		       record.total_TE= len(te)  
            
#CH_N108 add client date in sale order form
    def get_client_date(self):
	for rec in self:	    
	  #Client Date >>
	    n_client_date=n_date=False
	    if rec.delivery_day_3 == 'confirmed_purchase_order':
		if rec.lpo_receipt_date:
			n_date=rec.lpo_receipt_date
		elif rec.signed_quote_receipt_date:
			n_date=rec.signed_quote_receipt_date
		elif rec.email_confirmation_date:
			n_date=rec.email_confirmation_date
		else:
			n_date=rec.force_date

	    if rec.delivery_day_3 == 'receipt_of_payment':
		if rec.force_date:
			if not rec.pop_receipt_date:
				n_date=rec.force_date
			else:
				n_date=rec.pop_receipt_date
		else:
			invoice_paid_date=False
			invoice_ids=self.env['account.invoice'].search([('advance_invoice','=',True),('sale_id','=',rec.id)],limit=1)
			if invoice_ids:
				payment_date=self.env['account.move'].search([('name','=',invoice_ids.name)],limit=1)
				if payment_date:
					invoice_paid_date=payment_date.date
			if not invoice_paid_date:
				if not rec.pop_receipt_date:
					n_date=rec.force_date
				else:
					n_date=rec.pop_receipt_date
			else:
				n_date=invoice_paid_date
	    if not n_date:
			n_date=str(date.today())
	    if rec.delivery_day_type=='days' and n_date:
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.delivery_day))
	    elif rec.delivery_day_type=='weeks' and n_date :
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.delivery_day)*7)
	    elif rec.delivery_day_type=='months' and n_date :
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.delivery_day)*30)
	    elif rec.delivery_day_type=='Date':
			n_client_date= rec.delivery_date1

	    rec.client_date=n_client_date

    state = fields.Selection(selection_add=[('awaiting', 'Awaiting')]) # update sale order defaults states
    due_payment = fields.Selection([('pending', 'Pending'), ('half_payment', 'Half Pay'),('done','Done')],'Due Payment', default='done')
    payment_date=fields.Datetime('Invoice Due Date', compute='invoice_payment_date')
    contract_id=fields.Many2one('customer.contract', string="Contract Detail")
    is_contract=fields.Boolean('Is Contract')
    n_customer_documents_upload = fields.One2many('customer.upload.doc','sale_id')	#customer docs
    n_product_documents_upload = fields.One2many('customer.upload.doc','sale_id_product')	#products docs
    sale_lop_documents=fields.One2many('customer.upload.doc', 'sale_id_lpo')  #CH_N105 LPo docs
    auto_invoice = fields.Boolean(string='Auto Invoice on Delivery',default=True)
    full_invoice=fields.Boolean()
    force_date = fields.Date('Force Confirm Date')
    cr_state=fields.Selection([('request', 'Request'),('approve','Approved'), ('reject','Reject')], string='Status')
    cr_note=fields.Text('Reason')
    stop_delivery=fields.Boolean('Stop Delivery')
    total_pr_qty=fields.Float(compute=total_qty_data)
    total_TE=fields.Float(compute=total_qty_data)
    total_po_qty=fields.Float(compute=total_qty_data)
    total_mo_qty=fields.Char(compute=total_qty_data)
    invoice_val=fields.Char(compute=total_qty_data)
    total_reserved_qty=fields.Float(compute=total_qty_data)
    total_invoice_amt=fields.Float(compute=total_qty_data)
    client_date = fields.Date('Calculated Delivery Date', compute='get_client_date')  #CH_N108 add client delivery date
    trial_form_id=fields.Many2one('sale.order.trial.form', string='Trial Form', compute='trialform')
  #CH_N103 add fields for trial request data start>>>
    trail_sale_id=fields.Many2one('sale.order', string="Trial Order")
    sale_trail_id=fields.Many2one('sale.order', string="Sale Order")

    payment_id=fields.Many2one('account.payment','Payment Detail')
    advance_paid_amount=fields.Char(help='Advance Paid message')

    ### Cancel Sale order draft , sent and awaiting state
    
    #### Reverse Quotation in awaiting to draft state
    @api.multi
    def return_order(self):
        for record in self:
            if record.payment_id.state =='posted':
                   raise UserError('Once Advance Payment Received can not return Sale Order .Please contact to Admin.')
            else:
		    return_form = self.env.ref('gt_order_mgnt.sale_order_return_form', False)
		    if return_form:
		        return {
		            'name':'Return Sale order',
		            'type': 'ir.actions.act_window',
		            'view_type': 'form',
		            'view_mode': 'tree',
		            'res_model': 'sale.order.return',
		            'views': [(return_form.id, 'form')],
		            'view_id': return_form.id,
		            'target': 'new',
		        }

    @api.multi
    def add_lpo_number(self):
        for line in self:
            sale=self.env['sale.order'].search([('id','=',self._context.get('sale_id'))])
            vals=[]
            for order_line in sale.order_line:
                if order_line.product_id.name != 'Deposit Product':
                   vals.append(({'product_id':order_line.product_id.id
                ,'lind_id':order_line.id,'lpo_documents':order_line.lpo_documents.ids}))
            context = self._context.copy()
            context.update({'default_lpo_line':vals,'default_sale_id':sale.id})
          
            lpo_form = self.env.ref('gt_order_mgnt.n_sale_lpo_wizard', False)
            if lpo_form:
                return {
                    'name':'Add LPO Number in Sale Order line',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'sale.order.lpo',
                    'views': [(lpo_form.id, 'form')],
                    'view_id': lpo_form.id,
                    'target': 'new',
                    'context':context
                }
    @api.multi
    def trialform(self):
        for record in self:
            form=self.env['sale.order.trial.form'].search([('sale_id','=',record.id)], limit=1)
            if form:
               record.trial_form_id=form.id
               record.sale_trail_id.write({'trail_sale_id':record.id})
      
    @api.multi
    @api.onchange('trail_sale_id','sale_trail_id')
    def change_sale_trial_onchnage(self):
        for record in self:
            if record.trail_sale_id:
               record.trail_sale_id.sale_trail_id=record.id
	    if record.sale_trail_id:
               record.sale_trail_id.trail_sale_id=record.id
   #CH_N103 <<<end

    @api.multi
    def totalreservedqty(self):
        for line in self:
	    self.env.cr.execute("delete from n_reserve_productqty where create_uid="+str(self.env.uid))
	    
	    for rec in line.order_line:
		reserved_qty=qty_delivered=0.0
		for line1 in self.env['reserve.history'].search([('sale_line','=',rec.id)]):
			if line1.n_status in ('release','cancel','delivered','r_t_dispatch'):
				qty_delivered += line1.res_qty
			if line1.n_status in ('reserve'):
				reserved_qty += line1.res_qty
		if (reserved_qty-qty_delivered)>0 :
			self.env['n.reserve.productqty'].create({'product_id':rec.product_id.id,'order_id':line.id,
		'order_partner_id':rec.order_id.partner_id.id,'line_id':rec.id,'salesman_id':rec.salesman_id.id,'sale_reserve_qty':reserved_qty,
		'qty_delivered':qty_delivered})
                
            sl_tree = self.env.ref('gt_order_mgnt.order_view_reserve_product_qty_tree', False)
            if sl_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'n.reserve.productqty',
                    'views': [(sl_tree.id, 'tree')],
                    'view_id': sl_tree.id,
                    'target': 'current',
                    'domain':[ ('create_uid','=',self.env.uid),('order_id','=',line.id)],
                }
        return True

    @api.multi
    def totalpr(self):
        for line in self:
            pr_tree = self.env.ref('gt_order_mgnt.n_production_request_tree_history', False)
            pr_form = self.env.ref('gt_order_mgnt.mrp_production_request_form', False)
            if pr_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'n.manufacturing.request',
                    'views': [(pr_tree.id, 'tree'), (pr_form.id, 'form')],
                    'view_id': pr_tree.id,
                    'target': 'current',
                    'domain':[('n_sale_line','=',self.id)],
                }

        return True

    @api.multi
    def totalmrp(self):
        for line in self:
            mpr_tree = self.env.ref('mrp.mrp_production_tree_view', False)
            mpr_form = self.env.ref('mrp.mrp_production_form_view', False)
            if mpr_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'mrp.production',
                    'views': [(mpr_tree.id, 'tree'), (mpr_form.id, 'form')],
                    'view_id': mpr_tree.id,
                    'target': 'current',
		    'context':{'show_qty':True},
                    'domain':[('sale_id','=',self.id)],
                }

        return True

    @api.multi
    def totalpurchase(self):
        for line in self:
            po_tree = self.env.ref('purchase.purchase_order_tree', False)
            po_form = self.env.ref('purchase.purchase_order_form', False)
            if po_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'purchase.order',
                    'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                    'view_id': po_tree.id,
                    'target': 'current',
                    'domain':[('sale_id','=',self.id)],
                }

        return True
    @api.multi
    def totaltender(self):
        for line in self:
            to_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
            to_form = self.env.ref('purchase_requisition.view_purchase_requisition_form', False)
            if to_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'purchase.requisition',
                    'views': [(to_tree.id, 'tree'), (to_form.id, 'form')],
                    'view_id': to_tree.id,
                    'target': 'current',
                    'domain':[('sale_id','=',self.id)],
                }

        return True
    @api.multi
    def sale_order_invoice_create(self):
	order_form = self.env.ref('gt_order_mgnt.view_sale_order_invoice_form', False)
	context = self._context.copy()
        search_invoice=self.env['custom.saleorder.invoice'].search([('sale_id','=', self.id)])
        sale=self.env['custom.saleorder.invoice'].create({'sale_id':self.id,'invoice_policy':'manual'})  if not search_invoice else search_invoice
        context.update({'default_invoice_policy':'manual','sale_name':self.name})
        for line in self.order_line:
            if line.product_id.name != 'Deposit Product' and line.product_uom_qty > line.qty_invoiced:
               if search_invoice:
	          line.sale_invoice_id=search_invoice.id
               else:
                  line.sale_invoice_id=sale.id

        return {
            'name':'Sale order Invoice Create',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'custom.saleorder.invoice',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'res_id':search_invoice.id if search_invoice else sale.id,
            'target': 'new',
	    'context':context,
       }
       
    ### comment for some time
    '''@api.multi
    def action_done(self):
        invoice=self.env['account.invoice'].search([('sale_id', '=',self.id),('state','not in',('cancel','paid'))])
        picking=self.env['stock.picking'].search([('sale_id', '=',self.id),('state','not in',('cancel','done'))]) 
	for line in self.order_line:     
		if line.reserved_qty:
			vals={'product_id':line.product_id.id,'res_qty':line.reserved_qty,'sale_line':line.id,
				'n_status':'release','n_reserve_Type':'so','res_date':date.today(),}
			self.env['reserve.history'].create(vals)
			line.reserved_qty = 0.0
		if line.n_extra_qty:
			line.n_extra_qty = 0.0 
                if invoice:
                   raise UserError(str(len(invoice))+' '+'Invoice are not paid.please first paid invoice before set to done.')
                if picking:
                   raise UserError(str(len(picking)) +' '+'Delivery Orders Pending.Please first Delivered pending orders before set to done.')
                self.write({'state': 'done'})
                if self.state == 'done':
                   if line.qty_delivered:
                      if line.product_uom_qty > line.qty_delivered: 
                         extra_qty= line.product_uom_qty - line.qty_delivered
                         line.create({'product_id':line.product_id.id, 'product_uom_qty':extra_qty,'order_id':line.order_id.id,
                               'product_uom':line.product_uom.id, 'name':"Delivered Minimum qty:\n" + line.name,
                                'price_unit':-line.price_unit})
                         self.message_post(body='<span style="color:blue">Some Products add for subtract qty Beacause Delivey Qty is less than Order qty:</span><br></br>' +'Product Name:'+ str(line.product_id.name)+' '+'Qty Less:'+str(extra_qty))
	return super(SaleOrder,self).action_done()'''

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :retu0.000rns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}

        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
            for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                     line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)

        for invoice in invoices.values():
           # if not invoice.invoice_line_ids:
              #  raise UserError(_('There is no invoicable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()

        return [inv.id for inv in invoices.values()]   
        
    @api.multi
    def make_sale_contract(self):
        for record in self:
            n_dic=[]
            contract=self.env['customer.contract']
            contract_line=self.env['contract.product.line']
            if record.is_contract:
               contract_serch=contract.search([('customer_id','=', record.partner_id.id)], limit=1)
               if contract_serch:
                  record.contract_id=contract_serch.id
               else:
                  res_id=contract.create({'customer_id':self.partner_id.id,'contract_name':self.name,
                            'payment_term_id':self.payment_term_id.id,
                            'quotation_currency_id':self.n_quotation_currency_id.id,
                             'user_id':self.user_id.id, 'pricelist_id':self.pricelist_id.id,
                             'invoice_id':record.partner_invoice_id.id,
                             'delivery_id':record.partner_shipping_id.id})
                  record.contract_id=res_id.id
                  record.message_post(body='Contract Created:  ' + str(record.contract_id.name))
                  res_id.message_post(body='Sale Order Created:  ' + str(record.name))
               record.is_contract=True
               for line in record.order_line:
                   if line.product_id.name != 'Deposit Product':
		           line_search=contract_line.search([('cont_id', '=',record.contract_id.id), ('product_id', '=',line.product_id.id)])
		           if not line_search:
		              contract_line.create({'cont_id':record.contract_id.id, 'product_id':line.product_id.id,
		                                   'product_type':line.product_id.categ_id.id,
                                                    'contract_qty':line.product_uom_qty,
		                                   'uom_id':line.product_uom.id})
		              record.contract_id.message_post(body='Add Products:  ' + str(line.product_id.name))
		           else:
		               line_search.write({'contract_qty':(line_search.contract_qty + line.product_uom_qty)}) 
		               record.contract_id.message_post(body='Upate Qty in Product:  ' + str(line_search.product_id.name))
               if record.opportunity_id:
			record.opportunity_id.is_contract=True
    
    @api.onchange('incoterm')
    def _delivery_term_change(self):
    	'''Set Delivery Address to Null on Delivery term Change '''
	self.partner_shipping_id = False
	
    @api.onchange('partner_shipping_id')
    def _delivery_address_change(self):
    	'''Set Warehouse for Delivery if Delivery Term is EX-Factory according to selected shipping address '''
    	if self.incoterm.code == 'EXF':
    		wh_id=self.env['stock.warehouse'].search([('partner_id','=',self.partner_shipping_id.id)],limit=1)
    		if wh_id:
			self.warehouse_id = wh_id.id
	
    @api.multi
    @api.depends('picking_ids', 'invoice_ids')
    def invoice_payment_date(self):
        for record in self: 
            invoice=self.env['account.invoice'].search([('origin','=',record.name),('state','=','open')], limit=1) 
            if record.picking_ids:
               value=0
               days=0 
               for pick in record.picking_ids : 
                   if pick.state == 'delivered' and record.payment_term_id.payment_term_depend == 'delivery':
                      if pick.delivery_date:
                         date = datetime.strptime(str(pick.delivery_date),'%Y-%m-%d %H:%M:%S')
                         record.payment_date=date
                   if pick.state == 'delivered' and record.payment_term_id.payment_term_depend == 'credit' and record.payment_term_id.payment_due == 'delvery':                      
                      value = record.payment_term_id.time_limit_value
                      if record.payment_term_id.time_limit_type == 'day':
                         days = value
                      elif record.payment_term_id.time_limit_type == 'week':
                         days = value * 7
                      elif record.payment_term_id.time_limit_type == 'month':
                         days = value * 30
                      if pick.delivery_date:
                         date_dl=datetime.strptime(str(pick.delivery_date),'%Y-%m-%d %H:%M:%S')+timedelta(int(days))
                         record.payment_date=date_dl
            if invoice and record.payment_term_id.payment_term_depend == 'credit' and record.payment_term_id.payment_due == 'invoice':           
               value = record.payment_term_id.time_limit_value
               if record.payment_term_id.time_limit_type == 'day':
                  days = value
               elif record.payment_term_id.time_limit_type == 'week':
                    days = value * 7
               elif record.payment_term_id.time_limit_type == 'month':
                    days = value * 30
               if invoice.date_invoice:
                  date_dl=datetime.strptime(str(invoice.date_invoice),'%Y-%m-%d')+timedelta(int(days))
                  record.payment_date=date_dl
     #CH_N040 add due as payment term

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment term
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'report_currency_id' : self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id or self.env.user.company_id.currency_id.id
        }
        if self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note

        if self.partner_id.user_id:
            values['user_id'] = self.partner_id.user_id.id
        if self.partner_id.team_id:
            values['team_id'] = self.partner_id.team_id.id
        self.update(values)
        domain = {}
        partner_obj = self.env['res.partner']
        if self.partner_id:
            ipartners = [self.partner_id.id]
            partner_ids = partner_obj.search([('parent_id', '=', self.partner_id.id), ('type', '=', 'invoice')])
            if partner_ids:
                ipartners.append(partner_ids._ids)
            domain.update({'partner_invoice_id': [('id', 'in', ipartners)]})
            
            dpartners = [self.partner_id.id]
            dpartner_ids = partner_obj.search([('parent_id', '=', self.partner_id.id), ('type', '=', 'delivery')])
            if dpartner_ids:
                dpartners.append(dpartner_ids._ids)
            domain.update({'partner_shipping_id': [('id', 'in', dpartners)]})
        return {'domain' : domain}
        
    @api.multi
    def get_lead_time_information(self):
        max_customer_lead_time = 0.0
        manufacture_lead_time = 0.0
        for rec in self:
            for line in rec.order_line:
                if max_customer_lead_time < line.customer_lead:
                    max_customer_lead_time = line.customer_lead
                if line.product_id.produce_delay > 0:
                    if line.product_id.produce_delay_qty > 0:
                        days = line.product_uom_qty / (line.product_id.produce_delay_qty/line.product_id.produce_delay)
                        if manufacture_lead_time < days:
                            manufacture_lead_time = days
                
#        self.customer_lead_time = max_customer_lead_time
#        self.manufecture_lead_time = manufecture_lead_time
	   
            trasint_time = 0
	    if rec.partner_shipping_id and rec.incoterm.code != 'EXF': 
		if rec.partner_shipping_id.city_id:
			 trasint_time=rec.partner_shipping_id.city_id.transit_time
	    
            total = max_customer_lead_time + manufacture_lead_time + int(trasint_time)
            rec.customer_lead= (max_customer_lead_time and str(max_customer_lead_time) or '0') + '\tDays'
            rec.manufacturing_lead=(manufacture_lead_time and str(manufacture_lead_time) or '0') + '\tDays'
            rec.transit_time=(trasint_time and str(trasint_time) or '0') + '\tDays'
            text = 'Suggested Customer Lead time :\t' + (max_customer_lead_time and str(max_customer_lead_time) or '0') + '\tDays \n' \
            'Suggested Manufacture Lead time :\t' + (manufacture_lead_time and str(manufacture_lead_time) or '0') + '\tDays \n' \
            'Suggested Transit time :\t' + (trasint_time and str(trasint_time) or '0') + '\tDays\n' #\
            rec.lead_time_info = text

#CH_N043 add code to show payment term request button >>>
    @api.multi
    @api.onchange('payment_term_id')
    def n_payment_term(self):
	if self.payment_term_id.n_new_request:
		self.visible_request_button=True
	else:
		self.visible_request_button=False
	return 
#CH_N043 <<<

    @api.multi
    def show_payment_term(self):
	if not self.order_line:
		raise UserError(("Please add products in Records")) 
	if self.payment_term_id.n_new_request and self.visible_request_button:
		form_id = self.env.ref('gt_order_mgnt.request_payment_term_wizard_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'request.payment.term.wizard',
		    'views': [(form_id.id, 'form')],
		    'view_id': form_id.id,
		    'target':'new',
		} 

    @api.multi
    def confirm_sale_order(self):
	res_id=self.env['order.confirm.wizard'].search([('n_sale_order','=',self.id)])
	res_id.unlink()
	res_id=self.env['order.confirm.wizard'].create({'n_sale_order':self.id,'add_documents':False, })
	if self.state in ('awaiting', 'sale'):
		res_id.write({'add_documents':True, })
        if self.state in ('sale'):
		res_id.write({'state_bool':True})
        else:
                res_id.write({'state_bool':False})
	if not self.payment_term_id.n_new_request and not self.visible_request_button:
		form_id = self.env.ref('gt_order_mgnt.order_confirm_wizard_form_view1', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'order.confirm.wizard',
		    'views': [(form_id.id, 'form')],
		    'view_id': form_id.id,
		    'res_id':res_id.id,
		    'target':'new',
		}
	else:
		raise UserError('Please Select Proper Payment Term..')
		
    @api.multi
    def print_advance_payment_receipt(self):
        if self.payment_id.state =='posted':
            return self.env['report'].get_action(self, 'gt_order_mgnt.report_payment_sale_report')
        if self.payment_id.state =='draft':
            return self.env['report'].get_action(self, 'gt_sale_quotation.report_quotation_aalmir1')
        return False
     
    @api.multi
    def reminder_adv_amount(self):
        for record in self:
            ir_model_data = self.env['ir.model.data']
            try:
                template_id =self.env.ref('gt_order_mgnt.email_template_for_advance_payment_remainder1')
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict()
           
            ctx.update({
                'default_model': 'sale.order',
                'default_res_id': record.id,
                'default_composition_mode': 'comment',
                'default_use_template': bool(template_id),
                'default_template_id': template_id.id, 
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
    def action_confirm_by_sale_person(self):
        self.write({'state' : 'awaiting','date_order':datetime.now()})
	self.opportunity_id.stage_id=self.env['crm.stage'].search([('name','=','Awaiting')],limit=1) #CH_N030 add new stage for pipeline
        for obj in self:
            if obj.payment_term_id and obj.payment_term_id.advance_per > 0:
                ctx = self._context.copy()
                ctx.update({'active_id': obj.id, 'active_ids': [obj.id], 'active_model': 'sale.order'})
                sale_wiz = self.env['sale.advance.payment.inv'].sudo().with_context(ctx).create({'advance_payment_method': 'percentage', 'amount': obj.payment_term_id.advance_per})
                res=sale_wiz.sudo().with_context(ctx).create_invoices()
        return True
    
    @api.multi
    def make_lock(self):
	if self.payment_term_id.n_new_request:
           raise UserError(("Please select Payment term")) 
   #CH_N051 >>>>>> add code to delete payment term which are requested
	else:
		self.payment_term_requested=False
		requested_ids = self.env['account.payment.term.request'].search([('state', '=', 'requested'), ('quote_id', '=', self[0].id)])
		n_ids=[]
		if requested_ids:
			for ids in requested_ids:
				n_ids.append(ids.id)
			qry="delete from account_payment_term_request where id "+(" = "+str(n_ids[0]) if len(n_ids)==1 else "in "+str(tuple(n_ids)))
			self.env.cr.execute(qry)
	if not self.order_line:
		raise UserError(("Please add record in order line"))
	for order in self.order_line:
		if order.pricelist_type in ('1','2','4'):
			if  order.price_unit != order.final_price:
				raise UserError(("Please check final price and unit price of Product "+str(order.product_id.name)))
	if self.is_reception :
		for line in self.order_line:
			to_currency = line.product_id.currency_id
			sale_price = self.n_quotation_currency_id.compute(line.price_unit,to_currency)
			product_price = line.price_discount
			if sale_price < product_price:
				raise UserError('You can not sale Product {} less than Discount Price. {}'.format(line.product_id.name,str(product_price)))

        return super(SaleOrder, self).make_lock()
                
    @api.multi
    def do_revised(self):
        data = (self[0].name).split('_')
        name = self[0].name
        if self[0].opportunity_id.id:
            s_ids = self.search(['|', ('name','like', name), ('opportunity_id','=', self[0].opportunity_id.id)], order='id desc')
        if s_ids:
            seq = s_ids[0].sudo().revise_sequence + 1
        else:
            seq = self[0].sudo().revise_sequence + 1
        if len(data) > 1:
            name = data[0]
        name = name + '_' + str(seq)
        copy_quotation = self[0].with_context({'copy_quote' : True}).copy(default={'payment_term_requested': False, 'revise_sequence' : seq, 'validity_date' : False, 'state': 'draft', 'name': name, 'lock' : False,'due_payment':'done','visible_request_button':False})
        sale_form = self.env.ref('sale.view_order_form', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'views': [(sale_form.id, 'form')],
            'view_id': sale_form.id,
            'res_id' : copy_quotation.id,
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }

    force_confirm = fields.Boolean(string="Force Confirm", readonly=True)
    payment_term_requested = fields.Boolean('Payment Term Requested', default=False)
    visible_request_button = fields.Boolean(string='Visible Button', default=False)
    
    lpo = fields.Boolean(string="PO")
    lpo_name = fields.Char(string='PO Name')
    lpo_number = fields.Char(string='PO Number')
    lpo_receipt_date = fields.Date(string='PO Receipt Date')
    lpo_issue_date = fields.Date(string='PO Issued Date')
    lpo_document = fields.Binary(string='PO uploaded Document',attachment=True)
    
    signed_quote = fields.Boolean(string="Signed Quote")
    signed_quote_name = fields.Char(string='Signed Quotation Name')
    signed_quote_number = fields.Char(string='Signed Quotation Number')
    signed_quote_receipt_date = fields.Date(string='Signed Quotation Receipt Date')
    signed_quote_receipt_doc = fields.Binary(string='Signed Quotation uploaded Document',attachment=True)
    
    pop = fields.Boolean(string="POP")
    pop_receipt_name = fields.Char(string='POP uploaded Name')
    pop_receipt_date = fields.Date(string="POP Receipt Date")
    pop_uploaded_document = fields.Binary(string='POP uploaded Document',attachment=True)
    
    email = fields.Boolean(string="Email")
    email_uploaded_name = fields.Char(string='Email Uploaded Name')
    email_confirmation_date = fields.Date(string="Email Confirmation Date")
    email_uploaded_document = fields.Binary(string='Email Uploaded Document',attachment=True)
    
    match_payment_term = fields.Boolean(string='Payment Term checked by Sale Support', default=False)
    document_match = fields.Boolean(string='Documents checked by Sale Support', default=False)
    
    lead_time_info = fields.Text(string='Information', compute=get_lead_time_information)
    customer_lead=fields.Char(string='Suggested Customer Lead time', compute=get_lead_time_information)
    manufacturing_lead=fields.Char(string='Suggested Manufacture Lead time',compute=get_lead_time_information)
    transit_time=fields.Char(string='Suggested Transit time',compute=get_lead_time_information)
    is_reception=fields.Boolean('Is Reception',default=False)
    sale_lpo_number=fields.Char('PO Number',compute='sale_lpo')
    
    @api.multi
    def action_confirm(self):
	return super(SaleOrder,self).action_confirm()

    @api.multi
    @api.depends('sale_lop_documents')
    def sale_lpo(self):
	for record in self: 
		if record.sale_lop_documents:
			num = ",\n".join([lpo.lpo_number for lpo in record.sale_lop_documents])
			record.sale_lpo_number = num
            	else:
			if not record.lpo_name:
				record.sale_lpo_number = record.lpo_number

    ### add method prepare invoice 
    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['report_currency_id']=self.report_currency_id.id or False    
        invoice_vals['sale_id']=self.id or False 
        invoice_vals['comment'] = ''
        invoice_vals['report_company_name']=self.report_company_name.id
        invoice_vals['partner_id']=self.partner_id.id
        invoice_vals['partner_invoice_id']=self.partner_invoice_id.id
        return invoice_vals

    @api.multi
    def _get_origin_goods(self):
	c_ids=self.env['res.country'].search([('name','=','United Arab Emirates')],limit=1)
	if c_ids:
		return c_ids
        return 

#### Add fields in sale order 
    origin_id=fields.Many2one('res.country', string='Origin of Goods',default=_get_origin_goods)
    #total_net_weight=fields.Float('Total Net Wt', compute='total_net_weight_val')
    total_gross_weight=fields.Char('Total Gross Wt', compute='total_gross_weight_val')
   # total_gross_weight_unit=fields.Many2one('Total Gross Wt', compute='total_gross_weight_val')
    
    @api.multi
    @api.depends('order_line.weight')
    def total_gross_weight_val(self):
        for record in self:
		ids=[]
		if record.state not in ('done','cancel'):
			for line in record.order_line:
				if line.product_uom.name == 'Kg':
					ids.append(line.product_uom_qty)
				else:
					ids.append(line.weight*line.product_uom_qty)
	
		record.total_gross_weight = str(sum(ids))+'Kg (Approx)'
		
 #CH_N122 inherite method to remove cancel invoices           
    @api.depends('state', 'order_line.invoice_status')
    def _get_invoiced(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.

        The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
        for possible refunds created directly from existing invoices. This is necessary since such a
        refund is not directly linked to the SO.
        """
        for order in self:
            invoice_ids = order.order_line.mapped('invoice_lines').mapped('invoice_id')
            new_ids=[]
            for rec in invoice_ids:
                new_ids.append(rec.id)
            invoice_ids=self.env['account.invoice'].search([('id','in',new_ids),('state','!=','cancel')])

            # Search for refunds as well
            refund_ids = self.env['account.invoice'].browse()
            if invoice_ids:
                refund_ids = refund_ids.search([('type', '=', 'out_refund'), ('origin', 'in', invoice_ids.mapped('number')), ('origin', '!=', False)])

            line_invoice_status = [line.invoice_status for line in order.order_line]

            if order.state not in ('sale', 'done'):
                invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                invoice_status = 'to invoice'
            elif all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                invoice_status = 'invoiced'
            elif all(invoice_status in ['invoiced', 'upselling'] for invoice_status in line_invoice_status):
                invoice_status = 'upselling'
            else:
                invoice_status = 'no'
            order.update({
            	'invoice_count': len(set(invoice_ids.ids + refund_ids.ids)),
                'invoice_ids': invoice_ids.ids + refund_ids.ids,
                'invoice_status': invoice_status
            })

### Add sale.order.line class & fields vml
class SaleOrderLine(models.Model):
    _inherit='sale.order.line'
   
    @api.model
    def get_taxes(self):
	return self.env['account.tax'].search([('type_tax_use', '=', 'sale')], limit=1).ids

    weight=fields.Float('Gross Weight', related='product_id.weight')
    contract_bool=fields.Boolean('contract Bool')
    contract_remain_qty=fields.Float('Contract Remaining Qty')
    open_qty=fields.Float('Qty in Stock')
    contract_qty=fields.Float('Contract Qty')
    qty_exceed=fields.Boolean('Qty Exceed')
    total_delivered_qty=fields.Float('Total Delivered')
    lst_price=fields.Float("prouduct Price", related='product_id.lst_price')
    sale_invoice_id=fields.Many2one('custom.saleorder.invoice')
    mk_invoice_qty=fields.Float('Invoice Qty')
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)], default=get_taxes)
    lpo_documents=fields.Many2many('customer.upload.doc', string='PO Number')


   # Inherite this mathod from sale_stock to add state condition in stock moves records
    @api.multi
    def _get_delivered_qty(self):
        """Computes the delivered quantity on sale order lines, based on done stock moves related to its procurements
        """
        self.ensure_one()
        super(SaleOrderLine, self)._get_delivered_qty()
        qty = 0.0
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state in ('done','transit','dispatch','delivered') and r.picking_id.picking_type_code=='outgoing' and not r.scrapped):
             
            #Note that we don't decrease quantity for customer returns on purpose: these are exeptions that must be treated manually. Indeed,
            #modifying automatically the delivered quantity may trigger an automatic reinvoicing (refund) of the SO, which is definitively not wanted
            if move.location_dest_id.usage == "customer":
                qty += self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom) 
	for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and r.picking_id.picking_type_code=='incomming' and not r.scrapped):
        	qty -= self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom)
        return qty

    @api.multi
    def _prepare_invoice_line(self, qty):
        res=super(SaleOrderLine,self)._prepare_invoice_line(qty=qty)
        res['lpo_documents']=self.lpo_documents
        return res

    @api.multi
    @api.onchange('product_uom_qty' ,'qty_delivered')
    def delivered_qty_check(self):
        for record in self:
            if record.qty_delivered > record.product_uom_qty:
               self.env['sale.order.line'].create({'product_id':record.product_id.id, 'order_id':record.order_id.id}) 

    #@api.multi
    #@api.onchange('lst_price', 'product_uom_qty')
    #def unit_price_change(self):
    #    for record in self:
    #        if record.lst_price and not record.pricelist_type:
               #record.price_unit=record.lst_price

    #Override method for add invoice multiple status #CH_N059 start
    @api.depends('invoice_lines.invoice_id.state', 'invoice_lines.quantity')
    def _get_invoice_qty(self):
        """
        Compute the quantity invoiced. If case of a refund, the quantity invoiced is decreased. Note
        that this is the case only if the refund is generated from the SO and that is intentional: if
        a refund made would automatically decrease the invoiced quantity, then there is a risk of reinvoicing
        it automatically, which may not be wanted at all. That's why the refund has to be created from the SO
        """
        print "invoice comutation getting called---------------------"
        for line in self:
            qty_invoiced = 0.0
	    n_status_rel=[]
	    
            for invoice_line in line.invoice_lines:
                if invoice_line.invoice_id.state in ('draft','open','paid'):	#add draft status CH_N118
                    print "invoice_linehjbkjhkjhkjhkjhkjhkj",invoice_line.quantity,invoice_line.product_id.name
                    if invoice_line.invoice_id.type == 'out_invoice':
                        qty_invoiced += invoice_line.quantity
                    elif invoice_line.invoice_id.type == 'out_refund':
                        qty_invoiced -= invoice_line.quantity
                        
	    if qty_invoiced >0.0 and qty_invoiced < line.product_uom_qty:
		search_id=self.env['sale.order.line.status'].search([('n_string','=','partial_invoice')],limit=1) ## add status
		if search_id:
			n_status_rel.append((4,search_id.id))

	    elif qty_invoiced >= line.product_uom_qty:
		search_id=self.env['sale.order.line.status'].search([('n_string','=','partial_invoice')],limit=1) ## remove status
		if search_id:
			n_status_rel.append((3,search_id.id))

		search_id=self.env['sale.order.line.status'].search([('n_string','=','invoiced')],limit=1) ## add status
		if search_id:
			n_status_rel.append((4,search_id.id))
	    if n_status_rel:
	    	line.write({'n_status_rel':n_status_rel})
            line.qty_invoiced = qty_invoiced
	#Ch_N059>>>

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
	if context.get('n_sale_id'):
                args=[]
                product_qry="select id from sale_order_line where product_id not in (select id from product_product where product_tmpl_id in (select id from product_template where type = 'service')) and order_id={}".format(context.get('n_sale_id'))
                cr.execute(product_qry)
                product_ids=[i[0] for i in cr.fetchall()]
                args.extend([('id','in',product_ids)])
        return super(SaleOrderLine,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
        
#CH_N055 add class for store sale status
class SaleOrderLineStatus(models.Model):
	_name = 'sale.order.line.status'

	name = fields.Char('name')
	n_string = fields.Char('Relative Name')
	description = fields.Char('Description')

class SaleOrderReturn(models.Model):
	_name = 'sale.order.return'

        reason=fields.Text('Reason')
        document=fields.Binary('Document',default=False,attachment=True)
        name=fields.Char()
      
        @api.multi
        def return_reason(self):
            for record in self:
                obj=self.env['sale.order'].search([('id','=',self._context.get('active_id'))])
                if obj:
                   obj.payment_id.unlink()
                   obj.write({'state':'draft', 'lock':False})
                   temp_id = self.env.ref('gt_order_mgnt.email_template_forsale_order_return')
                   if temp_id:
                    user_obj = self.env['res.users'].browse(self.env.uid)
                    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    query = {'db': self._cr.dbname}
                    attachment=[]
                    fragment = {
		            'model': 'sale.order',
		            'view_type': 'form',
		            'id': obj.id,
                        }
                    attachment.append((self.name,self.document))
                    url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                    text_link = _("""<a href="%s">%s</a> """) % (url,obj.name)
                    body_html ='<b>Dear  '+str(obj.user_id.name) +',  Please Check Return Quotation'+'</b>'
                    body_html +='<li> Quotation No: '+str(text_link) +'</li>'
                    body_html +='<li> Customer  Name: '+str(obj.partner_id.name) +'</li>'
                    body_html +='<li>Payment Term: '+str(obj.payment_term_id.name) +'</li>' 
                    body_html +='<li>Reason: '+str(self.reason) +'</li>' 
                    body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',obj.id, context=self._context)
                    temp_id.write({'body_html': body_html, 'email_to':obj.user_id.login})
                    values = temp_id.generate_email(obj.id)
                    mail_mail_obj = self.env['mail.mail']
                    msg_id = mail_mail_obj.create(values) 
                    attachment_data={}
                    if self.document:
                       Attachment = self.env['ir.attachment']
                       attachment_ids = values.pop('attachment_ids', [])
                       attachment_data = {

		                'name':self.name,
		                'datas':self.document,
		                'res_model': 'mail.message',
		                'res_id': msg_id.mail_message_id.id,
		                  }
                       attachment_ids.append(Attachment.create(attachment_data).id)
                       if attachment_ids:
                          values['attachment_ids'] = [(6, 0, attachment_ids)]
                          msg_id.write({'attachment_ids': [(6, 0, attachment_ids)],
		                      })
                    msg_id.send()  

