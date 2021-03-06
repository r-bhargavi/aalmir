# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta


class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    check_total = fields.Boolean(string='Check Total',compute='_compute_check_total_tracker',default=False,store=True)
#    employee_bill = fields.Boolean(string='Employee Bill',default=False)
#    @api.onchange('employee_bill')
#    def employee_bill_onchange(self):
#        print "employee bil------------------",self.employee_bill
#    	if self.employee_bill and self.employee_bill == False:
#            pass
#        elif self.employee_bill and self.employee_bill ==True:
#            print "self._context-------------------",self._context
#            return {'domain': {'partner_id': [('employee', '=', True)]}}
    @api.depends('amount_total','state','origin')
    def _compute_check_total_tracker(self):
        print "yrfbfnmfdknkjfngkdjngkjdfbg-------------------------"
        for invoice in self:
            if invoice.type in ('in_invoice','in_refund'):
                if not invoice.origin and invoice.state in ('draft','waiting_approval'):
                    print "if condition matched-----------------"
                    non_approval=self.env['approval.config.bill.line'].search([('partner_id','=',invoice.partner_id.id)])
                    print "non_approvalnon_ap123123provalnon_approval",non_approval
                    if non_approval:
                        if non_approval.currency_id.id!=invoice.currency_id.id:
                            from_currency = non_approval.currency_id
                            to_currency = invoice.currency_id
                            limit_amt = from_currency.compute(non_approval.approve_amount, to_currency, round=False)
                        else:
                            limit_amt=non_approval.approve_amount
                        if invoice.amount_total>limit_amt:
                            invoice.check_total=True
                        else:
                            invoice.check_total=False
                    else:
                         invoice.check_total=True
                else:
                    print "ekse part-----345345----------------"
                    invoice.check_total=False
        print "self.check_totalself.check_totalself.check_total",invoice.check_total
  
            

    
