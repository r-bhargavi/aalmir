# -*- coding: utf-8 -*-
from openerp import api, fields, models


class LockWizard(models.TransientModel):
    _name = 'lock.wizard'
    
    def done(self):
        order_obj = self.env['sale.order'].browse(self._context.get('active_id'))
        order_obj.make_lock()
        return True
    
class LeadWon(models.TransientModel):
    
    _name = 'lead.won'
    
    @api.model
    def get_lead(self):
        return self._context.get('active_id') or False
    
    lead_id = fields.Many2one('crm.lead', 'Opportunity', default=get_lead)
    sale_id = fields.Many2one('sale.order', 'Quotation' ,  required=True)
    
    @api.one
    def done(self):
        self.sale_id.action_confirm()
        return True
        
    