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
from datetime import datetime,date
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
from urlparse import urljoin
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class BankReconcilation(models.Model):
    '''temporary Main table for bank cheque details'''
    _name = "bank.reconcilation"
    
    name= fields.Char(string='Name', default='Bank Reconcilation')
    reconcile_pending = fields.One2many('bank.reconcilation.line','reconcile_id','Cheque Details')
    reconcile_complete = fields.One2many('bank.reconcilation.line','reconcile_id','Cheque Details')
    partner_id = fields.Many2one('res.partner','Customer Name',domain=[('company_type','=','company')],help="Customer/Suppler Name")
    
    #bank_id = fields.Many2one('res.partner.bank', 'Bank Name')
    bank_name = fields.Many2one('cheque.bank.name', 'Bank Name',help='Customer Bank names')

    cheque_no = fields.Char('Cheque No.')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    status = fields.Selection([('pending','Pending'),('completed','Completed')],string="Status")
    cheque_type = fields.Selection([('internal','Internal'),('receipt','Receipt'),('payment','Payment')],string="Cheque Type")
    journal_id = fields.Many2one('account.journal', 'Bank Journal',help='Company Bank names',domain=[('type', '=', 'bank')])
    
    @api.onchange('status')
    def status_onchnage(self):
    	self.env['bank.reconcilation.line'].search([('reconcile_id','=',self.id)]).unlink()
    	self.reconcile_pending=[]
    	self.reconcile_complete=[]
    	#self.search_data()
    	
    @api.multi
    def search_data(self):
    	self.env['bank.reconcilation.line'].search([('reconcile_id','=',self.id)]).unlink()
    	
    	data=[]
    	domain=[]
    	if self.partner_id:
    		domain.append(('payment_id.partner_id','=',self.partner_id.id))
	if self.bank_name:
		domain.append(('bank_name','=',self.bank_name.id))
	if self.cheque_no:
		domain.append(('cheque_no','=',self.cheque_no))
	if self.from_date:
		domain.append(('cheque_date','>=',self.from_date))
	if self.to_date:
		domain.append(('cheque_date','<=',self.to_date))
	if self.status=='pending':
		domain.append(('reconcile_date','=',False))
	if self.status=='completed':
		domain.append(('reconcile_date','!=',False))
	if self.journal_id:
		domain.append(('payment_id.journal_id','=',self.journal_id.id))

	if self.cheque_type:
		if self.cheque_type == 'receipt':
			domain.append(('payment_id.payment_type','=','inbound'))
		if self.cheque_type == 'payment':
			domain.append(('payment_id.payment_type','=','outbound'))
		if self.cheque_type == 'internal':
			domain.append(('payment_id.payment_type','=','transfer'))
			
    	search_data = self.env['bank.cheque.details'].search(domain)
    	for rec in search_data :
    		data.append((0,0,{'partner_id':rec.payment_id.partner_id.id,'bank_name':rec.bank_name,
    					'cheque_no':rec.cheque_no,'cheque_date':rec.cheque_date,
					'reconcile_date':rec.reconcile_date,'cheque_id':rec.id, 
                                        'payment_id':rec.payment_id.id,
					'amount':rec.amount,'document':rec.payment_id.communication}))
					
    	if self.status=='pending':
    		self.reconcile_pending=data
	if self.status=='completed':
    		self.reconcile_complete=data

    @api.multi
    def reconcile(self):
    	for line in self.reconcile_pending:
    		if not line.rec_bool and line.reconcile_date:
    			line.cheque_id.reconcile_date = line.reconcile_date
    			line.rec_bool=True
    			line.cheque_id.user_id = self.env.user.id
                        if line.payment_id:
                            if all(x.reconcile_date for x in line.payment_id.cheque_details):
                            	line.payment_id.cheque_status = 'cleared'
                            if line.payment_id.sale_id:
                               line.payment_id.sale_id.advance_paid_amount="Cheque Cleared by Bank"
    	
class BankReconcilationLine(models.Model):
    '''temporary table for bank cheque details'''
    _name = "bank.reconcilation.line"
    
    reconcile_id = fields.Many2one('bank.reconcilation')
    partner_id = fields.Many2one('res.partner','Customer Name')
    #bank_id = fields.Many2one('res.partner.bank', 'Bank Name')
    bank_name = fields.Many2one('cheque.bank.name', 'Bank Name',help='Customer Bank names')
    cheque_no = fields.Char('Cheque No.')
    document = fields.Char('Interal Note')
    cheque_date = fields.Date('Cheque Date')
    amount = fields.Float('Amount')
    reconcile_date = fields.Date('Reconcile Date')
    rec_bool = fields.Boolean('Reconcile Bool')
    cheque_id = fields.Many2one('bank.cheque.details','Cheque id')
    payment_id=fields.Many2one('account.payment','Payment Details')
    
    @api.multi
    def reconcile(self):
        if not self.reconcile_date:
        	raise UserError('Please add Reconcilation Date')
    	self.cheque_id.reconcile_date = self.reconcile_date
    	self.rec_bool=True
    	self.cheque_id.user_id = self.env.user.id
        if self.payment_id:
           if all(x.reconcile_date for x in self.payment_id.cheque_details):
            		self.payment_id.cheque_status = 'cleared'
           if self.payment_id.sale_id:
              self.payment_id.sale_id.advance_paid_amount="Cheque Cleared by Bank"



