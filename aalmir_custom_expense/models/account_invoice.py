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
    @api.depends('amount_total')
    def _compute_check_total_tracker(self):
        print "dsfdsfdsfdsfdsfds-------------------------"
        if self.type in ('in_invoice','in_refund'):
            if self.state in ('draft') and not self.purchase_id:
                non_approval=self.env['approval.config.bill.line'].search([('partner_id','=',self.partner_id.id)])
                print "non_approvalnon_approvalnon_approval",non_approval
                if non_approval:
                    if non_approval.currency_id.id!=self.currency_id.id:
                        from_currency = non_approval.currency_id
                        to_currency = self.currency_id
                        limit_amt = from_currency.compute(non_approval.approve_amount, to_currency, round=False)
                    else:
                        limit_amt=non_approval.approve_amount
                    if self.amount_total>limit_amt:
                        self.check_total=True
                    else:
                        self.check_total=False
#            else:
#                self.check_total=True
        print "self.check_totalself.check_totalself.check_total",self.check_total
  
            

    