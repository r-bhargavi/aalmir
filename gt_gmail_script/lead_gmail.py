 # -*- coding: utf-8 -*-
##############################################################################
#
#
#    Copyright (C) 2013-Today(www.jupical.com).
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
from openerp import models, api, fields, _
import imaplib
import email
import email.header
from datetime import datetime
from openerp import tools, api, SUPERUSER_ID
from openerp.tools.translate import _
import logging
import time
from dateutil.relativedelta import relativedelta
_logger = logging.getLogger(__name__)
import ast
import re

class MailMessage(models.Model):
    
    _inherit = "mail.message"

    @api.multi
    def _notify(self, force_send=False, user_signature=True):
        """ Add the related record followers to the destination partner_ids if is not a private message.
            Call mail_notification.notify to manage the email sending
        """
        group_user = self.env.ref('base.group_user')
        # have a sudoed copy to manipulate partners (public can go here with 
        # website modules like forum / blog / ...
        self_sudo = self.sudo()

        # TDE CHECK: add partners / channels as arguments to be able to notify a message with / without computation ??
        self.ensure_one()  # tde: not sure, just for testinh, will see
        partners = self.env['res.partner'] | self.partner_ids
        channels = self.env['mail.channel'] | self.channel_ids

        # all followers of the mail.message document have to be added as partners and notified
        # and filter to employees only if the subtype is internal
#         if self_sudo.subtype_id and self.model and self.res_id:
#             followers = self.env['mail.followers'].sudo().search([
#                 ('res_model', '=', self.model),
#                 ('res_id', '=', self.res_id)
#             ]).filtered(lambda fol: self.subtype_id in fol.subtype_ids)
#             if self_sudo.subtype_id.internal:
#                 followers = followers.filtered(lambda fol: fol.channel_id or (fol.partner_id.user_ids and group_user in fol.partner_id.user_ids[0].mapped('groups_id')))
#             channels = self_sudo.channel_ids | followers.mapped('channel_id')
#             partners = self_sudo.partner_ids | followers.mapped('partner_id')
#         else:
#             channels = self_sudo.channel_ids
#             partners = self_sudo.partner_ids

        # remove author from notified partners
        if not self._context.get('mail_notify_author', False) and self_sudo.author_id:
            partners = partners - self_sudo.author_id

        # update message
        self.write({'channel_ids': [(6, 0, channels.ids)], 'needaction_partner_ids': [(6, 0, partners.ids)]})

        # notify partners and channels
        partners._notify(self, force_send=force_send, user_signature=user_signature)
        channels._notify(self)

        # Discard cache, because child / parent allow reading and therefore
        # change access rights.
        if self.parent_id:
            self.parent_id.invalidate_cache()

        return True

