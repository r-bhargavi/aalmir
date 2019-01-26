# -*- coding: utf-8 -*-

from openerp import models, api
from openerp import workflow
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import float_is_zero
from openerp import models, fields, api,_
from openerp.exceptions import UserError, ValidationError

class accountMove(models.Model):
    _inherit = "account.move"
#    uploaded_documents= fields.Many2many('ir.attachment','move_attachment_rel','move_doc','id','Upload Supporting Doc')
    uploaded_document= fields.Many2many('ir.attachment','move_doc_rel','mv_id','att_id','Upload Supporting Doc')

    
    name = fields.Char(string='Number', required=True, copy=False, track_visibility='onchange',default='/')
    ref = fields.Char(string='Reference', copy=False,track_visibility='onchange')
    date = fields.Date(track_visibility='onchange',required=True, states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    
    @api.multi
    def button_cancel(self):
    	if not self._context.get('voucher'):
    		jv_cnt = self.env['journal.voucher'].search([('name','=',self.name)])
    		if jv_cnt:
			raise UserError("Please Cancel the Journal voucher")
    	return super(accountMove,self).button_cancel()

 
#class account_journal(models.Model):
#    _inherit = "account.journal"
#
#    type = fields.Selection(selection_add=[('card', 'Card')])

       
