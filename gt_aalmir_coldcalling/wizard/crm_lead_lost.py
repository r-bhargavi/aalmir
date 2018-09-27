# -*- coding: utf-8 -*-
from openerp import api, fields, models


class CrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'
    
    description = fields.Text(string="Description")

    @api.multi
    def action_lost_reason_apply(self):
        res = False
        for wizard in self:
            self.lead_id.lost_reason = self.lost_reason_id.id
            stage_ids = self.env['crm.stage'].search([('name','=','Lost')])
            if stage_ids:
                self.lead_id.stage_id = stage_ids[0].id
                quote_ids = self.env['sale.order'].search([('opportunity_id','=', self.lead_id.id)])
                quote_ids.write({'state': 'cancel'})
                body = "<div><b>Lost</b></div><div>Lost Reason: %s</div><div>Lost Description : %s</div>" % ((self.lost_reason_id and self.lost_reason_id.name), self.description )
                self.lead_id.message_post(body=body,subject="Lost")
        return res
