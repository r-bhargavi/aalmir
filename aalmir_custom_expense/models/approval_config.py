# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class ApprovalConfig(models.Model):
    _name = 'approval.config'
    
    
    name=fields.Char(string='Approval Name')
    approval_line = fields.One2many('approval.config.line','approve_id','Approval Lines')
	
class ApprovalConfigLine(models.Model):
    _name = 'approval.config.line'
    
    approve_id = fields.Many2one('approval.config', 'Approve ID')
    partner_id = fields.Many2one('res.partner', 'Partner')
    approval_by = fields.Many2one('res.users', 'Approval By')
    approve_amount = fields.Float('Approval Amount')
