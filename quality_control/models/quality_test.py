# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp


class QualityTest(models.Model):
    """
    A test is a group of questions along with the values that make them valid.
    """
    _name = 'quality.test'
    _description = 'Quality Inspection test'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Name', required=True, translate=True, select=True)
    test_lines = fields.One2many('quality.test.question', inverse_name='test',string='Questions', copy=True)
    fill_correct_values = fields.Boolean(string='Pre-fill with correct values')
    inspection_type = fields.Selection([('generic', 'Generic'),('related', 'Related')],string='Inspection Type',
    				 select=True, required=True, default='generic')
    #category = fields.Many2one('quality.test.category', string='Category')
    company_id = fields.Many2one('res.company', string='Company',
				default=lambda self: self.env['res.company']._company_default_get('quality.test'))


class QualityTestQuestion(models.Model):
    """Each test line is a question with its valid value(s)."""
    _name = 'quality.test.question'
    _description = 'Quality control question'
    _order = 'sequence, id'

    @api.one
    @api.constrains('ql_values')
    def _check_valid_answers(self):
        if (self.question_type == 'qualitative' and self.ql_values and
                not self.ql_values.filtered('ok')):
            raise exceptions.Warning(_("There isn't no value marked as OK. You have to mark at ""least one."))

    @api.one
    @api.constrains('min_value', 'max_value')
    def _check_valid_range(self):
        if self.question_type == 'quantitative' and self.min_value > self.max_value:
            raise exceptions.Warning(_("Minimum value can't be higher than maximum value."))

    name = fields.Char(string='Name', required=True, select=True, translate=True)
    test = fields.Many2one('quality.test', string='Test')
    sequence = fields.Integer(string='Sequence', required=True, default="10")
    question_type = fields.Selection([('qualitative', 'Qualitative'),('quantitative', 'Quantitative')], string='Type', required=True)
    ql_values = fields.One2many('quality.test.question.value', inverse_name="test_line",
        string='Qualitative values', copy=True)
    notes = fields.Text(string='Notes')
    min_value = fields.Float(string='Min',digits=dp.get_precision('Quality Control'))
    max_value = fields.Float(string='Max',digits=dp.get_precision('Quality Control'),)
    uom_id = fields.Many2one('product.uom', string='Uom')

    
class QualityTestQuestionValue(models.Model):
    _name = 'quality.test.question.value'
    _description = 'Possible values for qualitative questions.'

    test_line = fields.Many2one("quality.test.question", string="Test question")
    name = fields.Char(string='Name', required=True, select=True, translate=True)
    ok = fields.Boolean(string='Correct answer?',help="When this field is check, then considered as correct answer.")
    
    
