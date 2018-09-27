# -*- coding: utf-8 -*-
from openerp import models, fields, api,_
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare, float_round
from openerp.exceptions import UserError
from urlparse import urljoin
from urllib import urlencode

class resPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self,vals):
	if vals.get('customer') or vals.get('supplier'):
        	vals.update({'n_cust_uid':self.env['ir.sequence'].next_by_code('customer.uid') or 'New'})
	return super(resPartner,self).create(vals)

    n_cust_uid = fields.Char("Customer Unique ID")

