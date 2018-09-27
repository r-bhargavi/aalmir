# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from openerp.osv import osv
import json
from dateutil import parser

class AccountReceiptParser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(AccountReceiptParser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_details': self.get_details,
            'get_details_inv': self.get_details_inv,
        })
        self.context = context

    def get_details_inv(self, doc):
        lines = []
        acc_inv = self.pool.get('account.invoice').search(self.cr, self.uid, [('id', '=', doc.id)])
        acc_inv_rec = self.pool.get('account.invoice').browse(self.cr, self.uid, acc_inv, context=None)
        pay=0.0
        if acc_inv_rec.payments_widget != 'false':
            d = json.loads(acc_inv_rec.payments_widget)
            
            for payment in d['content']:
                pay +=payment['amount']
        total_amount = acc_inv_rec.amount_total
        if acc_inv_rec.state == 'draft':
            balance_amount = total_amount
        else:
            balance_amount = acc_inv_rec.residual_new1
        paid = total_amount - balance_amount
        vals = {
            'total_amount': total_amount,
            'balance_amount': total_amount - pay if not acc_inv_rec.residual_new1  else balance_amount,
            'paid': pay,
        }
        lines.append(vals)
        return lines

    def get_details(self, doc):
        lines = []
        acc_inv = self.pool.get('account.invoice').search(self.cr, self.uid, [('id', '=', doc.id)])
        acc_inv_rec = self.pool.get('account.invoice').browse(self.cr, self.uid, acc_inv, context=None)
        if acc_inv_rec.payments_widget != 'false':
            d = json.loads(acc_inv_rec.payments_widget)
            for payment in d['content']:
                my_date = parser.parse(payment['date'])
                proper_date_string = my_date.strftime('%d/%m/%Y')
                vals = {
                    'memo': payment['ref'][:15],
                    'amount': payment['amount'],
                    'method': payment['journal_name'],
                    'date': proper_date_string,
                }
                lines.append(vals)
        return lines


class PrintReport(osv.AbstractModel):
    _name = 'report.stock_merge_picking.report_payment'
    _inherit = 'report.abstract_report'
    _template = 'stock_merge_picking.report_payment'
    _wrapped_report_class = AccountReceiptParser


