
from openerp import fields, models, api, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp
import pytz
from openerp import tools
from openerp.exceptions import UserError
import time
from openerp.osv import osv
import datetime as new_dt
import logging
from openerp import http
_logger = logging.getLogger(__name__)

# /home/jupical/workspasce/odoo_9.0/addons/web/static/src/js/widgets/notification.js
# /home/jupical/workspasce/odoo_9.0/addons/web/static/src/xml/base.xml

class CalendarEvent(models.Model):
    
    _inherit = "calendar.event"
    
    lead_act = fields.Boolean('Lead Activity', default=False)
    
class calendar_attendee(osv.Model):
    """
    Calendar Attendee Information
    """
    _inherit = 'calendar.attendee'
    
    def _send_mail_to_attendees(self, cr, uid, ids, email_from=tools.config.get('email_from', False),
                                template_xmlid='calendar_template_meeting_invitation', force=False, context=None):
        return super(calendar_attendee, self)._send_mail_to_attendees(cr, uid, ids, email_from=email_from,
                                template_xmlid='my_calendar_template_meeting_invitation', force=force, context=context)
        
class calendar_alarm_manager(osv.AbstractModel):
    _inherit = 'calendar.alarm_manager'
        
    def do_mail_reminder(self, cr, uid, alert, context=None):
        if context is None:
            context = {}
        res = False

        event = self.pool['calendar.event'].browse(cr, uid, alert['event_id'], context=context)
        alarm = self.pool['calendar.alarm'].browse(cr, uid, alert['alarm_id'], context=context)

        if alarm.type == 'email':
            res = self.pool['calendar.attendee']._send_mail_to_attendees(
                cr,
                uid,
                [att.id for att in event.attendee_ids],
                email_from=event.user_id.partner_id.email,
                template_xmlid='my_calendar_template_meeting_reminder',
                force=True,
                context=context
            )
        return res
    
    def do_notif_reminder(self, cr, uid, alert, context=None):
        alarm = self.pool['calendar.alarm'].browse(cr, uid, alert['alarm_id'], context=context)
        event = self.pool['calendar.event'].browse(cr, uid, alert['event_id'], context=context)

        if alarm.type == 'notification':
            message = event.display_time

            delta = alert['notify_at'] - datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24

            return {
                'event_id': event.id,
                'title': event.event_name or event.name,
                'message': message,
                'timer': delta,
                'notify_at': alert['notify_at'].strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }

class CalenderEvent(models.Model):

    _inherit = 'calendar.event'

    event_type = fields.Selection([('task', 'Task'), ('meeting', 'Meeting'), ('call', 'Calling'), ('other', 'Other')],
                                  string="Event Type", default='other')

