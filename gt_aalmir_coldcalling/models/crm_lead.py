# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# CH01 -- Changes to add email and pop for coldcolling

from openerp import api, fields, models, _
from datetime import datetime,timedelta, date
from openerp import tools
from openerp.exceptions import UserError
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import email_re, email_split
from openerp import SUPERUSER_ID
from operator import itemgetter
from dateutil.relativedelta import relativedelta

CRM_LEAD_FIELDS_TO_MERGE = ['name',
    'partner_id',
    'campaign_id',
    'company_id',
    'country_id',
    'team_id',
    'state_id',
    'stage_id',
    'medium_id',
    'source_id',
    'user_id',
    'title',
    'city',
    'contact_name',
    'description',
    'email',
    'fax',
    'mobile',
    'partner_name',
    'phone',
    'probability',
    'planned_revenue',
    'street',
    'street2',
    'zip',
    'create_date',
    'date_action_last',
    'date_action_next',
    'email_from',
    'email_cc',
    'partner_name']

import time
import re
import logging
_logger = logging.getLogger(__name__)
class crm_lead2opportunity_partner(models.Model):
    _inherit = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'
     
    @api.multi
    def action_apply(self):
       res= super(crm_lead2opportunity_partner , self).action_apply()
       lead_obj = self.env['crm.lead']
       lead_ids = self._context.get('active_ids')
       for lead in lead_obj.browse(lead_ids):
           vals={'user_id':lead.user_id.id, 'lead_id':lead.id, 'customer_name':lead.partner_id.name, 
                  'name':lead.name,'email':lead.email_from, 'contact_time':datetime.now(),
                   'is_qualify':True}
           self.env['crm.coldcalling.history'].create(vals)
           lead.write({'qualified_date':datetime.now() , 'coldcalling_id':lead.id,'lead_create_date':datetime.now()})
       return res
       
class ResUsers(models.Model):
    _inherit='res.users'
    salesperson_target=fields.Char('Daily Calls Target')
    salesperson_bool=fields.Boolean('Is Salesperson')
    monthly_target=fields.Char('Monthly Sale Target')
    
class crm_lead(models.Model):
    _inherit = "crm.lead"
    
    @api.multi
    def send_mail(self):
        template_id=self.env['mail.template']
        template=template_id.search([('name', '=', 'Student Details - Send by Email')])[0]
        #res = self.pool.get('mail.template').send_mail(cr, uid, template, ids, force_send=True, context=context)
        return self.pool['mail.template'].send_mail(
   self.env.cr, self.env.uid, template.id, self.id, force_send=True,
   context=self.env.context)
    ### Add coldcalling id in oppotunity for track record  by vml
    coldcalling_id=fields.Many2one('crm.lead')
    ### add pop for coldcalling id in oppotunity for track record  by vml

#CH_N073 >>>
    @api.multi
    @api.depends('partner_id.mobile','partner_id.phone','mobile','phone')
    def _get_mobileNo(self):
	for rec in self:
		if rec.partner_id:
			partner_ids=self.env['res.partner'].search([('id','=',rec.partner_id.id)])
			if partner_ids.mobile:
				rec.mobile=partner_ids.mobile
			if partner_ids.phone:
				rec.phone=partner_ids.phone
#CH_N073 <<<

    @api.multi
    def action_coldcalling_opportinity(self):
        ir_model_data = self.env['ir.model.data']
        form_id = ir_model_data.get_object_reference('gt_sale_quotation', 'popup_coldcalling_opportunity')[1]
        return {
            'name' : 'ColdCalling',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.lead',
            'views': [(form_id, 'form')],
            'view_id': form_id,
            'target': 'new',
            'res_id': self[0].id,
        }
    partner_id =  fields.Many2one("res.partner", "Customer")
