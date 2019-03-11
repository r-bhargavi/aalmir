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