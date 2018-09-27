# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#CH03 add on_change to change base currency and converted currency

from openerp import api, fields, models, _
from openerp import fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta

class resUsers(models.Model):
	_inherit = "res.users"

	@api.model
	def name_search(self,name, args=None, operator='ilike', limit=100):
		''' inherite function to show only inventory users'''
		'''if self._context.get('warehouse'):
			groups_ids=self.env['res.groups'].search([('name','=','Store Operator')])
			ids=[]
			for user in groups_ids:
				ids.extend(user.users._ids) 
			args=[('id','in',ids)]'''
	    	return super(resUsers,self).name_search(name, args, operator=operator, limit=limit)
		
