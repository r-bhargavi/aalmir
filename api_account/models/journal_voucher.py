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
from openerp.tools import amount_to_text_fr
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools import float_is_zero, float_compare
from openerp.tools.translate import _
from openerp.tools import amount_to_text_en
from openerp.tools.amount_to_text_en import amount_to_text
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError
from urllib import urlencode
from urlparse import urljoin
import json
import math
import openerp.addons.decimal_precision as dp


class JournalVoucher(models.Model):
	_name='journal.voucher'
	_inherit = ['mail.thread']
        
        
        @api.multi
        def reset_to_draft(self):
            self.write({'state':'draft'})
        @api.multi
        def approve_voucher(self):
            self.post_voucher()
#            self.write({'state':'approved'})
            
        @api.multi
        def reject_voucher(self):
            cofirm_form = self.env.ref('api_account.pay_cancel_wizard_view_form', False)
            if cofirm_form:
                return {
                            'name':'Cancel Wizard',
                            'type': 'ir.actions.act_window',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'cancel.pay.reason.wizard',
                            'views': [(cofirm_form.id, 'form')],
                            'view_id': cofirm_form.id,
                            'target': 'new'
                        }
#            self.write({'state':'reject'})
            
            
        @api.multi
        def submit_voucher(self):
            for record in self:
                record.assert_balanced()
                temp_id = self.env.ref('api_account.email_template_for_voucher_approval')
                if temp_id:
                    recipient_partners=''
                    group = self.env['res.groups'].search([('name', '=', 'Approve Voucher')])
                    for recipient in group.users:
                        recipient_partners += ","+str(recipient.login)
                    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    query = {'db': self._cr.dbname}
                    fragment = {
                              'model': 'jounal.voucher',
                              'view_type': 'form',
                              'id': record.id,
                             }
                    url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))

#                    print "urlurl",url
                    text_link = _("""<a href="%s">%s</a> """) % (url,"VOUCHER")
#                    print "text_linktext_linktext_link",text_link
#                    body ='You have been requested for approval for the attached voucher. ' 
#                    body +='<li> <b>View Voucher :</b> '+str(text_link) +'</li>'
#                    body +='<li> <b>Voucher date :</b>'+str(record.date) +'</li>'
#                    body +='<li> <b>Note :</b> '+str(record.note) +'</li>'
                record.state='submitted'
                
                if self.sent_mail==True:
                        body ='This is reminder for approval for the attached voucher. ' 
                        body ='This is to just inform you that you have been marked as a person who has to approve the attached voucher. ' 

#                        body +='<li> <b>View Voucher :</b> '+str(text_link) +'</li>'
                        body +='<li> <b>Voucher :</b> '+str(record.name) +'</li>'
                        body +='<li> <b>Voucher date :</b>'+str(record.date) +'</li>'
                        body +='<li> <b>Note :</b> '+str(record.note) +'</li>'
                        record.state='resent_for_approval'
                        temp_id.write({'body_html': body, 'email_to':recipient_partners,
                                          'email_from':record.env.user.login})
                        values = temp_id.generate_email(record.id)
                        mail_mail_obj = self.env['mail.mail']
                        msg_id = mail_mail_obj.create(values) 
                        record.sent_mail=True
                        print "text_linktext_linktext_link",text_link
                        msg_id.send()	  
                record.sent_mail=True


	@api.model
	def default_currency(self):
		return self.env.user.company_id.currency_id.id or False
	
	@api.model
	def default_company(self):
		return self.env.user.company_id or False

	name=fields.Char()
        uploaded_doc= fields.Many2many('ir.attachment','jo_voucher_attachment_rel','voucher_id','attach_id','Upload Supporting Doc')

	partner_id=fields.Many2one('res.partner', 'Partner')
	currency_id=fields.Many2one('res.currency', 'Currency',readonly=True, default=default_currency)
	company_id = fields.Many2one('res.company', 'Company', default=default_company)
	journal_id=fields.Many2one('account.journal', 'Journal')
	move_id=fields.Many2one('account.move', 'Journal Entries')
	date=fields.Date('Date',default=fields.Date.context_today)    
	voucher_line=fields.One2many('journal.voucher.line','voucher_id')
	multi_voucher_line=fields.One2many('journal.voucher.line','voucher_id')
	note=fields.Text('Narration',track_visibility='always')
	refuse_reason=fields.Text('Refuse Reason',track_visibility='onchange')
	state=fields.Selection([('draft','Unposted'),('submitted','Submitted For Approval'),('resent_for_approval','Resent For Approval'),('approved','Approved'),('reject','Rejected'),('posted','Posted')], default='draft', string='Status',copy=False,track_visibility='always')
	amount=fields.Float('Amount',compute="get_amount_total")
	multi=fields.Boolean('Is Multi Partner',default=False,help="To Create Entry for Multiple partners")
	sent_mail=fields.Boolean('Mail Sent',default=False,help="To indicate the first mail for approval voucher is being sent")
	
	@api.model
	def get_amount_total(self):
		for rec in self:
			rec.amount=sum(line.debit for line in rec.voucher_line)
			
	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('journal.voucher')
		voucher = super(JournalVoucher, self).create(vals)
		#voucher.assert_balanced()
		return voucher

	@api.multi
	def write(self, vals):
		res = super(JournalVoucher, self).write(vals)
		return res
	
	@api.onchange('company_id')
	def _get_company_data(self):
		#partner_id = self.env['res.partner'].search([('company_id','=',self.company_id.id)])
		#journal = self.env['account.journal'].search([('company_id','=',self.company_id.id)])
