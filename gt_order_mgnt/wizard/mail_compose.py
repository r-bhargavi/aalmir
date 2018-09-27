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
_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    email_ids=fields.Char('Email ID')

    @api.multi
    def send_mail_action_po(self):
        if self._context and self._context.has_key('default_res_id') and self._context.get('default_res_id'):
            if self._context.has_key('default_model') and self._context.get('default_model'):
                browse_rec = self.env[self._context.get('default_model')].browse(self._context.get('default_res_id'))
                template_ids=False
                if self._context.get('default_model') =='purchase.order':
                   template_ids = self.env.ref('gt_order_mgnt.email_template_for_purchase_requested_user_po11')
                else:
                   template_ids=self.template_id
                recipient_partners=self.email_ids
                values={}
               
                if template_ids:
                   values = template_ids.generate_email(browse_rec.id)
                   values['email_to'] = recipient_partners
                   values['subject'] = self.subject
                else:
                   values={'email_to':recipient_partners, 'subject':self.subject,
                           'body_html':self.body}
                mail_mail_obj = self.env['mail.mail']
                msg_id = mail_mail_obj.create(values) 
                Attachment = self.env['ir.attachment']
                attachment_ids = values.pop('attachment_ids', [])
                attachments = values.pop('attachments', [])
                if attachments:
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
                         msg_id.write({'attachment_ids': [(6, 0, attachment_ids)]})
                msg_id.send()
             
        return True
      
       