class CrmLead(models.Model):

    _inherit= "crm.lead"

    def retrieve_sales_dashboard(self, cr, uid, context=None):
        res = super(CrmLead, self).retrieve_sales_dashboard(cr, uid, context=context)

        res.update({
            'meeting': {
                'today': 0,
                'next_7_days': 0,
            },
            'task': {
                'today': 0,
                'next_7_days': 0,
            },
            'call': {
                'today': 0,
                'next_7_days': 0,
            },#CH_020 start add to show data in dashboard >>>
	    'done': {
                'this_month': 0,
                'last_month': 0,
            },
            'won': {
                'this_month': 0,
                'last_month': 0,
            },#CH_020 end <<<
	   })

        # Meetings
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        max_date = (datetime.now() + timedelta(days=8)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date),
            ('user_id','=',uid)
        ]
        # We need to add 'mymeetings' in the context for the search to be correct.
        calendar_obj = self.pool.get('calendar.event')
        meetings = calendar_obj.search(cr, uid, meetings_domain, context=context)
        for meeting in calendar_obj.browse(cr, uid, meetings, context=context):
            if meeting.start_datetime:
                start = datetime.strptime(meeting.start_datetime, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                if meeting.event_name and meeting.event_type and meeting.event_type == 'meeting':
                    if start == date.today():
                        res['meeting']['today'] += 1
                    if start >= date.today() and start <= date.today() + timedelta(days=7):
                        res['meeting']['next_7_days'] += 1
                elif meeting.event_name and meeting.event_type and meeting.event_type == 'task':
                    if start == date.today():
                        res['task']['today'] += 1
                    if start >= date.today() and start <= date.today() + timedelta(days=7):
                        res['task']['next_7_days'] += 1
                elif meeting.event_name and meeting.event_type and meeting.event_type == 'call':
                    if start == date.today():
                        res['call']['today'] += 1
                    if start >= date.today() and start <= date.today() + timedelta(days=7):
                        res['call']['next_7_days'] += 1

	#CH_N020 add to get WON opportunities data start >>>
	opportunities = self.pool.get('sale.order').search(cr, uid,[('state','in',('sale','done')), ('user_id','=',uid)],context=context)
	
	for opp in self.pool.get('sale.order').browse(cr, uid,opportunities):
            # Won in Opportunities
            if opp.date_order:
		#current_month_start=new_dt.date.today().replace(day=1)
                date_closed = datetime.strptime(opp.date_order, tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                if date_closed <= date.today() and date_closed >= date.today().replace(day=1):
                    if opp.n_base_currency_amount:
                        res['won']['this_month'] += opp.n_base_currency_amount

                elif date_closed < date.today().replace(day=1) and date_closed >= date.today().replace(day=1) - relativedelta(months=+1):
                    if opp.n_base_currency_amount:
                        res['won']['last_month'] += opp.n_base_currency_amount

        # crm.activity is a very messy model so we need to do that in order to retrieve the actions done.
        cr.execute("""
            SELECT
                m.id,
                m.subtype_id,
                m.date,
                l.user_id,
                l.type
            FROM
                "mail_message" m
            LEFT JOIN
                "crm_lead" l
            ON
                (m.res_id = l.id)
            INNER JOIN
                "crm_activity" a
            ON
                (m.subtype_id = a.subtype_id)
            WHERE
                (m.model = 'crm.lead') AND (l.user_id = %s) AND (l.type = 'opportunity')
        """, (uid,))
        activites_done = cr.dictfetchall()

        for act in activites_done:
            if act['date']:
                date_act = datetime.strptime(act['date'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                if date_act <= date.today() and date_act >= date.today().replace(day=1):
                        res['done']['this_month'] += 1
                elif date_act < date.today().replace(day=1) and date_act >= date.today().replace(day=1) - relativedelta(months=+1):
                    res['done']['last_month'] += 1

        user = self.pool('res.users').browse(cr, uid, uid, context=context)
        res['done']['target'] = user.target_sales_done
        res['won']['target'] = user.monthly_target

        res['currency_id'] = user.company_id.currency_id.id
	#CH_N020 end <<<
        return res

    
    def _merge_notify(self, cr, uid, opportunity_id, opportunities, context=None):
        """
        Create a message gathering merged leads/opps information.
        """
        #TOFIX: mail template should be used instead of fix body, subject text
        details = []
        result_type = self._merge_get_result_type(cr, uid, opportunities, context)
        if result_type == 'lead':
            merge_message = _('Merged leads')
        else:
            merge_message = _('Merged opportunities')
        subject = [merge_message]
#        for opportunity in opportunities:
#            subject.append(opportunity.name)
#            title = "%s : %s" % (opportunity.type == 'opportunity' and _('Merged opportunity') or _('Merged lead'), opportunity.name)
#            fields = list(CRM_LEAD_FIELDS_TO_MERGE)
#            details.append(self._mail_body(cr, uid, opportunity, fields, title=title, context=context))
#
#        # Chatter message's subject
#        subject = subject[0] + ": " + ", ".join(subject[1:])
#        details = "\n\n".join(details)
#        return self.message_post(cr, uid, [opportunity_id], body=details, subject=subject, context=context)
    
    def log_meeting(self, cr, uid, ids, meeting_subject, meeting_date, duration, context=None):
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        meet_date = datetime.strptime(meeting_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
#        meeting_usertime = fields.datetime.context_timestamp(cr, uid, meet_date, context=context).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        html_time = "<time datetime='%s+00:00'>%s</time>" % (meeting_date, meet_date)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (html_time, meeting_subject, duration)
        return True
    
    @api.model
    def get_partner(self):
        user = self.env['res.users'].sudo().browse(self.env.uid)
        return [user.partner_id.id]

    assign_partner = fields.Many2many('res.partner', 'activity_partner_rel' , 'lead_id', 'partner_id', string="Assign To", default=get_partner)
    activ_log = fields.Boolean('Activity', default=False)
    date_action1 = fields.Datetime(string='Next Activity Date', select=True, default=datetime.now())
    task = fields.Boolean('task', default=False)
    call = fields.Boolean('call', default=False)
    meeting = fields.Boolean('meeting', default=False)
    note = fields.Boolean('note', default=False)
    set_reminder = fields.Boolean('Reminder',default=False)
    set_schedule = fields.Boolean('Schedule',default=False)
    availability = fields.Selection([('available', 'Available'), ('not_available', 'Not Available')],
                                    string="Availability", default="available")
    action_visible = fields.Boolean(string="Action Date visible", default=False)
    notify_manager = fields.Boolean('Notify Manager?', default=False)

    @api.onchange('date_due_action', 'date_action')
    @api.one
    def onchange_date(self):
        if self.date_action:
            if self.date_action < time.strftime('%Y-%m-%d 00:00:00'):
                raise UserError(_('Please change Schedule Date which must be greater to Current Date'))
            
    @api.onchange('set_reminder', 'set_schedule')
    @api.one
    def onchange_set_reminder(self):
        if self.set_reminder == True or self.set_schedule == True:
            self.action_visible = True
        else:
            self.action_visible = False

    @api.multi
    def action_activity_reminder(self):
        lead = self[0]
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        res['context'] = {
             'search_default_lead_act' : True,
        }
        return res

    def _get_event_type(self, lead):

        event_type = 'other'
        if lead.next_activity_id.name =='Meeting':
            event_type = 'meeting'
        elif lead.next_activity_id.name =='Task':
            event_type = 'task'
        elif lead.next_activity_id.name =='Call':
            event_type = 'call'
        return event_type

    def _get_assignee_names(self, lead):

        assignee = ""
        if lead.assign_partner:
            for partner in lead.assign_partner:
                assignee += partner.name
                assignee += "/"
            assignee += lead.user_id and lead.user_id and lead.user_id.name or ""
        else:
            assignee += lead.user_id and lead.user_id and lead.user_id.name or ""
        return assignee

    def _get_assignee_cc(self, lead):

        cc_emails = []
        if lead.assign_partner:
            for partner in lead.assign_partner:
                if partner.email:
                    cc_emails.append(partner.email)
        return cc_emails

    def _check_sale_group(self, lead):

        return self.env['res.users'].has_group('base.group_sale_manager')

    def _prepare_current_url(self, lead):

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url +="/web#id=%s"%str(lead.id)
        base_url +="&view_type=form&model=crm.lead&menu_id=186&action=251"
        return base_url

    @api.multi
    def log_next_activity_done(self):  
        to_clear_ids = []
        for lead in self:
            if not lead.next_activity_id:
                continue
                
            if lead.next_activity_id.name == 'Call' and not lead.title_action:
                raise UserError(('Please Add Remark'))
            
            if lead.next_activity_id.name in ['Task', 'Note', 'Meeting'] and not lead.title_action:
                raise UserError(('Please Add Description'))
            
            body_html = """<div><b>${object.next_activity_id.name}</b></div>
            
            %if object.next_activity_id.name == 'Meeting':

%if object.date_action:
<div>Schedule Date: ${object.date_action}</div>
%endif
%if object.title_action:
<div>Description   :   ${object.title_action}</div>
%endif
% if object.assign_partner:
  <div> Attendee   :   
	% for attendee in object.assign_partner:
	  ${attendee.name}
	  % if attendee.email:
	      ( ${attendee.email} ) ,
          %endif
	% endfor
  </div>
%endif
%endif
            %if object.next_activity_id.name == 'Task':
%if object.date_action:
<div>Task Expected Date: ${object.date_action}</div>
%endif
%if object.title_action:
<div>Description   :   ${object.title_action}</div>
%endif
% if object.assign_partner:
  <div> Assign To   :   
	% for attendee in object.assign_partner:
	  ${attendee.name}
	  % if attendee.email:
	      ( ${attendee.email} ) ,
          %endif
	% endfor
  </div>
%endif
%endif
            %if object.next_activity_id.name == 'Call':
%if object.date_action:
<div>Reminder Date   :   ${object.date_action}</div>
%endif
<div>Availability   :   ${(object.availability).title().replace('_', ' ')}</div>
%if object.title_action:
<div>Remark   :   ${object.title_action}</div>
%endif
%endif
%if object.next_activity_id.name == 'Note':
%if object.title_action:
<div>${object.title_action}</div>
%endif
%endif"""


            rendered_template = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'crm.lead', lead.id, context=self._context)
            msg_id = lead.message_post(rendered_template, subtype_id=lead.next_activity_id.subtype_id.id)
            #Sending instance email for notification!
            activity_type = lead.next_activity_id.name
            is_manager = self._check_sale_group(lead)
            current_url = self._prepare_current_url(lead)
            if activity_type in ('Task','Note','Meeting'):
                mail_server_obj = self.env['ir.mail_server']
                mail_server = mail_server_obj.search([('user_id', '=', self._uid)])
                if not mail_server:
                    mail_server = mail_server_obj.search([('user_id', '=', False)])
                # assignee = self._get_assignee_names(lead)
                login_user =self.env['res.users'].browse(self._uid)
                sub_message = login_user.partner_id and login_user.partner_id.name and login_user.partner_id.name.title() or "Sales "
                if activity_type == 'Task':
                    sub_message += " has assigned new task to you for "
                elif activity_type =='Note':
                    sub_message += " has added one note for you on "
                sub_message += lead.name
                instance_email_body_html= """ """
                instance_email_body_html += _("Hello User,")
                instance_email_body_html += "<br/><br/>"
                body_message = sub_message
                body_message += "<br/><br/>"
                body_message += "<b><u>Here is more detail:</u></b>"
                body_message += "<br/><br/>"
                if activity_type == 'Task':
                    body_message += "<b>Task creation date : </b>"
                    body_message += datetime.strftime(datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
                    if lead.set_schedule:
                        body_message += "<br/>"
                        body_message += "<b>Task scheduled date : </b>"
                        body_message += lead.date_action or ""
                    body_message += "<br/>"
                    body_message += "<b>Task description : </b>"
                    body_message += lead.title_action or ""
                elif activity_type == 'Meeting' and lead.set_schedule:
                    body_message += "<b>Meeting creation date :</b>"
                    body_message += datetime.strftime(datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
                    body_message += "<br/>"
                    body_message += "<b>Meeting scheduled date :</b>"
                    body_message += lead.date_action or ""
                    body_message += "<br/>"
                    body_message += "<b>Meeting description :</b>"
                    body_message += lead.title_action or ""
                elif activity_type =='Note':
                    body_message += "<b>Note description :</b>"
                    body_message += lead.title_action or ""
                body_message += "<br/>"
                body_message += "<b>Customer : </b>"
                body_message += lead.partner_id and lead.partner_id.name or ""
                body_message += "<br/>"
                body_message += "<b>Lead name :</b>"
                lead_url_data = "<a href=%s>"%current_url
                lead_url_data += lead.name
                lead_url_data += "</a>"
                body_message += lead_url_data
                body_message += "<br/><br/>"

                body_message += "--------------------------"
                if mail_server.user_id:
                    body_message += mail_server.user_id.signature or ""
                instance_email_body_html += body_message
                cc_emails = self._get_assignee_cc(lead)
                email_to = lead.user_id and lead.user_id.partner_id and lead.user_id.partner_id.email or 'no-reply@mir.ae'
                if activity_type == 'Note'  and lead.notify_manager:
                    team = self.env['crm.team'].search([], limit=1)
                    if team and team.user_id:
                        email_to = team.user_id.login

                msg = mail_server_obj.build_email(
                    email_from=mail_server.smtp_user,
                    email_to=[email_to],
                    email_cc=cc_emails,
                    subject=sub_message,
                    body=instance_email_body_html,
                    reply_to=mail_server.smtp_user,
                    subtype='html',
                    subtype_alternative='plain',
                )
                try:
                    if activity_type =='Task' or is_manager or lead.notify_manager or lead.set_schedule:
                        res = mail_server_obj.send_email(msg, mail_server_id=mail_server.id)
                except AssertionError as error:
                    if error.message == mail_server_obj.NO_VALID_RECIPIENT:
                        _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                     msg_id, email_to)
            to_clear_ids.append(lead.id)
            
#            if lead.next_activity_id.name in ['Meeting'] or lead.set_reminder == True or lead.set_schedule == True:
            if lead.set_reminder == True or lead.set_schedule == True:
                alarm_obj = self.env['calendar.alarm']
                event_obj = self.env['calendar.event']
                user = self.env['res.users'].browse(self.env.uid)
                alarm_ids = alarm_obj.search([('duration','=', 15), ('interval','=','minutes')])
                lead.write({'activ_log': True})
                par_id = [part.id for part in lead.assign_partner]
                par_id += [user.partner_id.id, ]
                event_type = self._get_event_type(lead)
                value = {
                    'event_name': '[' + lead.next_activity_id.name + '] ' + (lead.title_action or ''),
                    'name': lead.name,
                    'lead_id': lead.id,
                    'opportunity_id': lead.id,
                    'start_date' : lead.date_action or datetime.now(),
                    'start' : lead.date_action or datetime.now(),
                    'duration' : 0.5,
                    'partner_ids' : [(6, 0, list(set(par_id)))],
                    'alarm_ids' : [(6, 0, alarm_ids.ids)] ,
                    'allday' : False,
                    'lead_act': True,
                    'event_type':event_type,
                    'user_id':lead.user_id and lead.user_id.id or self._uid,
                }
                start = datetime.strptime((lead.date_action or datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)), DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_date'] = (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                value['stop'] = lead.date_due_action or (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_datetime'] = lead.date_due_action or (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                value['start_date'] = start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                value['start'] = start.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                event_obj.create(value)
            lead.write({'assign_partner': [(6,0,[])], 'task': False,'meeting_or_task': False, 'date_due_action': False,'date_action': False,})
            lead.write({'last_activity_id': lead.next_activity_id.id, 
                'title_action': False,
                'date_action': False,
                'date_due_action': False,
                'assign_partner': [(6,0, [])],
                'meeting_or_task' : False,
                'task': False,
                'set_schedule': False,
                'set_reminder': False,
                'availability': 'available',
                'note': False,
                'call': False,
                'action_visible': False,
                'meeting': False,
                'notify_manager':False})

        if to_clear_ids:
            self.pool['crm.lead'].cancel_next_activity(self._cr, self._uid, to_clear_ids, context=self._context)
        return True
    
    @api.multi
    def cancel_next_activity(self):
        return self.write({
            'next_activity_id': False,
            'date_action': False,
            'title_action': False,
            'next_action1': False,
            'next_action2': False,
            'next_action3': False,
            'title_action': False,
            'date_action': False,
            'date_due_action': False,
            'assign_partner': [(6,0, [])],
            'meeting_or_task' : False,
            'task': False,
            'set_schedule': False,
            'set_reminder': False,
            'availability': 'available',
            'note': False,
            'call': False,
            'meeting': False,
            'action_visible': False,
        })

    @api.onchange('availability', 'next_activity_id')
    @api.one
    def onchange_avail(self):
        if self.availability != 'available' and self.next_activity_id.name == 'Call':
            self.update({'set_reminder': True})
        if self.availability == 'available' or self.next_activity_id.name != 'Call' or not self.next_activity_id:
            self.update({'set_reminder': False})
        if self.next_activity_id.name in  ['Call','Note']:
            self.update({'assign_partner':False})

    def onchange_next_activity_id(self, cr, uid, ids, next_activity_id, context=None):
        if not next_activity_id:
            return {'value': {
                'next_action1': False,
                'next_action2': False,
                'next_action3': False,
                'title_action': False,
                'date_action': False,
                'date_due_action': False,
                'assign_partner': [(6,0, [])],
                'meeting_or_task' : False,
                'task': False,
                'set_schedule': False,
                'set_reminder': False,
                'availability': 'available',
                'note': False,
                'call': False,
                'meeting': False,
                'action_visible': False,
            }}
        activity = self.pool['crm.activity'].browse(cr, uid, next_activity_id, context=context)
        date_action = False;task=False;task1= False;task2= False;task3= False;task4= False;
        if activity.days:
            date_action = (datetime.now() + timedelta(days=activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        if activity.name in ['Meeting', 'Task']:
            task = True
        if activity.name in ['Task']:
            task1 = True
        if activity.name in ['Note']:
            task2 = True
        if activity.name in ['Call']:
            task3 = True
        if activity.name in ['Meeting']:
            task4 = True
        return {'value': {
            'next_activity_1': activity.activity_1_id and activity.activity_1_id.name or False,
            'next_activity_2': activity.activity_2_id and activity.activity_2_id.name or False,
            'next_activity_3': activity.activity_3_id and activity.activity_3_id.name or False,
            'title_action': activity.description,
#            'date_action': datetime.now(),
            'last_activity_id': False,
            'task': task1,
            'meeting_or_task' : task,
            'note' : task2,
            'call' : task3,
            'meeting' : task4,
            'set_schedule': False,
            'set_reminder': False,
            'date_action':False,
            'assign_partner': [(6,0, [])],
        }}


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(SaleOrder, self).search(args, offset, limit, order, count=count)
        context = self._context or {}
        if context.get('from_lead_button'):
            if context.get('search_default_sales'):
                if context.get('search_default_cancel'):
                    return res.filtered(lambda record: record.state != 'cancel')
        return res