#		return {'domain':{'journal_id':[('company_id','=',self.company_id.id)],
#				  'partner_id':[('company_id','=',self.company_id.id),('customer','=',False),('supplier','=',False)]}}
		return {'domain':{'journal_id':[('company_id','=',self.company_id.id)]}}
		
	@api.onchange('journal_id')
	def _update_voucher_line(self):
		if self.journal_id:
			if len(self.voucher_line)==0 and not self.multi:
				self.voucher_line=[(0,0,{'account_id':self.journal_id.default_credit_account_id.id,
							'debit':0.0,'credit':0.0,})]
			elif len(self.multi_voucher_line)==0 and self.multi:
				self.multi_voucher_line=[(0,0,{
							'account_id':self.journal_id.default_credit_account_id.id,
							'debit':0.0,'credit':0.0,})]
		
	@api.multi
	def assert_balanced(self):
		line_records = self.multi_voucher_line if self.multi else self.voucher_line
		
		debit=sum(line.debit for line in line_records)
		credit=sum(line.credit for line in line_records)
		if round(credit,2) != round(debit,2):
			raise UserError(_("API-Alert\n Cannot create unbalanced journal entry."))
		
	@api.multi
	def post_voucher(self):
		self.assert_balanced()
		for record in self:
			vals=[]
			line_records = record.multi_voucher_line if record.multi else record.voucher_line
			for line in line_records:
				partner_id = line.partner_id.id if line.partner_id else record.partner_id.id
				from_currency =  record.journal_id.currency_id or self.env.user.company_id.currency_id
				to_currency = self.env.user.company_id.currency_id
				debit_amt = from_currency.compute(line.debit,to_currency,round=False)
				credit_amt = from_currency.compute(line.credit,to_currency,round=False)
				amount = line.debit or -line.credit
				vals.append((0,0,{
					'account_id':line.account_id.id,'name':line.name,
					'ref':record.name,
					'debit':debit_amt,'credit': credit_amt,
					'amount_currency': amount if from_currency != to_currency else 0.0,
					'currency_id': from_currency.id if from_currency != to_currency else False,
					'partner_id':partner_id}))
							
			# delete existing records and create new one
			if record.move_id:
				record.move_id.line_ids.unlink()
			move_vals={}
                        move_vals={'line_ids':vals,
                                    'date':record.date,
                                    'journal_id':record.journal_id.id,
                                    'name':record.name,
                                    'narration':record.note}
                        if record.uploaded_doc:
                            move_vals.update({'uploaded_document':[(4, record.uploaded_doc.ids)]})
			move=self.env['account.move'].create(move_vals)
			record.move_id=move.id
			move.post()
			record.currency_id = from_currency.id
		return self.write({'state': 'posted'})
	
	@api.multi
	def cancel(self):
		for record in self:
			record.move_id.with_context(voucher=True).button_cancel()
			record.state='draft'
		
class JournalVoucherLine(models.Model):
	_name='journal.voucher.line'

	account_id=fields.Many2one('account.account','Account')
	debit=fields.Float('Debit',default=0.0)
	credit=fields.Float('Credit',default=0.0)
	name=fields.Char('Label')
	voucher_id=fields.Many2one('journal.voucher')
	partner_id=fields.Many2one('res.partner','Partner')
	company_id = fields.Many2one('res.company','Company')
	
	@api.onchange('company_id')
	def _get_company_data(self):
            return {'domain':{'journal_id':[('company_id','=',self.company_id.id)]}}

				  
