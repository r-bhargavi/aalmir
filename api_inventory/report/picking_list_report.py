# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw
from openerp import api, models
from datetime import datetime, timedelta
import json

class picking_list_report_parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(picking_list_report_parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_view': self._get_view,
            'get_details': self.get_details,
        })
        
    def _get_view(self, object):
        return object.from_preview
     
    def get_details(self, doc):
        lines = []
        dict_store={}
        for batches in self.pool.get('mrp.order.batch.number').browse(self.cr, self.uid, [doc.id], context=None):
        	if dict_store.get(batches.store_id.id):
        		dict_store[batches.store_id.id] += batches.convert_product_qty
		else:
			dict_store[batches.store_id.id] = batches.convert_product_qty
	for di in dict_store:
                vals = {
                    'method': payment['journal_name'],
                }
                lines.append(vals)
	return lines
        
class picking_list_report_parser(models.AbstractModel):
    _name = 'report.api_inventory.report_picking_list_all'
    _inherit = 'report.abstract_report'
    _template = 'api_inventory.report_picking_list_all'
    _wrapped_report_class = picking_list_report_parser
    
