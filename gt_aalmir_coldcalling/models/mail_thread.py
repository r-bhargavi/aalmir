# -*- coding: utf-8 -*-

import base64
import datetime
import dateutil
import email
import hashlib
import hmac
import json
import lxml
from lxml import etree
import logging
import pytz
import re
import socket
import time
import xmlrpclib
from email.message import Message
from email.utils import formataddr
from werkzeug import url_encode

from openerp import _, api, fields, models
from openerp import exceptions
from openerp import tools
from openerp.addons.mail.models.mail_message import decode
from openerp.tools.safe_eval import safe_eval as eval


_logger = logging.getLogger(__name__)


mail_header_msgid_re = re.compile('<[^<>]+>')


def decode_header(message, header, separator=' '):
    return separator.join(map(decode, filter(None, message.get_all(header, []))))


class MailThread(models.AbstractModel):
    ''' mail_thread model is meant to be inherited by any model that needs to
        act as a discussion topic on which messages can be attached. Public
        methods are prefixed with ``message_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.

        ``mail.thread`` defines fields used to handle and display the
        communication history. ``mail.thread`` also manages followers of
        inheriting classes. All features and expected behavior are managed
        by mail.thread. Widgets has been designed for the 7.0 and following
        versions of OpenERP.

        Inheriting classes are not required to implement any method, as the
        default implementation will work for any model. However it is common
        to override at least the ``message_new`` and ``message_update``
        methods (calling ``super``) to add model-specific behavior at
        creation and update of a thread when processing incoming emails.

        Options:
            - _mail_flat_thread: if set to True, all messages without parent_id
                are automatically attached to the first message posted on the
                ressource. If set to False, the display of Chatter is done using
                threads, and no parent_id is automatically set.

    MailThread features can be somewhat controlled through context keys :

     - ``mail_create_nosubscribe``: at create or message_post, do not subscribe
       uid to the record thread
     - ``mail_create_nolog``: at create, do not log the automatic '<Document>
       created' message
     - ``mail_notrack``: at create and write, do not perform the value tracking
       creating messages
     - ``tracking_disable``: at create and write, perform no MailThread features
       (auto subscription, tracking, post, ...)
     - ``mail_save_message_last_post``: at message_post, update message_last_post
       datetime field
     - ``mail_auto_delete``: auto delete mail notifications; True by default
       (technical hack for templates)
     - ``mail_notify_force_send``: if less than 50 email notifications to send,
       send them directly instead of using the queue; True by default
     - ``mail_notify_user_signature``: add the current user signature in
       email notifications; True by default
    '''
    _inherit = 'mail.thread'


    @api.model
    def message_parse(self, message, save_original=False):
        """Parses a string or email.message.Message representing an
           RFC-2822 email, and returns a generic dict holding the
           message details.

           :param message: the message to parse
           :type message: email.message.Message | string | unicode
           :param bool save_original: whether the returned dict
               should include an ``original`` attachment containing
               the source of the message
           :rtype: dict
           :return: A dict with the following structure, where each
                    field may not be present if missing in original
                    message::

                    { 'message_id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'body': unified_body,
                      'attachments': [('file1', 'bytes'),
                                      ('file2', 'bytes')}
                    }
        """
        msg_dict = {
            'message_type': 'email',
        }
        if not isinstance(message, Message):
            if isinstance(message, unicode):
                # Warning: message_from_string doesn't always work correctly on unicode,
                # we must use utf-8 strings here :-(
                message = message.encode('utf-8')
            message = email.message_from_string(message)

        message_id = message['message-id']
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            _logger.debug('Parsing Message without message-id, generating a random one: %s', message_id)
        msg_dict['message_id'] = message_id

        if message.get('Subject'):
            msg_dict['subject'] = decode(message.get('Subject'))

        # Envelope fields not stored in mail.message but made available for message_new()
        msg_dict['from'] = decode(message.get('from'))
        msg_dict['to'] = decode(message.get('to'))
        msg_dict['cc'] = decode(message.get('cc'))
        msg_dict['email_from'] = decode(message.get('from'))
        partner_ids = self._message_find_partners(message, ['To', 'Cc'])
        msg_dict['partner_ids'] = [(4, partner_id) for partner_id in partner_ids]

        if message.get('Date'):
            try:
                date_hdr = decode(message.get('Date'))
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers.
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(tz=pytz.utc)
            except Exception:
                _logger.info('Failed to parse Date header %r in incoming mail '
                                'with message-id %r, assuming current date/time.',
                                message.get('Date'), message_id)
                stored_date = datetime.datetime.now()
            msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        if message.get('In-Reply-To'):
            parent_ids = self.env['mail.message'].search([('message_id', '=', decode(message['In-Reply-To'].strip()))], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id

        if message.get('References') and 'parent_id' not in msg_dict:
            msg_list = mail_header_msgid_re.findall(decode(message['References']))
            parent_ids = self.env['mail.message'].search([('message_id', 'in', [x.strip() for x in msg_list])], limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id
	if message.get('Subject') and 'parent_id' not in msg_dict:
            nmsg_id= ' '.join([line.strip() for line in decode(message.get('Subject')).strip().splitlines()])
            parent_ids = self.env['mail.message'].search([('subject', 'ilike',nmsg_id)], order='id desc',limit=1)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.id

        msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message, save_original=save_original)
        return msg_dict

    #------------------------------------------------------
    # Note specific
    #------------------------------------------------------

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:
             1. If the message replies to an existing thread_id, and
                properly contains the thread model in the 'In-Reply-To'
                header, use this model/thread_id pair, and ignore
                custom_value (not needed as no creation will take place)
             2. Look for a mail.alias entry matching the message
                recipient, and use the corresponding model, thread_id,
                custom_values and user_id.
             3. Fallback to the ``model``, ``thread_id`` and ``custom_values``
                provided.
             4. If all the above fails, raise an exception.

           :param string message: an email.message instance
           :param dict message_dict: dictionary holding message variables
           :param string model: the fallback model to use if the message
               does not match any of the currently configured mail aliases
               (may be None if a matching alias is supposed to be present)
           :type dict custom_values: optional dictionary of default field values
                to pass to ``message_new`` if a new record needs to be created.
                Ignored if the thread record already exists, and also if a
                matching mail.alias was found (aliases define their own defaults)
           :param int thread_id: optional ID of the record/thread from ``model``
               to which this mail should be attached. Only used if the message
               does not reply to an existing thread and does not match any mail alias.
           :return: list of [model, thread_id, custom_values, user_id, alias]

        :raises: ValueError, TypeError
        """
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        MailMessage = self.env['mail.message']
        Alias = self.env['mail.alias']
        fallback_model = model

        # Get email.message.Message variables for future processing
        message_id = message.get('Message-Id')
        email_from = decode_header(message, 'From')
        email_to = decode_header(message, 'To')
        references = decode_header(message, 'References')
        in_reply_to = decode_header(message, 'In-Reply-To').strip()
        thread_references = references or in_reply_to

        # 0. First check if this is a bounce message or not.
        #    See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #    As all MTA does not respect this RFC (googlemail is one of them),
        #    we also need to verify if the message come from "mailer-daemon"
        localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        if message.get_content_type() == 'multipart/report' or localpart == 'mailer-daemon':
            _logger.info("Not routing bounce email from %s to %s with Message-Id %s",
                         email_from, email_to, message_id)
            return []

        # 1. message is a reply to an existing message (exact match of message_id)
        ref_match = thread_references and tools.reference_re.search(thread_references)
        msg_references = mail_header_msgid_re.findall(thread_references)
        mail_messages = MailMessage.sudo().search([('message_id', 'in', msg_references)], limit=1)
        if ref_match and mail_messages:
            model, thread_id = mail_messages.model, mail_messages.res_id
            alias = Alias.search([('alias_name', '=', (tools.email_split(email_to) or [''])[0].split('@', 1)[0].lower())])
            alias = alias[0] if alias else None
            x=self.env[model].browse(thread_id)
            if x:
		if model=='sale.order' and x.state=='cancel':
			nthread_id=self.env[model].search([('state','in',('sale','done'))],limit=1).id
			if not nthread_id:
				return []
			thread_id = nthread_id

            route = self.with_context(drop_alias=True).message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, alias),
                update_author=True, assert_model=False, create_fallback=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
		
                return [route]
            elif route is False:
                return []

        # 2. message is a reply to an existign thread (6.1 compatibility)
        if ref_match:
            reply_thread_id = int(ref_match.group(1))
            reply_model = ref_match.group(2) or fallback_model
            reply_hostname = ref_match.group(3)
            local_hostname = socket.gethostname()
            # do not match forwarded emails from another OpenERP system (thread_id collision!)
            if local_hostname == reply_hostname:
                thread_id, model = reply_thread_id, reply_model
                if thread_id and model in self.pool:
                    record = self.env[model].browse(thread_id)
                    compat_mail_msg_ids = MailMessage.search([
                        ('message_id', '=', False),
                        ('model', '=', model),
                        ('res_id', '=', thread_id)])
                    if compat_mail_msg_ids and record.exists() and hasattr(record, 'message_update'):
                        route = self.message_route_verify(
                            message, message_dict,
                            (model, thread_id, custom_values, self._uid, None),
                            update_author=True, assert_model=True, create_fallback=True)
                        if route:
                            # parent is invalid for a compat-reply
                            message_dict.pop('parent_id', None)
                            _logger.info(
                                'Routing mail from %s to %s with Message-Id %s: direct thread reply (compat-mode) to model: %s, thread_id: %s, custom_values: %s, uid: %s',
                                email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                            return [route]
                        elif route is False:
                            return []

        # 3. Reply to a private message
        if in_reply_to:
            mail_message_ids = MailMessage.search([
                ('message_id', '=', in_reply_to),
                '!', ('message_id', 'ilike', 'reply_to')
            ], limit=1)
            if mail_message_ids:
                route = self.message_route_verify(
                    message, message_dict,
                    (mail_message_ids.model, mail_message_ids.res_id, custom_values, self._uid, None),
                    update_author=True, assert_model=True, create_fallback=True, allow_private=True)
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: direct reply to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, mail_message_ids.id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []
                    
        print "before.......!!!!!!!!!!!!!!!!!!!!!!!!!RES ID"
        crm_id=False
        body ,attachment=self.env['mail.thread']._message_extract_payload(message, save_original=True)
        if body:
            for item in body.split("</p>"):
                    if '<p style="display:none"' in item:
                           for isplit in item.split('>'):
                                if 'SENDAPI' in isplit :
                                       crm_id= isplit.split('-')[1] if len(isplit.split('-'))>1 else False
                                       _logger.info('New ID found for insert... %s'%(crm_id,))
                                       
            mail_res_ids = MailMessage.search([('res_id', '=',crm_id),('model','=','crm.lead')], limit=1)
            print "!!!!!!!!!!!!!!!!!1------",mail_res_ids,crm_id
            if mail_res_ids:
                route = self.message_route_verify(
                    message, message_dict,
                    (mail_res_ids.model, mail_res_ids.res_id, custom_values, self._uid, None),
                    update_author=True, assert_model=True, create_fallback=True, allow_private=True)
                print "@@@########1res_id.......-",route,crm_id
                if route:
                    _logger.info(
                        'Routing mail of Message-Id %s: Searching %s Res_id to a private message: %s, custom_values: %s, uid: %s',message_id,crm_id, mail_res_ids.id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []
                _logger.info('Searching Thought Res model ID To  %s, for MEssage %s result is %s',crm_id, msg_id,str(smail_res_id))
                
        print "before.......!!!!!!!!!!!!!!!!!!!!!!!!!BEFORE SUBject..."
        #Check If Message has not In-reply-to , Referance and also has no CRM id(APISEND Number)
        sub_msg_id= ' '.join([line.strip() for line in decode_header(message, 'Subject').strip().splitlines()])
        if sub_msg_id and crm_id==False:
            email_to= ''
            if decode_header(message, 'From'):
            	d_msg=decode_header(message, 'From').split('<')
                email_to = d_msg.rstrip('>') if len(d_msg)>1 else decode_header(message, 'From')
            elif decode_header(message, 'To'):
            	d_msg=decode_header(message, 'To').split('<')
                email_to = d_msg.rstrip('>') if len(d_msg)>1 else decode_header(message, 'To')
            
            mail_message_ids = MailMessage.search([('subject', '=ilike',sub_msg_id),('email_from','ilike',email_to)], limit=1)
            print "!!!!!!!!!!!!!!!!!1------",mail_message_ids,email_to
            if mail_message_ids:
                route = self.message_route_verify(
                    message, message_dict,
                    (mail_message_ids.model, mail_message_ids.res_id, custom_values, self._uid, None),
                    update_author=True, assert_model=True, create_fallback=True, allow_private=True)
                print "@@@@@@@@@@@@@@@@@@@@@@1------",route
                if route:
                    _logger.info(
                        'Routing mail from %s to %s with Message-Id %s: Searching though Subject to a private message: %s, custom_values: %s, uid: %s',
                        email_from, email_to, message_id, mail_message_ids.id, custom_values, self._uid)
                    return [route]
                elif route is False:
                    return []
                    
	_logger.info('Searching though Subject to  %s, Is failed for MEssage %s',sub_msg_id, message_id)
	
        # no route found for a matching reference (or reply), so parent is invalid
        message_dict.pop('parent_id', None)

        # 4. Look for a matching mail.alias entry
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = \
             ','.join([decode_header(message, 'Delivered-To'),
                       decode_header(message, 'To'),
                       decode_header(message, 'Cc'),
                       decode_header(message, 'Resent-To'),
                       decode_header(message, 'Resent-Cc')])
        local_parts = [e.split('@')[0].lower() for e in tools.email_split(rcpt_tos)]
        if local_parts:
            aliases = Alias.search([('alias_name', 'in', local_parts)])
            if aliases:
                routes = []
                for alias in aliases:
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(cr, uid, message, context=context)
                        user_id = self._uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, eval(alias.alias_defaults), user_id, alias)
                    route = self.message_route_verify(
                        message, message_dict, route,
                        update_author=True, assert_model=True, create_fallback=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 5. Fallback to the provided parameters, if they work
        if not thread_id:
            # Legacy: fallback to matching [ID] in the Subject
            match = tools.res_re.search(decode_header(message, 'Subject'))
            thread_id = match and match.group(1)
            # Convert into int (bug spotted in 7.0 because of str)
            try:
                thread_id = int(thread_id)
            except:
                thread_id = False
        route = self.message_route_verify(
            message, message_dict,
            (fallback_model, thread_id, custom_values, self._uid, None),
            update_author=True, assert_model=True)
        if route:
            _logger.info(
                'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                email_from, email_to, message_id, fallback_model, thread_id, custom_values, self._uid)
            return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )
