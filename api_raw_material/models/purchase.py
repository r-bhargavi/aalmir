# -*- coding: utf-8 -*-
# copyright reserved

from datetime import date, datetime,timedelta
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError
    	
class StockPurchaseRequest(models.Model):
    _inherit='stock.purchase.request.line'
   
    material_request_id=fields.Many2one('mrp.raw.material.request', 'RM Request No.')
    