class GmailData(models.Model):
    
    _inherit = "fetchmail.server"
    
    owner = fields.Many2one('res.users', string="Owner")
    
    @api.one
    def process_mailbox(self, M, server_date, box_name):
        context_dt = self._context.copy()
        context_dt.update({'fetchmail_server_id': self.id});model_data = False
        if not self.object_id:
            alias = self.user.split('@')[0]
            alias_obj = self.env['mail.alias'].sudo().search([('alias_name', '=', alias)])
            if alias_obj:
                if alias_obj.alias_defaults:
                    context_dt.update(ast.literal_eval(alias_obj.alias_defaults))
                model_data = alias_obj.alias_model_id and  alias_obj.alias_model_id.model
        mail_thread = self.pool['mail.thread']; mail_message = self.env['mail.message']; action_pool = self.pool.get('ir.actions.server')
        rv, data = M.search(None, server_date)
        _logger.info('Searching.............%s == %s == %s'%(server_date,box_name,data))
        if rv != 'OK':
            return
        list1 = data[0].split()
        #list1.reverse()
        msg_ids = ','.join(list1)
        if not len(list1):
            return True
        result, response = M.fetch(msg_ids, '(BODY.PEEK[])')
        if result != 'OK':
            return 
        _logger.info('data found.............%s '%(msg_ids,))
        for i in range(0, len(response)-1):
            data_msg = response[i]
            if not isinstance(data_msg, tuple):
                continue
            num = data_msg[0].split(' ')
            
            res_id = None
            msg = email.message_from_string(data_msg[1])
            rep_msg_id = msg['In-Reply-To']
            ref_msg_id = msg['References']
            msg_id = msg['Message-ID']
            msub_id = msg['Subject'] 
            
            crm_id=False
            email_to= ''
            
            sub_msg_id= ' '.join([line.strip() for line in msub_id.strip().splitlines()]) if msub_id else False
            #Check if Message is present in system or not if Yes then continue for new messages.
            if msg_id:
                mmail_ids = mail_message.sudo().search([('message_id', '=', msg_id.strip())])
                if mmail_ids:
                    continue
            if not rep_msg_id and not ref_msg_id:
                try:
                    _logger.info('Searching.. Custome Code in LINK...........')
                    body ,attachment=self.env['mail.thread']._message_extract_payload(msg, save_original=True)
                    for item in body.split("</p>"):
                        if '<p style="display:none"' in item:
                               for isplit in item.split('>'):
                                    if 'SENDAPI' in isplit :
                                           crm_id= isplit.split('-')[1] if len(isplit.split('-'))>1 else False
                                           _logger.info('New ID found for insert... %s'%(crm_id,))
                                       
                    smail_res_id = mail_message.sudo().search([('res_id', '=',crm_id),('model','=','crm.lead')])
                    if not smail_res_id:
                        continue
                except Exception as e:
                     _logger.info('Exception in get message body and attachment...........')
                     _logger.info('Error %s', e.message, exc_info=True)
                _logger.info('Searching Thought Res_Model To  %s, for MEssage %s result is %s',crm_id, msg_id,str(smail_res_id))
            #Check If Message has not In-reply-to , Referance and also has no CRM id(APISEND Number)
            if not rep_msg_id and not ref_msg_id and not crm_id:
                print "Before!!!!!!!!333333333333333.........",sub_msg_id,msg_id,
                if sub_msg_id.strip()=='':  #Continue if subject is blank
                    continue
                if box_name == 'Sent' and msg['From']:
                    email_to = msg['From'].split('<')[1].rstrip('>') if len(msg['From'].split('<'))>1 else msg['From']
                elif box_name == 'Inbox' and msg['To']:
                    email_to = msg['To'].split('<')[1].rstrip('>') if len(msg['To'].split('<'))>1 else msg['To']

                smail_sub = mail_message.sudo().search([('subject','=ilike',sub_msg_id),('email_from','ilike',email_to)])
                print "999999999",smail_sub,email_to    
                if not smail_sub:
                    continue
                _logger.info('Searching Thought Subject To  %s, for MEssage %s result is %s',sub_msg_id, msg_id,str(smail_sub))
            if box_name != 'Lead' and not model_data and not rep_msg_id and not ref_msg_id and not msub_id and not crm_id:
                   continue
            if rep_msg_id or ref_msg_id:
                mail_ids=False
                if rep_msg_id:
                    mail_ids = mail_message.sudo().search([('message_id', '=', rep_msg_id.strip())])
                if not mail_ids and ref_msg_id:
                    ref_msg_id=ref_msg_id.split(' ')
                    rmail_ids = mail_message.sudo().search([('message_id', 'in', ref_msg_id)])
                    if not rmail_ids:
                            continue
                    _logger.info('Searching Thought Referances To  %s, for MEssage %s result is %s',ref_msg_id, msg_id,str(rmail_ids))
                elif not mail_ids and not ref_msg_id:
                    continue

            print "111111111",msg_id,msub_id,email_to,rep_msg_id,ref_msg_id,
            try:
            #if True:
                _logger.info('MSG. Searching............')#.%s'%(data_msg[1],))
                res_id = None
                context_dt.update({'from_force_create': True})
                res_id = mail_thread.message_process(self._cr, self._uid, self.object_id.model or model_data or 'crm.lead',
                                 data_msg[1],
                                 save_original=self.original,
                                 strip_attachments=(not self.attach),
                                 context=context_dt)
                if res_id and self.action_id:
                    action_pool.run(self._cr, self._uid, [self.action_id.id], {'active_id': res_id, 'active_ids': [res_id], 'active_model': self._context.get("thread_model", self.object_id.model or model_data or 'crm.lead')})
                _logger.info('MSG Completed....................................%s'%(res_id,))
                #M.store(num[0], '+FLAGS', '\\Seen')
            except Exception as e:
                _logger.info('Failed to process mail from %s server %s.', self.type, self.name, exc_info=True)
                _logger.info('Error %s', e.message, exc_info=True)
        return True
    
    @api.model
    def _gmail_data(self):
        try:
            fetch_s_ids = self.sudo().search([('owner','=', self.env.uid), ('state','=', 'done')])
            return fetch_s_ids.sudo().gmail_data()
        except Exception:
            _logger.info('Error====== Owner not found')
            pass
    
    @api.multi
    def gmail_data(self):
        for server in self:
            _logger.info('Server ======>%s'%(server.name))
            model_data = False
            if server.state != 'done':
                continue
            if not server.date:
                server.date = (datetime.now() - relativedelta(days=1))
            if server.date == False:
                server.write({'date': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})

            server_date = '(SINCE "%s")' % (datetime.strptime(server.date,'%Y-%m-%d %H:%M:%S') - relativedelta(days=1)).strftime('%d-%b-%Y')
            #server_date = '(SINCE "%s" BEFORE "%s")' % ((datetime.strptime(server.date,'%Y-%m-%d %H:%M:%S') - relativedelta(days=1)).strftime('%d-%b-%Y'),(datetime.strptime(server.date,'%Y-%m-%d %H:%M:%S')+ relativedelta(days=5)).strftime('%d-%b-%Y') )
            _logger.info('Fetch Date ======>%s'%(server_date))
            M = imaplib.IMAP4_SSL(server.server)
            if not server.object_id:
                alias = server.user.split('@')[0]
                alias_obj = server.env['mail.alias'].sudo().search([('alias_name', '=', alias)])
                if alias_obj:
                    model_data = alias_obj.alias_model_id and  alias_obj.alias_model_id.model
            try:
                rv, data = M.login(server.user, server.password)
                if not model_data:
                    _logger.info('model_data not Found...')
                    if [None] in M.list('Lead'):
                        M.create("Lead")
                    rv, data = M.select('Lead')
                    if rv == 'OK':
                        server.process_mailbox(M, server_date, 'Lead')
                    rv, data = M.select('[Gmail]/Sent Mail')
                    if rv == 'OK':
                        server.process_mailbox(M, server_date, 'Sent')
                    rv, data = M.select('INBOX')
                    if rv == 'OK':
                        server.process_mailbox(M, server_date, 'Inbox')
                if model_data:
                    _logger.info('model_data Found...%s'%(model_data))
                    rv, data = M.select('INBOX')
                    if rv == 'OK':
                        server.process_mailbox(M, server_date, 'Inbox')
                    rv, data = M.select('[Gmail]/Sent Mail')
                    if rv == 'OK':
                        server.process_mailbox(M, server_date, 'Sent')             
            except Exception as ae:
                _logger.info('!!!Error %s', ae.message, exc_info=True)
                return False
            finally:
                try:
                    M.close()
                except:
                    pass
                M.logout()
            _logger.info('Server ======>%s ===> Time===>%s'%(server.name, time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)))
            time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            server.write({'date': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
            #server.write({'date': (datetime.strptime(server.date,'%Y-%m-%d %H:%M:%S'))+ relativedelta(days=5)})

        return True

class CrmLead(models.Model):
    _inherit = "crm.lead"
    
    msg_id = fields.Char('Gmail Message')
    mail_subject = fields.Char('Mail Subject')
    
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        partner_obj = self.env['res.partner']
        res = super(CrmLead, self).message_new(msg_dict, custom_values=custom_values)
        res1 = self.browse(res)
        name, email = self.env['res.partner']._parse_partner_name(msg_dict.get('from'))
        if res1.type == 'opportunity':
            part_ids = partner_obj.search([('email','=', email)])
            if part_ids:
                p_id = part_ids[0]
            else:
                p_id = partner_obj.create({'name' : name, 'email': email})
            res1.write({'partner_id' : p_id.id, 'contact_name' : name, 'email_from': email})
        else:
            res1.write({'contact_name' : name, 'email_from': email})
        return res

    @api.model
    def create(self, vals):
        if not self._context.get('from_so') and not self._context.get('cold_calling') and not self._context.get('from_lead_menu'):
            if not vals.get('name'):
                vals.update({'name': vals.get('mail_subject')})
            fetchmail_server_id=self._context.get('fetchmail_server_id')
            fetchmail=self.env['fetchmail.server'].browse(fetchmail_server_id)
            if not fetchmail.object_id and not fetchmail.object_id.model == 'crm.lead' and not self._context.get('cold_calling'):
                vals.update({'user_id': False, 'type': 'lead'})
                stage = self.env['crm.stage'].search([('name', '=', 'New')])
                if stage:
                    vals.update({'stage_id': stage[0].id})
            if fetchmail.object_id and fetchmail.object_id.model == 'crm.lead':
                stage = self.env['crm.stage'].search([('name', '=', 'Open')])
                user = self.env['res.users'].search([('login', '=', fetchmail.user)])
                if user:
                    vals.update({'type': 'opportunity','user_id': user.id, 'team_id': user.sale_team_id and user.sale_team_id.id})
                if stage:
                    vals.update({'stage_id': stage[0].id})
#               
            if not vals.get('team_id'):
                team_ids = self.env['crm.team'].search([])
                if team_ids:
                    vals.update({'team_id' : team_ids[0].id})
        return super(CrmLead, self).create(vals) 
        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
