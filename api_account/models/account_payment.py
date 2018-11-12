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
from datetime import datetime,date,timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
from urlparse import urljoin
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit='account.invoice'

    payment_documents = fields.One2many('payment.receipt.documents','invoice_id','Product Name')

class PaymentDocuments(models.Model):
    _name = "payment.receipt.documents"
	
    invoice_id = fields.Many2one('account.invoice', 'Invoice Name')
    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    name=fields.Char('Name')
    amount=fields.Float('Paid Amount')	
		
class accountPayment(models.Model):
    _inherit='account.payment'

#    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    uploaded_document = fields.Many2many('ir.attachment','bill_attachment_pay_rel','bill','pay_id','Upload Document')
    bank_id = fields.Many2one('res.partner.bank', 'Bank Name',track_visibility='always')

    send_ftr_req=fields.Boolean(string="FTR Sent",default=False)
    doc_name=fields.Char()
    payment_method = fields.Selection([('neft', 'Fund Transfer'),
				    ('cheque', 'Cheque')],string='Type',track_visibility='always')
    pay_p_up = fields.Selection([('post', 'Posted'),
				    ('not_posted', 'Not Posted')],string='Fund Posted/Unposted',track_visibility='always')
    chq_s_us = fields.Selection([('signed', 'Signed'),
				    ('not_signed', 'Not Signed')],string='Cheque Signed/Unsigned',track_visibility='always')
				    
    cheque_details = fields.One2many('bank.cheque.details','payment_id','Cheque Details')
    pay_type = fields.Selection([('sale', 'Sale'),
				    ('purchase', 'Purchase'),
				    ('cash', 'Cash'),
				    ('bank', 'Bank'),
				    ('general', 'Miscellaneous')],related='journal_id.type',track_visibility='always')
    user_id = fields.Many2one('res.users', 'Reconcile By')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status',track_visibility='always')
    
#    @api.multi
#    def button_invoices(self):
#        if self.payment_type=='outbound':
#            
#            tree_view = self.env.ref('account.invoice_supplier_tree', False)
#            form_view = self.env.ref('account.invoice_supplier_form', False)
#        if self.payment_type=='inbound':
#            tree_view = self.env.ref('account.invoice_tree', False)
#            form_view = self.env.ref('account.invoice_form', False)
#            print "form_viewform_viewform_view",form_view
#
#        return {
#            'name': _('Paid Invoices'),
#            'view_type': 'form',
#            'view_mode': 'tree',
#            'res_model': 'account.invoice',
#            'views': [(tree_view.id,'tree'),(form_view.id, 'form')],
#            'view_id': tree_view.id,
#            'type': 'ir.actions.act_window',
#            'domain': [('id', 'in', [x.id for x in self.invoice_ids])],
#        }


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            bank_id=self.env['res.partner.bank'].search([('partner_id','=',self.partner_id.id)])
            if bank_id:
                self.bank_id=bank_id.id
    
#    adding company domain on change of payment type
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        # Set payment method domain
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}

        res['domain']['journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        if self._context.get('active_model')=='account.invoice':
            obj = self.env['account.invoice'].browse(self._context.get('active_id'))
            res['domain']['journal_id'].append(('company_id', '=', obj.company_id.id))
        return res
    @api.multi
    def post_funds(self):
        
        self.write({'pay_p_up':'post'})
    @api.multi
    def send_fund_tfr_req(self):
        cofirm_form = self.env.ref('api_account.fund_transfer_wiz_form', False)
        if cofirm_form:
            return {
                        'name':'Fund Transfer Request Details',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'fund.transfer.wizard',
                        'views': [(cofirm_form.id, 'form')],
                        'view_id': cofirm_form.id,
                        'target': 'new',
                        'context':{'force_confirm':True}
                    }
        return True
    
    @api.multi
    def post(self):
    	for res in self:
    		amount=res.amount
    		if res.pay_type =='bank' and res.payment_method =='cheque':
    			n_amount=0
    			for line in res.cheque_details:
    				n_amount += line.amount
    				if line.cheque_date < str(datetime.today()-timedelta(days=180)):
    					raise UserError(_("Cheque date older than six month can't be accepted."))
				
    			#if n_amount != amount :
    			#	raise UserError(_("total of cheque amount is not equals to Payment amount"))
		if res.payment_method !='cheque' and res.cheque_details:
			res.cheque_details=[]
        obj = self.env['account.invoice'].browse(self._context.get('active_id'))
        if obj and self.uploaded_document and not self.sale_id:
		res=self.env['payment.receipt.documents'].create({'invoice_id':obj.id,
								'uploaded_document':self.uploaded_document,
								'name':self.communication, 'amount':self.amount})
	return super(accountPayment,self).post()
    
    @api.onchange('cheque_details')
    def amount_change(self):
   	for record in self:
   		if record.pay_type =='bank' and record.payment_method=='cheque':
	    		amount = 0.0
	    		for line in record.cheque_details:
	    			if line.id != record.id:
	    				amount += line.amount
			if amount:
				record.amount = amount 

    @api.onchange('pay_type')
    def pay_type_onchange(self):
    	if self.pay_type != 'bank':
    		self.payment_method=False
	
class BankChequeDetails(models.Model):
    '''to store cheque details against bank'''
    _name = "bank.cheque.details"
    
    payment_id = fields.Many2one('account.payment','Payment Name')
    journal_id = fields.Many2one('account.journal',related="payment_id.journal_id",string='Journal')
    partner_id = fields.Many2one('res.partner',related="payment_id.partner_id",string='Supplier/Customer')
    bank_name = fields.Many2one('cheque.bank.name','Bank Name')
    communication = fields.Char(related="payment_id.communication",string='Internal Note',track_visibility='always')
    cheque_no = fields.Char('Cheque No.',track_visibility='always')
    cheque_date = fields.Date('Cheque Date',track_visibility='always')
    branch_name = fields.Char('Bank Branch Name',track_visibility='always')
    amount = fields.Float('Amount')
    reconcile_date = fields.Date('Reconcile Date',track_visibility='always')
    register_payment_id=fields.Many2one('account.register.payments')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')],related="payment_id.cheque_status", string='Cheque Status')
    
class ChequeBankName(models.Model):
    '''to store cheque details against bank'''
    _name = "cheque.bank.name"
    		   	
    name = fields.Char('Name')		   	
    		   			   			
