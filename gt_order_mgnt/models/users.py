# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api

class Users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    signature_image = fields.Binary(string='Signature Upload')
    digital_signature = fields.Binary(string='Digital Signature')
    approve_purchase = fields.Boolean('Can Approve PO')
    approve_expense = fields.Boolean('Allowed Expense Configuration',help="If checked then allowed to configure Expenses")
    designation_purchase = fields.Char('Designation on Purchase')
    machine_ids = fields.Many2many('machinery', string='Machine')
    employee_ids = fields.Many2many('hr.employee', string='Operators')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('po_user'):
           if self._context.get('1_user'):
              users=self.search([('approve_purchase','=',True),('id','!=',self._context.get('1_user'))])
              return [(rec.id,rec.name) for rec in users]
              
        if self._context.get('po_user_1'):
           if self._context.get('2_user') or self._context.get('3_user'):
              lst=[]
              lst.append(self._context.get('2_user'))
              lst.append(self._context.get('3_user'))
              users=self.search([('approve_purchase','=',True),('id','not in',lst)])
              return [(rec.id,rec.name) for rec in users]
              
        if self._context.get('po_user_2'):
           if self._context.get('1_user') or self._context.get('3_user'):
              lst=[]
              lst.append(self._context.get('1_user'))
              lst.append(self._context.get('3_user'))
              users=self.search([('approve_purchase','=',True),('id','not in',lst)])
              return [(rec.id,rec.name) for rec in users]

        if self._context.get('po_user_3'):
           if self._context.get('1_user') or self._context.get('2_user'):
              lst=[]
              lst.append(self._context.get('1_user'))
              lst.append(self._context.get('2_user'))
              users=self.search([('approve_purchase','=',True),('id','not in',lst)])
              return [(rec.id,rec.name) for rec in users]
 
        if self._context.get('machines_name'):
            if self._context.get('machine_id'):
               users=self.search([('machine_ids','=',self._context.get('machine_id'))])
               return [(rec.id,rec.name) for rec in users]
               
        if self._context.get('operator'):
           if self._context.get('order_id'):
              order=self.env['mrp.production.workcenter.line'].search([('id','=',self._context.get('order_id'))])
              return [(rec.id,rec.name) for rec in order.user_ids]
              
        return super(Users,self).name_search(name, args, operator=operator, limit=limit)

class ResCompany(models.Model):
    _inherit='res.company'
    
    purchase_note=fields.Text('Purchase Note')   
    n_invoice_note=fields.Text('Invoice Note')
    report_note=fields.Text('Electronic Generated Signature')
    company_active=fields.Boolean('Company Active')
    min_amount=fields.Float()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


    @api.multi
    def write(self,vals):
#        print "jjjjjjjjjjjjjjjjjjjjjjjjjjjj",vals
        return super(ResCompany,self).write(vals)

