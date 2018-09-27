# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, exceptions, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
import openerp.addons.decimal_precision as dp
from datetime import datetime,date
import re
from dateutil.relativedelta import relativedelta
import math
import sys
import logging
_logger = logging.getLogger(__name__)
import os
import base64
				
class stockPickingType(models.Model):
	_inherit = "stock.picking.type"

	@api.multi
	def picking_count_operations(self):
		for rec in self:
			in_pick=self.env['stock.picking'].search([('picking_type_id','=',rec.id),('picking_status','=','pick_list'),('state','in',('assigned','partially_available'))])
			rec.count_in_picking_order= len(in_pick)
			
			disp_pick=self.env['stock.picking'].search([('picking_type_id','=',rec.id),('picking_status','=','r_t_dispatch'),('state','in',('assigned','partially_available'))])
			rec.count_ready_to_dispatch= len(disp_pick)
			
	count_in_picking_order = fields.Integer('IN Picking', compute='picking_count_operations')
	count_ready_to_dispatch = fields.Integer('Ready To Dispatch', compute='picking_count_operations')
	
	@api.multi
	def get_action_picking_tree_deady_to_dispatch(self):
		return self._get_action('api_inventory.action_picking_tree_ready_to_dispatch')

	@api.multi
	def get_action_picking_tree_in_picking(self):
		return self._get_action('api_inventory.action_picking_tree_in_picking_state')


