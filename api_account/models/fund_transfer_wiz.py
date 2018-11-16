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
import base64


class FundTRansferApprove(models.Model):
    _name='fund.transfer.approve'
  
    uploaded_proof = fields.Many2many('ir.attachment','bill_attachment_fund_rel','bill','fund_id','Payment Proof')
    internal_note_tt=fields.Text('Remarks on Fund Transfer',track_visibility='always')
    @api.multi 
    def transfer_funds(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        pay_brw=self.env['account.payment'].browse(active_ids)
        for record in pay_brw:
            record.write({'pay_p_up':'post','internal_note_tt':self.internal_note_tt})
            if self.uploaded_proof:
                record.write({'uploaded_proof':[(4, self.uploaded_proof.ids)]})



class FundTRansferRequest(models.Model):
    _name='fund.transfer.wizard'
  
    mail_details = fields.Html('Fund Details',copy=False)
    
    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        record=self.env['account.payment'].browse(active_ids)
        res = super(FundTRansferRequest,self).default_get(fields)
        print "fieldsfieldsfields",fields
        inv_ref=''
        vendor_inv=''
        if record.invoice_ids:
            for each_inv in record.invoice_ids:
                inv_ref+=(str(each_inv.number)+' '+str(each_inv.date_invoice))+','
                vendor_inv+=(str(each_inv.reference if each_inv.reference else '')+' '+str(each_inv.vendor_invoice_date))+','
        body ='<li> <b>Below are the details for Fund Transfer Requested.'+'</li>'
        body +='<li> <b>From Company :</b>'+str(record.company_id.name) +'</li>'
        body +='<li> <b>Company Bank Account Name :</b>'+str(record.journal_id.name) +'</li>'
        body +='<li> <b>Payment Ref :</b>'+str(record.name) +'</li>'
        body +='<li> <b>Vendor name :</b>'+str(record.partner_id.name) +'</li>'
        if inv_ref:
            body +='<li> <b>Vendor Bill Ref :</b>'+str(inv_ref) +'</li>'
            body +='<li> <b>Vendor Invoice Details :</b>'+str(vendor_inv) +'</li>'

        body +='<li> <b>Vendor Bank Account Number :</b>'+str(record.bank_id.acc_number) +'</li>'
        body +='<li> <b>Vendor Bank IBAN :</b>'+str(record.bank_id.iban_number if record.bank_id.iban_number else '') +'</li>'
        body +='<li> <b>Vendor Bank Account Name :</b>'+str(record.bank_id.account_name if record.bank_id.account_name else '') +'</li>'
        body +='<li> <b>Vendor Bank Swift Code :</b>'+str(record.bank_id.swift_code if record.bank_id.swift_code else '') +'</li>'
        body +='<li> <b>Vendor Bank Address :</b>'+str(record.bank_id.bank_id.street if record.bank_id.bank_id.street else '')+','+str(record.bank_id.bank_id.state.name if record.bank_id.bank_id.state else '')+','+str(record.bank_id.bank_id.zip if record.bank_id.bank_id.zip else '')+','+str(record.bank_id.bank_id.country.name if record.bank_id.bank_id.country else '')+','+str(record.bank_id.bank_id.street if record.bank_id.bank_id.street else '')+'</li>'

        body +='<li> <b>Total Amount requested :</b> '+str(record.amount) +''+str(record.currency_id.name) +'</li>'
        body +='<li> <b>Payment date :</b> '+str(record.payment_date) +'</li>'
        body +='<li> <b>Internal Note :</b> '+str(record.communication if record.communication else '') +'</li>'
        body +='<li> <b>Remarks :</b> '+str(record.internal_note if record.internal_note else '') +'</li>'
        body +='<li> <b>Remarks On Transfer:</b> '+str(record.internal_request_tt if record.internal_request_tt else '') +'</li>'

        res.update({'mail_details':body})
        return res
    
    
    @api.multi 
    def send_mail(self):
        report_obj = self.pool.get('report')
        Attachment = self.env['ir.attachment']

        group = self.env['res.groups'].search([('name', '=', 'Transfer Request Approve')])
        print "groupgroupgroupgroup",group
        if group:
            user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', [group.id])])
            print "user_idsuser_ids",user_ids
            email_to = ''.join([user.partner_id.email + ',' for user in user_ids])
            email_to = email_to[:-1]
            print "email_toemail_to",email_to
        else:
            email_to=self.approved_by.login
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        pay_brw=self.env['account.payment'].browse(active_ids)
        for record in pay_brw:
            inv_ref=''
            vendor_inv=''
            attachment_data={} 
            attachment_ids_invoice=[]
            attachments_inv=[]

            if pay_brw.invoice_ids:
                print "pay_brw.invoice_idspay_brw.invoice_ids",pay_brw.invoice_ids
                for each_inv in pay_brw.invoice_ids:
                    data=report_obj.get_pdf(self._cr, self._uid, each_inv.ids,
                        'gt_order_mgnt.report_invoice_aalmir',  context=self._context)
                    val  = base64.encodestring(data)
                    rep_name='Invoice:'+str(each_inv.number)+'.pdf'
                    attachments_inv.append((rep_name,val))
                    
                    for attachment in attachments_inv: 
		       attachment_data = {
				        'name': attachment[0],
				        'datas_fname': attachment[0],
				        'datas': attachment[1],
				        'res_model': 'mail.message',
#				        'res_id': msg_id.mail_message_id.id,
                                        'type':'binary',
				        
				          }
		       attachment_ids_invoice.append(Attachment.create(attachment_data).id)
                    inv_ref+=(str(each_inv.number)+''+str(each_inv.date_invoice))+','
                    vendor_inv+=(str(each_inv.reference if each_inv.reference else '')+' '+str(each_inv.vendor_invoice_date))+','

            temp_id = self.env.ref('gt_order_mgnt.email_template_for_fund_transfer_request')
            if temp_id:
               base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			 'model': 'account.payment',
			 'view_type': 'form',
			 'id': record.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
               print "urlurl",url
               text_link = _("""<a href="%s">%s</a> """) % (url,"VIEW REQUEST")
               body ='<li><b>Below are the details for Fund Transfer Requested.'+'</li>'
               body +='<li> <b>TT Request :</b> '+str(text_link) +'</li>'
               body +='<li> <b>From Company :</b>'+str(record.company_id.name) +'</li>'
               body +='<li> <b>Company Bank Account Name :</b>'+str(record.journal_id.name) +'</li>'
               body +='<li> <b>Payment Ref :</b>'+str(record.name) +'</li>'
               body +='<li> <b>Vendor name :</b>'+str(record.partner_id.name) +'</li>'
               if inv_ref:
                   body +='<li> <b>Vendor Bill Ref :</b>'+str(inv_ref) +'</li>'
                   body +='<li> <b>Vendor Invoice Details :</b>'+str(vendor_inv) +'</li>'

               body +='<li> <b>Vendor Bank Account Number :</b>'+str(record.bank_id.acc_number) +'</li>'
               body +='<li> <b>Vendor Bank IBAN :</b>'+str(record.bank_id.iban_number if record.bank_id.iban_number else '') +'</li>'
               body +='<li> <b>Vendor Bank Account Name :</b>'+str(record.bank_id.account_name if record.bank_id.account_name else '') +'</li>'
               body +='<li> <b>Vendor Bank Swift Code :</b>'+str(record.bank_id.swift_code if record.bank_id.swift_code else '') +'</li>'
               body +='<li> <b>Vendor Bank Address :</b>'+str(record.bank_id.bank_id.street if record.bank_id.bank_id.street else '')+','+str(record.bank_id.bank_id.state.name if record.bank_id.bank_id.state else '')+','+str(record.bank_id.bank_id.zip if record.bank_id.bank_id.zip else '')+','+str(record.bank_id.bank_id.country.name if record.bank_id.bank_id.country else '')+','+str(record.bank_id.bank_id.street if record.bank_id.bank_id.street else '')+'</li>'

               body +='<li> <b>Total Amount requested :</b> '+str(record.amount) +''+str(record.currency_id.name) +'</li>'
               body +='<li> <b>Payment date :</b> '+str(record.payment_date) +'</li>'
               body +='<li> <b>Internal Note :</b> '+str(record.communication if record.communication else '') +'</li>'
               body +='<li> <b>Remarks :</b> '+str(record.internal_note if record.internal_note else '') +'</li>'
               body +='<li> <b>Remarks on transfer:</b> '+str(record.internal_request_tt if record.internal_request_tt else '') +'</li>'
	       temp_id.write({'body_html': body, 'email_to':email_to,
                              'email_from':self.env.user.login})
               values = temp_id.generate_email(record.id)
               mail_mail_obj = self.env['mail.mail']
               msg_id = mail_mail_obj.create(values) 
               all_attach=[]
               if attachment_ids_invoice:
                   all_attach.append(attachment_ids_invoice)
               if record.uploaded_document_tt:
                    all_attach.append(record.uploaded_document_tt.ids)
                    msg_id.write({'attachment_ids':[(4, all_attach)]}) 
               msg_id.send()	
               inv_ref=''

               if record.invoice_ids:
                   for each_inv in record.invoice_ids:
                      inv_ref+=each_inv.number+','
               record.write({'send_ftr_req':True,'mail_details':body})
