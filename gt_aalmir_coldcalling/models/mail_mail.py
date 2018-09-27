
from openerp import api, fields, models, _
from openerp.addons.base.ir.ir_mail_server import MailDeliveryException
import psycopg2
from openerp import tools
import base64
import logging
from urlparse import urljoin
from urllib import urlencode
_logger = logging.getLogger(__name__)

class MailMail(models.Model):

    _inherit = "mail.mail"

    def fetch_cc_data(self, email_cc_ids):
	_logger.info('API-EXCEPTION Sen EMAIL Partners..',email_cc_ids[0])
        cc_data = ""
        if len(email_cc_ids[0])>2:
            for partner in self.env['res.partner'].browse(email_cc_ids[0][2]):
		_logger.info('API-EXCEPTION Sen EMAIL Partners..',partner.email)
                if partner.email:
                    cc_data +=partner.email
                cc_data += ','

        return cc_data

    def _get_mail_server(self, mail):
        user = self.env['res.users'].search([('partner_id', '=', mail.author_id.id)])
        mail_server = self.env['ir.mail_server'].search([('user_id','=',user.id)])
        if not mail_server:
            mail_server = self.env['ir.mail_server'].search([('user_id', '=', False)])
            print"mail_servermail_server",mail_server
            
        return mail_server.id, mail_server.smtp_user

    @api.multi
    def send(self, auto_commit=False, raise_exception=False):
        print "Send is called..."

        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        IrMailServer = self.env['ir.mail_server']

        for mail in self:
            try:
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model = self.env['ir.model'].sudo().search([('model', '=', mail.model)])[0]
                else:
                    model = None
                if model:
                    mail = mail.with_context(model_name=model.name)
                    # code to upadate sales person on email send in lead.
                    if mail.mail_message_id.model == 'crm.lead':
                    	crm_id = self.env['crm.lead'].search([('id','=',mail.mail_message_id.res_id)])
			if not crm_id.user_id:
				crm_id.user_id=mail.mail_message_id.create_uid.id
                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                               for a in mail.attachment_ids.sudo().read(['datas_fname', 'datas'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail.send_get_email_dict())
                for partner in mail.recipient_ids:
                    email_list.append(mail.send_get_email_dict(partner=partner))

                # headers
                headers = {}
                bounce_alias = self.env['ir.config_parameter'].get_param("mail.bounce.alias")
                catchall_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s-%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s-%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due do sending an email without computed recipients.'),
                })
                mail_sent = False

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None

                if self._context and self._context.has_key('email_cc_ids') and self._context.get('email_cc_ids'):
                    email_cc = tools.email_split(self.fetch_cc_data(self._context.get('email_cc_ids')))
                else:
                    email_cc = tools.email_split(mail.email_cc)

                mail_server_id, email_from = self._get_mail_server(mail)
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=email_cc,
                        reply_to=email_from,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = IrMailServer.send_email(msg, mail_server_id=mail_server_id)
                    except AssertionError as error:
                        if error.message == IrMailServer.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                mail._postprocess_sent_message_v9(mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                raise
            except psycopg2.Error:
                # If an error with the database occurs, chances are that the cursor is unusable.
                # This will lead to an `psycopg2.InternalError` being raised when trying to write
                # `state`, shadowing the original exception and forbid a retry on concurrent
                # update. Let's bubble it.
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message_v9(mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise
            if auto_commit is True:
                self._cr.commit()
        return True

    @api.model
    def create(self, values):
	n_string=''
       	if values.get('model') =='crm.lead' and values.get('res_id'):
       		n_string="SENDAPI-"+str(values.get('res_id'))
	if values.get('model') =='sale.order' and values.get('res_id'):
		sale_id= self.env['sale.order'].browse(values.get('res_id'))
		if sale_id and sale_id.opportunity_id:
       			n_string="SENDAPI-"+str(sale_id.opportunity_id.id)
	body1 =''
	base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	values.update({'n_body':values.get('body')})
    	query = {'db': self._cr.dbname}
	#if values.get('partner_ids'):
    	body1 +='<div style="color:black">  <ul><li>To : '
    	if values.get('mail_message_id'):
		message_id=self.env['mail.message'].browse(values.get('mail_message_id'))
		if message_id.model =='crm.lead' and message_id.res_id:
	       		n_string="SENDAPI-"+str(message_id.res_id)
		if message_id.model =='sale.order' and message_id.res_id:
			sale_id= self.env['sale.order'].browse(message_id.res_id)
			if sale_id and sale_id.opportunity_id:
	       			n_string="SENDAPI-"+str(sale_id.opportunity_id.id)
		if '<div style="color:black">  <ul><li>To : '+str(values.get('email_to')) not in message_id.body:
			for rec in message_id.partner_ids:
				fragment = {
				    'model': 'res.partner',
				    'view_type': 'form',
				    'id': rec.id,
					 }
			  	url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
			  	text_link = _("""<a href="%s" target=_blank>%s</a> """) % (url,rec.name)
			  	body1 +=str(text_link)+','+' '
    	elif values.get('recipient_ids'):
		for key,rec in enumerate(values.get('recipient_ids')): 
			fragment = {
			    'model': 'res.partner',
			    'view_type': 'form',
			    'id': rec[1],
				 }
			url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
			text_link = _("""<a href="%s" target=_blank>%s</a> """) % (url,self.env['res.partner'].browse(rec[1]).name)
			body1 +=str(text_link)+','+' '
	elif values.get('email_to'):
		body1+= str(values.get('email_to'))
     	#if body1:
	body1 +="</li></ul> "
	body1 +='<ul><li>Subject : '+str(values.get('subject'))+"</li></ul> "
	body1 +='<ul><li>Message : '+str(values.get('body') if values.get('body') else values.get('body_html'))+"</li></ul> "
	body1 +='</div>'	
	if values.get('mail_message_id'):
		message_id=self.env['mail.message'].browse(values.get('mail_message_id'))
		if '<div style="color:black">  <ul><li>To : ' not in message_id.body:
			self.env['mail.message'].browse(values.get('mail_message_id')).write({'body':body1})
	else:
		values.update({'body':body1})
	if n_string:

		values.update({'body_html':values.get('body_html')+str('<p style="display:none" name="APINumber">'+str(n_string)+'</p>')})
	if '<div style="color:black">  <ul><li>To : ' in values.get('body_html') and values.get('mail_message_id'):
		mail_id=self.env['mail.mail'].search([('mail_message_id','=',values.get('mail_message_id'))],limit=1)
		if mail_id.body_html:
			values.update({'body_html':mail_id.body_html})	
	m_id=super(MailMail, self).create(values)
        return m_id

class Message(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        # coming from mail.js that does not have pid in its values
        return super(Message, self).create(values)

