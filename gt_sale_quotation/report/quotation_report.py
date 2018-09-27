# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
class quotation_report_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(quotation_report_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_current_bank': self._get_current_bank,
            'get_view': self._get_view,
#            'get_delivery_lead_time': self._get_delivery_lead_time,
        })
        
    def _get_view(self, object):
        return object.from_preview
    
    def _get_current_bank(self, object):
        report_currency = usd_bank= False #CH_N018 
        for bank in object.company_id.partner_id.bank_ids:
            if bank.currency_id.name=='USD':		#CH_N018 Add to show USD bank detail if bank is not present for currency
 		usd_bank=bank
            if object.report_currency_id.id == bank.currency_id.id and bank.active_account == True:
                report_currency = bank
                break
	    if not object.report_currency_id and object.n_quotation_currency_id:
		if object.n_quotation_currency_id.id == bank.currency_id.id and bank.active_account == True:
                	report_currency = bank
                	break
		
        if report_currency == False:			#CH_N018 start
		report_currency = usd_bank		#CH_N018 end
        return report_currency
    
#    def _get_delivery_lead_time(self, object):
#        if object.commitment_date:
#            cdate = datetime.strptime(object.commitment_date, '%m/%d/%Y %H:%M:%S')
#            d = cdate - datetime.now()
#            return str(d.days) + 'Days'
#        else:
#            return ''
    
class report_quotation_parser(models.AbstractModel):
    _name = 'report.gt_sale_quotation.report_quotation_aalmir1'
    _inherit = 'report.abstract_report'
    _template = 'gt_sale_quotation.report_quotation_aalmir1'
    _wrapped_report_class = quotation_report_parser
