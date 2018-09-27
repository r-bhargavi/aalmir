
# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import json

class saleSupportWizard(models.TransientModel):
    _name = 'sale.support.wizard'
    
    warehouse_id = fields.Many2one('stock.warehouse','Warehouse')
    
    @api.multi
    def search_sale(self):
    	sale_line_id=[]
	for rec in self:
		sale_line_id=self.env['sale.order.line'].search([('state','=','sale'),('order_id.warehouse_id','=',rec.warehouse_id.id)])._ids
		if not sale_line_id:
			raise UserError("No Sale order for warehouse '{}'".format(rec.warehouse_id.name))
	tree_view= self.env.ref('gt_order_mgnt.sale_support_view_new', False) 
	if tree_view:
		return {'name' :'Sale Support {}'.format(rec.warehouse_id.name),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'tree',
			'res_model': 'sale.order.line',
			'views': [(tree_view.id, 'tree')],
			'view_id': tree_view.id,
			'target': 'current',
			'domain':[('id','in',sale_line_id)],
		    	}

class stockwarehosue(models.Model):
    _inherit = 'stock.warehouse'
    
    @api.model
    def name_search(self, name, args=None, operator='ilike',limit=100):
    	print "pp...."
	if self._context.get('wiz'):
		sale_id=self.env['sale.order'].search([('state','=','sale')])
		if sale_id:
	    		warehosue=set([wh.warehouse_id.id for wh in sale_id])
			args=[('id','in',list(warehosue))]	
		else:
			return []
    	return super(stockwarehosue,self).name_search(name, args, operator=operator, limit=limit)
    	
