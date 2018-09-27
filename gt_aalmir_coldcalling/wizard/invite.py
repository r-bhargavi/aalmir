# -*- coding: utf-8 -*-

from openerp import _, api, fields, models

class ResUsers(models.Model):
    _inherit='res.users'
    is_user=fields.Boolean('Is User', related='partner_id.is_user', inherited=True, default=True)
    
class ResPartner(models.Model):
    _inherit='res.partner'
    is_user=fields.Boolean('Is User')


