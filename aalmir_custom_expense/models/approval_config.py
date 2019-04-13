# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class ApprovalConfig(models.Model):
    _name = 'approval.config'
    
    
    name=fields.Char(string='Approval Name')
    product_type=fields.Many2one('type.product', 'Product Type')
    approval_line = fields.One2many('approval.config.line','approve_id','Approval Lines')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id)
    approve_not_req_upto = fields.Float('Approval Not Required Upto')

    @api.onchange('product_type')
    def product_type_onchange(self):
    	if self.product_type:
            ac_id=self.search([('product_type','=',self.product_type.id)])
            if ac_id:
                self.product_type=False
                return {'warning': {'title': "Invalid", 'message': "Approval Configuration already exist for this product type!!!!"}}



    
    @api.model
    def create(self, vals):
        approve_config = super(ApprovalConfig, self).create(vals)
        approve_config.write({'name':self.env['type.product'].browse(vals.get('product_type')).name})
#        vals['name'] = self.env['ir.sequence'].next_by_code('approval.config')
        print "vls----------------",vals
        if not vals.get('approval_line',False):
            raise UserError(_('There is no Approval Line defined in Approval Configuration.'))
        for each_line in approve_config.approval_line:
            if each_line.approve_amount_upto==0.0:
                raise UserError(_('No Approval Line can have 0 amount!!'))
        return approve_config
	
class ApprovalConfigLine(models.Model):
    _name = 'approval.config.line'
    
    approve_id = fields.Many2one('approval.config', 'Approve ID')
    approval_by = fields.Many2one('res.users', 'Approval By')
    approve_amount_upto = fields.Float('Can approve expenses upto')

    _sql_constraints = [('approve_approval_by_uniq', 'unique (approve_id,approval_by)',     
                 'Duplicated Approval By User not allowed in Approval Config Line!'),('approve_approve_amount_upto_uniq', 'unique (approve_id,approve_amount_upto)',     
                 'Duplicated Amount Approve Upto in approval config line not allowed !')]
    
#    @api.onchange('approval_by')
#    def approval_by_onchange(self):
#        user_list=[]
#        group_id = self.env['ir.model.data'].get_object_reference('aalmir_custom_expense','restricted_hr_expense_grant')[1]
#        print "group_idgroup_idgroup_id",group_id
#        for usr in self.env['res.groups'].search([('id', '=',group_id)]).users:
#            user_list.append(usr.id)
#        print "user_listuser_list",user_list
#        return {'domain': {'approval_by': [('id', 'in', user_list)]}}
    
    @api.onchange('approve_amount_upto')
    def approve_amount_upto_onchange(self):
    	if self.approve_amount_upto:
            if self.approve_amount_upto<=self.approve_id.approve_not_req_upto:
#                self.approve_amount_upto=0.0
                return {'warning': {'title': "Invalid", 'message': "You cannot add amount less then the approval not req upto in Configuration!!"}}


    
