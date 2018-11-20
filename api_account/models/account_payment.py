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
import json
from openerp.tools import float_is_zero

from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit='account.invoice'

    payment_documents = fields.One2many('payment.receipt.documents','invoice_id','Product Name')
    @api.one
    def _get_outstanding_info_JSON(self):
        check=super(AccountInvoice,self)._get_outstanding_info_JSON()
        self.env.cr.execute("select payment_id from account_invoice_payment_rel where invoice_id="+str(self.id) )
    	pay_inv_rel_id=self.env.cr.fetchone()
        print "pay_inv_rel_idpay_inv_rel_id",pay_inv_rel_id
        if pay_inv_rel_id:
            pay_id=self.env['account.payment'].browse(pay_inv_rel_id[0])
            bill_line_vals,pick_ids,vals,rec_ids=[],[],{},[]
            if self.picking_ids:
                if pay_id.bill_line:
                    bill_ids=[x.bill_id.id for x in pay_id.bill_line]
                    print "bill_idsbill_ids",bill_ids
                    if self.id in bill_ids:
                        line_id=self.env['payment.bill.line'].search([('bill_id','=',self.id)])
                        rec_ids=[x.receiving_id.id for x in line_id]
                for each_pick in self.picking_ids:
                    if each_pick.id not in rec_ids:
                        pick_ids.append(each_pick.id)
                        vals={'receiving_id':[(4, pick_ids)]}
                        vals.update({'bill_id':self.id,'payterm_id':self.payment_term_id.id})
                        print "val------------------------",vals
                        bill_line_vals.append((0,0,vals))
                        pay_id.write({'bill_line':bill_line_vals})
        return check
            
class PaymentDocuments(models.Model):
    _name = "payment.receipt.documents"
	
    invoice_id = fields.Many2one('account.invoice', 'Invoice Name')
    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    name=fields.Char('Name')
    amount=fields.Float('Paid Amount')	
		
class accountPayment(models.Model):
    _inherit='account.payment'

    uploaded_document = fields.Binary(string='Uploaded Document', default=False , attachment=True)
    uploaded_document_tt = fields.Many2many('ir.attachment','bill_attachment_pay_rel','bill','pay_id','Upload TT Docs',copy=False,track_visibility='always')
    bank_id = fields.Many2one('res.partner.bank', 'Bank Name',track_visibility='always',copy=False)

    send_ftr_req=fields.Boolean(string="FTR Sent",default=False,copy=False)
    doc_name=fields.Char()
    payment_method = fields.Selection([('neft', 'Fund Transfer'),
				    ('cheque', 'Cheque')],string='Type',track_visibility='always',copy=False)
    pay_p_up = fields.Selection([('post', 'Done'),
				    ('not_posted', 'Pending')],copy=False,string='Transfer Status',track_visibility='always')
    chq_s_us = fields.Selection([('signed', 'Signed'),
				    ('not_signed', 'Not Signed')],copy=False,string='Cheque Signed/Unsigned',track_visibility='always')
				    
    cheque_details = fields.One2many('bank.cheque.details','payment_id','Cheque Details')
    pay_type = fields.Selection([('sale', 'Sale'),
				    ('purchase', 'Purchase'),
				    ('cash', 'Cash'),
				    ('bank', 'Bank'),
				    ('general', 'Miscellaneous')],related='journal_id.type',track_visibility='always')
    user_id = fields.Many2one('res.users', 'Reconcile By')
    cheque_status=fields.Selection([('not_clear','Not Cleared'),('cleared','Cleared')], string='Cheque Status',track_visibility='always')
