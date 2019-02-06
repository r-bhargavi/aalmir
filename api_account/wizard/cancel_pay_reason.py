# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class PayCancelWizard(models.TransientModel):

    _name = "cancel.pay.reason.wizard"
    _description = "Cancel Pay  Reason wizard"

    description = fields.Char(string='Reason', required=True)    
#    uploaded_document_cancel = fields.Binary(string='Upload Cancel Proof', default=False , attachment=True)
    uploaded_document_cancel = fields.Many2many('ir.attachment','cancel_attachment_wiz_rel','cancel_att','wiz_id','Upload Cancel Proof',copy=False,track_visibility='always')



    @api.multi
    def pay_refuse_reason(self):
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        print "dfsfsdfs",self._context
        if self._context.get('active_model',False)=='mrp.raw.material.request':
            rm_brw=self.env['mrp.raw.material.request'].browse(active_ids)
            rm_brw.write({'rm_reject_reason':self.description})
            rm_brw.production_id.write({'rm_reject_reason':self.description})
            rm_brw.reject_state()
        elif self._context.get('active_model',False)=='mrp.bom':
            bom_brw=self.env['mrp.bom'].browse(active_ids)
            bom_brw.write({'refuse_reason':self.description,'state':'reject'})

        elif self._context.get('active_model',False)=='hr.expense':
            exp_brw=self.env['hr.expense'].browse(active_ids)
            print "exp_brwexp_brw",exp_brw
            pay=exp_brw.payment_id
            exp_brw.account_move_id.button_cancel()
            pay.expense_id=False
            if exp_brw.cheque_details:
                for each_chq in exp_brw.cheque_details:
                    each_chq.unlink()
                    
            all_attach=[]
            if self.uploaded_document_cancel:
                 all_attach.append(self.uploaded_document_cancel.ids)
                 exp_brw.write({'uploaded_document_cancel':[(4, all_attach)]}) 
            exp_brw.write({'cancel_reason':self.description,'state':'draft','approved_by':False,'payment_method':'','bank_journal_id_expense':False,'cheque_status':'','chq_s_us':'','is_bank_journal':False,'payment_id':False})
            check=pay.with_context(call_from_wiz=True).cancel()
            if pay.cheque_details:
                for each_chq in pay.cheque_details:
                    each_chq.unlink()
            pay.unlink()
            
        else:
            pay = self.env['account.payment'].browse(active_ids)
            pay.write({'cancel_reason':self.description,'state':'draft','uploaded_document_cancel':self.uploaded_document_cancel})
            check=pay.with_context(call_from_wiz=True).cancel()
            if pay.cheque_details:
                for each_chq in pay.cheque_details:
                    each_chq.unlink()
            all_attach=[]
            if self.uploaded_document_cancel:
                 all_attach.append(self.uploaded_document_cancel.ids)
                 pay.write({'uploaded_document_cancel':[(4, all_attach)]}) 
            if pay.expense_id:
                pay.expense_id.with_context({'call_from_pay':True}).cancel_expense()
                pay.expense_id.account_move_id.button_cancel()
                if pay.expense_id.cheque_details:
                    for each_chq in pay.expense_id.cheque_details:
                        each_chq.unlink()
                all_attach=[]
                if self.uploaded_document_cancel:
                    all_attach.append(self.uploaded_document_cancel.ids)
                    pay.expense_id.write({'uploaded_document_cancel':[(4, all_attach)]})
                pay.expense_id.write({'cancel_reason':self.description,'state':'draft','approved_by':False,'payment_method':'','bank_journal_id_expense':False,'cheque_status':'','chq_s_us':'','is_bank_journal':False,'payment_id':False})
                pay.unlink()
        
        return {'type': 'ir.actions.act_window_close'}
