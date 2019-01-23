# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class ApprovalConfigBill(models.Model):
    _name = 'approval.config.bill'
    
    
    name=fields.Char(string='Approval Name')
    approval_line_bill = fields.One2many('approval.config.bill.line','approve_id','Approval Lines')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('approval.config.bill')
        print "vls----------------",vals
        approve_config = super(ApprovalConfigBill, self).create(vals)
        return approve_config
	
class ApprovalConfigLine(models.Model):
    _name = 'approval.config.bill.line'
    
    approve_id = fields.Many2one('approval.config.bill', 'Approve ID')
    partner_id = fields.Many2one('res.partner', domain=[('supplier','=',True),('parent_id','=',False)])
    approval_by = fields.Many2one('res.users', 'Approval By')
    approve_amount = fields.Float('Approval Not Req Upto')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)

    _sql_constraints = [('approve_product_type_uniq', 'unique (approve_id,partner_id)',     
                 'Duplicate Partner in approval bill config line not allowed !')]
    
    @api.onchange('approval_by')
    def approval_by_onchange(self):
        user_list=[]
        group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant')[1]
        print "group_idgroup_idgroup_id",group_id
        for usr in self.env['res.groups'].search([('id', '=',group_id)]).users:
            user_list.append(usr.id)
        print "user_listuser_list",user_list
        return {'domain': {'approval_by': [('id', 'in', user_list)]}}


    
