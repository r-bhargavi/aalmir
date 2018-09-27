from openerp import fields, models ,api, _,SUPERUSER_ID
from openerp.exceptions import UserError, ValidationError
import logging
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp
import math
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
import json

class stockWarehouse(models.Model):
	_inherit = "stock.warehouse"

	@api.model
	def create(self,vals):
		rec = super(stockWarehouse,self).create(vals)
		# create menu for sale support(order dashboard)
		view_id = self.env.ref('gt_order_mgnt.sale_support_view_new', False)
		search_view_id = self.env.ref('gt_order_mgnt.view_sale_support_filter', False)
		action_id=self.env['ir.actions.act_window'].create({'name':str(rec.name)+' Sale Support',
				'res_model':'sale.order.line','type':'ir.actions.act_window',
				'tager':'current','view_type':'form','view_mode':'tree',
				'view_id':view_id.id,'search_view_id':search_view_id.id,
				'context':{'search_default_order_id':1},
				'domain':'''[('order_id.state', '=', 'sale'), ('state', 'not in', ('done','cancel')),
				 	('product_id.name', 'not in', ('Advance Payment','Deposit Product')),
				 	('order_id.warehouse_id.id','=',{})]]'''.format(rec.id),
				})
		parent_id = self.env['ir.model.data'].get_object_reference('gt_order_mgnt', 'menu_sale_support')[1]
		self.env['ir.ui.menu'].create({'name':str(rec.name)+' Dashboard','sequence':3,
						'parent_id':parent_id,
						'action':str('ir.actions.act_window,')+str(action_id.id)})
    		return rec

	@api.multi
	def unlink(self):
		action = self.env['ir.actions.act_window'].search([('name','=',str(self.name)+' Sale Support')])
		if action :
			action.unlink()
		menu_id = self.env['ir.ui.menu'].search([('name','=',str(self.name)+' Dashboard')])
		if menu_id :
			menu_id.unlink()
		return super(stockWarehouse,self).unlink()

