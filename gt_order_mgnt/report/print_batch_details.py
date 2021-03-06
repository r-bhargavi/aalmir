# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta

class production_batch_details_parser_wo(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(production_batch_details_parser_wo, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
        	'get_external_code':self._get_external_code,
            	'get_customer_data':self._get_customer_data,
            	'get_barcode_data':self._get_barcode_data,
            	'get_quantity':self._get_quantity,
            	'get_print_data':self._get_print_data,
            	'get_new_val':self._get_new_val,
            	'get_new_data':self._get_new_data,
            	'get_view': self._get_view,
        })
        
    def _get_view(self):
        return object.from_preview
    
    def _get_external_code(self,object):
    	
    	return ''

    def _get_new_val(self,object):
    	
    	return ''
    
    def _get_new_data(self,object):
    	
    	return ''
    	
    def _get_customer_data(self,object):
    	cnt=0
	request_ids=self.pool.get('n.manufacturing.request').search(self.cr, self.uid, 
							[('name','=',object.production_id.request_line.name)], context=None)
	request_id=self.pool.get('n.manufacturing.request').browse(self.cr, self.uid,request_ids, context=None)
    	return request_id.n_sale_line.partner_id.name if request_id else ''

    def _get_barcode_data(self,object,count):
    	result=''
    	if len(object)<=count:
    		return ''
	line=object[count]
	if line:
		if line.print_bool:
			result=line.name
    	return result
    	
    def _get_quantity(self,object,count):
	result=''
	if len(object)<=count:
    		return ''
	line=object[count] 
        print "linelineline",line
	if line:
		if line.print_bool:
			result=''.join([str(line.convert_product_qty),line.uom_id.name if line.uom_id else ''])
    	return result

    def _get_print_data(self,object):  
    	res=[]
    	for rec in object.batch_ids:
		if rec.print_bool:
		     	res.append(rec)
     	return res
     	
class report_quotation_parser(models.AbstractModel):
    _name = 'report.gt_order_mgnt.production_batch_details_print_wo'
    _inherit = 'report.abstract_report'
    _template = 'gt_order_mgnt.production_batch_details_print_wo'
    _wrapped_report_class = production_batch_details_parser_wo


