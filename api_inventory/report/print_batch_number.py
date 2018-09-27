# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
class production_batch_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(production_batch_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_barcode_data': self._get_barcode_data,
            'get_print_data':self._get_print_data,
            'get_view': self._get_view,
        })
        
    def _get_view(self, object):
        return object.from_preview
    
    def _get_barcode_data(self,object,count):
    	cnt=0
    	result=''
	if len(object)<=count:
    		return ''
	line=object[count] 
	if line:
		if line.print_bool:
			result = line.name
    	return result

    def _get_print_data(self,object):  
    	res=[]
    	for rec in object.inprocess_batches:
		if rec.print_bool:
		     	res.append(rec)
     	for rec in object.produce_batches:
		if rec.print_bool:
		     	res.append(rec)
     	return res
    	
class report_quotation_parser(models.AbstractModel):
    _name = 'report.api_inventory.production_batch_number_print'
    _inherit = 'report.abstract_report'
    _template = 'api_inventory.production_batch_number_print'
    _wrapped_report_class = production_batch_parser
    
