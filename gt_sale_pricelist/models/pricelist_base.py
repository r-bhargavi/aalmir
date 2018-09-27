 # -*- coding: utf-8 -*-
##############################################################################
#
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import fields, models ,api, _

class material_details(models.Model):
    _name = 'material.details'

    name =  fields.Many2one('product.product',string='Name')
    kg_price = fields.Float(string='Kg Price',digits=(3, 2))
    density = fields.Float(string='Density',digits=(3, 2))
    product_type = fields.Many2many('product.type', 'prod_type_mat_rel', 'mat_id', 'type_id', string="Product Type")

class product_details(models.Model):
    _name = 'product.type'

    name =  fields.Many2one('product.template',string='Film Converison')
    price_per_kg= fields.Float(string='Price Per Kg',digits=(3, 2))
    calculation_for_print_area = fields.Float(string='Calculation For Print Area',digits=(3, 2))
    #category = fields.Many2one('product.category',string='Category')

class Bag_type(models.Model):
    _name = 'bag.type'

    name =  fields.Many2one('product.attribute',string='Type Of Bag')
    conversion_charge= fields.Float(string='Conversion Charges',digits=(3,5))
    extra_weight = fields.Float(string='Extra Weight',digits=(3,5))

class printing_type(models.Model):
    _name = 'printing.type'

    name =  fields.Char(string='Printing')
    cost= fields.Float(string='Cost',digits=(2,2))
    plates = fields.Float(string='Plates',digits=(2,2))
#    exceed_per = fields.Float(string="Excees %", digits=(2,2))

    @api.multi
    def write(self,vals):
        if self.env.uid==1:
            return super(printing_type,self).write(vals)
        else:
            return True
class delivery_location(models.Model):
    _name = 'delivery.location'

    name =  fields.Char(string='Delivery Location')
    km1= fields.Float(string='3000',digits=(2,10))
    km2= fields.Float(string='7000',digits=(2,10))
    km3= fields.Float(string='15000',digits=(2,10))

class packing_details(models.Model):
    _name = 'packing.details'

    name =  fields.Char(string='Paking')
    cost= fields.Float(string='Cost',digits=(2,2))

class microns_details(models.Model):
    _name = 'microns.details'

    name =  fields.Many2one('product.attribute',string='Microns')
    microns1= fields.Float(string='40 - 250',digits=(2,4))
    microns2= fields.Float(string='25 - 39.5',digits=(2,4))
    microns3= fields.Float(string='Less than 24.9',digits=(2,4))

class ink_details(models.Model):
    _name = 'ink.type'

    name =  fields.Char(string='Ink Type')
    ink_price_per_kg= fields.Float(string='Price Per Kg',digits=(2,2))
    ink_price= fields.Char(string='Price')
    ink_printing_plates= fields.Float(string='Printing Plate',digits=(2,2))

class Discount_details(models.Model):
    _name = 'discount.type'

    qty_from = fields.Char(string='Quantity')
    # qty_to = fields.Integer(string='To Quantity')
    discount = fields.Integer(string='Discount Eligiblity (%)')


class Stratch_details(models.Model):
    _name = 'stratch.calculator'
    _rec_name = 'weight_each_roll_in_kg'

    thickness = fields.Char(string='Thickness')
    weight_each_roll_in_kg = fields.Float(string='weight of each roll in kg',digits=(2,2))
    pcs_ctn = fields.Float(string='pcs/ ctn',digits=(2,2))
    kg_ctn = fields.Float(string='kg/ cTn',digits=(2,2))
    price_ctn = fields.Float(string='Price /CTN',digits=(2,2))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

class inclusions_details(models.Model):
    _name = 'inclusions.details'

    name =  fields.Char(string='Inclusion Name')
    itype = fields.Selection([('per_glue','Glue'),
				('per_cour_res_lin','Permanant Courrier'),
				('resealable_tape','Tape'),
				('smpl_zipper','Zipper'),
				('security_tape','Security Tape'),],string="Type")
    inclusions= fields.Float(string='Cost/lm',digits=(2,10),help='Cost per linear Meter')
    

