# -*- coding: utf-8 -*-
##############################################################################
#
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

from datetime import datetime, date, timedelta
from datetime import datetime, timedelta
from openerp.tools.translate import _
class CrmLead(models.Model):
    _inherit = 'crm.lead'
    sale_id=fields.Many2one('sale.order', compute='saleoder')
    @api.multi
    def saleoder(self):
        for record in self:
            for order in record.order_ids:
                if order.state in ('sale', 'awaiting'):
                   record.sale_id=order.id
    @api.one
    @api.depends('order_ids')
    def _get_sale_amount_total(self):
        total = 0.0
        nbr = 0
        company_currency = self.company_currency or self.env.user.company_id.currency_id
        for order in self.order_ids:
            if order.state in ('draft', 'sent','awaiting'):
                nbr += 1
            if order.state not in ('draft', 'sent','awaiting','cancel'):
                total += order.currency_id.compute(order.amount_untaxed, company_currency)
        self.sale_amount_total = total
        self.sale_number = nbr
   

class CrmTeam(models.Model):
    _inherit = 'crm.team'
        
    @api.multi
    def get_pending_payment_request(self):
        for obj in self:
            if self.user_has_groups('base.group_system') or self.user_has_groups('account.group_account_user'):
                requests = self.env['account.payment.term.request'].search([('state','=','requested'),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
            else:
                requests = self.env['account.payment.term.request'].search([('state','=','requested'), ('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
            if requests:
                obj.pending_request = len(requests)
            else:
                obj.pending_request = 0
    
    @api.multi
    def get_order_pending_request(self):
        for obj in self:
            requests = self.env['sale.order'].search([('state', '=', 'awaiting')])
            if requests:
                obj.order_pending_request = len(requests)
            else:
                obj.order_pending_request = 0
    @api.multi
    def get_order_pending_request_salesperson(self):
        for obj in self:
            requests = self.env['sale.order.line'].search([('order_id.user_id','=',self.env.user.id),('company_id','child_of',[self.env.user.company_id.id])])
            if requests:
                obj.line_pending_request = len(requests)
            else:
                obj.line_pending_request = 0

    @api.multi
    def get_accepted_payment_request(self):
        for obj in self:
            if self.user_has_groups('base.group_system') or self.user_has_groups('account.group_account_user'):
                requests = self.env['account.payment.term.request'].search([('state','=','approved'),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
            else:
                requests = self.env['account.payment.term.request'].search([('state','in',('approved','update')),('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
	    count=0
            if requests:
		for line in requests:
			if line.quote_id.state in ('draft','sent','awaiting'):
				count +=1
                obj.accepted_request = count
            else:
                obj.accepted_request = 0

    @api.multi
    def get_order_pending_request_salesperson(self):
        for obj in self:
            requests = self.env['sale.order.line'].search([('order_id.user_id','=',self.env.user.id),('company_id','child_of',[self.env.user.company_id.id])])
            if requests:
                obj.line_pending_request = len(requests)
            else:
                obj.line_pending_request = 0

    @api.multi
    def get_rejected_payment_request(self):
        for obj in self:
            if self.user_has_groups(' base.group_system') or self.user_has_groups('account.group_account_user'):
                requests = self.env['account.payment.term.request'].search([('state','=','rejected'),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
            else:
                requests = self.env['account.payment.term.request'].search([('state','=','rejected'), ('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
            if requests:
                obj.rejected_request = len(requests)
            else:
                obj.rejected_request = 0
    
    @api.multi
    def accepted_payment_term(self):
        if self.user_has_groups('base.group_system') or self.user_has_groups('account.group_account_user'):
            requests = self.env['account.payment.term.request'].search([('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        else:
            requests = self.env['account.payment.term.request'].search([('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        return {
            'name': 'Accepted Payment Term',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.payment.term.request',
            'view_id': self.env.ref('gt_order_mgnt.account_payment_term_approved_tree_view').id,
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_approved' : 1}
        }
    
    @api.multi
    def rejected_payment_term(self):
        if self.user_has_groups('base.group_system') or self.user_has_groups('account.group_account_user'):
            requests = self.env['account.payment.term.request'].search([('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        else:
            requests = self.env['account.payment.term.request'].search([('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        return {
            'name': 'Rejected Payment Term',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.payment.term.request',
            'view_id': self.env.ref('gt_order_mgnt.account_payment_term_rejeted_tree_view').id,
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_rejected' : 1}
        }
    
    @api.multi
    def pending_payment_term(self):
        if self.user_has_groups('base.group_system') or self.user_has_groups('account.group_account_user'):
            requests = self.env['account.payment.term.request'].search([('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        else:
            requests = self.env['account.payment.term.request'].search([('sales_person_id', '=', self.env.uid),('quote_id.company_id','child_of',[self.env.user.company_id.id])])
        return {
            'name': 'Pending Payment Term',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.payment.term.request',
            'view_id': self.env.ref('gt_order_mgnt.account_payment_term_rejeted_tree_view').id,
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_requested' : 1}
        }
    
    @api.multi
    def action_order_pending_request(self):
        requests = self.env['sale.order'].search([('state', '=', 'awaiting')])
        return {
            'name': 'Awaiting Sale Orders',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'view' : [(self.env.ref('sale.view_order_tree').id, 'tree'), (self.env.ref('gt_order_mgnt.order_confirm_sale_form_view').id, 'form')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_requested' : 1}
        }
    
    @api.multi
    def action_order_pending_salesperson(self):
        return {
            'name': 'Sale orders Status for salesperson',
            'view_type': 'form',
            'view_mode': 'tree,',
            'res_model': 'sale.order.line',
            'view' : [(self.env.ref('gt_order_mgnt.sale_support_view_new').id, 'tree')],
            'type': 'ir.actions.act_window',
           'domain' : [('order_id.user_id', '=', self.env.user.id)],
            'context' : {'search_default_requested' : 1}
        }

    accepted_request = fields.Integer('#Accepted Payment Request', compute =get_accepted_payment_request)
    rejected_request = fields.Integer('#Rejected Payment Request', compute =get_rejected_payment_request)
    pending_request = fields.Integer('#Pending Payment Request', compute =get_pending_payment_request)
    order_pending_request = fields.Integer('#Pending Payment Request', compute =get_order_pending_request)
    line_pending_request = fields.Integer('#Pending Payment Request Line', compute =get_order_pending_request_salesperson)
    
    @api.multi
    def show_discount_requested(self):
    	'''INherite view to show proper quotation according to sale view '''
    	form_view = self.env.ref('sale.view_order_form',False)
	tree_view = self.env.ref('sale.view_quotation_tree',False)
	sale_id =  self.env['sale.order'].search([('team_id','=',self.id),('state','=','draft'), ('approval_status', '=', 'waiting_approval')])
	if any([x.is_reception==True for x in sale_id]):
		form_view = self.env.ref('gt_order_mgnt.view_sale_reception_form_api',False)
		tree_view = self.env.ref('gt_order_mgnt.view_sale_reception_tree_api',False)
	result={
	    'name': 'Discount Requested',
	    'type': 'ir.actions.act_window',
	    'view_type': 'form',
	    'view_mode': 'form',
	    'res_model': 'sale.order',
	    'target': 'current',
	}
	if sale_id:
		if len(sale_id)==1:
			result.update({'views' : [(form_view.id,'form')],
		    		     'view_id': form_view.id,
		    		     'res_id':sale_id.id})
	     	else:
	     		result.update({'views' : [(tree_view.id,'tree'),(form_view.id,'form')],
            			     'view_id': tree_view.id,
		    		     'domain':[('id','in',sale_id._ids)]})
	    	return result
        
    @api.multi
    def show_approve_discount(self):
    	form_view = self.env.ref('sale.view_order_form',False)
	tree_view = self.env.ref('sale.view_quotation_tree',False)
	sale_id =  self.env['sale.order'].search([('team_id','=',self.id),('state','=','draft'),('approval_status', '=','approved')])
	if any([x.is_reception==True for x in sale_id]):
		form_view = self.env.ref('gt_order_mgnt.view_sale_reception_form_api',False)
		tree_view = self.env.ref('gt_order_mgnt.view_sale_reception_tree_api',False)
	result={
	    'name': 'Discount Approved',
	    'type': 'ir.actions.act_window',
	    'view_type': 'form',
	    'view_mode': 'form',
	    'res_model': 'sale.order',
	    'target': 'current',
	}
	if sale_id:
		if len(sale_id)==1:
			result.update({'views' : [(form_view.id,'form')],
		    		     'view_id': form_view.id,
		    		     'res_id':sale_id.id})
	     	else:
	     		result.update({'views' : [(tree_view.id,'tree'),(form_view.id,'form')],
            			     'view_id': tree_view.id,
		    		     'domain':[('id','in',sale_id._ids)]})
	    	return result


