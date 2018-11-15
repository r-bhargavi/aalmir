 # -*- coding: utf-8 -*-
##############################################################################
#
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
from datetime import datetime,date
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
from urlparse import urljoin
from urllib import urlencode
import ast
import uuid
import re
_logger = logging.getLogger(__name__)

class MailComposeMessage(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'purchase.order' and self._context.get('default_res_id'):
            order = self.env['purchase.order'].browse([self._context['default_res_id']])
            if order.state == 'draft':
                order.state = 'sent'
            if self._context.get('from_purchase') and order.state == 'purchase':
               order.write({'state':'sent po'})
           
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)

class PurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'
   
    sale_price=fields.Float('Quote Price')
    #approved_price=fields.Float('Approved Price')
    #approved_status=fields.Selection([('approved','Approved'),('not_approved','Not Approved')], string='Price Approved Status', compute='approved_product_price')

    '''@api.multi
    @api.depends('price_unit','approved_price')
    def approved_product_price(self):
        for record in self:
            if record.price_unit and record.approved_price:
               if record.price_unit > record.approved_price:
                  record.approved_status='not_approved'
               else:
                  record.approved_status='approved'''''

    @api.depends('order_id.state', 'move_ids.state')
    def _compute_qty_received(self):
        productuom = self.env['product.uom']
        for line in self:
            if line.order_id.state not in ['purchase', 'done','sent po']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            bom_delivered = self.sudo()._get_bom_delivered(line.sudo())
            if bom_delivered and any(bom_delivered.values()):
                total = line.product_qty
            elif bom_delivered:
                total = 0.0
            else:
                total = 0.0
                for move in line.move_ids:
                    if move.state == 'done':
                        if move.product_uom != line.product_uom:
                            total += productuom._compute_qty_obj(move.product_uom, move.product_uom_qty, line.product_uom)
                        else:
                            total += move.product_uom_qty
            line.qty_received = total

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
           self.taxes_id=self.env['account.tax'].search([('type_tax_use', '=', 'purchase')], limit=1).ids
        else:
           self.taxes_id=False
        return res

    @api.multi
    @api.onchange('price_unit')
    def exceptio_message(self):
        for record in self:
	    if record.price_unit and record.sale_price:
		    if record.price_unit >= record.sale_price:
		       #record.exception_bool=True
		       raise UserError(_('Your %s Price unit is greater than Quote price') % record.price_unit)
               
