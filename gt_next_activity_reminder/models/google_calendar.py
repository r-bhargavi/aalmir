# -*- coding: utf-8 -*-

from openerp import api, fields, models, _

class calendar_event(models.Model):
    _inherit = "calendar.event"
    
    event_name = fields.Char(string="Name")
    
    @api.model
    def create(self, vals):
        print "BEfore vals..",vals
        if vals.get('event_name'):
            vals.update({'name' : vals.get('event_name')})
        if vals.get('name'):
            vals.update({'event_name' : vals.get('name')})
        print "AFter vals..",vals
        return super(calendar_event, self).create(vals)
