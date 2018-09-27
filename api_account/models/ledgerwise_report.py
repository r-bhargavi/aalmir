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

class LedgerwiseReport(models.Model):
    '''temporary Main table for ledgerwise details report'''
    _name = "ledgerwise.report"
    _order = 'id asc'
    
    name= fields.Char(string='Name', default='LedgerWise Report')
    ledgerwise_line = fields.One2many('ledgerwise.report.line','order_id','Ledger Details')
    ledgerwise_detailed_line = fields.One2many('ledgerwise.report.line','line_id','Ledger Details')
    ledgerwise_account_line  = fields.One2many('ledgerwise.report.line','acc_id','Ledger Details')
    report_type = fields.Selection([('detail','Detailed'),('summary','Summary')],'Report Type')
    ledger_type = fields.Selection([('customer','Customer'),('supplier','Supplier'),('ledger','General Ledger'),
    					('employee','Employees'),
    					('bank_cash','Bank & Cash'),],'Ledger Type')
    pay_type = fields.Selection([('pay_rec','Payable/Receivable'),('payable','Payable'),('receve','Receivable'),('other','Other'),('all','All')],default='pay_rec',string='Filter')
    account_id = fields.Many2one('account.account','Account')
    partner_id = fields.Many2one('res.partner','Ledger')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.user.company_id)
    
    @api.onchange('report_type')
    def report_type_onchange(self):
	self.ledger_type=False
	
    @api.onchange('ledger_type')
    def ledger_type_onchange(self):
	self.partner_id=False
	self.from_date=False
	self.to_date=False
	self.account_id=False
	if self.ledger_type =='bank_cash':
		return {'domain':{'account_id':[('user_type_id.type','=','liquidity')]}}

    @api.multi
    def find_childs_partner(self,partner_id,all_partner=[]):
	#all_partner=[partner_id.id]
	partners_ids = self.env['res.partner'].search([('parent_id','=',partner_id.id)])
	if not partners_ids:
		return [partner_id.id]
	for child in partners_ids:
		child_partners = self.env['res.partner'].search([('parent_id','=',child.id)])
		all_partner.append(child.id)
		if child_partners:
			all_partner + self.find_childs_partner(child,all_partner)
	return all_partner

    @api.multi
    def search_report(self):
    	domain=[('move_id.state','=','posted')]
    	for res in self:
    		account_move=self.env['account.move.line']
    		report_line = self.env['ledgerwise.report.line']
    		report_detail_line = self.env['ledgerwise.report.line.details']
    		account_obj=self.env['account.account']
    		if res.from_date:
    			 from_date =res.from_date
		else:
			 res.from_date='2016-07-01'
			 from_date = '2016-07-01'
			 
		if res.to_date:
    			 domain.append(('date','<=',res.to_date))
		else:
			 res.to_date = date.today()
			 domain.append(('date','<=',datetime.strftime(datetime.now(),'%Y-%m-%d')))
			 
    		if res.report_type=='detail' and res.ledger_type in ('customer','supplier'):
    			res.ledgerwise_detailed_line.unlink()
    			if not res.partner_id :
    				raise UserError("No Ledger selected")

			partner_ids=self.find_childs_partner(res.partner_id,[res.partner_id.id])
			partner=('partner_id','in',partner_ids)
			# code to find openig balance of customre>>
			opeing_records=account_move.search([partner,('date','<',from_date),('account_id.user_type_id.type','in',('receivable','payable')),('move_id.state','=','posted')],order='date asc')
			opening_balance={}
			opening_bal=0.0
			for line in opeing_records:
				if line.credit and line.account_id.user_type_id.type in ('receivable','payable'):
					opening_bal -= line.credit
				elif line.debit:
					opening_bal += line.debit

			report_line.create({'narration':'OPENING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})	
			#<<<<
			domain.extend([partner,('date','>=',from_date),('account_id.user_type_id.type','in',('receivable','payable'))])

			# code to find transaction records >>>
			line_ids=self.env['account.move.line'].search(domain,order='date asc')
			for records in line_ids:
				invoice=self.env['account.invoice'].search([('move_id','=',records.move_id.id)])
				po_number=','.join([i.lpo_number for i in invoice.document_id])
				if records.credit and records.account_id.user_type_id.type in ('receivable','payable'):
					opening_bal -= records.credit
					report_line.create({'date':records.date,
							'account':records.account_id.id,
							'journal':records.journal_id.id,
							'po_number':po_number,
							'narration':records.name if len(records.name)>2 else records.move_id.name,
							'credit_amount':records.credit if records.credit else 0.0,
							'debit_amount':records.debit if records.debit else 0.0,
							'amount':opening_bal,
							'move':records.move_id.id,
							'line_id':res.id})
				if records.debit:
					opening_bal += records.debit
					report_line.create({'date':records.date,
							'account':records.account_id.id,
							'journal':records.journal_id.id,
							'po_number':po_number,
							'narration':records.name if len(records.name)>2 else records.move_id.name,
							'credit_amount':records.credit if records.credit else 0.0,
							'debit_amount':records.debit if records.debit else 0.0,
							'amount':opening_bal,
							'move':records.move_id.id,
							'line_id':res.id})
			# <<<
			#Closig Balance
			report_line.create({'narration':'CLOSING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})	
		
    		elif res.report_type=='detail' and res.ledger_type =='employee':
    			res.ledgerwise_detailed_line.unlink()
    			if not res.partner_id :
    				raise UserError("No Ledger selected")
			partner_ids=self.find_childs_partner(res.partner_id,[res.partner_id.id])
			partner=('partner_id','in',partner_ids)
			# code to find openig balance of customre>>
			acc_id=[]
			if res.pay_type =='pay_rec':
				acc_id = account_obj.search(['|',('name','=','Employees Advances'),
						('user_type_id.type','in',('receivable','payable'))])
			elif  res.pay_type =='all':
				acc_id = account_obj.search([('user_type_id','!=',False)])
			elif res.pay_type =='payable':
				acc_id = account_obj.search([('user_type_id.type','=','receivable')])
			elif  res.pay_type =='receve':
				acc_id = account_obj.search(['|',('user_type_id.type','=','receivable'),
								('name','=','Employees Advances')])
			elif  res.pay_type =='other':
				acc_id = account_obj.search(['|',('name','!=','Employees Advances'),
						('user_type_id.type','not in',('receivable','payable'))])
			account_dom=('account_id','in',acc_id._ids)
			
			opeing_records=account_move.search([partner,account_dom,('date','<',from_date),('move_id.state','=','posted')],order='date asc')
			opening_balance={}
			opening_bal=0.0
			for line in opeing_records:
				if line.credit :
					opening_bal -= line.credit
				elif line.debit:
					opening_bal += line.debit

			report_line.create({'narration':'OPENING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})	
			#<<<<
			domain.extend([partner,account_dom,('date','>=',from_date)])

			# code to find transaction records >>>
			print "kkkkkkkkk,,",domain
			line_ids=self.env['account.move.line'].search(domain,order='date asc')
			for records in line_ids:
				invoice=self.env['account.invoice'].search([('move_id','=',records.move_id.id)])
				po_number=','.join([i.lpo_number for i in invoice.document_id])
				if records.credit :
					opening_bal -= records.credit
					report_line.create({'date':records.date,
							'account':records.account_id.id,
							'journal':records.journal_id.id,
							'po_number':po_number,
							'narration':records.name if len(records.name)>2 else records.move_id.name,
							'credit_amount':records.credit if records.credit else 0.0,
							'debit_amount':records.debit if records.debit else 0.0,
							'amount':opening_bal,
							'move':records.move_id.id,
							'line_id':res.id})
				if records.debit:
					opening_bal += records.debit
					report_line.create({'date':records.date,
							'account':records.account_id.id,
							'journal':records.journal_id.id,
							'po_number':po_number,
							'narration':records.name if len(records.name)>2 else records.move_id.name,
							'credit_amount':records.credit if records.credit else 0.0,
							'debit_amount':records.debit if records.debit else 0.0,
							'amount':opening_bal,
							'move':records.move_id.id,
							'line_id':res.id})
			# <<<
			#Closig Balance
			report_line.create({'narration':'CLOSING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})	

    		elif res.report_type=='detail' and res.ledger_type in ('ledger','bank_cash'):
    			res.ledgerwise_detailed_line.unlink()
    			if not res.account_id :
    				raise UserError("No Ledger selected")
			account=('account_id','=',res.account_id.id)
			# code to find openig balance of customre>>
			opeing_records=account_move.search([account,('date','<',from_date),('move_id.state','=','posted')],order='date asc')
			opening_bal=0.0
			un_reconcile=[]
			reconcile_lines = {}
			cheque_ids= []
			journal_currency = False
			for line in opeing_records:
				flag=True
				journal_currency = line.journal_id.currency_id or line.account_id.currency_id
				for chq in line.payment_id.cheque_details:
					flag=False # to avoid get entry amount
					if chq.id in cheque_ids:
						continue
					cheque_ids.append(chq.id)
					# unreconcile cheques in previous dates
					if not chq.reconcile_date :
							un_reconcile.append({'date':chq.cheque_date,
							'account':line.account_id.id,
							'journal':line.journal_id.id,
							'narration':line.name if len(line.name)>2 else \
										 line.move_id.name,
							'credit_amount':chq.amount if line.credit else 0.0,
							'debit_amount':chq.amount if line.debit else 0.0,
							'partner_id':line.partner_id.id,
							'move':line.move_id.id,
							'line_id':res.id})
						# get reconciled entryes from previous date
					elif chq.reconcile_date and chq.reconcile_date >= from_date and chq.reconcile_date <= res.to_date:
							reconcile_date = chq.reconcile_date
							new_li = reconcile_lines.get(reconcile_date,[])
							new_li.append({	'account':line.account_id.id,
							'journal':line.journal_id.id,
							'narration':line.name if len(line.name)>2 \
										else line.move_id.name,
							'credit_amount':chq.amount if line.credit else 0.0,
							'debit_amount':chq.amount if line.debit else 0.0,
							'move':line.move_id.id,
							'payment_date':line.date,
							'reconcile':False,
							'partner_id':line.partner_id.id})
							reconcile_lines.update({str(reconcile_date):new_li})
					elif chq.reconcile_date and chq.reconcile_date < from_date:
						opening_bal += -chq.amount if line.credit else chq.amount
				# if payment type is not cheque				
				if flag:
					opening_bal += -line.credit or line.debit
								
			report_line.create({'narration':'OPENING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})
			#<<<<
			
			domain.extend([account,('date','>=',from_date)])
			# code to find transaction records >>>
			line_ids=self.env['account.move.line'].search(domain,order='date asc')
			cheque_ids = []
			for records in line_ids:
				flag=True
				journal_currency = records.journal_id.currency_id or records.account_id.currency_id
				for chq in records.payment_id.cheque_details:
					flag=False # to avoid get entry amount
					if chq.id in cheque_ids:
						continue
					cheque_ids.append(chq.id)
					# unreconcile cheques in previouos dates
					if not chq.reconcile_date :
						un_reconcile.append({'date':chq.cheque_date,
						'account':records.account_id.id,
						'journal':records.journal_id.id,
						'narration':records.name if len(records.name)>2 \
									else records.move_id.name,
						'credit_amount':chq.amount if records.credit else 0.0,
						'debit_amount':chq.amount if records.debit else 0.0,
						'move':records.move_id.id,
						'payment_date':records.date,
						'partner_id':records.partner_id.id,
						'line_id':res.id})
						
					elif chq.reconcile_date and chq.reconcile_date <= res.to_date:
						new_li = reconcile_lines.get(chq.reconcile_date,[])
						new_li.append({	'account':records.account_id.id,
						'journal':records.journal_id.id,
						'narration':records.name if len(records.name)>2 \
									else records.move_id.name,
						'credit_amount':chq.amount if records.credit else 0.0,
						'debit_amount':chq.amount if records.debit else 0.0,
						'move':records.move_id.id,
						'payment_date':records.date,
						'partner_id':records.partner_id.id})
						reconcile_lines.update({str(chq.reconcile_date):new_li})

				# Payment is not cheque
				if flag :
					new_li = reconcile_lines.get(records.date,[])
					new_li.append({	'account':records.account_id.id,
							'journal':records.journal_id.id,
							'narration':records.name if len(records.name)>2 \
										else records.move_id.name,
							'credit_amount':records.credit if records.credit else 0.0,
							'debit_amount':records.debit if records.debit else 0.0,
							'move':records.move_id.id,
							'payment_date':records.date,
							'partner_id':records.partner_id.id})
					reconcile_lines.update({str(records.date):new_li})
			# <<<
			
			##>>> Code to Create Records in LedgerWise
			date_data = reconcile_lines.keys()
			date_data.sort()
			for order in date_data:
				data = reconcile_lines.get(order)
				for line in data:
					if line.get('credit_amount'):
						opening_bal -= line.get('credit_amount')
					elif line.get('debit_amount'):
						opening_bal += line.get('debit_amount')
					line.update({'date':str(order),'line_id':res.id,'amount':opening_bal})
					report_line.create(line)
			## <<
			
			#Closig Balance
			report_line.create({'narration':'CLOSING BALANCE',
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})
							
			if journal_currency:
				opening_bal = self.env.user.company_id.currency_id.compute(opening_bal,journal_currency)
				report_line.create({'narration':'{} Balance'.format(journal_currency.name),
							'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
							'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
							'line_id':res.id})
							
			report_line.create({'narration':'Un-Reconcile Entries',
							'credit_amount': 0.0,
							'debit_amount': 0.0,
							'line_id':res.id})

			unreconcile=0.0
			for data in un_reconcile:
				report_line.create(data)
				unreconcile -= data.get('credit_amount')
				unreconcile += data.get('debit_amount')
				
			if unreconcile:	
				report_line.create({'narration':'TOTAL Un-Reconcile',
							'credit_amount':abs(unreconcile) if unreconcile<0.0 else 0.0,
							'debit_amount':unreconcile if unreconcile>0.0 else 0.0,
							'line_id':res.id})
							
		elif res.report_type=='summary' and res.ledger_type in ('customer','supplier'):
			res.ledgerwise_line.unlink()
			partner=[]
    			if res.ledger_type=='supplier':
    				partner=[('partner_id.supplier','=',True)]
			elif res.ledger_type=='customer':
    				partner=[('partner_id.customer','=',True)]
				
			# Calculate Opening 
			opeing_records=account_move.search(partner+[('date','<',from_date),('account_id.user_type_id.type','in',('receivable','other','payable')),('move_id.state','=','posted')],order='date asc')
			opening_balance={}
			for line in opeing_records:
				if opening_balance.get(line.partner_id.id):
					if line.credit and line.account_id.user_type_id.type in ('receivable','payable'):
						opening_balance[line.partner_id.id][0] += line.credit
					elif line.debit:
						opening_balance[line.partner_id.id][1] += line.debit
				else:
					values=[0,0]
					if line.credit and line.account_id.user_type_id.type in ('receivable','payable'):
						values[0] = line.credit
					elif line.debit:
						values[1] = line.debit
					opening_balance[line.partner_id.id]=values
			#<<<
			#Calculate Closing >>>

			domain.extend(partner+[('date','>=',from_date),('account_id.user_type_id.type','in',('receivable','other','payable'))])
			closing_records = account_move.search(domain,order='date asc')
			closing_balance = {}

			for line in closing_records:
				if closing_balance.get(line.partner_id.id):
					if line.credit and line.account_id.user_type_id.type in ('receivable','payable'):
						closing_balance[line.partner_id.id][0] += line.credit
					elif line.debit:
						closing_balance[line.partner_id.id][1] += line.debit
				else:
					values=[0,0]
					if line.credit and line.account_id.user_type_id.type in ('receivable','payable'):
						values[0] = line.credit
					elif line.debit:
						values[1] = line.debit
					closing_balance[line.partner_id.id]=values

			for rec in opening_balance:
				opening = opening_balance.get(rec)[1] - opening_balance.get(rec)[0]
				closing = 0.0
				if closing_balance.get(rec):
					closing_bal = closing_balance.get(rec)[1] - closing_balance.get(rec)[0]
					closing_balance.pop(rec)
					if opening != 0.0:
						closing += closing_bal 
					else:
						closing = closing_bal 
				report_line.create({'partner_id':rec,'credit_amount':opening,
							'debit_amount':closing,'acc_id':res.id})

			if closing_balance:
				for rec1 in closing_balance:
					cl_credit = closing_balance.get(rec1)[0]
					cl_debit = closing_balance.get(rec1)[1]
					report_line.create({'partner_id':rec1,'credit_amount':0.0,
								'debit_amount':cl_debit - cl_credit,
								'acc_id':res.id})
		
		elif res.report_type=='summary' and res.ledger_type =='employee':
			res.ledgerwise_line.unlink()
			res.ledgerwise_account_line.unlink()
			partner_ids = self.env['res.partner'].search([('employee','=',True)])
			acc_id=[]
			if res.pay_type =='pay_rec':
				acc_id = account_obj.search(['|',('name','=','Employees Advances'),
						('user_type_id.type','in',('receivable','payable'))])
			elif  res.pay_type =='all':
				acc_id = account_obj.search([('user_type_id','!=',False)])
			elif res.pay_type =='payable':
				acc_id = account_obj.search([('user_type_id.type','=','receivable')])
			elif  res.pay_type =='receve':
				acc_id = account_obj.search(['|',('user_type_id.type','=','receivable'),
								('name','=','Employees Advances')])
			elif  res.pay_type =='other':
				acc_id = account_obj.search(['|',('name','!=','Employees Advances'),
						('user_type_id.type','not in',('receivable','payable'))])
			account_dom=('account_id','in',acc_id._ids)
		
			for par_rec in partner_ids:
				opeing_records=account_move.search([('partner_id','=',par_rec.id),account_dom,
							('date','<',from_date),('move_id.state','=','posted')
							],order='date asc')
				opening_bal=0.0
				for line in opeing_records:
					if line.credit :
						opening_bal -= line.credit
					elif line.debit:
						opening_bal += line.debit
				# create Record in Summary line
				rp_line = report_line.create({'partner_id':par_rec.id,'credit_amount':opening_bal,
								'order_id':res.id,'debit_amount':0.0})
				# create record in summary details line		
				report_detail_line.create({'narration':'OPENING BALANCE',
								'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
								'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
								'line_id':rp_line.id})	
				#<<<<
				newdomain=domain+[('partner_id','=',par_rec.id),account_dom,('date','>=',from_date)]

				# code to find transaction records >>>
				line_ids=self.env['account.move.line'].search(newdomain,order='date asc')
				for records in line_ids:
					invoice=self.env['account.invoice'].search([('move_id','=',records.move_id.id)])
					po_number=','.join([i.lpo_number for i in invoice.document_id])
					if records.credit :
						opening_bal -= records.credit
						report_detail_line.create({'date':records.date,
								'account':records.account_id.id,
								'journal':records.journal_id.id,
								'po_number':po_number,
								'narration':records.name if len(records.name)>2 else records.move_id.name,
								'credit_amount':records.credit if records.credit else 0.0,
								'debit_amount':records.debit if records.debit else 0.0,
								'amount':opening_bal,
								'move':records.move_id.id,
								'line_id':rp_line.id})
					if records.debit:
						opening_bal += records.debit
						report_detail_line.create({'date':records.date,
								'account':records.account_id.id,
								'journal':records.journal_id.id,
								'po_number':po_number,
								'narration':records.name if len(records.name)>2 else records.move_id.name,
								'credit_amount':records.credit if records.credit else 0.0,
								'debit_amount':records.debit if records.debit else 0.0,
								'amount':opening_bal,
								'move':records.move_id.id,
								'line_id':rp_line.id})
				# <<<
				#Closig Balance in summaryy details line
				report_detail_line.create({'narration':'CLOSING BALANCE',
								'credit_amount':abs(opening_bal) if opening_bal<0.0 else 0.0,
								'debit_amount':opening_bal if opening_bal>0.0 else 0.0,
								'line_id':rp_line.id})
				# update closing balance
				rp_line.debit_amount = opening_bal
		elif res.report_type=='summary'  and res.ledger_type in ('ledger','bank_cash'):
			res.ledgerwise_account_line.unlink()
			res.ledgerwise_line.unlink()
			domain1= [('user_type_id.type','=','liquidity')] if res.ledger_type=='bank_cash' else []
			acc_ids = self.env['account.account'].search(domain1)
			account=('account_id','in',acc_ids._ids)

			# Calculate Opening 
			opeing_records=account_move.search([account,('date','<',from_date),('move_id.state','=','posted')],order='date asc')
			account_balance = {}
			cheque_ids =[]
			for line in opeing_records:
				flag=True
				for chq in line.payment_id.cheque_details:
					flag=False
					if chq.id in cheque_ids:
						continue
					cheque_ids.append(chq.id)
					balance_dic = account_balance.get(line.account_id.id,[0,0,0])
					if not chq.reconcile_date :
						balance_dic[2] += -chq.amount if line.credit else chq.amount
					# get reconciled entryes from previous date
					elif chq.reconcile_date and chq.reconcile_date > from_date and chq.reconcile_date < res.to_date:
						
						balance_dic[1] += -chq.amount if line.credit else chq.amount
					elif chq.reconcile_date and chq.reconcile_date < from_date:
						balance_dic[0] += -chq.amount if line.credit else chq.amount
					account_balance.update({line.account_id.id:balance_dic})
				if flag:
					balance_dic = account_balance.get(line.account_id.id,[0,0,0])
					balance_dic[0] += -line.credit or line.debit
					account_balance.update({line.account_id.id:balance_dic})
			#<<<
			#Calculate Closing >>>
			domain.extend([account,('date','>=',from_date)])
			closing_records = account_move.search(domain,order='date asc')
			for line in closing_records:
				flag=True
				for chq in line.payment_id.cheque_details:
					flag=False
					if chq.id in cheque_ids:
						continue
					cheque_ids.append(chq.id)
					balance_dic = account_balance.get(line.account_id.id,[0,0,0])
					if not chq.reconcile_date :
						balance_dic[2] += -chq.amount if line.credit else chq.amount
					# get reconciled entryes from previous date
					elif chq.reconcile_date and chq.reconcile_date < res.to_date:
						
						balance_dic[1] += -chq.amount if line.credit else chq.amount
					account_balance.update({line.account_id.id:balance_dic})
				if flag:
					balance_dic = account_balance.get(line.account_id.id,[0,0,0])
					balance_dic[1] += -line.credit or line.debit
					account_balance.update({line.account_id.id:balance_dic})
					
			for rec in account_balance:
				report_line.create({'account':rec,'credit_amount':account_balance[rec][0],
							'debit_amount':account_balance[rec][1],'acc_id':res.id})

    @api.multi
    def print_report(self):
    	self.ensure_one()
        self.sent = True
        self.search_report()
        if self.report_type=='detail':
        	return self.env['report'].get_action(self, 'api_account.report_ledgerwiser_report_detailed')
        elif self.report_type=='summary':
        	return self.env['report'].get_action(self, 'api_account.report_ledgerwise_summary')
    	pass
    			 								
class ledgerwiseLine(models.Model):
    '''ledgerwise report line'''
    _name = "ledgerwise.report.line"
	
    order_id = fields.Many2one('ledgerwise.report')
    line_id = fields.Many2one('ledgerwise.report')
    acc_id = fields.Many2one('ledgerwise.report')
    partner_id = fields.Many2one('res.partner','Ledger')
    account = fields.Many2one('account.account','Account')
    journal = fields.Many2one('account.journal','Journal')
    move = fields.Many2one('account.move','Journal Entry')
    po_number = fields.Char('PO Number')
    narration = fields.Char('Naration')
    date = fields.Date('Date')
    reconcile = fields.Date('Reconcile')
    payment_date = fields.Date('Payment Date')
    credit_amount = fields.Float('Credit Amount')
    debit_amount = fields.Float('Debit Amount')
    amount = fields.Float('Balance')

    ledgerwise_detail_line = fields.One2many('ledgerwise.report.line.details','line_id','Ledger Details',help="Show Detail report in summary report")
    
class ledgerwiseLineDetails(models.Model):
    '''ledgerwise report line details show details in ledgerwiser summary report'''
    _name = "ledgerwise.report.line.details"
	
    line_id = fields.Many2one('ledgerwise.report.line')
    date = fields.Date('Date')
    account = fields.Many2one('account.account','Account')
    journal = fields.Many2one('account.journal','Journal')
    move = fields.Many2one('account.move','Journal Entry')
    po_number = fields.Char('PO Number')
    narration = fields.Char('Naration')
    reconcile = fields.Date('Reconcile')
    payment_date = fields.Date('Payment Date')
    credit_amount = fields.Float('Credit Amount')
    debit_amount = fields.Float('Debit Amount')
    amount = fields.Float('Balance')

class res_partner(models.Model):
	_inherit='res.partner'
	
	@api.model
	def name_search(self, name, args=None, operator='ilike',limit=100):
		# used in move to location validation wizard
		if self._context.get('ledger') :
    			if not self._context.get('ledger_type'):
    				return []
			elif self._context.get('ledger_type'):
				args=[]
				if self._context.get('ledger_type')=='customer':
					args=[('customer','=',True),('company_type','=','company')]
				if self._context.get('ledger_type')=='supplier':
					args=[('supplier','=',True),('company_type','=','company')]
				if self._context.get('ledger_type')=='employee':
					employee = self.env['hr.employee'].search([('address_home_id','!=',False)])
					args=[('id','in',[e.address_home_id.id for e in employee])]
		return super(res_partner,self).name_search(name, args, operator=operator,limit=limit)

