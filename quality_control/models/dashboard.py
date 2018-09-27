# -*- coding: utf-8 -*-
# copyright reserved

from openerp import fields, models ,api, _
from openerp.exceptions import UserError, ValidationError
import logging
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta
import json

class QualityDashboard(models.Model):
    _name = 'quality.dashboard'
    
    name = fields.Char(string="Name")
    color = fields.Integer(string='Color Index')
    
    @api.one
    def _kanban_dashboard_graph(self):
	    ids=self.env['account.journal'].search([('type','=','bank')],limit=1)
            self.kanban_dashboard_graph = json.dumps(ids.get_line_graph_datas())

    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    @api.multi
    def action_open_quality(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'mo':
		domain=[('n_type', '=','new')]
		_name = "Manufacturing Check Orders"
	if self._context.get('n_state') == 'repaired':
		domain=[('n_type', '=','repaired')]
		_name = "Repaired Quality Checks"
	'''if self._context.get('n_state') == 'available':
		domain=[('state', '=', 'available')]
		_name = "Available Orders"
	if self._context.get('n_state') == 'waiting':
		domain=[('state', '=', 'waiting')]
		_name = "Waiting Orders" '''
		
	po_tree = self.env.ref('quality_control.quality_checking_line_tree_view', False)
	po_form = self.env.ref('quality_control.quality_checking_line_form_view', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'quality.checking.line',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }

    @api.multi
    def _get_statedetail(self):
	ids1=self.env['quality.checking'].search([('mrp_id','!=',False),('state','not in',('complete','canceled'))])
	ids2=self.env['quality.checking'].search([('purchase_id','!=',False),('state','not in',('complete','canceled'))])
	ids3=self.env['quality.checking'].search([('state','=','available')])
	ids4=self.env['quality.checking'].search([('state','=','waiting')])
     #inspection
        ids5= self.env['quality.inspection'].search([('state','=','draft')])
        ids6= self.env['quality.inspection'].search([('state','=','ready')])
        ids7= self.env['quality.inspection'].search([('state','=','partial_failed')])
        ids8= self.env['quality.inspection'].search([('state','=','partial')])
     #test
     	ids9= self.env['quality.test'].search([('inspection_type','=','generic')])
        ids10= self.env['quality.test'].search([('inspection_type','=','related')])
     #Questions
     	ids11= self.env['quality.test.question'].search([('question_type','=','qualitative')])
        ids12= self.env['quality.test.question'].search([('question_type','=','quantitative')])
       
     #quality check line 
        ids13=self.env['quality.checking.line'].search([('n_type','=','new')])
        ids14=self.env['quality.checking.line'].search([('n_type','=','repaired')])
	return {
		'mo_ids':len(ids1),
		'po_ids':len(ids2),
		'available':len(ids3),
		'waiting':len(ids4),
		'draft':len(ids5),
		'ready':len(ids6),
		'failed':len(ids7),
		'success':len(ids8),
		'generic':len(ids9),
		'related':len(ids10),
		'qualitative':len(ids11),
		'quantitative':len(ids12),
                'from_mo':len(ids13), 
                'from_repaired':len(ids14)
		}


    @api.one
    def _get_detail(self):
        self.status_dashboard = json.dumps(self._get_statedetail())

    status_dashboard = fields.Text(compute = '_get_detail')

    @api.multi
    def action_open_inspection(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'draft':
		domain=[('state', '=', 'draft')]
		_name = "Inspections In Draft State"
	if self._context.get('n_state') == 'ready':
		domain=[('state', '=', 'ready')]
		_name = "Inspections In Ready State"
	if self._context.get('n_state') == 'partial_failed':
		domain=[('state', '=', 'partial_failed')]
		_name = "Inspections In Partial Failed State"
	if self._context.get('n_state') == 'partial':
		domain=[('state', '=', 'partial')]
		_name = "Inspections In Partial Success State"
		
	po_tree = self.env.ref('quality_control.quality_inspection_tree_view', False)
	po_form = self.env.ref('quality_control.quality_inspection_form_view', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'quality.inspection',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }

    @api.multi
    def action_open_tests(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'generic':
		domain=[('inspection_type', '=', 'generic')]
		_name = "Generic Test"
	if self._context.get('n_state') == 'related':
		domain=[('inspection_type', '=', 'related')]
		_name = "related Tests"
		
	po_tree = self.env.ref('quality_control.quality_test_tree_view', False)
	po_form = self.env.ref('quality_control.quality_test_form_view', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'quality.test',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }

    @api.multi
    def action_open_questions(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'qualitative':
		domain=[('question_type', '=', 'qualitative')]
		_name = "Qualitative Questions"
	if self._context.get('n_state') == 'quantitative':
		domain=[('question_type', '=', 'quantitative')]
		_name = "Quantitative Questions"
		
	po_tree = self.env.ref('quality_control.quality_test_question_tree_view', False)
	po_form = self.env.ref('quality_control.quality_test_question_form_view', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'quality.test.question',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }

