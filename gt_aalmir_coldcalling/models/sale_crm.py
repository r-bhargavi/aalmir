# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def create(self, vals):
        if self._context.get('from_lead'):
            obj = self.env['crm.lead'].browse(self._context.get('from_lead'))
            stage_ids = self.env['crm.stage'].search([('name','=', 'Quoted')])
            if stage_ids:
                obj.stage_id = stage_ids[0].id
        return super(sale_order, self).create(vals)
        
   
