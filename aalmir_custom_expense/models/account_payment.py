# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models ,api, _

		
class accountPayment(models.Model):
    _inherit='account.payment'

    expense_pay = fields.Boolean('Expense Pay')
    expense_id = fields.Many2one('hr.expense', 'Expense')
    expense_payment_rel = fields.Many2many('hr.expense','pay_exp_rel','exp_id','pay_id','Expenses',copy=False,track_visibility='always')
    expense_count=fields.Float('Expenses', compute='total_expenses')
    
    @api.multi
    def total_expenses(self):
        for record in self:
            exp_ids_count=[]
	    if record.expense_id:
                exp_ids_count.append(record.expense_id.id)
            if record.expense_payment_rel:
                exp_ids_count.append(x.id for x in record.expense_payment_rel.ids)
        print "exp_ids_countexp_ids_count",exp_ids_count
        record.expense_count=len(exp_ids_count)
        print "record.expense_countrecord.expense_count",record.expense_count

    @api.multi
    def open_expenses(self):
        for pay in self:
            exp_ids=[]
            exp_tree = self.env.ref('hr_expense.view_expenses_tree', False)
            print "exp_treeexp_tree",exp_tree
            exp_form = self.env.ref('hr_expense.hr_expense_form_view', False)
            print "exp_formexp_form",exp_form
            if pay.expense_id:
                exp_ids.append(pay.expense_id.id)
            if pay.expense_payment_rel:
                exp_ids.append(pay.expense_payment_rel.ids)
            print "exp_idsexp_ids",exp_ids
            if exp_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree, form',
                    'res_model': 'hr.expense',
                    'views': [(exp_tree.id, 'tree'), (exp_form.id, 'form')],
                    'view_id': exp_tree.id,
                    'target': 'current',
                    'domain':[('id','in',exp_ids)],
                }
        return True
    
    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            return {'domain': {'partner_id': ['|',('employee', '=', True),(self.partner_type, '=', True)]}}
        
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        # Set partner_id domain
        if self.partner_id and self.payment_type=='transfer':
            print "calllll to onchange pay type-------------------"
            self.partner_id= False