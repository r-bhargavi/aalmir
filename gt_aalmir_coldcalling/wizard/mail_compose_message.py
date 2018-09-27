# -*- coding: utf-8 -*-

import base64
import re

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp.tools.safe_eval import safe_eval as eval

class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    dep_id = fields.Many2one('dep.mail', 'Department')
    cc_ids = fields.Many2many('res.partner', "cc_compose_partner_rel", 'compose_id', 'partner_id', string="Cc")
    irrelevant_reason_id = fields.Many2one('irrelevant.reason', 'Irrelevant Reason')
    irr_reason_description = fields.Text("Irrelevant Reason Description")
    
    @api.onchange('irrelevant_reason_id','irr_reason_description')
    def onchange_irrelevant(self):
        body=self.body
        if self.irrelevant_reason_id and self.irr_reason_description:
           body +='<li>Irrelevant Reason:  '+str(self.irrelevant_reason_id.name)+'</li>'
           body +='<li>Irrelevant Description:  '+str(self.irr_reason_description)+'</li>'
        self.body=body

    @api.onchange('dep_id')
    def onchange_dep(self):
        body=self.body
        if self.dep_id and self.dep_id.partner_ids: 
            body +='<li>Department Name:'+str(self.dep_id.name)+'</li>'
            self.partner_ids = [(6, 0, (
            self.partner_ids and (self.partner_ids.ids + self.dep_id.partner_ids.ids) or self.dep_id.partner_ids.ids))]
        self.body=body

    @api.model
    def default_get(self, fields):
        result = super(MailComposer, self).default_get(fields)
        if self._context and self._context.has_key('default_res_id') and self._context.get('default_res_id'):
            if self._context.has_key('default_model') and self._context.get('default_model'):
                browse_rec = self.env[self._context.get('default_model')].browse(self._context.get('default_res_id'))
                if hasattr(browse_rec, 'partner_id'):
                    if browse_rec.partner_id:
                        result.update({'partner_ids': [(4,browse_rec.partner_id.id)]})
                    else:
                        if not self._context.get('from_irrelavent'):
                           result.update({'email_ids':browse_rec.email_from})
                if self._context.get('default_model') == 'sale.order':
                    subject = browse_rec.opportunity_id.name
                    subject1 = browse_rec.company_id.name
                    if browse_rec.state in ('draft', 'sent'):
                        subject1 += ' Quotation'
                    else:
                        subject1 += ' Order'
                    subject1 += " (Ref "
                    subject1 += browse_rec.name or 'n/a'
                    subject1 += ")"
                    result.update({'subject': subject})

        return result

    @api.multi
    def send_mail_action(self):
        res = super(MailComposer, self).send_mail_action()
        if self._context.get('from_cold_calling_comment'):
            history_obj = self.env['crm.coldcalling.history']
            hobj = history_obj.browse(int(self._context.get('from_cold_calling_comment')))
            hobj.write({'send_mail' : True})
        print"yyyyyyyyyyyyyyyy",self._context.get('from_irrelavent')
        if self._context.get('from_irrelavent'):
            lead = self.env['crm.lead'].browse(self._context.get('lead_id'))
            lead.active = False
            lead.irrelevant_reason_id = self.irrelevant_reason_id and self.irrelevant_reason_id.id or False
            lead.irr_reason_description = self.irr_reason_description or ""
        return res

