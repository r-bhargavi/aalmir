# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta


class TypeProduct(models.Model):
    _name = "type.product"
    
    
    name = fields.Char('TypeProduct')
    
class productTemplate(models.Model):
    _inherit = "product.template"
    
    
    partner_id_preferred = fields.Many2one('res.partner', 'Preferred Partner')
    
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    
    type_product = fields.Many2one('type.product', 'Category Product')
    
    @api.model
    def create(self, vals):
        product = super(ProductProduct, self).create(vals)
        seq_obj = self.env['ir.sequence']

        if product.product_material_type.string=='expense':
            v=False
            v= seq_obj.next_by_code('expense.internal.number')
            product.write({'default_code' :v})
        return product
    
    @api.onchange('type_product')
    def type_product_onchange(self):
    	if self.type_product:
            self.type='service'