#    email_from = fields.Char(related='partner_id.email', string="Email")
    #phone = fields.Char(related='partner_id.phone', string="Phone")
    #mobile = fields.Char(related='partner_id.mobile', string="Mobile")
    mobile1 = fields.Char(compute='_get_mobileNo', string="Mobile")
    phone1 = fields.Char(compute='_get_mobileNo', string="Mobile")
    write_date = fields.Datetime(string="Last updated Date")
    irrelevant_reason_id = fields.Many2one('irrelevant.reason', 'Irrelevant Reason')
    irr_reason_description = fields.Text("Irrelevant Description")
    
    is_contract =fields.Boolean('Is contract',help='Pipeline is a Contracted Customer pipeline,it can create More than one sales orders',default=False)
    ###add contarct name
    contract_name=fields.Char('Contract Name/No.',help='Fill the Contract name/ number')
    
    def _prepare_current_url(self, lead):

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url +="/web#id=%s"%str(lead.id)
        base_url +="&view_type=form&model=crm.lead&menu_id=186&action=251"
        return base_url

    def _send_assign_notfication(self, lead, vals, real_user_id):
        recipient = self.env['res.users'].browse(vals.get('user_id'))
        sender = self.env['res.users'].browse(real_user_id)
        mail_server_obj = self.env['ir.mail_server']
        mail_server = mail_server_obj.search([('user_id', '=', real_user_id)], limit=1)
        if not mail_server:
            mail_server = mail_server_obj.search([('user_id', '=', False)], limit=1)
        if not mail_server:
            raise UserError(("Please configure outgoing mail server!"))
        current_url = self._prepare_current_url(lead)
        sub_message = "Lead has been assigned to you for "
        sub_message += lead.name
        recipient_name = recipient.name or ""
        instance_email_body_html = """ """
        instance_email_body_html += _("Hello %s,"% recipient_name.title())
        instance_email_body_html += "<br/><br/>"
        body_message = sub_message
        body_message += "<br/><br/>"
        body_message += "<b><u>Here is more detail:</u></b>"
        body_message += "<br/><br/>"
        body_message += "<b>Lead assigned time : </b>"
        body_message += datetime.strftime(datetime.now(), DEFAULT_SERVER_DATETIME_FORMAT)
        body_message += "<br/>"
        body_message += "<b>Customer : </b>"
        body_message += lead.partner_id and lead.partner_id.name or ""
        body_message += "<br/>"
        body_message += "<b>Lead :</b>"
        lead_url_data = "<a href=%s>" % current_url
        lead_url_data += lead.name
        lead_url_data += "</a>"
        body_message += lead_url_data
        body_message += "<br/>"
        body_message += "<b>Assigned by : </b>"
        body_message += sender.partner_id and sender.partner_id.name and sender.partner_id.name.title() or ""
        body_message += "<br/><br/>"
        body_message += "--------------------------"
        if mail_server.user_id:
            body_message += mail_server.user_id.signature or ""
        instance_email_body_html += body_message
        email_to = recipient and recipient.partner_id and recipient.partner_id.email or recipient.login
	if email_to:
		msg = mail_server_obj.build_email(
		    email_from=mail_server.smtp_user,
		    email_to=[email_to],
		    email_cc=[],
		    subject=sub_message,
		    body=instance_email_body_html,
		    reply_to=mail_server.smtp_user,
		    subtype='html',
		    subtype_alternative='plain',
		)
		try:
		    res = mail_server_obj.send_email(msg, mail_server_id=mail_server.id)
		except AssertionError as error:
		    if error.message == mail_server_obj.NO_VALID_RECIPIENT:
		        _logger.info("Ignoring invalid recipients for mail.mail %s",
		                      email_to)
        return True

    @api.multi
    def write(self, vals):
        for lead in self:
            if self._context.has_key('real_user_id'):
                real_user_id = self._context.get('real_user_id')
            else:
                real_user_id = self._uid
            if vals.has_key('user_id') and vals.get('user_id')!= real_user_id:
                self._send_assign_notfication(lead, vals, real_user_id)
                quoations = self.env['sale.order'].search([('opportunity_id','=',lead.id)])
                quoations.write({'user_id':real_user_id})
            if vals.get('stage_id') and lead.stage_id.name == 'Lost':
                raise UserError(("Can't move from Lost"))
            if (not lead.user_id) and self.user_has_groups('base.group_sale_salesman'): #and not self.user_has_groups('base.group_sale_manager') and not self.user_has_groups('base.group_system'):
                if not vals.get('user_id'):
                    vals.update({'user_id': lead.env.uid})
                    
	#CH_N073 >>>
	    if vals.get('partner_id') or self.partner_id:
		partner_id= vals.get('partner_id') if vals.get('partner_id') else self.partner_id.id
		partner_ids=self.env['res.partner'].search([('id','=',partner_id)])
		if vals.get('mobile'):
			partner_ids.mobile=vals.get('mobile')
		if vals.get('phone'):
			partner_ids.phone=vals.get('phone')
	#CH_N073<<<<<<<
	
	    if not lead.user_id :#and not vals.get('user_id'):
		ids=self.env['mail.message'].search([('res_id','=',lead.id),('create_uid','!=',1),('message_type','=','email')],order='id desc',limit=1) 
		if ids:
			vals.update({'user_id':ids.create_uid.id})
	    return super(crm_lead, lead).write(vals)

    @api.multi
    def unlink(self):
        for rec in self:
            obj = self.env['crm.lead.lost']
            rec_ids = obj.search([('lead_id','=', rec.id)])
            if rec_ids:
                rec_ids.unlink()
        return super(crm_lead, self).unlink()

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            if not self.name:
                self.name = self.partner_id and self.partner_id.name or ''
            if not self.contact_name:
                self.contact_name = self.partner_id and self.partner_id.name or ''
            if not self.phone:
                self.phone = self.partner_id and self.partner_id.phone or False
            if not self.mobile:
                self.mobile = self.partner_id and self.partner_id.mobile or False
            if not self.email_from:
                self.email_from = self.partner_id and self.partner_id.email or ''

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self._context.get('from_opp_form') and view_type=='tree':
            view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        if self._context.get('merge_form'):
            if view_type == 'form':
                view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        if self._context.get('needaction_menu_ref') == 'sale.menu_sale_quotations':
            if view_type=='form':
                view_id = self.env.ref('crm.crm_case_form_view_oppor').id
            if view_type=='tree':
                view_id = self.env.ref('crm.crm_case_tree_view_oppor').id
        res = super(crm_lead, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        return res

    def merge_opportunity(self, cr, uid, ids, user_id=False, team_id=False, context=None):
        """
        Different cases of merge:
        - merge leads together = 1 new lead
        - merge at least 1 opp with anything else (lead or opp) = 1 new opp

        :param list ids: leads/opportunities ids to merge
        :return int id: id of the resulting lead/opp
        """
        if context is None:
            context = {}

        if len(ids) <= 1:
            raise UserError(_('Please select more than one element (lead or opportunity) from the list view.'))

        opportunities = self.browse(cr, uid, ids, context=context)
        sequenced_opps = []
        # Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        # The confidence level increases with the stage sequence, except when the stage probability is 0.0 (Lost cases)
        # An Opportunity always has higher confidence level than a lead, unless its stage probability is 0.0
        for opportunity in opportunities:
            sequence = -1
            if opportunity.stage_id and opportunity.stage_id.on_change:
                sequence = opportunity.stage_id.sequence
            sequenced_opps.append(((int(sequence != -1), sequence, -opportunity.id), opportunity))

        sequenced_opps.sort(reverse=True)
        opportunities = map(itemgetter(1), sequenced_opps)
        ids = [opportunity.id for opportunity in opportunities]
        highest = opportunities[0]
        opportunities_rest = opportunities[1:]

        tail_opportunities = opportunities_rest

        fields = list(CRM_LEAD_FIELDS_TO_MERGE)
        merged_data = self._merge_data(cr, uid, ids, highest, fields, context=context)

        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id

        # Merge notifications about loss of information
        opportunities = [highest]
        opportunities.extend(opportunities_rest)

        self.merge_dependences(cr, uid, highest.id, tail_opportunities, context=context)
		#extra code in order management >>>>>start
        # Check if the stage is in the stages of the sales team. If not, assign the stage with the lowest sequence
        if merged_data.get('team_id'):
            team_stage_ids = self.pool.get('crm.stage').search(cr, uid, [('team_ids', 'in', merged_data['team_id']), ('type', 'in', [merged_data.get('type'), 'both'])], order='sequence', context=context)
            if merged_data.get('stage_id') not in team_stage_ids:
                merged_data['stage_id'] = team_stage_ids and team_stage_ids[0] or False
        # Write merged data into first opportunity
        self.write(cr, uid, [highest.id], merged_data, context=context)
        # Delete tail opportunities 
        # We use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
#        self.unlink(cr, SUPERUSER_ID, [x.id for x in tail_opportunities], context=context)
		#end <<<<<<<<<<<<<<<<<<<<
        stage_ids = self.pool.get('crm.stage').search(cr, SUPERUSER_ID, [('name','=', 'Merge')])
        if stage_ids:
            self.write(cr, SUPERUSER_ID, [x.id for x in tail_opportunities], {'stage_id' : stage_ids[0], 'type' : 'opportunity'}, context=context)
            merge_ids = [x.id for x in tail_opportunities]
            if highest.opp_merge_ids:
                merge_ids.extend(highest.opp_merge_ids._ids)
            self.write(cr, SUPERUSER_ID, [highest.id], {'opp_merge_ids' : [(6,0, merge_ids)]}, context=context)
        return highest.id

    def retrieve_sales_dashboard(self, cr, uid, context=None):
        res = {
            'meeting': {
                'today': 0,
                'next_7_days': 0,
            },
            'activity': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'closing': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'done': {
                'this_month': 0,
                'last_month': 0,
            },
            'won': {
                'this_month': 0,
                'last_month': 0,
            },
            'nb_opportunities': 0,
        }

        opportunities = self.search_read(
            cr, uid,
            [('type', '=', 'opportunity'), ('user_id', '=', uid)],
            ['date_deadline', 'next_activity_id', 'date_action', 'date_closed', 'planned_revenue'], context=context)

        for opp in opportunities:
            # Expected closing
            if opp['date_deadline']:
                date_deadline = datetime.strptime(opp['date_deadline'], tools.DEFAULT_SERVER_DATE_FORMAT).date()
                if date_deadline == date.today():
                    res['closing']['today'] += 1
                if date_deadline >= date.today() and date_deadline <= date.today() + timedelta(days=7):
                    res['closing']['next_7_days'] += 1
                if date_deadline < date.today():
                    res['closing']['overdue'] += 1

            # Next activities
            if opp['next_activity_id'] and opp['date_action']:
                date_action = datetime.strptime(opp['date_action'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
                if date_action == datetime.now():
                    res['activity']['today'] += 1
                if date_action >= datetime.now() and date_action <= datetime.now() + timedelta(days=7):
                    res['activity']['next_7_days'] += 1
                if date_action < datetime.now():
                    res['activity']['overdue'] += 1

            # Won in Opportunities
            if opp['date_closed']:
                date_closed = datetime.strptime(opp['date_closed'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
                if date_closed <= datetime.now() and date_closed >= datetime.now().replace(day=1):
                    if opp['planned_revenue']:
                        res['won']['this_month'] += opp['planned_revenue']
                elif date_closed < datetime.now().replace(day=1) and date_closed >= datetime.now().replace(day=1) - relativedelta(months=+1):
                    if opp['planned_revenue']:
                        res['won']['last_month'] += opp['planned_revenue']

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
                date_act = datetime.strptime(act['date'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
                if date_act <= datetime.now() and date_act >= datetime.now().replace(day=1):
                        res['done']['this_month'] += 1
                elif date_act < datetime.now().replace(day=1) and date_act >= datetime.now().replace(day=1) - relativedelta(months=+1):
                    res['done']['last_month'] += 1

        # Meetings
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        max_date = (datetime.now() + timedelta(days=8)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date)
        ]
        # We need to add 'mymeetings' in the context for the search to be correct.
        meetings = self.pool.get('calendar.event').search_read(cr, uid, meetings_domain, ['start'], context=context.update({'mymeetings': 1}) if context else {'mymeetings': 1})
        for meeting in meetings:
            if meeting['start']:
                start = datetime.strptime(meeting['start'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()

                if start == date.today():
                    res['meeting']['today'] += 1
                if start >= date.today() and start <= date.today() + timedelta(days=7):
                    res['meeting']['next_7_days'] += 1

        res['nb_opportunities'] = len(opportunities)

        user = self.pool('res.users').browse(cr, 1, uid, context=context)
        res['done']['target'] = user.target_sales_done
        res['won']['target'] = user.target_sales_won
        res['currency_id'] = user.company_id.currency_id.id
        return res

    @api.multi
    def action_schedule_reminder(self):
        return {
            'name': 'My Reminders',
            'view_type': 'form',
            'view_mode': 'calendar,tree,form',
            'res_model': 'calendar.event',
            'views': [[self.env.ref('calendar.view_calendar_event_calendar').id, 'calendar'],[self.env.ref('calendar.view_calendar_event_tree').id, 'tree'],[self.env.ref('calendar.view_calendar_event_form').id, 'form']],
            'type': 'ir.actions.act_window',
            'domain' : [('user_id','=',self.env.uid), ('cold_calling_reminder','=', True), ('lead_id','=',self[0].id)],
            'context' : {'lead_id' : self[0].id, 'default_lead_id' : self[0].id}
        }


    @api.multi
    def action_set_lost(self):
        """ Lost semantic: probability = 0, active = False """
        for rec in self:
            rec.write({'probability': 0})  #CH_N037 add code to set pipeline probabilty to Zero
            if self._context.get('from_opp'):
                stage_ids = self.env['crm.stage'].search([('name','=','Lost')])
                if stage_ids:
                    rec.stage_id = stage_ids[0].id
            else:
                ir_model_data = self.env['ir.model.data']
                try:
                    compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
                except ValueError:
                    compose_form_id = False

                message_obj = self.env['mail.message']
                m_ids = message_obj.search([('res_id','=',self[0].id), ('model','=', 'crm.lead'), ('body','!=','')])
                if m_ids:
                    l = len(m_ids)
                    msg = m_ids[l-1].body or ' '
                else:
                    msg = ''
                #if not msg:
#                    rec.probability = 0
                    #rec.active = False
                    #return True
                ctx = dict()
                ctx.update({
                    'default_model': 'crm.lead',
                    'default_res_id': self.ids[0],
                    'default_composition_mode': 'comment',
                    'default_partner_ids': [],
                    'default_subject': 'Forward',
                   # 'default_body': msg,
                    'mark_so_as_sent': True,
                    'lead_id' : self[0].id,
                    'from_irrelavent' : True

                })
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mail.compose.message',
                    'views': [(compose_form_id, 'form')],
                    'view_id': compose_form_id,
                    'target': 'new',
                    'context': ctx,
                }
        return True

    @api.model
    def create(self, vals):
        _logger.info('Context %s'%( self._context))

        if self._context.get('from_force_create'):
            if vals.get('email_from') and not vals.get('partner_id'):
                name, email = self.env['res.partner']._parse_partner_name(vals.get('email_from'))
                email = email.strip()
                vals.update({'contact_name': name, 'email_from': email})
#CH_N073 >>>
	if vals.get('partner_id'):
		partner_ids=self.env['res.partner'].search([('id','=',vals.get('partner_id'))])
		if vals.get('mobile'):
			partner_ids.mobile=vals.get('mobile')
		if vals.get('phone'):
			partner_ids.phone=vals.get('phone')
#CH_N073<<<

        if not self._context.get('from_so'):
            if self._context.get('cold_calling'):
                vals.update({'stage_2' : 'not_contacted', 'stage_id' : False})
            else:
                vals.update({'stage_2' : False})
            stage_obj = self.env['crm.stage']
            _logger.info("vals.get('type') %s"%(vals.get('type')))
            if vals.get('type') == 'opportunity' and self._context.get('from_lead_menu'):
                stage_ids = stage_obj.search([('name','=','Open')])
                _logger.info("stage_ids--------------%s"%(stage_ids))
                if stage_ids:
                    vals.update({'stage_id': stage_ids[0].id})
                if not vals.get('user_id'):
                    _logger.info("vals.get('user_id')-------------%s" %(vals.get('user_id')))
                    vals.update({'user_id': self.env.uid})
            else:
                if not self._context.get('cold_calling') and not self._context.get('fetchmail_server_id'):
                    stage_ids = stage_obj.search([('name','=','New')])
                    if stage_ids:
                        vals.update({'stage_id': stage_ids[0].id, 'user_id': False})
            if not vals.get('team_id'):
                team_ids = self.env['crm.team'].search([])
                if team_ids:
                    vals.update({'team_id' : team_ids[0].id})
            res = super(crm_lead, self).create(vals)
            print "kkkkkkkkkk.......",res
            if self._context.get('from_lead_menu'):
                stage_ids = stage_obj.search([('name','=','Open')])
                if stage_ids:
                    if not vals.get('stage_id'):
                        res.update({'stage_id': stage_ids[0].id})
                    if vals.get('stage_id') == stage_ids[0].id:
                        res.update({'type' : 'opportunity'})
                    if not vals.get('user_id'):
                        res.update({'stage_id': stage_ids[0].id})

        else:
            if not vals.get('team_id'):
                team_ids = self.env['crm.team'].search([])
                if team_ids:
                    vals.update({'team_id' : team_ids[0].id})
            res = super(crm_lead, self).create(vals)
        return res


    @api.model
    def default_get(self, fields):
        res = super(crm_lead, self).default_get(fields)
        stage_obj = self.env['crm.stage']
        if self._context.get('cold_calling'):
            if self.user_has_groups('base.group_sale_salesman') and not self.user_has_groups('base.group_sale_manager') and not self.user_has_groups('base.group_system'):
                res.update({'user_id': self.env.uid})
            else:
                res.update({'user_id': False})
        if res.get('type') == 'opportunity':
            stage_ids = stage_obj.search([('name','=','Open')])
            if stage_ids:
                res.update({'stage_id': stage_ids[0].id, 'user_id': self.env.uid})
        else:
            if not self._context.get('cold_calling'):
                stage_ids = stage_obj.search([('name','=','New')])
                if stage_ids:
                    res.update({'stage_id': stage_ids[0].id, 'user_id': False})
        return res

    @api.multi
    def get_contact(self):
        return {
            'name': 'Make a Comment',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.coldcalling.history',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target' : 'new',
            'context': {'default_lead_id' : self[0].id, 'default_user_id' : self.env.uid},
        }

    @api.multi
    def get_qualify(self):        
        self.coldcalling_bool=True
        self.lead_create_date=datetime.now()
        return {
            'name': 'Opportunity',
            'view_mode': 'form',
            'res_model': 'crm.lead2opportunity.partner',
            'view_id': self.env.ref('crm.view_crm_lead2opportunity_partner').id,
            'type': 'ir.actions.act_window',
            'target' : 'new',
            'context' : {'active_id' : self.id, 'active_ids' : [self.id], 'active_model': 'crm.lead', 'from_cold_calling' : True}
        }

    @api.multi
    def get_opportunity(self):
        self.stage_2 = 'opportunity'
    ### Add Disqualify history in crm.lead.history by vml
    @api.multi
    def disqualify(self):
        for record in self :
            vals={'user_id':record.user_id.id, 'lead_id':record.id, 'customer_name':record.partner_id.name, 
                  'name':record.name,'email':record.email_from, 'contact_time':datetime.now(),
                   'is_disqualify':True}
            if vals:
               self.env['crm.coldcalling.history'].create(vals)
               record.write({'disqualified_date':datetime.now()})
               self.stage_2 = 'disqualified'

    @api.multi
    def get_history(self):
        name = self[0].contact_name
        mail_id=[]
        mail=self.env['mail.mail'].search([('res_id', '=',self.id)])
        for record in mail:
            history=self.env['crm.coldcalling.history'].search([('mail_id', '=',record.id)])
            if not history:
                body_val=re.sub('<[^<]+?>', '', record.body_html)
                self.env['crm.coldcalling.history'].create({'mass_subject':record.subject, 'res_id':record.res_id,
                'name':body_val, 'mail_id':record.id ,'is_mass_mail':True, 
                 'mass_state':record.state, 'mass_email':record.email_from,
                  'recv_mass_email':record.recipient_ids.email})
        if not name:
            name = "Person"
        name += ' From ' + self[0].name
        if self[0].email_from:
            name += ' (' + self[0].email_from + ')'
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.coldcalling.history',
            'views': [[self.env.ref('gt_aalmir_coldcalling.crm_cold_calling_history_tree_view').id, 'tree']],
            'type': 'ir.actions.act_window',
            'domain' : ['|',('lead_id','=',self.id), ('res_id','=',self.id)],
            'context' : {'lead_id' : self.id, 'default_lead_id' : self.id},
            'target':'new'
        }

    @api.multi
    def _get_last_contacted(self):
        history_obj = self.env['crm.coldcalling.history']
        for rec in self:
            history_ids = history_obj.search([('lead_id','=', rec.id)], order="contact_time desc")
            if history_ids:
                rec.last_contacted = history_ids[0].contact_time

    def onchange_next_activity_id(self, cr, uid, ids, next_activity_id, context=None):
        if not next_activity_id:
            return {'value': {
                'next_action1': False,
                'next_action2': False,
                'next_action3': False,
                'title_action': False,
                'date_action': False,
            }}
        activity = self.pool['crm.activity'].browse(cr, uid, next_activity_id, context=context)
        date_action = False
        if activity.days:
            date_action = (datetime.now() + timedelta(days=activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        if activity.name in ['Meeting','Task']:
            task = True
        else:
            task = False
        return {'value': {
            'next_activity_1': activity.activity_1_id and activity.activity_1_id.name or False,
            'next_activity_2': activity.activity_2_id and activity.activity_2_id.name or False,
            'next_activity_3': activity.activity_3_id and activity.activity_3_id.name or False,
            'title_action': activity.description,
            'date_action': datetime.now(),
            'last_activity_id': False,
            'meeting_or_task' : task
        }}

    def log_next_activity_done(self, cr, uid, ids, context=None, next_activity_name=False):
        to_clear_ids = []
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.next_activity_id:
                continue
            body_html = ''
            if lead.next_activity_id.name in ['Meeting','Task']:
                body_html = """ From Date : """ + (lead.date_action or ' ') + """ To Date : """ + (lead.date_due_action or ' ')
            body_html += """<div><b>${object.next_activity_id.name}</b></div>
%if object.title_action:
<div>${object.title_action}</div>
%endif
Assign TO :
"""
            partners = []
            for i in lead.activity_assign_to:
                partners.append(i.id)
                body_html += i.name + """(""" + i.email + """),"""
            body_html[:-1]
            body_html = self.pool['mail.template'].render_template(cr, uid, body_html, 'crm.lead', lead.id, context=context)
            msg_id = lead.message_post(body_html, subtype_id=lead.next_activity_id.subtype_id.id)
            to_clear_ids.append(lead.id)
            self.write(cr, uid, [lead.id], {'last_activity_id': lead.next_activity_id.id , 'date_due_action': False, 'activity_assign_to': [], 'meeting_or_task': False}, context=context)
            if partners:
                cr.execute("delete from activity_assign_rel where lead_id = %s and partner_id in %s", (lead.id, tuple(partners)))
        if to_clear_ids:
            self.cancel_next_activity(cr, uid, to_clear_ids, context=context)
        return True

    @api.multi
    @api.depends('order_ids')
    def _get_sale_amount_total(self):
        for rec in self:
            total = 0.0
            nbr = 0
            company_currency = rec.company_currency or rec.env.user.company_id.currency_id
            order_ids = self.env['sale.order'].search([('opportunity_id','=', rec.id)])
            for order in order_ids:
                if order.state in ('draft', 'sent', 'cancel'):
                    nbr += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    total += order.currency_id.compute(order.amount_untaxed, company_currency)
            rec.sale_amount_total = total
            rec.sale_number = nbr

    @api.multi
    def _get_sales_person(self):
        for rec in self:
            if self.user_has_groups('base.group_sale_salesman') and not self.user_has_groups('base.group_sale_manager') and not self.user_has_groups('base.group_system'):
                rec.is_sales_person = True
                if rec.user_id == self.env.user:
                	rec.is_assing_button=True
            else:
                rec.is_sales_person = False

    @api.model
    def _get_salesman(self):
        if self.user_has_groups('base.group_sale_salesman') and not self.user_has_groups('base.group_sale_manager') and not self.user_has_groups('base.group_system'):
            return True
        else:
            return False

    is_sales_person = fields.Boolean(string="Sales Person", compute=_get_sales_person, default=_get_salesman)
    stage_2 = fields.Selection([('not_contacted', 'Not Contacted'),
                                ('contacted', 'Contacted'),
			        ('qualified', 'Qualified'),
                                ('disqualified', 'Disqualified')], string="Status")

    is_assing_button = fields.Boolean(string="Assing Button", compute=_get_sales_person)
    lead_create_date = fields.Datetime('Created Date', default=time.strftime("%Y-%m-%d %H:%M:%S"))
    last_contacted = fields.Datetime('Last Contacted Date')
    category = fields.Many2one('product.category', string="Category")
    title_action = fields.Text('Next Activity Summary')
    date_action = fields.Datetime(string='Next Activity Date', select=True)
    date_due_action = fields.Datetime(string='End Date', default=False)
    meeting_or_task = fields.Boolean(string='Meeting Task')
    activity_assign_to = fields.Many2many('res.users', 'activity_assign_rel' , 'lead_id', 'partner_id', string="Assign To")
    merge_id = fields.Many2one('crm.lead', string="Merge Lead")
    opp_merge_ids = fields.One2many('crm.lead', 'merge_id', string="Merge Leads")
    sale_amount_total= fields.Float(compute='_get_sale_amount_total', string="Sum of Orders", readonly=True, digits=0)
    sale_number = fields.Integer(compute='_get_sale_amount_total', string="Number of Quotations", readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', select=True)
    stage_name = fields.Char(related='stage_id.name', string="Stage Name")
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', select=True)
    ## add field vml
    number_of_days=fields.Char('Last Contact Days', compute='days_between',store=True)
    #created_days=fields.Char('Create Days')
    contact_interval = fields.Selection([('15', '15'),
                                ('20', '20'),
			        ('25', '25'),
                                ('30', '30'), ('35', '35'), ('40', '40'),('45', '45'),('50', '50')], 
                                 default='30', string="Contact Interval")
    cont_pre_val=fields.Char('Contact Pre')
    cont_last_val=fields.Char('Contact Last')
    cont_bool=fields.Boolean('Contact Bool', default=False)
    coldcalling_ids=fields.One2many('crm.coldcalling.history', 'lead_id')
    interval_date=fields.Datetime('Interval Date')
    qualified_date=fields.Datetime('Qualify Date')
    disqualified_date=fields.Datetime('Qualify Date')
    coldcalling_bool=fields.Boolean('Coldcalling')
    history_recent = fields.Char('Remark',compute="_get_receint_history")

    @api.multi
    def _get_receint_history(self):
	for res in self:
		history=self.env['crm.coldcalling.history'].search([('lead_id','=',res.id)],order="contact_time desc",limit=1)
		if history:
			res.history_recent=history.name
    
    @api.multi
    @api.onchange('contact_interval')
    def contact_intervat_method(self):
        for record in self:
            if record.contact_interval:
               if record.cont_bool == False:
                  record.cont_pre_val=record.contact_interval
                  record.cont_bool=True
               if record.cont_bool == True:
                  record.cont_last_val=record.contact_interval
                  record.interval_date =datetime.now()
    ### Add method calculate Number of day vml
    @api.multi
    @api.depends('last_contacted')
    def days_between(self):
       for record in self:
           if record.last_contacted: 
              d1=datetime.now().strftime('%Y-%m-%d %H:%M:%S') ;
              date_create = datetime.strptime(d1, "%Y-%m-%d %H:%M:%S")
              date_open = datetime.strptime(record.last_contacted, "%Y-%m-%d %H:%M:%S")
              ans = date_create - date_open
              record.number_of_days=ans.days
    @api.onchange('email_from')
    def onchange_internal_type(self):
        if not self._context.get('cold_calling'):
            res_partner_obj = self.env['res.partner']
            if not self._context.get('from_fetchmail') and self.email_from and re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", self.email_from) == None:
                return {'warning': {'title': "Invalid", 'message': "Please Add Valid Email"}}
            else:
                if self.email_from:
                    res_partner_obj_search = res_partner_obj.search([('email','=',self.email_from)])
                    if res_partner_obj_search:
                        if self.partner_id:
                            self.partner_id = res_partner_obj_search[0].id
                            if not self.phone:
                                self.phone = res_partner_obj_search[0].mobile or res_partner_obj_search[0].phone
                            if not self.mobile:
                                self.mobile = res_partner_obj_search[0].mobile or res_partner_obj_search[0].phone
                            if not self.name:
                                self.name = res_partner_obj_search[0].name
                            if not self.contact_name:
                                self.contact_name = res_partner_obj_search[0].name

    @api.multi
    def _validate_email(self):
        for lead in self:
            if not self._context.get('from_fetchmail'):
                if lead.email_from and re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", lead.email_from) == None:
                    return False
        return True

    _constraints = [
        (_validate_email, 'Please enter a valid email address.', ['email_from']),
    ]



class crm_coldcalling_history(models.Model):
    _name = "crm.coldcalling.history"
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'utm.mixin']
    _rec_name = 'customer_name'
    _order = 'contact_time desc'

    @api.multi
    def action_save_comment(self):
        for cold_his in self:
            if cold_his.reminder_time:
                cold_his.set_reminder_calender()
            res = self.env['ir.actions.act_window'].for_xml_id('gt_aalmir_coldcalling', 'crm_cold_calling_action')
            cold_his.lead_id.stage_2 = 'contacted'
            return res

    @api.model
    def default_get(self, fields):
        res = super(crm_coldcalling_history, self).default_get(fields)
        res.update({'contact_time' : datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        return res

    @api.multi
    def set_reminder_calender(self):
        for cold_his in self:
            if not cold_his.reminder_time:
                raise UserError(('Please Add Reminder Time'))
            alarm_obj = self.env['calendar.alarm']
            event_obj = self.env['calendar.event']
            user = self.env['res.users'].browse(self.env.uid)
            name = cold_his.lead_id and cold_his.lead_id.name or ""
	    ##CH01 start >>>
            alarm = alarm_obj.search([('type','=', 'notification'),('duration','=', 10), ('interval','=','minutes')], limit=1)
	    email = alarm_obj.search([('type','=', 'email'),('duration','=', 15), ('interval','=','minutes')], limit=1)
            a_id = []
            if alarm:
                a_id.append(alarm.ids)
	    if email:
		a_id.append(email.ids)
	    #CH01 end <<<
            context = self._context.copy()
            context.update({'active_model' : 'crm.coldcalling.history', 'active_id' : cold_his.id, 'active_ids' : [cold_his.id]})
            value = {
                'event_name': '[Cold Calling Reminder] ' + (cold_his.name or ''),
                'name': cold_his.lead_id and cold_his.lead_id.name or "",
                'lead_id': cold_his.lead_id and cold_his.lead_id.id or False,
                'cold_calling_reminder' : True,
                'start_date' : cold_his.reminder_time,
                'start' : cold_his.reminder_time,
                'duration' : 0.5,
                'partner_ids' : [(6, 0, [user.partner_id.id])],
                'alarm_ids' : [(6, 0, [a_id])],
                'comment_id' : cold_his.id
            }
            if cold_his.reminder_time:
                start = datetime.strptime(cold_his.reminder_time, DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_date'] = (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATE_FORMAT)
                value['stop'] = (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                value['stop_datetime'] = (start + timedelta(hours=0.5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                value['start_date'] = start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                value['start'] = start.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            event_obj.with_context(context).create(value)
            cold_his.write({'set_reminder': True})
            cold_his.lead_id.write({'name': name})
            return True

    @api.model
    def create(self, vals):
        vals.update({'user_id': self.env.uid})
        if vals.get('contact_time'):
            lead_obj = self.env['crm.lead']
            lead = lead_obj.browse(vals.get('lead_id'))
            lead.write({'last_contacted' : vals.get('contact_time')})
        return super(crm_coldcalling_history, self).create(vals)
    
    @api.multi
    def action_mail_send(self):
        for coldcaling in self:
            coldcaling.lead_id.stage_2 = 'contacted'
            if coldcaling.reminder_time:
                coldcaling.set_reminder_calender()
            ir_model_data = self.env['ir.model.data']
            try:
                template_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'email_send_comment')[1]
            except ValueError:
                template_id = False
            try:
                compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
            except ValueError:
                compose_form_id = False
            ctx = dict()
            partner = self.env['res.partner']
            if coldcaling.lead_id.partner_id:
                p_id = coldcaling.lead_id.partner_id.id
            elif not coldcaling.lead_id.partner_id and coldcaling.lead_id.email_from:
                p_id = partner.search([('email','=', coldcaling.lead_id.email_from)], limit=1).id
                if not p_id:
                    name = (coldcaling.lead_id.email_from).split('@')
                    partner = partner.create({'name': name[0], 'email': coldcaling.lead_id.email_from})
                    p_id = partner.id
            else:
                p_id = False
            if p_id:
                partner_ids = [p_id]
            else:
                partner_ids = []

            ctx.update({
                'default_model': 'crm.coldcalling.history',
                'default_res_id': coldcaling.id,
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'default_partner_ids': partner_ids,
                'default_subject': ' ',
                'mark_so_as_sent': True,
                'from_cold_calling_comment' : coldcaling.id
            })
            return {
                'name' : 'Mail',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form_id, 'form')],
                'view_id': compose_form_id,
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    def qualify(self):
        res = self.lead_id.get_qualify()
        return res

    @api.multi
    def _my_message(self):
        for rec in self:
            if rec.message_ids:
                rec.my_mail = rec.message_ids[0].id

    @api.multi
    def action_mail_history(self):
        res_id = self._context.get('mail_history')
        vals =  {
            'name': 'Email',
            'view_mode': 'form',
            'res_model': 'mail.message',
#            'view_id': self.env.ref('view_message_form_History_view_aalmir')[0],
            'res_id': res_id,
            'type': 'ir.actions.act_window',
            'target' : 'new',
        }
        return vals
    ## add pop for mass mail vml
    @api.multi
    def action_reminder_history_mass_mail(self):
        ir_model_data = self.env['ir.model.data']
        form_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'reminder_popup_in_mass_mail')[1]
        return {
            'name' : 'Reminder',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.coldcalling.history',
            'views': [(form_id, 'form')],
            'view_id': form_id,
            'target': 'new',
            'res_id': self[0].id,
        }
    ## add pop  for Disqualify coldcalling 
    @api.multi
    def action_reminder_history_disqualify(self):
        ir_model_data = self.env['ir.model.data']
        form_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'reminder_popup_in_disqualify')[1]
        return {
            'name' : 'Disqualify',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.coldcalling.history',
            'views': [(form_id, 'form')],
            'view_id': form_id,
            'target': 'new',
            'res_id': self[0].id,
        }
    ## add pop  for qualify coldcalling 
    @api.multi
    def action_reminder_history_qualify(self):
        ir_model_data = self.env['ir.model.data']
        form_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'reminder_popup_in_qualify')[1]
        return {
            'name' : 'Qualify',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.coldcalling.history',
            'views': [(form_id, 'form')],
            'view_id': form_id,
            'target': 'new',
            'res_id': self[0].id,
        }
    @api.multi
    def action_reminder_history(self):
        ir_model_data = self.env['ir.model.data']
        form_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'reminder_popup_in_comment')[1]
        return {
            'name' : 'Reminder',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'crm.coldcalling.history',
            'views': [(form_id, 'form')],
            'view_id': form_id,
            'target': 'new',
            'res_id': self[0].id,
        }

    contact_time = fields.Datetime('Contact Time')
    reminder_time = fields.Datetime('Reminder Time')
    name = fields.Text('Comment')
    availability = fields.Selection([('available','Available'),('not_available', 'Not Available')], string="Availability", default="available")
    user_id = fields.Many2one('res.users', String="Sales Person")
    lead_id = fields.Many2one('crm.lead', string="Lead")
    customer_name = fields.Char(related='lead_id.contact_name', string="Name", store=True)
    company_name = fields.Char(related='lead_id.name', string="Company Name", store=True)
    email = fields.Char(related='lead_id.email_from', string="Email", store=True)
    reminder_name = fields.Char('Reminder Name')
    send_mail = fields.Boolean(string="EMail", default=False)
    set_reminder = fields.Boolean(string="Reminder", default=False)
    my_mail = fields.Many2one('mail.message', compute="_my_message", string="Email")
    ###### add field vml
    res_id=fields.Char('Res_id')
    mail_id=fields.Char('Mail_id')
    is_mass_mail=fields.Boolean("is Mass Mail")
    mass_subject=fields.Char('Mass Subject')
    mass_email=fields.Char(' Sender mail')
    recv_mass_email=fields.Char(' Receiver mail')
    mass_state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='outgoing')
    is_disqualify=fields.Boolean('Is Disqualify')
    is_qualify=fields.Boolean('Is Qualify')
    
class DepMail(models.Model):
    _name = "dep.mail"

    name = fields.Char('Department Name')
    partner_ids = fields.Many2many('res.partner', 'res_partner_department', 'dep_id', 'part_id', 'Partners')
    
    @api.onchange('dep_id')
    def onchange_dep(self):
        if self.dep_id and self.dep_id.partner_ids:
            self.partner_ids = [(6,0, (self.partner_ids and (self.partner_ids.ids+ self.dep_id.partner_ids.ids) or self.dep_id.partner_ids.ids))]
    
    dep_id = fields.Many2one('dep.mail', 'Department')
    cc_ids = fields.Many2many('res.partner', "cc_compose_partner_rel", 'compose_id', 'partner_id', string="Cc")

    @api.model
    def default_get(self, fields):
        result = super(MailComposeMessage, self).default_get(fields)
        if self._context and self._context.has_key('default_res_id') and self._context.get('default_res_id'):
            if self._context.has_key('default_model') and self._context.get('default_model'):
                browse_rec = self.env[self._context.get('default_model')].browse(self._context.get('default_res_id'))
                if hasattr(browse_rec,'partner_id'):
                    if browse_rec.partner_id:
                        result.update({'partner_ids':[browse_rec.partner_id.id]})
        return result
        
class IrreleventReason(models.Model):

    _name = 'irrelevant.reason'

    name = fields.Char("Reason", required=True)


class crmStages(models.Model):
	_inherit='crm.stage'
	
	@api.multi
	def write(self,vals):
		print "...........",self,vals
		return super(crmStages,self).write(vals)
		
