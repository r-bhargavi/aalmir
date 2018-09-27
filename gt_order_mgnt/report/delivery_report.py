# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
class delivery_report_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(delivery_report_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_current_bank': self._get_current_bank,
            'get_view': self._get_view,
        })
        
    def _get_view(self, object):
        return object.from_preview
    
    def _get_current_bank(self, object):
        bank1 = False
        for bank in object.company_id.partner_id.bank_ids:
            if object.report_currency_id.id == bank.currency_id.id and bank.active_account == True:
                bank1 = bank
                break
        return bank1    
 
class report_delivery_parser(models.AbstractModel):
    _name = 'report.gt_order_mgnt.report_delivery_aalmir'
    _inherit = 'report.abstract_report'
    _template = 'gt_order_mgnt.report_delivery_aalmir'
    _wrapped_report_class = delivery_report_parser
