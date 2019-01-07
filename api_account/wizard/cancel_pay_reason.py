# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class PayCancelWizard(models.TransientModel):

    _name = "cancel.pay.reason.wizard"
    _description = "Cancel Pay  Reason wizard"

    description = fields.Char(string='Reason', required=True)    
    uploaded_document_cancel = fields.Binary(string='Upload Cancel Proof', default=False , attachment=True)


    @api.multi
    def pay_refuse_reason(self):
        self.ensure_one()

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        pay = self.env['account.payment'].browse(active_ids)
        pay.write({'cancel_reason':self.description,'state':'draft','uploaded_document_cancel':self.uploaded_document_cancel})
        check=pay.with_context(call_from_wiz=True).cancel()
        if pay.cheque_details:
            for each_chq in pay.cheque_details:
                each_chq.unlink()
        if pay.expense_id:
            pay.expense_id.with_context({'call_from_pay':True}).cancel_expense()
            pay.expense_id=False
            pay.communication=''
        return {'type': 'ir.actions.act_window_close'}