#    mail_details=fields.Text('Fund Details',copy=False)
    mail_details = fields.Html('Fund Details',copy=False)

    uploaded_proof = fields.Many2many('ir.attachment','pay_attachment_fund_rel','fund_id','pay_id','Payment Proof',copy=False)
    internal_note_tt=fields.Text('Any remarks after transfer',track_visibility='always',copy=False)
    internal_request_tt=fields.Text('Note to write on transfer',track_visibility='always',copy=False)
    bill_line = fields.One2many('payment.bill.line','payment_id','Bill/Receiving Details')

    
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

    @api.multi
    def cancel(self):
        check=super(accountPayment,self).cancel()
        if self.cheque_details:
            for each_chq in self.cheque_details:
                each_chq.unlink()
        if self.expense_id:
            self.expense_id.with_context({'call_from_pay':True}).cancel_expense()
        return check
    @api.onchange('payment_method')
    def pay_method_onchange(self):
        print "dsfhdsjf========================"
    	if self.payment_method and self.payment_method=='neft' and self.payment_type=='outbound':
            self.pay_p_up='not_posted'
        else:
            self.pay_p_up=''

#    	if self.payment_method and self.payment_method=='cheque':
#            self.payment_method_code='check_printing'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            bank_id=self.env['res.partner.bank'].search([('partner_id','=',self.partner_id.id),('active_account','=',True)])
            if len(bank_id)==1:
                self.bank_id=bank_id.id
    
#    adding company domain on change of payment type
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if not self.invoice_ids:
            # Set default partner type for the payment type
            self.payment_method=False
            self.journal_id=False
            self.bank_id=False
            self.chq_s_us=''
            self.pay_p_up=''
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
    def sign_check(self):
        self.write({'chq_s_us':'signed'})
        
    @api.multi
    def post_funds(self):
        confirm_form = self.env.ref('api_account.fund_transfer_approve_wiz_form', False)
        print "confirm_formconfirm_formconfirm_form",confirm_form
        return {
                        'name':'Post Transfer Request',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'fund.transfer.approve',
                        'views': [(confirm_form.id, 'form')],
                        'view_id': confirm_form.id,
                        'target': 'new'
                    }
        
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
                        'target': 'new'
                    }
        return True
    
    @api.multi
    def post(self):
        check=super(accountPayment,self).post()
    	for res in self:
                if res.payment_type=='outbound' and res.journal_id.type=='cash':
                    res.write({'pay_p_up':'post'})
                if res.pay_p_up and res.pay_p_up=='not_posted' and res.payment_type=='outbound':
                    print "res.invoice_idsres.invoice_ids",res.invoice_ids
                    if res.invoice_ids:
                        for each_inv in res.invoice_ids:
                            bill_line_vals,pick_ids,vals=[],[],{}

                            if each_inv.picking_ids:
                                for each_pick in each_inv.picking_ids:
                                    pick_ids.append(each_pick.id)
                                vals={'receiving_id':[(4, pick_ids)]}
                            vals.update({'bill_id':each_inv.id,'payterm_id':each_inv.payment_term_id.id})
                            bill_line_vals.append((0,0,vals))
                            bill_line=res.write({'bill_line':bill_line_vals})
                            print "bill_linebill_linebill_line",bill_line
                    print "res.bank_id.partner_id.id",res.bank_id.partner_id.id,res.partner_id.id
                    if res.bank_id and res.bank_id.partner_id.id!=res.partner_id.id:
                        raise UserError(_("Bank selected in Payment should have same Partner defined!!"))

                    wiz_id = self.env['fund.transfer.wizard'].create({'mail_details':''})
                    print "wiz_idwiz_idwiz_id",wiz_id
                    wiz_id.with_context({'active_ids':res.id}).send_mail()
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
	return check
    
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
    @api.onchange('cheque_status')
    def cheque_statuss_onchange(self):
    	if self.cheque_status and self.cheque_status=='cleared':
            self.chq_s_us='signed'
            
class PaymentBillLine(models.Model):
    _name = 'payment.bill.line'
    
    payment_id = fields.Many2one('account.payment', 'PaymentID')
    bill_id = fields.Many2one('account.invoice', 'Bill ID')
    payterm_id = fields.Many2one('account.payment.term', 'Payterm ID')
#    receiving_date = fields.Date(string='Receiving Date')
    receiving_id = fields.Many2many('stock.picking','picking_bill_line_rel','pick','bill_line_id','Receiving IDS',copy=False,track_visibility='always')

	
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
    		   			   			
