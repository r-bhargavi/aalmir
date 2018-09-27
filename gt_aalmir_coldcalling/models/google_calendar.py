# -*- coding: utf-8 -*-

from openerp import api, fields, models, _

class calendar_event(models.Model):
    _inherit = "calendar.event"
    
    lead_id = fields.Many2one('crm.lead', string="Lead")
    cold_calling_reminder = fields.Boolean(string="Reminder")
    last_contacted = fields.Datetime(related="lead_id.last_contacted", string='Last Contacted Date')
#    name = fields.Char(related="lead_id.name", string='Name')
    contact_name = fields.Char(related="lead_id.contact_name", string='Contact Name')
#    contact_name = fields.Char(related="lead_id.contact_name", string='Contact Name')
    phone = fields.Char(related="lead_id.phone", string='Phone')
#    phone = fields.Char(related="lead_id.phone", string='Phone')
    mobile = fields.Char(related="lead_id.mobile", string='Mobile')
    email_from = fields.Char(related="lead_id.email_from", string='Email From')
    comment_id = fields.Many2one('crm.coldcalling.history', string="Comments")
    comment_name = fields.Text(related='comment_id.name', string="Comments")