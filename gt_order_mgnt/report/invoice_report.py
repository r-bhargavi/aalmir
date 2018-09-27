# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
import json

class invoice_report_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(invoice_report_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_current_bank': self._get_current_bank,
            'get_view': self._get_view,
            'get_details': self.get_details,
        })
        
    def _get_view(self, object):
        return object.from_preview
    
   
    def _get_current_bank(self, object):
        bank1 = usd_bank=False 
        for bank in object.company_id.partner_id.bank_ids:
            if bank.currency_id.name=='USD':		
 		usd_bank=bank
            if object.currency_id.id == bank.currency_id.id and bank.active_account == True:
                bank1 = bank
                break
        if bank1 == False:			
		bank1 = usd_bank		
        return bank1   
     
    def get_details(self, doc):
        lines = []
        acc_inv = self.pool.get('account.invoice').search(self.cr, self.uid, [('id', '=', doc.id)])
        acc_inv_rec = self.pool.get('account.invoice').browse(self.cr, self.uid, acc_inv, context=None)
        if acc_inv_rec.payments_widget != 'false':
            d = json.loads(acc_inv_rec.payments_widget)
            for payment in d['content']: 
                vals = {
                    'method': payment['journal_name'],
                }
                lines.append(vals)
        return lines
        
class report_invoice_parser(models.AbstractModel):
    _name = 'report.gt_order_mgnt.report_invoice_aalmir_vendor'
    _inherit = 'report.abstract_report'
    _template = 'gt_order_mgnt.report_invoice_aalmir_vendor'
    _wrapped_report_class = invoice_report_parser
