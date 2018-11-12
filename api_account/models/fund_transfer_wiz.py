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


class FundTRansferRequest(models.Model):
    _name='fund.transfer.wizard'
  
    mail_details=fields.Text('Mail Preview')
    
    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        record=self.env['account.payment'].browse(active_ids)
        res = super(FundTRansferRequest,self).default_get(fields)
        print "fieldsfieldsfields",fields
        fragment = {
			 'model': 'account.payment',
			 'view_type': 'form',
			 'id': record.id,
			}
        body ='This is to inform you that you have been requested for funds transfer for the below payment details.' +'\n'
        body +='From Company :'+ str(record.company_id.name)+'\n'
        body +='Payment Ref :'+ str(record.name)+'\n'
        body +='Vendor name :'+ str(record.partner_id.name) +'\n'
        body +='Vendor Bank Account Number :'+str(record.bank_id.acc_number) +'\n'
        body +='Vendor Bank IBAN :'+str(record.bank_id.iban_number) +'\n'
        body +='Total Amount requested: '+ str(record.amount)+'\n'
        body +='Payment date: '+ str(record.payment_date)  +'\n'
        body +='Internal Note:'+ str(record.communication)  +'\n'
        body +='Remarks:' + str(record.internal_note)  +'\n'

        res.update({'mail_details':body})
        return res
    
    
    @api.multi 
    def send_mail(self):
        group = self.env['res.groups'].search([('name', '=', 'Send Fund Transfer Request')])
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
               print "text_linktext_linktext_link",text_link
               body ='This is to inform you that you have been requested for funds transfer for the below payment details.' 
               body +='<li> <b>View Request :</b> '+str(text_link) +'</li>'
               body +='<li> <b>From Company :</b>'+str(record.company_id.name) +'</li>'
               body +='<li> <b>Payment Ref :</b>'+str(record.name) +'</li>'
               body +='<li> <b>Vendor name :</b>'+str(record.partner_id.name) +'</li>'
               body +='<li> <b>Vendor Bank Account Number :</b>'+str(record.bank_id.acc_number) +'</li>'
               body +='<li> <b>Vendor Bank IBAN :</b>'+str(record.bank_id.iban_number) +'</li>'
               body +='<li> <b>Total Amount requested :</b> '+str(record.amount) +'</li>'
               body +='<li> <b>Payment date :</b> '+str(record.payment_date) +'</li>'
               body +='<li> <b>Internal Note :</b> '+str(record.communication) +'</li>'
               body +='<li> <b>Remarks :</b> '+str(record.internal_note) +'</li>'
	       temp_id.write({'body_html': body, 'email_to':email_to,
                              'email_from':self.env.user.login})
               values = temp_id.generate_email(record.id)
               mail_mail_obj = self.env['mail.mail']
               msg_id = mail_mail_obj.create(values) 
               attachments = values.pop('attachments', [])
               if record.uploaded_document:
#                  attachments.append((record.doc_name,record.uploaded_document))
#               if attachments:
                    values['attachment_ids'] =[(4, record.uploaded_document.ids)]
                    msg_id.write({'attachment_ids':[(4, record.uploaded_document.ids)]}) 
               msg_id.send()	       
               record.write({'send_ftr_req':True})