class PurchaseOrder(models.Model):
    _inherit='purchase.order'

    @api.model
    def default_get(self, fields):
        result= super(PurchaseOrder, self).default_get(fields)
        if self.env.user.company_id:
           result.update({'vendor_remark':self.env.user.company_id.purchase_note})
        purchase=self.env['purchase.order'].search(['|','|',('management_user','!=',False),('procurement_user','!=',False),('inventory_user','!=',False)], limit=1)
        if purchase.management_user:
           result.update({'management_user':purchase.management_user.id or False})
        if purchase.procurement_user:
           result.update({'procurement_user':purchase.procurement_user.id or False})
        if purchase.inventory_user:
           result.update({'inventory_user':purchase.inventory_user.id or False})
	result.update({'picking_type_id':False})
        return result

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.fiscal_position_id = False
            self.payment_term_id = False
            self.currency_id = False
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(self.partner_id.id)
            self.payment_term_id = False
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
        return {}
  
    production_reqst_id=fields.Many2one('production.request.detail' ,related='requisition_id.production_reqst_id')
    delivery_date=fields.Datetime('Delivery Date', compute='stock_delivery_date')
    line_id=fields.Many2one('sale.order.line' ,string="Sale order line", related='requisition_id.line_id')
    sale_id=fields.Many2one('sale.order',string="Sale Order", related='requisition_id.sale_id')
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name",related='requisition_id.contract_id')
    production_id=fields.Many2one('mrp.production', string='Manufacturing Number',)
    production_ids=fields.Many2one('mrp.production', string='Manufacturing Number',related='requisition_id.production_id')
    request_id=fields.Many2one('n.manufacturing.request', string='Production Request', related='requisition_id.request_id')
    n_request_date=fields.Date('Product Requested Date')
    n_request_date_bool = fields.Boolean(string="bool",default=False)
    n_request_date_bool1 = fields.Boolean(string="bool",default=False)
    vendor_instruction=fields.Text('Vendor Instruction')
    vendor_remark=fields.Text('Terms & Conditions')
    tax_ids = fields.Many2many('account.tax', 
                                'product_taxes_rel_purchase_ext',
                                'tax_id',
                                'pur_id',
                                'Global Taxes')
    current_users_bool=fields.Boolean(compute='get_user_id')
    management_user=fields.Many2one('res.users','Management User')
    procurement_user=fields.Many2one('res.users','Procurement User')
    inventory_user=fields.Many2one('res.users','Finance User')
    approve_mgnt=fields.Boolean()
    approve_prq=fields.Boolean()
    approve_inv=fields.Boolean()
    attend_id=fields.Many2one('res.partner','Atten')
    sent_mail=fields.Boolean('Hide send mail button', default=False)
    approved_msg1=fields.Char()
    approved_msg2=fields.Char()
    approved_msg3=fields.Char()
    date_planned_bool=fields.Boolean()
    new_schedule_date=fields.Datetime('Schedule Date')
    payment_term_bool =fields.Selection([('purchase','Purchase'),('new','New'),('mile','Milestone')])
    management_name=fields.Char()
    procurement_name=fields.Char()
    inventory_name=fields.Char()
    management_name_bool=fields.Boolean()
    procurement_name_bool=fields.Boolean()
    inventory_name_bool=fields.Boolean()
    employee_id=fields.Many2one('hr.employee' ,'Requested User')
    employee_email=fields.Char('User Email', related='employee_id.work_email')
    #requested_user=fields.Many2one('res.users','Existing User')
    document_ids=fields.Many2many('ir.attachment', 'reject_rel_po','reject_rel2_po','id',string='Documents')
    vendor_vat=fields.Char('Vendor VAT' ,related='partner_id.vat')
    vendor_vat_bool=fields.Boolean(default=True)
    milestone_ids=fields.One2many('purchase.milestone.payment.term', 'purchase_id')
    warranty=fields.Text('Warranty')
    show_product_schedule=fields.Boolean('Product Schedule Receive Date on Report', default=True)
    default_signature1=fields.Boolean('Use Default Signature', default=True)
    default_signature2=fields.Boolean('Use Default Signature', default=True)
    default_signature3=fields.Boolean('Use Default Signature', default=True)
    show_delivery_term=fields.Boolean(default=True)
    show_stamp=fields.Boolean('Show Stamp on Report',default=True)
    report_company_name=fields.Many2one('res.company','LetterHead Company Name', default=lambda self: self.env['res.company']._company_default_get('purchase.order'))
    state = fields.Selection([
        ('draft', 'Draft PO'),
        ('sent', 'Draft PO Sent'),
        ('awaiting','Awaiting'), 
        ('rejected','Rejected'),
        ('to approve', 'Approved'),
        ('purchase', 'Purchase Order'),
        ('sent po', 'Sent PO'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    po_validation=fields.Selection([('max', 'Max'),('medium','Medium'),('min','Min')],compute='validation_val')
    payment_term_request =fields.Selection([('request','Requested'),('approve','Approved'),('reject','Rejected')])


    show_delivery_address=fields.Boolean(string='Delivery Address',default=True,help="Show Delivery Address on print")
    internal_note=fields.Text('Internal Note')
    converted_amount_total = fields.Monetary(string='Converted Total', compute='_get_converted_total')
    company_currency_id=fields.Many2one('res.currency','Company Currency', related='company_id.currency_id')
    allow_extra = fields.Boolean(string='Extra Receive',default=False,help="Allow Logistics to Receive Extra Quantity")
    
    @api.multi
    @api.depends('amount_total', 'currency_id')
    def _get_converted_total(self):
        for record in self:
            from_currency = record.currency_id
            to_currency = self.env.user.company_id.currency_id
            if record.amount_total:
               record.converted_amount_total = from_currency.compute(record.amount_total, to_currency, round=False)

    @api.multi
    def button_draft(self):
        self.write({'state': 'draft','sent_mail':False})
        return {}

    @api.multi
    def button_done(self):
        pickings=self.env['stock.picking'].search([('purchase_id','=',self.id),('state','in',('draft','awaiting','confirmed','assigned'))])
        if pickings:
           raise UserError(_('Please first Complete Receiving Shipments before set to Done.'))
        invoices=self.env['account.invoice'].search([('origin','=',self.name),('state','in',('draft','open'))])
        if invoices:
           raise UserError(_('Please first Done All Vendor Bills  before set to Done.'))
        self.write({'state': 'done'})

    @api.multi
    def button_cancel(self):
        res=super(PurchaseOrder,self).button_cancel() 
        self.payment_term_request=[]
        self.payment_term_bool=[]
        self.sent_mail=False
        #self.name=(self.name).replace('PO', 'DPO')
        if self.approve_mgnt:
	   self.approve_mgnt=False
	   self.approved_msg1=" " 
		
        if self.approve_inv:
	   self.approve_inv=False
	   self.approved_msg3=" "

        if self.approve_prq:
	   self.approve_prq=False
	   self.approved_msg2=" "
        return res

    @api.multi  
    def force_confirm(self):
        for line in self:
            cofirm_form = self.env.ref('gt_order_mgnt.purchase_order_cancel_form', False)
            if cofirm_form:
                return {
                    'name':'Purchase Order Force Confirm',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order.cancel',
                    'views': [(cofirm_form.id, 'form')],
                    'view_id': cofirm_form.id,
                    'target': 'new',
                    'context':{'force_confirm':True}
                }
        return True
        
 
    @api.multi
    @api.depends('amount_total','company_id.po_double_validation_amount','company_id.min_amount')
    def validation_val(self):
        for record in self:
            max_val=self.env.user.company_id.currency_id.compute(record.company_id.po_double_validation_amount, record.currency_id)
            min_val=self.env.user.company_id.currency_id.compute(record.company_id.min_amount, record.currency_id)
            if record.amount_total >= max_val:
               record.po_validation='max'
            if record.amount_total <= max_val and record.amount_total >= min_val:
               record.po_validation='medium'
            if record.amount_total <= min_val:
               record.po_validation='min'
    @api.multi
    def approve_reason(self):
        for line in self:
            cancel_form = self.env.ref('gt_order_mgnt.purchase_order_cancel_form', False)
            if cancel_form:
                return {
                    'name':'Purchase Order Approve',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order.cancel',
                    'views': [(cancel_form.id, 'form')],
                    'view_id': cancel_form.id,
                    'target': 'new',
                }
        return True
       
    @api.multi
    @api.onchange('management_user','procurement_user','inventory_user')
    def users_designation_name(self):
        for record in self:
            if record.management_user:
               record.management_name=record.management_user.designation_purchase
            else:
               record.management_name=False
            if record.procurement_user:
               record.procurement_name=record.procurement_user.designation_purchase
            else:
               record.procurement_name=False
            if record.inventory_user:
               record.inventory_name=record.inventory_user.designation_purchase
            else:
               record.inventory_name=False

    @api.multi
    def open_invoices(self):
        for line in self:
            order_cal_tree = self.env.ref('account.invoice_supplier_tree', False)
            order_form = self.env.ref('account.invoice_supplier_form', False)
            if order_cal_tree:
                return {
                    'name':'Vendor Bills',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'account.invoice',
                    'views': [(order_cal_tree.id, 'tree'),(order_form.id, 'form')],
                    'view_id': order_cal_tree.id, 
                    'target': 'current',
                    'domain':[('origin','=',line.name)],
                    'context':{'default_purchase_id':line.id, 'type': 'in_invoice',
                               }
                    
                }
        return True

    @api.onchange('payment_term_id')
    def payment_term_onchange(self):
	if self.payment_term_id.n_milestone_request:
	   self.payment_term_bool = 'mile'
	elif self.payment_term_id.n_new_request:
           self.payment_term_bool = 'new'
        else:
            self.payment_term_bool = 'purchase'
    @api.multi
    def request_payment_term(self):
	if self.payment_term_id.n_new_request:
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
    def button_confirm(self):
        if self.payment_term_request == 'request':
           raise UserError('Payment Term Request not Complete')
        if self.state in ('to approve'):
           self.name=(self.name).replace('DPO', 'PO')
           self._add_supplier_to_product()
           self.button_approve()
           if self.payment_term_id.advance_per or self.milestone_ids:
               for line in self.order_line:
                  if line.product_id.purchase_method != 'purchase':
                     line.product_id.purchase_method = 'purchase'
               journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1) 
               invoice=self.env['account.invoice'].create({'purchase_id':self.id, 
                     'type': 'in_invoice','origin':self.name,
                     'account_id':self.partner_id.property_account_payable_id.id,
                     'partner_id':self.partner_id.id,'payment_term_id':self.payment_term_id.id,
                     'journal_id':journal.id, 'currency_id':self.currency_id.id})
               invoice.purchase_order_change()
               invoice.compute_taxes()
               invoice.date_due=date.today()
               if self.payment_term_id.advance_per:
                  amount=(self.amount_total * self.payment_term_id.advance_per)/100
                  invoice.write({'payable_amount':(amount),
                  'payable_discount':str(self.payment_term_id.advance_per) + "% Adavance of PO:"})
               '''order_form = self.env.ref('account.invoice_supplier_form', False)  
               if order_form:
                   return {
		            'name':'Vendor Bills',
		            'type': 'ir.actions.act_window',
		            'view_type': 'form',
		            'view_mode': 'form,',
		            'res_model': 'account.invoice',
		            'views': [(order_form.id, 'form')],
		            'view_id': order_form.id, 
		            'target': 'current',
		            'context':{'default_purchase_id':self.id, 
                             'type': 'in_invoice','default_date_due':datetime.now().isoformat()}
                   }'''

    ### sent Requested User mail
    @api.multi
    def action_mail_send(self):
        for purchase in self:
            ir_model_data = self.env['ir.model.data']
            try:
                template_id =self.env.ref('gt_order_mgnt.email_template_for_purchase_requested_user_po11')
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict()
            p_id=self.env.user.partner_id.id
            partner_ids = [p_id]
            ctx.update({
                'default_model': 'purchase.order',
                'default_res_id': purchase.id,
                'default_composition_mode': 'comment',
                'default_use_template': bool(template_id),
                'default_template_id': template_id.id, 
                'default_email_ids':purchase.employee_email,
                'default_composition_mode': 'comment',
                'mark_so_as_sent': True,
                'from_purchase_order':True
               
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
    def request_payment_term(self):
	if not self.order_line:
		raise UserError(("Please add products in Records")) 
	if self.payment_term_id.n_new_request:
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
    def resend_approval_mail(self):
        for line in self:
            cancel_form = self.env.ref('gt_order_mgnt.purchase_order_cancel_form', False)
            if cancel_form:
                return {
                    'name':'Purchase Order Approve',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order.cancel',
                    'views': [(cancel_form.id, 'form')],
                    'view_id': cancel_form.id,
                    'target': 'new',
                }
        return True
    @api.multi 
    def pending_send_mail(self):
        if self.payment_term_request in ('request','reject') or self.payment_term_id.n_new_request:
           raise UserError('Please first Confirm Payment Term Request.')
        template_ids = self.env.ref('gt_order_mgnt.email_template_for_purchase_approve_pending1')
        recipient_partners=''
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        query = {'db': self._cr.dbname}
        fragment = {
		'model': 'purchase.order',
		'view_type': 'form',
		'id': self.id,
		}
        url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
        text_link = _("""<a href="%s">%s</a> """) % (url,self.name)
        body='<b>Purchase Order Approval Required  </b>'
        body +='<li> Purchase Order No: '+str(text_link) +'</li>'
        body +='<li> Vendor  Name: '+str(self.partner_id.name or self.partner_id.parent_id.name) +'</li>' 
        body +='<li> Total Amount: '+str(self.amount_total) +str(self.currency_id.name)+'</li>'
        body +='<li> Sent By: '+str(self.env.user.name) +'</li>'
        body +='<li> Sent Date: '+str(date.today()) +'</li>' 
        body +='<li> Requested By: '+str(self.employee_id.name if self.employee_id else 'NA' ) +'</li>'
        body +='<li> Internal Note: '+str(self.internal_note if self.internal_note else 'NA') +'</li>'
        
        template_ids.write({'body_html':body})
        #r_word='Rejected'
        if self.state == 'awaiting':
           if not self.approve_mgnt:
              recipient_partners +=str(self.management_user.login)
           if not self.approve_prq:
              recipient_partners += ","+str(self.procurement_user.login)
           if not self.approve_inv:
              recipient_partners += ","+str(self.inventory_user.login)

        if self.state == 'rejected':
           if self.approve_mgnt:# and r_word == self.approved_msg1.split(' ', 1)[0]:
              #recipient_partners +=str(self.management_user.login)
              self.approve_mgnt=False
              self.approved_msg1=''
           if self.approve_prq:# and r_word == self.approved_msg2.split(' ', 1)[0]:
              #recipient_partners += ","+str(self.procurement_user.login)
              self.approve_prq=False
              self.approved_msg2=''
           if self.approve_inv:# and r_word == self.approved_msg3.split(' ', 1)[0]:
              #recipient_partners += ","+str(self.inventory_user.login)
              self.approve_inv=False
              self.approved_msg3=''
	if self.state in ('rejected','draft'):
		      if self.management_user.id == self.env.user.id:
		         self.approve_mgnt=True
		         self.approved_msg1="Approved By "+" "+str(self.env.user.name) +" on Behalf of Procurement"+ ' '+str(date.today()) 
		      else:
		         recipient_partners +=str(self.management_user.login)

		      if self.inventory_user.id == self.env.user.id:
		         self.approve_inv=True
		         self.approved_msg3="Approved By "+" "+str(self.env.user.name) +" on Behalf of Procurement"+ ' '+str(date.today()) 
		      else:
		         recipient_partners += ","+str(self.inventory_user.login)

		      if self.procurement_user.id == self.env.user.id:
		         self.approve_prq=True
		         self.approved_msg2="Approved By "+" "+str(self.env.user.name) +" on Behalf of Procurement"+ ' '+str(date.today()) 
		      else:
		         recipient_partners += ","+str(self.procurement_user.login)
        values = template_ids.generate_email(self.id)
        values['email_to'] = recipient_partners
        self.sent_mail=True
        self.write({'state': 'awaiting'})
        mail_mail_obj = self.env['mail.mail']
        msg_id = mail_mail_obj.create(values) 
        Attachment = self.env['ir.attachment']
        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        attachment_data={}
        for attachment in attachments:
            attachment_data = {
		                'name': attachment[0],
		                'datas_fname': attachment[0],
		                'datas': attachment[1],
		                'res_model': 'mail.message',
		                'res_id': msg_id.mail_message_id.id,
		                
		                  }
        attachment_ids.append(Attachment.create(attachment_data).id)
        if attachment_ids:
           values['attachment_ids'] = [(6, 0, attachment_ids)]
	   msg_id.write({'attachment_ids': [(6, 0, attachment_ids)],
		                      })
        msg_id.send()  
        return msg_id
        
    @api.multi
    @api.onchange('approve_inv')
    def get_behalf_approve1(self):
        for record in self:
            if record.inventory_user and record.approve_inv: 
               record.approved_msg3="Approved By " +" "+str(self.env.user.name) +" on Behalf of Finance "+ ''+str(date.today()) 
      
            else:
               record.approved_msg3=False
            if record.approve_mgnt and record.approve_prq and record.approve_inv and record.state == 'awaiting':
               record.state='to approve'
            else:
               if record.state == 'awaiting':
                  record.state='awaiting' 
              
    @api.multi
    @api.onchange('approve_prq',)
    def get_behalf_approve2(self):
        for record in self:
            if record.approve_prq:
               if record.procurement_user and record.approve_prq: 
                  record.approved_msg2="Approved By "+" "+str(self.env.user.name) +" on Behalf of Procurement"+ ' '+str(date.today()) 
            else:
               record.approved_msg2=False
            if record.approve_mgnt and record.approve_prq and record.approve_inv and record.state == 'awaiting':
               record.state='to approve'
            else:
               if record.state == 'awaiting':
                  record.state='awaiting' 
               
    @api.multi
    @api.onchange('approve_mgnt',)
    def get_behalf_approve3(self):
        for record in self:
            if record.management_user and record.approve_mgnt:
               record.approved_msg1="Approved By "+" "+str(self.env.user.name)+" on Behalf of Management"+ ' '+str(date.today()) 
            else:
               record.approved_msg1=False
            if record.approve_mgnt and record.approve_prq and record.approve_inv and record.state == 'awaiting':
               record.state='to approve'
            else:
               if record.state == 'awaiting':
                  record.state='awaiting' 
              
    @api.multi
    @api.depends('management_user','procurement_user','inventory_user','approve_mgnt','approve_prq','approve_inv')
    def get_user_id(self):
        for record in self: 
            user=1
            user=record.management_user.id or record.procurement_user.id or record.inventory_user.id
            if record.management_user.id == self.env.user.id and record.approve_mgnt: 
               record.current_users_bool=True
               break;
            else:
               record.current_users_bool=False
            if record.procurement_user.id == self.env.user.id and record.approve_prq: 
               record.current_users_bool=True
               break;
            else:
               record.current_users_bool=False
            if record.inventory_user.id == self.env.user.id and record.approve_inv: 
               record.current_users_bool=True
               break;
            else:
               record.current_users_bool=False
            if self.env.user.id ==1:
               record.current_users_bool=True
               break;

    @api.model
    def _prepare_picking(self):
       res=super(PurchaseOrder,self)._prepare_picking()
       requisition=self.env['purchase.requisition'].search([('id','=',self.requisition_id.id)])
       res['purchase_id']=self.id
       res['request_sch_date_mo']=requisition.pr_request_date
       res['mo_qty']=requisition.mo_qty
       res['mo_uom_id']=requisition.mo_uom_id.id
       res['customer_name_report']='Vendor Name'
       res['report_name']='Receiving Order List'
       return res

    @api.multi    
    def compute_global_tax(self):
        for record in self.order_line:
            if record.product_id:
                record.write({'taxes_id':[(6, 0, [x.id for x in self.tax_ids])]})     
    @api.multi
    def action_view_invoice(self):
        res=super(PurchaseOrder, self).action_view_invoice()
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]
        result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id, 'default_taxe':[(6, 0, [x.id for x in self.tax_ids])]}
        result['context']['default_taxe'] = [(6, 0, [x.id for x in self.tax_ids])]
        return result

    @api.multi
    def download_reports(self):
	if self.state in ('draft','sent','awaiting','to approve'):
           res=self.env['report'].get_action(self, 'purchase.report_purchasequotation')
        if self.state in ('purchase','done','sent po'):
           if self.state=='purchase':
              self.state='sent po'
           res=self.env['report'].get_action(self, 'purchase.report_purchaseorder')
        return res

    @api.multi
    def print_order(self):
        return self.env['report'].get_action(self, 'purchase.report_purchaseorder')

    @api.multi
    def purchase_schedule_date(self):
	order_form = self.env.ref('gt_order_mgnt.manufacturing_date_history_form_view', False)
	context = self._context.copy()
	context.update({'default_n_line_id':self.line_id.id,'default_n_prevoiusdate':self.n_request_date,
			'default_n_prevoiusdate1':self.n_request_date,'default_n_status':'draft',
                        'default_n_po':self.id})

        return {'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'mrp.complete.date',
		    'views': [(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'target': 'new',
		    'context':context,}

    @api.multi
    def stock_message_id(self):
        for record in self:
            if record.picking_ids:
               for pick in record.picking_ids:
                   record.message_ids=pick.message_ids

    @api.depends('picking_ids.min_date')
    def stock_delivery_date(self):
        for record in self:
            if record.picking_ids:
               for rec in record.picking_ids:
                   if rec.state in ('assigned'):
                      record.delivery_date= rec.min_date
                      record.message_ids=rec.message_ids
   
    @api.multi
    def preview_purchaseOrder(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_name=''
        if self.state in ('draft','sent','awaiting','to approve'):
           report_name="/report/pdf/purchase.report_purchasequotation/"
        if self.state in ('purchase','done','sent po'):
           report_name="/report/pdf/purchase.report_purchaseorder/"
        return {
            "type": "ir.actions.act_url",
            "url": base_url + report_name + str(self.id),
            "target": "new",}

    @api.model
    def create(self, vals): 
        name=''
	if vals.get('requisition_id'):
		te_id=self.env['purchase.requisition'].search([('id','=',vals.get('requisition_id'))])
		vals.update({'n_request_date':te_id.schedule_date,'notes':te_id.note_from_PR,'vendor_remark':te_id.description})
        if vals.get('name', 'New') == 'New':
           seq_no=self.env['ir.sequence'].next_by_code('purchase.order') or '/'
           no=seq_no[2:]
           name=''
        if vals.get('state', 'draft'):
           name +='DPO'+no
        vals['name'] =name 
        if vals.get('date_planned'):
           vals['new_schedule_date']=vals.get('date_planned')
        res=super(PurchaseOrder, self).create(vals)
        if vals.get('milestone_ids'):
           total=sum(line.value for line in res.milestone_ids)
           if total>100 or total<100:
              raise UserError("Milestone Payment Term values should be 100.")
        return res

    @api.multi
    def write(self, vals):
        res=super(PurchaseOrder, self).write(vals)
        if self.milestone_ids:
           total=sum(ml.value for ml in self.milestone_ids)
           if total > 100 or total <100:
              raise UserError("Milestone Payment Term values should be 100.")
              
        if 'allow_extra' in vals.keys():
        	if self.state == 'done':
        		raise UserError(" You can't Change,Purchase Order is Done")
        	self.message_post(body="Allow Extra Receive Quantity <b>{}</b>".format(str(vals.get('allow_extra'))))
        return res

    @api.multi
    def unlink(self): 
        for res in self:
	   if res.name.upper() !='NEW':
              raise UserError("You don't Have Access to delete Purchase Order")
        return super(PurchaseOrder, self).unlink()
    
class purchaseRequisition(models.Model):
    _inherit='purchase.requisition'
    
    @api.multi
    def print_order(self):
        return self.env['report'].get_action(self, 'purchase_requisition.report_purchaserequisitions')

    @api.model
    def seqprq(self):
        seq_no=self.env['ir.sequence'].next_by_code('purchase.order.requisition') or '/'
        seq=''
        if seq_no:
           no=seq_no[2:]
           seq="PRQ"+no
        return seq

    name=fields.Char(default=seqprq)
    production_reqst_id=fields.Many2one('production.request.detail')
    sale_id=fields.Many2one('sale.order', string="Sale Order")
    line_id=fields.Many2one('sale.order.line' ,string="Sale order line")
    request_line = fields.Many2one('n.manufacturing.request', 'Manufacture Request')
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name")
    production_id=fields.Many2one('mrp.production', string='Manufacturing Number', related='request_id.n_mo_number')
    m_production_id=fields.Many2one('mrp.production', string='Manufacturing Number',)
    mo_qty=fields.Float('Scheduled Qty')
    mo_uom_id=fields.Many2one('product.uom', string="Unit")
    request_id=fields.Many2one('n.manufacturing.request', string='Production Request')
    extra_docs=fields.Many2many('ir.attachment','pr_extra_attachment_rel','extra_doc','id','Documents')
    pr_request_date = fields.Date('Requested Date From Production')
    note_from_PR = fields.Text('Instruction From Production')
    purchase_request_id=fields.Many2one('stock.purchase.request', 'Purchase Request No.')

    @api.v7
    def _prepare_purchase_order_line(self, cr, uid, requisition, requisition_line, purchase_id, supplier, context=None):
        res = super(purchaseRequisition, self)._prepare_purchase_order_line(cr, uid, requisition, requisition_line, purchase_id, supplier, context=context)
        res.update({'sale_price':requisition_line.sale_price,})
        return res

    @api.model
    def create(self,vals):
	user_search=self.env['res.users'].search([('designation','=','Purchase Manager')])
	if user_search:
		vals.update({'user_id':user_search[0].id})
	return super(purchaseRequisition,self).create(vals)

    @api.multi
    def unlink(self): 
        for res in self:
	   if res.name.upper() !='NEW':
              raise UserError("You don't Have Access to delete Purchase Requisition")
        return super(purchaseRequisition, self).unlink()

class purchase_requisition_line(models.Model):
    _inherit='purchase.requisition.line'
    sale_price=fields.Float('Quote Price')
   
class ProductionRequestDetail(models.Model):
    _name='production.request.detail'

    @api.model
    def default_get(self,fields):
        rec = super(ProductionRequestDetail, self).default_get(fields)
	obj = self.env['n.manufacturing.request'].browse(self._context.get('active_id'))
	if obj.n_product_id:
		rec.update({'product_id' : obj.n_product_id.id,'product_type':obj.n_product_id.categ_id.cat_type,'request_line':obj.id})
	if obj.n_sale_line:
		rec.update({'sale_id' : obj.n_sale_line.id})
	if obj.n_sale_order_line:
		rec.update({'line_id' : obj.n_sale_order_line.id})
	if obj.n_order_qty:
		rec.update({'total_qty' : obj.n_order_qty})
	if obj.n_delivery_date:
		rec.update({'request_date' : obj.n_delivery_date})
	return rec

    name=fields.Char('Name')
    fully_purchase=fields.Boolean('Fully Purchase', default=True)
    half_purchase=fields.Boolean('Half Purchase')
    film_process=fields.Boolean('Film Extruder Process')
    printing_process=fields.Boolean('Printing Process')
    cutting_bool=fields.Boolean('Cutting Process')

    sale_id=fields.Many2one('sale.order', "Sale Order")
    line_id=fields.Many2one('sale.order.line', string="Line")
    request_line = fields.Many2one('n.manufacturing.request', 'Manufacture Request')

    sale_price=fields.Float('Sale Price', related='line_id.price_unit')
    product_id=fields.Many2one('product.product', "Product")
    product_type=fields.Selection([('film','Films and Bags'),('injection','Injection')],string="Product Type")

    product_uom_id=fields.Many2one('product.uom', related='line_id.product_uom')
    material_details=fields.Many2one('material.details', "Material")
    material_tolerance=fields.Char('Tolerance')
    colour=fields.Many2one('production.request.colour','Colour')
    colour_tolerance=fields.Char('Tolerance')
    width=fields.Many2one('production.request.width', 'Width')
    width_tolerance=fields.Char('Tolerance')
    length=fields.Many2one('production.request.length', 'Length')
    length_tolerance=fields.Char('Tolerance')
    thickness=fields.Many2one('production.request.thickness','Thickness')
    thickness_tolerance=fields.Char('Tolerance')
    treatment=fields.Many2one('production.request.treatment', 'Treatment')
    treatment_tolerance=fields.Char('Tolerance')
    type_val=fields.Many2one('production.request.type', 'Type')
    type_val_tolerance=fields.Char('Tolerance')
    core_id=fields.Many2one('production.request.core','Core ID')
    core_id_tolerance=fields.Char('Tolerance')
    avg_weight=fields.Many2one('production.request.avg.weight','Avg Weight')
    avg_weight_tolerance=fields.Char('Tolerance')
    appearance=fields.Many2one('production.request.appearance','Appearance')
    appearance_tolerance=fields.Char('Tolerance')
    strength=fields.Many2one('production.request.strength','Strength')
    strength_tolerance=fields.Char('Tolerance')
    sealing=fields.Many2one('production.request.sealing','Sealing')
    sealing_tolerance=fields.Char('Tolerance')
    ## printing process
    cutting_process=fields.Many2one('production.request.cut.process','Cutting Process')
    cutting_process_tolerance=fields.Char('Tolerance')
    cutting_size=fields.Many2one('production.request.cut.size','Cutting Size')
    cutting_size_tolerance=fields.Char('Tolerance')
    printing_colour=fields.Many2one('production.request.print.color','Printing Colour')
    printing_colour_tolerance=fields.Char('Tolerance')
    ecas_logo=fields.Selection([('yes', 'Yes'),('no', 'NO')], string="Ecas Logo")
    d2w_logo=fields.Selection([('yes', 'Yes'),('no', 'NO')], string="D2W Logo")
    print_mark=fields.Many2one('production.request.print.mark','Print Mark')
    art_color=fields.Many2many('production.request.art.color',string="Colour")
    art_color_tolerance=fields.Char('Tolerance')
    ### extra fields
    production_sheet=fields.Many2many('ir.attachment','extra_attachment_rel','extra_doc','id','Extra Documents')
    special_instruction=fields.Text("Special Instruction")
    total_qty=fields.Float('Total Qty')
    #mo_qty=fields.Float
    request_date=fields.Datetime('Request Date')
    user_id=fields.Many2one('res.users', "Prepared By", default=lambda self: self.env.user)
    state = fields.Selection([('draft','Draft'),('request','Request'),('done','Done')],string="Status",default="draft")

    @api.multi
    def create_purchase_order(self):
	self.state='done'
        purchase=self.env['purchase.requisition']
        obj = self.env['n.manufacturing.request'].browse(self._context.get('active_id'))
        
        mail_mail = self.env['mail.mail']
        mail_ids = []
        status_list=[]
        footer = _("Kind regards.\n") 
        
        footer +=self.env.user.company_id.name       
        for record in self:
            print"---------ppppppp",record.product_uom_id.id
	    status_list=[] 
            product=self.env['product.template'].search([('id','=',record.product_id.product_tmpl_id.id)])
            subject =record.name
            body = "Purchase Tender create for this product" +"<br></br>"
            body +="<b>Product Name:</b>" + record.product_id.name+"\t"
            body += "<b>Total Qty:</b>" +str(record.total_qty) +"<br></br>"
            body +="<b>Date:</b>" +record.request_date+"\t"
            body +="<b>Special Instruction:</b>" +record.special_instruction +"<br></br>" if record.special_instruction else False
            body +="<b>Prepared By:</b>" +record.user_id.name+"<br></br>" if record.user_id else False
            purchase_id=purchase.create({'production_reqst_id':record.id, 'schedule_date':record.request_date,
                                       'contract_id':obj.contract_id.id,'origin':record.sale_id.name, 'request_id':obj.id,
                            'note_from_PR':record.special_instruction, 'sale_id':record.sale_id.id,'line_id':record.line_id.id,
                            'line_ids':[(0,0, {'product_id':record.product_id.id, 'product_qty':record.total_qty,
                                                'sale_price':record.sale_price,'request_line':record.request_line,
                                                'product_uom_id':record.product_uom_id.id, 'schedule_date':record.request_date,})],
			    'extra_docs':record.production_sheet if record.production_sheet else '','pr_request_date':record.request_date})

            obj.write({'n_po_number':purchase_id.id,'n_state':'purchase',})
	    new_id=self.env['sale.order.line.status'].search([('n_string','=','purchase')],limit=1)	#add status
	    if new_id and self.line_id:
		status_list.append((4,new_id.id))
		self.line_id.n_status_rel = status_list

            outsource_rec="%s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s %s" %(record.material_details.name.name or "", 
                               record.colour.name or "",record.width.name or "", record.length.name or "",
                                 record.thickness.name or "", record.treatment.name or "", record.type_val.name  or "",
                                 record.core_id.name or "", record.avg_weight.name or "",record.sealing.name or "",
                                 record.appearance.name or "", record.strength.name or "", record.sealing.name or "", 
                                  record.cutting_process.name or "", record.cutting_size.name or "", record.printing_colour.name or "",
                                  record.print_mark.name or "",)
            product.write({'description_purchase':outsource_rec})
            datas= record.production_sheet if record.production_sheet else ''
            mail_val=mail_mail.create({'email_to':'self.env.user.login',
                                      'email_from':self.env.user.login,
                                       'subject': subject,
                                       #'attachment_ids':[(0, 0, {'name':record.name,'type':'binary','datas_fname': record.name,
                                       #                  'res_model':'production.request.detail','datas':datas})], 
                                       'auto_delete':False,
                                       'body_html': '<pre><span class="inner-pre" style="font-size: 15px">%s<br>%s<br></pre>' %( body,footer) }) 
        
        mail_ids.append(mail_val)
        mail_mail.send(mail_ids)
        
    @api.multi
    def create_manufacturing_order(self):
        line = self[0]
        obj = self.env['n.manufacturing.request'].browse(self._context.get('active_id'))
	context = self._context.copy()
	bom_ids=[]	
	res=self.create_purchase_order()
	context.update({'request_id':obj.id, 'default_production_reqst_id':self.id, 'default_contract_id':obj.contract_id.id, 
                      'default_half_purchase':True,'default_production_rqst_date':self.request_date, 
                       })
	#self._with_context=context
        mrp_id=self.env['mrp.production'].with_context({'request_id':obj.id}).create({'request_line':obj.id, 'date_planned':date.today(),
                                                 'requisition_id':obj.n_po_number.id})
	mrp_id.product_qty=self.total_qty
        status_list=[]
	search_id=self.env['sale.order.line.status'].search([('n_string','=','production_request')],limit=1) ## remove status
	if search_id:
		status_list.append((3,search_id.id))
	new_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1)	#add status
	if new_id:
		status_list.append((4,new_id.id))
	if self.line_id:
		self.line_id.n_status_rel = status_list
        mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.production',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
		    'res_id':mrp_id.id,
                    'target': 'current',
                    'context': context,
             }

class ProductionRequestColor(models.Model):
    _name='production.request.colour'
    name=fields.Char('Name')
class ProductionRequestwidth(models.Model):
    _name='production.request.width'
    name=fields.Char('Name')
class ProductionRequestlength(models.Model):
    _name='production.request.length'
    name=fields.Char('Name')
class ProductionRequestthickness(models.Model):
    _name='production.request.thickness'
    name=fields.Char('Name')
class ProductionRequesttreatment(models.Model):
    _name='production.request.treatment'
    name=fields.Char('Name')
class ProductionRequesttype(models.Model):
    _name='production.request.type'
    name=fields.Char('Name')
class ProductionRequestcore(models.Model):
    _name='production.request.core'
    name=fields.Char('Name')
class ProductionRequestavgweight(models.Model):
    _name='production.request.avg.weight'
    name=fields.Char('Name')
class ProductionRequestavgappearance(models.Model):
    _name='production.request.appearance'
    name=fields.Char('Name')
class ProductionRequestavgstrength(models.Model):
    _name='production.request.strength'
    name=fields.Char('Name')
class ProductionRequestavgsealing(models.Model):
    _name='production.request.sealing'
    name=fields.Char('Name')
class ProductionRequestavgcuttingprocess(models.Model):
    _name='production.request.cut.process'
    name=fields.Char('Norder_idame')
class ProductionRequestavgcuttingsize(models.Model):
    _name='production.request.cut.size'
    name=fields.Char('Name')
class ProductionRequestavgprintmark(models.Model):
    _name='production.request.print.mark'
    name=fields.Char('Name')
class ProductionRequestavgprintcolor(models.Model):
    _name='production.request.print.color'
    name=fields.Char('Name')
    
class ProductionRequestavgartcolor(models.Model):
    _name='production.request.art.color'
    name=fields.Char('Name')

# Code to send Purchase request from 
    
class StockPurchaseRequest(models.Model):
    _name='stock.purchase.request'
    _inherit=['mail.thread']

    name=fields.Char('Name')
    delivery_id=fields.Many2one('stock.picking', 'Delivery No.')
    production_id=fields.Many2one('mrp.production', 'Manufacturing No.')
    product_id=fields.Many2one('product.product', 'Product Name')
    p_request_line_ids=fields.One2many('stock.purchase.request.line', 'purchase_request_id', 'Request Lines')
    p_required_qty=fields.Float('Required Qty',compute='p_total_qty')
    p_state=fields.Selection([('draft','Requested'),('requisition','Purchase Requisition'), ('reject','Rejeted'),('done','Done')], string='Status', default='draft')    
    requisition_id=fields.Many2one('purchase.requisition', 'Purchase Requisition No.')
    
    @api.multi
    def done_sate(self):
        self.state ='done'
        
    @api.multi
    @api.depends('p_request_line_ids.select_bool')
    def p_total_qty(self):
       for rec in self:
           for record in rec.p_request_line_ids:
               if record.select_bool and not record.supplier:
                  record.purchase_request_id.p_required_qty += record.qty
    
    @api.multi
    def create_purchaserequisition(self):
        for record in self:
            requs_date=self.env['purchase.requisition']
            requisition=0
            if not record.p_request_line_ids: #not record.p_required_qty or :
               raise UserError(_("Please Select atleast one product lines...."))
            else:
               purchase=False
               vals={}
               for line_val in record.p_request_line_ids:
                   if not purchase:
                      user=self.env['hr.employee'].search([('user_id','=',line_val.user_pr_id.create_uid.id)], limit=1)
                      if line_val.supplier:
                         purchase=self.env['purchase.order'].create({'partner_id':line_val.supplier.id,
                       'new_schedule_date':line_val.user_pr_id.date_planned, 'employee_id':user.id})
                   if  line_val.supplier and line_val.select_bool:
                       line=self.env['purchase.order.line'].create({'product_id':line_val.product_id.id, 'order_id':purchase.id, 'product_uom':line_val.uom_id.id, 'price_unit':0.0,'product_qty':line_val.qty,
                             'name':'test','date_planned':line_val.required_date})
                       line_val.select_bool=False
                       line_val.purchase_id=purchase.id
                       line_val.user_pr_id.state='in_purchase'
                   else:
		       requ_search=requs_date.search([('purchase_request_id','=',record.id),('state','=','draft')], limit=1)
		       if requ_search: 
		          requisition=requ_search
		          for reqst in requ_search.line_ids:
		              reqst.product_qty = reqst.product_qty + record.p_required_qty
		          
		       else:
		           res=requs_date.create({'origin':record.name, 
		                        #'ordering_date':, 'schedule_date':,
		                        'line_ids': [(0, 0, {
						'product_id': record.product_id.id,
		                                
						'product_qty': record.p_required_qty,
						'product_uom_id': record.p_request_line_ids[0].uom_id.id
						})],
		                              })
		           requisition=res 
		       record.p_state = 'requisition'
		       record.requisition_id=requisition.id
		       requisition.purchase_request_id=record.id                
		       for line in record.p_request_line_ids:
                           if not line.supplier:
				   requisition.pr_request_date=line.required_date
				   requisition.m_production_id=line.production_id.id

				   if line.select_bool:
				      line.requisition_id=requisition.id
				      line.select_bool=False
				      body='<b>Purchase Requisiton created for Products:  </b>'
				      body +='<ul><li> Purchase Requisiton No. : '+str(requisition.name) +'</li></ul>'
				      body +='<ul><li> Purchase Request No. : '+str(record.name) +'</li></ul>'
				      body +='<ul><li> Delivery No. : '+str(line.delivery_id.name) +'</li></ul>'
				      body +='<ul><li> Manufacturing No. : '+str(line.production_id.name) +'</li></ul>'
				      body +='<ul><li> Product Name : '+str(record.product_id.name) +'</li></ul>'
				      body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
				      body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
				      requisition.message_post(body=body)
				      line.delivery_id.message_post(body=body)
				      line.production_id.message_post(body=body)
				      record.message_post(body=body)
    @api.model
    def create(self, vals):
       if not vals.get('name'):
          vals['name'] = self.env['ir.sequence'].next_by_code('stock.purchase.request') or 'New'
       result = super(StockPurchaseRequest, self).create(vals)
       return result
       
    @api.multi
    def rejectstate(self):
        self.p_state = 'reject'
        
class StockPurchaseRequestLine(models.Model):
    _name='stock.purchase.request.line'
    
    product_id=fields.Many2one('product.product', string='Product')
    qty=fields.Float('Quantity')
    uom_id=fields.Many2one('product.uom', string="Unit")
    select_bool=fields.Boolean('Select')
    delivery_id=fields.Many2one('stock.picking', 'Delivery No.')
    production_id=fields.Many2one('mrp.production', 'Manufacturing No.')
    
    purchase_request_id=fields.Many2one('stock.purchase.request', 'Request No.')
    p_state=fields.Selection([('draft','Requested'),('requisition','Purchase Requisition'), ('reject','Rejeted'),('done','Done')], string='Status', )
    name=fields.Char()
    requisition_id=fields.Many2one('purchase.requisition', 'Purchase Requisition No.')
    required_date=fields.Datetime('Required Date')
    supplier = fields.Many2one('res.partner',string='Supplier')  
    description=fields.Char('Description') 
    purchase_id=fields.Many2one('purchase.order', string='Purchase Order No.')
    user_pr_id=fields.Many2one('user.purchase.request', string='User Purchase Request No.')

    '''@api.multi
    @api.onchange('product_id')
    def product_check(self):
        for record in self:
            if record.product_id:
               rq_data=self.env['stock.purchase.request']
               reqst_search=rq_data.search([('product_id','=',record.product_id.id ), ('p_state','in',('draft','requisition'))], limit=1)
               if reqst_search:
                  line=self.env['stock.purchase.request.line'].create({'product_id':record.product_id.id,
				          'qty':record.qty, 'uom_id':record.uom_id.id, 'supplier':record.supplier.id,
                                           'description':record.description,
				           'required_date':record.required_date,'purchase_request_id':reqst_search.id})
                  print"______-----------------------",reqst_search, line, record.id, self._origin.id
               #res=self.env['stock.purchase.request.line'].browse(self._origin.id)  
               #print"_-----------------",res
               #res.unlink()
               #return { 'type': 'ir.actions.client', 'tag': 'reload', } '''
                  
    @api.multi
    def select(self):
        for record in self:
            record.select_bool =True
           # record.purchase_request_id.p_required_qty += record.qty
           # return{'res_model': 'stock.purchase.request.to.reload'}
           
    @api.multi
    def notselect(self):
        for record in self:
            record.select_bool =False
            #record.purchase_request_id.p_required_qty -= record.qty
            #pass
            
class PurchaseMilestonePaymentTerm(models.Model):
    _name='purchase.milestone.payment.term'      
    
    value=fields.Float('Value')
    term_name_id=fields.Many2one('purchase.milestone.payment.term.name','Name')
    purchase_id=fields.Many2one('purchase.order', string='Purchase Order No.')  
    done_ok=fields.Boolean('Status')
    
    @api.multi
    def payment_done(self):
        for record in self:
            if record.purchase_id.invoice_ids and not record.done_ok:
               amount1=(record.purchase_id.amount_total *record.value)/100
               amount=(record.purchase_id.amount_total *record.value)/100
               for invoice in record.purchase_id.invoice_ids:
                   amount +=invoice.payable_amount	
                   invoice.date_due=date.today()			
                   invoice.write({'payable_amount':(amount),
                    'payable_discount':"Due Amount:"})
               self.done_ok=True
               email_to=''
               group_id = self.env.ref('account.group_account_manager', False)
               if group_id:
                  user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', [group_id.id])])
               if user_ids:
                  email_to = ''.join([user.partner_id.email + ',' for user in user_ids])
                  email_to = email_to[:-1]
               body='<b>Milestone Payment Done Request:</b>'
               body +='<ul><li> Purchase Order No.    : '+str(record.purchase_id.name) +'</li></ul>'
               body +='<ul><li> Vendor  Name. : '+str(record.purchase_id.partner_id.name or record.purchase_id.partner_id.parent_id.name) +'</li></ul>'
               body +='<ul><li> Done By  : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li> Done Date      : '+str(date.today()) +'</li></ul>' 
               body +='<ul><li> Done Amount     : '+str(amount1) + " " +str(record.purchase_id.currency_id.name)+'</li></ul>'
               template_ids = self.env.ref('gt_order_mgnt.email_template_for_milestone_payment')
               template_ids.write({'body_html':body})
               if template_ids:
                  values = template_ids.generate_email(record.purchase_id.id)
                  values['email_to'] = email_to
                  mail_mail_obj = self.env['mail.mail']
                  msg_id = mail_mail_obj.create(values) 
                  msg_id.send()
    '''@api.multi
    def write(self,vals):
        res=super(PurchaseMilestonePaymentTerm, self).write(vals)
    	for rec in self:
            if vals.get('done_ok'):
               body='<b>Payment Term confirmed</b>'
               body +='<ul><li> Term Name  : '+str(rec.term_name_id.name) +'</li></ul>'
               body +='<ul><li> Value  : '+str(rec.value) +'%</li></ul>'
	       body +='<ul><li> Done By  : '+str(self.env.user.name) +'</li></ul>'
	       body +='<ul><li> Done Date      : '+str(date.today()) +'</li></ul>'
               rec.purchase_id.message_post(body=body)
    	return res'''
    	
class PurchaseMilestonePaymentTermName(models.Model):
    _name='purchase.milestone.payment.term.name' 
    
    name=fields.Char('Name')
   

class PurchaseOrdercancel(models.Model):
    _name='purchase.order.cancel'
  
    po_reason=fields.Text('Remarks')
    document=fields.Binary('Document',default=False,attachment=True)
    document_name=fields.Char()

    @api.multi
    def resend_mail(self):
        for record in  self:
            obj=self.env['purchase.order'].browse(self._context.get('active_id'))
            res=obj.pending_send_mail()
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
		'model': 'purchase.order',
		'view_type': 'form',
		'id': obj.id,
		}
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,obj.name)
            body='<b>Purchase Order Resent For Approval Required  </b>'
            body +='<ul><li> Purchase Order No.    : '+str(text_link) +'</li></ul>'
            body +='<ul><li> Vendor  Name. : '+str(obj.partner_id.name or obj.partner_id.parent_id.name) +'</li></ul>'
            body +='<ul><li> Total Amount : '+str(obj.amount_total) +str(obj.currency_id.name)+'</li></ul>'
            body +='<ul><li> Sent By  : '+str(self.env.user.name) +'</li></ul>'
            body +='<ul><li> Sent Date      : '+str(date.today()) +'</li></ul>' 
            body +='<ul><li> Requested By  : '+str(obj.employee_id.name if obj.employee_id else 'NA')  +'</li></ul>'
            body +='<ul><li> Remarks  : '+str(self.po_reason)  +'</li></ul>'
            res.write({'body_html':body, 'subject':'API-ERP PO Resend Alert:Purchase Order Resent For Approval Required:  '+str(obj.name)})
            res.mail_message_id.write({'body':body})
        
 
    @api.multi
    def force_confirm(self):
        attachment=[]
        for record in self.env['purchase.order'].browse(self._context.get('active_id')):
            if not record.approve_mgnt:
		   record.approve_mgnt=True
		   record.approved_msg1="Force Approved By "+" "+str(self.env.user.name) +' '+str(date.today()) 
		
            if not record.approve_inv:
		   record.approve_inv=True
		   record.approved_msg3="Force Approved By "+" "+str(self.env.user.name) + ' '+str(date.today()) 

            if not record.approve_prq:
		   record.approve_prq=True
		   record.approved_msg2="Force Approved By "+" "+str(self.env.user.name) + ' '+str(date.today())
            if self.document:
               attachment.append((self.document_name,self.document))
            body="Purchase Order Force Approved"
            body +='<li>Force Approved By - :'+str(self.env.user.name)+'</li>'
            body +='<li>Approved Date - :'+str(date.today())+'</li>'
            body +='<li>Remark - :'+str(self.po_reason)+'</li>'
            record.message_post(body=body, attachments=attachment)
            record.state='to approve'

    @api.multi
    def approve_puchase_order(self):
        for record in self.env['purchase.order'].browse(self._context.get('active_id')): 
            user_login=record.create_uid.login
            if record.management_user.id == self.env.user.id: 
               record.approve_mgnt=True
               record.approved_msg1="Approved By"+" "+str(record.management_user.name)+ " "+str(date.today()) 
            if record.procurement_user.id == self.env.user.id: 
               record.approve_prq=True
               record.approved_msg2="Approved By "+" "+str(record.procurement_user.name)+ " "+str(date.today())
            if record.inventory_user.id == self.env.user.id: 
               record.approve_inv=True
               record.approved_msg3="Approved By "+" "+str(record.inventory_user.name)+ " "+str(date.today())
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
		'model': 'purchase.order',
		'view_type': 'form',
		'id': record.id,
		}
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
            body='<b>Purchase Order Details:</b>'
            body +='<ul><li> Purchase Order No.    : '+str(text_link) +'</li></ul>'
            body +='<ul><li> Vendor  Name. : '+str(record.partner_id.name or record.partner_id.parent_id.name) +'</li></ul>'
            body +='<ul><li> Requested By  : '+str(record.employee_id.name if record.employee_id else 'NA') +'</li></ul>'
            body +='<ul><li> Approved By  : '+str(self.env.user.name) +'</li></ul>'
            body +='<ul><li> Approved Date      : '+str(date.today()) +'</li></ul>' 
            body +='<ul><li> Remark      : '+str(self.po_reason) +'</li></ul>' 
            if record.approve_inv and record.approve_mgnt and record.approve_prq:
               record.write({'state':'to approve'})
            template_ids = self.env.ref('gt_order_mgnt.email_template_for_purchase_approved')
            template_ids.write({'body_html':body,'subject':'API-ERP PO Apporved Alert:Purchase Order:'+ " "+str(record.name)+ " -"+'Approved'})
            if template_ids:
               values = template_ids.generate_email(record.id)
               values['email_to'] = user_login
               mail_mail_obj = self.env['mail.mail']
               msg_id = mail_mail_obj.create(values) 
               msg_id.send()
        return True

    @api.multi
    def reject_puchase_order(self):
        for record in self.env['purchase.order'].browse(self._context.get('active_id')): 
            user_login=record.create_uid.login
            record.state='rejected'
            if record.management_user.id == self.env.user.id: 
               record.approve_mgnt=True
               record.approved_msg1="Rejected By"+" "+str(record.management_user.name)+ " "+str(date.today()) 
            if record.procurement_user.id == self.env.user.id: 
               record.approve_prq=True
               record.approved_msg2="Rejected By "+" "+str(record.procurement_user.name)+ " "+str(date.today())
            if record.inventory_user.id == self.env.user.id: 
               record.approve_inv=True
               record.approved_msg3="Rejected By "+" "+str(record.inventory_user.name)+ " "+str(date.today())
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
		'model': 'purchase.order',
		'view_type': 'form',
		'id': record.id,
		}
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
            body='<b>Purchase Order Details:</b>'
            body +='<ul><li> Purchase Order No.    : '+str(text_link) +'</li></ul>'
            body +='<ul><li> Vendor  Name. : '+str(record.partner_id.name or record.partner_id.parent_id.name) +'</li></ul>'
            body +='<ul><li> Requested By  : '+str(record.employee_id.name if record.employee_id else 'NA') +'</li></ul>'
            body +='<ul><li> Rejected By  : '+str(self.env.user.name) +'</li></ul>'
            body +='<ul><li> Rejected Date      : '+str(date.today()) +'</li></ul>' 
            body +='<ul><li> Remark      : '+str(self.po_reason) +'</li></ul>'
            
            template_ids = self.env.ref('gt_order_mgnt.email_template_for_purchase_approved')
            template_ids.write({'body_html':body,'subject':'API-ERP PO Reject Alert:Purchase Order:'+ " "+str(record.name)+ " - "+'   Rejected'})
            record.sent_mail=False
            if template_ids:
               values = template_ids.generate_email(record.id)
               values['email_to'] = user_login
               mail_mail_obj = self.env['mail.mail']
               msg_id = mail_mail_obj.create(values) 
               msg_id.send()
               
        return True
            
