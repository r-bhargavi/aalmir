# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class BillRefuseWizard(models.TransientModel):

    _name = "vendor.bill.refuse.wizard"
    _description = "Bill refuse Reason wizard"

    description = fields.Char(string='Reason', required=True)

    @api.multi
    def bill_refuse_reason(self):
        self.ensure_one()

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        bill = self.env['account.invoice'].browse(active_ids)
        bill.write({'refuse_reason':self.description,'state':'rejected'})
        return {'type': 'ir.actions.act_window_close'}
