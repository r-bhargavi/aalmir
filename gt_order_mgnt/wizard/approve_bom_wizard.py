# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ApproveBomWizard(models.TransientModel):

    _name = "approve.bom.wizard"
    _description = "Approve BOM wizard"

    description = fields.Char(string='Remarks on Approval')

    @api.multi
    def approve_bom_now(self):
        self.ensure_one()

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        bom = self.env['mrp.bom'].browse(active_ids)
        bom.write({'remarks':self.description,'state':'approve'})
        return {'type': 'ir.actions.act_window_close'}
