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
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import logging
from datetime import datetime
_logger = logging.getLogger(__name__)
from urllib import urlencode
from urlparse import urljoin

class price_current_value(models.Model):
    _name = 'price.current.value'
    
    unit = fields.Many2one('product.uom', string="UOM")
    unit_price = fields.Float('Unit Price')
    qty = fields.Float('Quantity')

class pricelist_calculater(models.Model):
    _name = 'pricelist.calculater'
    
    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            name = 'View Product Details'
            result.append((rec.id, name))
        return result
    
    @api.model
    def _default_total_printing_area_formula(self):
        return "(self.product_type.calculation_for_print_area)*(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(float(self.printing_area)/100)*(self.printing_type.plates)"
    
    @api.model
    def _last_total_printing_area_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_total_printing_area:
                return c_ids[0].last_total_printing_area
            else:
                return c_ids[0].default_total_printing_area
        else:
            return "(self.product_type.calculation_for_print_area)*(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(float(self.printing_area)/100)*(self.printing_type.plates)"
    
    @api.model
    def _default_ink_weigth_formula(self):
        return """self.printing_type.name == 'Full print' and (self.total_printing_area)*(0.0003)*1.22 or (self.total_printing_area) * (0.0009) * 1.22"""
    
    @api.model
    def _last_ink_weigth_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_ink_weigth:
                return c_ids[0].last_ink_weigth
            else:
                return c_ids[0].default_ink_weigth
        else:
            return """self.printing_type.name == 'Full print' and (self.total_printing_area)*(0.0003)*1.22 or (self.total_printing_area) * (0.0009) * 1.22"""
    
    @api.model
    def _default_weight_per_gram_formula(self):
        return "(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(self.micron/10000.0)*(self.material_type.density)*(self.product_type.calculation_for_print_area)+((self.bag_type.extra_weight)+self.ink_weigth)"
    
    @api.model
    def _last_weight_per_gram_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_weight_per_gram:
                return c_ids[0].last_weight_per_gram
            else:
                return c_ids[0].default_weight_per_gram
        else:
            return "(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(self.micron/10000.0)*(self.material_type.density)*(self.product_type.calculation_for_print_area)+((self.bag_type.extra_weight)+self.ink_weigth)"
    
    @api.model
    def _default_weight_per_kg_formula(self):
        return "self.weight_per_gram/1000.0"
    
    @api.model
    def _last_weight_per_kg_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_weight_per_kg:
                return c_ids[0].last_weight_per_kg
            else:
                return c_ids[0].default_weight_per_kg
        else:
            return "self.weight_per_gram/1000.0"
        
    @api.model
    def _default_total_weight_formula(self):
        return "self.unit.name == 'Kg' and self.qty or self.unit.name == 'Pcs' and self.weight_per_kg * self.qty"
    
    @api.model
    def _last_total_weight_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_total_weight:
                return c_ids[0].last_total_weight
            else:
                return c_ids[0].default_total_weight
        else:
            return "self.unit.name == 'Kg' and self.qty or self.unit.name == 'Pcs' and self.weight_per_kg * self.qty"
        
    @api.model
    def _default_price_per_kg_formula(self):
        return "self.price_per_pc/self.weight_per_kg"
    
    @api.model
    def _last_price_per_kg_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_price_per_kg:
                return c_ids[0].last_price_per_kg
            else:
                return c_ids[0].default_price_per_kg
        else:
            return "self.price_per_pc/self.weight_per_kg"
            
    @api.model
    def _default_printing_cost_formula(self):
        return "self.total_printing_area * 0.45"
    
    @api.model
    def _last_printing_cost_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_printing_cost:
                return c_ids[0].last_printing_cost
            else:
                return c_ids[0].default_printing_cost
        else:
            return "self.total_printing_area * 0.45"
        
    @api.model
    def _default_total_pcs_formula(self):
        return "self.unit.name == 'Kg' and (self.weight_per_kg and self.total_weight / self.weight_per_kg) or self.unit.name == 'Pcs' and self.qty or 0"
    
    @api.model
    def _last_total_pcs_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_total_pcs:
                return c_ids[0].last_total_pcs
            else:
                return c_ids[0].default_total_pcs
        else:
            return "self.unit.name == 'Kg' and (self.weight_per_kg and self.total_weight / self.weight_per_kg) or self.unit.name == 'Pcs' and self.qty or 0"
        
    @api.model
    def _default_max_discount_formula(self):
        return "(self.bag_type and self.total_weight) and ((self.bag_type.name.name == 'Garbage bag' and self.total_weight >= 500.1 and self.total_weight <= 1000) and 5 or (self.bag_type.name.name == 'Garbage bag' and self.total_weight >= 4999) and 10 or (self.total_weight >= 500.1 and self.total_weight <= 1000) and 5 or (self.total_weight >= 1001 and self.total_weight <= 4999) and 10 or (self.total_weight >= 5000) and 20 or 0) or 0"
    
    @api.model
    def _last_max_discount_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_max_discount:
                return c_ids[0].last_max_discount
            else:
                return c_ids[0].default_max_discount
        else:
            return "(self.bag_type and self.total_weight) and ((self.bag_type.name.name == 'Garbage bag' and self.total_weight >= 500.1 and self.total_weight <= 1000) and 5 or (self.bag_type.name.name == 'Garbage bag' and self.total_weight >= 4999) and 10 or (self.total_weight >= 500.1 and self.total_weight <= 1000) and 5 or (self.total_weight >= 1001 and self.total_weight <= 4999) and 10 or (self.total_weight >= 5000) and 20 or 0) or 0"
            
    @api.model
    def _default_total_price_formula(self):
        return "self.unit and (self.product_type.name.name == 'Stretch Film' and (self.stratch_calculator and (self.unit.name == 'pcs') and self.price_per_pc * self.qty or self.price_per_kg * self.qty) or (self.unit.name == 'pcs' and self.price_per_pc * self.qty or self.price_per_kg * self.qty)) or 0"
    
    @api.model
    def _last_total_price_formula(self):
        c_ids = self.search([], order='id desc')
        if c_ids:
            if c_ids[0].last_total_price:
                return c_ids[0].last_total_price
            else:
                return c_ids[0].default_total_price
        else:
            return "self.unit and (self.product_type.name.name == 'Stretch Film' and (self.stratch_calculator and (self.unit.name == 'pcs') and self.price_per_pc * self.qty or self.price_per_kg * self.qty) or (self.unit.name == 'pcs' and self.price_per_pc * self.qty or self.price_per_kg * self.qty)) or 0"
    
    ## add by Vimal start 13feb 17 >>>>
    @api.multi
    @api.onchange('change_bool')
    def price_cal_readonly(self):
        for record in self:
            if self.change_bool == True:
                self.n_state='qty_change'
                self.n_hide =False
            if self.change_bool == False:
                self.n_state='make_change'
                self.n_hide =True
    ## end <<<<

    product_type=  fields.Many2one('product.type',string='Product Type')
    check_product_type = fields.Boolean(string="Product Type", default=True)
    product_type_name = fields.Char(related='product_type.name.name')
    

    material_type =  fields.Many2one('material.details',string='Material')
    
    check_material_type = fields.Boolean(string="Material")
    stratch_calculator =  fields.Many2one('stratch.calculator',string='Stratch Film')
    check_stratch_calculator = fields.Boolean(string="Stratch Film")
    bag_type =  fields.Many2one('bag.type',string='Type Of Bags/film')
    bag_name =  fields.Char(related='bag_type.name.name',string='Bag Type')
    check_bag_type = fields.Boolean(string="Type Of Bags/film")
    delivery_location =  fields.Many2one('delivery.location',string='Delivery Location')
    check_delivery_location = fields.Boolean(string="Delivery Location")
    packing_type =  fields.Many2one('packing.details',string='Packing')
    check_packing_type = fields.Boolean(string="Packing")
    unit =  fields.Many2one('product.uom',string='Quantity Required Unit')
    description = fields.Text(string="Descriptiom", compute="_get_description", store=True)
    
    qty =  fields.Integer(string='Quantity')
    moq_length = fields.Float(compute="_get_calculate_prices", string='MOQ Required in pcs', digits=dp.get_precision('product'), store=True)
    check_moq_length = fields.Boolean(string="MOQ Required in pc/length(cm)")
    ink_weigth = fields.Float(compute="_get_calculate_prices", string='Ink Weight', digits=dp.get_precision('product'), store=True)
    check_ink_weigth = fields.Boolean(string="Ink Weight")
    total_printing_area = fields.Float(compute="_get_calculate_prices", string='Total Printing areas cm2', digits=dp.get_precision('product'), store=True)
    check_total_printing_area = fields.Boolean(string="Total Printing areas cm2")

    micron =  fields.Integer(string='Thickness (micron)')
    check_micron = fields.Boolean(string="Thickness (micron)")
    printing_type =  fields.Many2one('printing.type',string='Printing')
    check_printing_type = fields.Boolean(string="Printing")
    printing_type_name = fields.Char(related='printing_type.name')
    printing_area =  fields.Integer(string='Printing Area %')
    check_printing_area = fields.Boolean(string="Printing Area")

    lenght =  fields.Integer(string='Length (cm)')
    check_lenght = fields.Boolean(string="Length")
    width =  fields.Integer(string='Width (cm)')
    check_width = fields.Boolean(string="Width")
    left =  fields.Integer(string='Left gusset (cm)')
    check_left = fields.Boolean(string="Left gusset")
    right =  fields.Integer(string='Right gusset (cm)')
    check_right = fields.Boolean(string="Right gusset")
    top =  fields.Integer(string='Top fold (cm)')
    check_top = fields.Boolean(string="Top fold")
    bottom =  fields.Integer(string='Bottom gusset (cm)')
    check_bottom = fields.Boolean(string="Bottom gusset")

    weight_per_gram = fields.Float(compute="_get_calculate_prices", string="Weight Per Item(gm)", digits=dp.get_precision('Payment Term'), store=True)
    check_weight_per_gram = fields.Boolean(string="Weight Per Gram")
    weight_per_kg = fields.Float(compute="_get_calculate_prices", string="Weight Per Item(Kg)", digits=dp.get_precision('Payment Term'), store=True)
    check_weight_per_kg = fields.Boolean(string="Weight Per Kg")
    total_weight = fields.Float(compute="_get_calculate_prices", string="Total Weight", digits=dp.get_precision('product'), store=True)
    check_total_weight = fields.Boolean(string="Total Weight")
    price_per_kg = fields.Float(compute="_get_calculate_prices", string="Price Per KG", digits=dp.get_precision('Payment Term'), store=True)
#    check_price_per_kg = fields.Boolean(string="Price Per KG")
    price_per_pc = fields.Float(compute="_get_calculate_prices", string="Price Per PC", digits=dp.get_precision('Payment Term'), store=True)
#    check_price_per_pc = fields.Boolean(string="Price Per PC")
    printing_cost = fields.Float(compute="_get_calculate_prices", string="Printing Cost", digits=dp.get_precision('product'), store=True)
    check_printing_cost = fields.Boolean(string="Printing Cost")
    total_pcs = fields.Float(compute="_get_calculate_prices", string="Total PCS", digits=dp.get_precision('product'), store=True)
    check_total_pcs = fields.Boolean(string="Total PCS")
    max_discount = fields.Integer(compute="_get_calculate_prices", string='Max Discount Eligibility', store=True)
#    check_max_discount = fields.Boolean(string="Max Discount Eligibility")
    total_price = fields.Float(compute="_get_calculate_prices", string="Total Price", digits=dp.get_precision('product'), store=True)
#    check_total_price = fields.Boolean(string="Total Price")
    total_price_stretch = fields.Float(compute="_get_calculate_prices", string="Total Price", digits=dp.get_precision('product'), store=True)
    
    #test
    test = fields.Boolean(string="Test")
    
    #price Configuration
    show_formula = fields.Boolean(string="Show Formula")
    
#    default_total_printing_area = fields.Text(string="Total Printing areas cm2", default="(self.product_type.calculation_for_print_area)*(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(float(self.printing_area)/100)*(self.printing_type.plates)")
#    default_total_printing_area = fields.Text(string="Total Printing areas cm2", default=_default_total_printing_area_formula)
#    default_ink_weigth = fields.Text(string="Ink Weight With Full Print", default=_default_ink_weigth_formula)
#    default_weight_per_gram = fields.Text(string="Weight Per Gram", default=_default_weight_per_gram_formula)
#    default_weight_per_kg = fields.Text(string="Weight Per Bag/Roll Kg", default=_default_weight_per_kg_formula)
#    default_total_weight = fields.Text(string="Total weight (Kg)", default=_default_total_weight_formula)
#    default_price_per_pc = fields.Text(string="Price Per Kg", default=_default_total_weight_formula)
#    default_price_per_kg = fields.Text(string="Price Per Kg", default=_default_price_per_kg_formula)
#    default_printing_cost = fields.Text(string="Printing plate Cost", default=_default_printing_cost_formula)
#    default_total_pcs = fields.Text(string="Total pcs", default=_default_total_pcs_formula)
#    default_max_discount = fields.Text(string="Max Discount Eligibility", default=_default_max_discount_formula)
##    default_total_price = fields.Text(string="Total Price", default=_default_total_price_formula)
#    
#    last_total_printing_area = fields.Text(string="Total Printing areas cm2", default=_last_total_printing_area_formula) 
#    last_ink_weigth = fields.Text(string="Ink Weight With Full Print", default=_last_ink_weigth_formula)
#    last_weight_per_gram = fields.Text(string="Weight Per Gram", default=_last_weight_per_gram_formula)
#    last_weight_per_kg = fields.Text(string="Weight Per Bag/Roll Kg", default=_last_weight_per_kg_formula)
#    last_total_weight = fields.Text(string="Total weight (Kg)", default=_last_total_weight_formula)
#    last_price_per_kg = fields.Text(string="Price Per Kg", default=_last_price_per_kg_formula)
#    last_printing_cost = fields.Text(string="Printing plate Cost", default=_last_printing_cost_formula)
#    last_total_pcs = fields.Text(string="Total pcs", default=_last_total_pcs_formula)
#    last_max_discount = fields.Text(string="Max Discount Eligibility", default=_last_max_discount_formula)
##    last_total_price = fields.Text(string="Total Price", default=_last_total_price_formula)
#    
#    current_total_printing_area = fields.Text(string="Total Printing areas cm2", default=_last_total_printing_area_formula)
#    current_ink_weigth = fields.Text(string="Ink Weight With Full Print", default=_last_ink_weigth_formula)
#    current_weight_per_gram = fields.Text(string="Weight Per Gram", default=_last_weight_per_gram_formula)
#    current_weight_per_kg = fields.Text(string="Weight Per Bag/Roll Kg", default=_last_weight_per_kg_formula)
#    current_total_weight = fields.Text(string="Total weight (Kg)", default=_last_total_weight_formula)
#    current_price_per_kg = fields.Text(string="Price Per Kg", default=_last_price_per_kg_formula)
#    current_printing_cost = fields.Text(string="Printing plate Cost", default=_last_printing_cost_formula)
#    current_total_pcs = fields.Text(string="Total pcs", default=_last_total_pcs_formula)
#    current_max_discount = fields.Text(string="Max Discount Eligibility", default=_last_max_discount_formula)
#    current_total_price = fields.Text(string="Total Price", default=_last_total_price_formula)
    
    ##CH_N06 start >>
    product_bool = fields.Boolean(string="product boolean" ,default=False)  
    change_bool  = fields.Boolean("Keep Same" ,default=False)
    n_hide  = fields.Boolean("Make Changes? hide" ,default=False)
    n_state =fields.Selection([('draft','Draft'),
                                ('done','Done'),
                                ('make_change','Make Change'),
                                ('qty_change','Change')],default='draft')
    #sale_order_id= fields.One2many('sale.order.line','price_calculator_id')      
    ##CH_N06 end

    @api.onchange('stratch_calculator', 'printing_area', 'product_type', 'bag_type', 'material_type', 'delivery_location', 'packing_type', 'printing_type', 'unit', 'qty', 'micron', 'lenght', 'width', 'left','right','top','bottom')
    def onchange_calc(self):
        #Total Printing areas cm2
        _logger.info('onchange_calc........................................')
        micron_obj = self.env['microns.details']
        domain = {}
        if self.qty:
            if not str(self.qty).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Quantity"}}
            
        if self.micron:
            if not str(self.micron).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Micron"}}
            
        if self.printing_area:
            if not str(self.printing_area).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Printing Area"}}
            
        if self.lenght:
            if not str(self.lenght).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Lenght"}}
            
        if self.width:
            if not str(self.width).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Width"}}
            
        if self.left:
            if not str(self.left).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Left Gusset"}}
            
        if self.right:
            if not str(self.right).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Right Gusset"}}
            
        if self.top:
            if not str(self.top).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Top fold"}}
            
        if self.bottom:
            if not str(self.bottom).isdigit():
                return {'warning': {'title': "Invalid", 'message': "Enter Valid Bottom gusset"}}
            
        if self.product_type.name.name not in ('Bags','Bags Multi Layer'):
            pa_obj = self.env['bag.type']
            p_ids = pa_obj.search([('name.name','=', 'Select type')])
            if p_ids:
                self.bag_type = p_ids[0].id
        if self.product_type:
            query = "select mat_id from prod_type_mat_rel where type_id = " + str(self.product_type.id)
            self.env.cr.execute(query)
            mat_ids = [i[0] for i in self.env.cr.fetchall()]
            _logger.info('mat_ids %s', (mat_ids,))
            domain.update({'material_type' : [('id','in', mat_ids)]})
        self.total_printing_area = (self.product_type.calculation_for_print_area)*(self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(float(self.printing_area)/100)*(self.printing_type.plates)
        #Ink Weight
        if self.printing_type.name in ('Graphic full', 'Graphic partial'):
            self.ink_weigth = (self.total_printing_area)*(0.0003)*1.22
        else:
            self.ink_weigth = (self.total_printing_area) * (0.0009) * 1.22

        if self.printing_type.name == 'no printing':
            self.printing_area = 0
      
        if self.printing_area > 100:
            return {'warning': {'title': "Invalid", 'message': "It must be less then 100!!"}}
        if self.lenght and self.width and self.material_type and self.micron and self.product_type and self.bag_type:
            eweight = 0
            if self.bag_type and self.bag_type.name.name in ['Draw string']:
                eweight = (2.5 * self.material_type.density * 0.012 * 2 * self.width)
                self.bag_type.write({'extra_weight': eweight})
            elif self.bag_type and self.bag_type.name.name in ['Courrier permanent 2x strip','Courrier permanent', 'Courrier resealable']:
                eweight = (26 * self.material_type.density * 0.004 * self.width)
                self.bag_type.write({'extra_weight': eweight})
            elif self.bag_type and self.bag_type.name.name in ['Zip lock specimen bag with pouch']: #1oct17
                eweight = (16 * self.material_type.density * 0.004 * self.width)
                self.bag_type.write({'extra_weight': eweight})
            else:
                eweight = self.bag_type.extra_weight
            
            self.weight_per_gram = (self.lenght+self.top+self.bottom)*(self.width+self.left+self.right)*(self.micron/10000.0)*(self.material_type.density)*(self.product_type.calculation_for_print_area)+((eweight)+self.ink_weigth)
        if self.weight_per_gram:
            self.weight_per_kg = self.weight_per_gram/1000.0
        #MOQ Required in pc/length(cm)
        if self.weight_per_kg > 0:
            self.moq_length = 500.0/ float(self.weight_per_kg)
        #Total weight (Kg)
        if self.weight_per_kg and self.qty:
            if self.unit.name == 'Kg':
                self.total_weight =self.qty
            if self.unit.name == 'Pcs':
                self.total_weight =self.weight_per_kg * self.qty

        #Price Per Kg
        if self.total_weight <=3000:
            delivery_charges = self.delivery_location.km1
        elif (self.total_weight >=3001 and self.total_weight <=7000):
            delivery_charges = self.delivery_location.km2
        elif (self.total_weight >=7001 and self.total_weight <=15000):
            delivery_charges = self.delivery_location.km3
        else:
            delivery_charges = 0
#            return {'warning': {'title': "Invalid", 'message': "NE"}}

        
        ink_price_per_kg = 0.01 # price per kg is default set please change it form ink.type
        ink_price = 0
        if self.weight_per_kg:
            ink_price = (self.ink_weigth * ink_price_per_kg)/self.weight_per_kg
        
        margin_profit=1.3
#        =(VLOOKUP(producttype,filmconversion,2,0)+dlvrychargesperkilo+IF(totalweightkg>=500,VLOOKUP(materialtype,materiallist,2,0),IF(AND(totalweightkg<500,totalweightkg>=200),VLOOKUP(materialtype,materiallist,2,0)+5,"Cannot Make"))+VLOOKUP(printtype,printingprices2,2,0)+VLOOKUP(packing,packingvar,2,0)+inkcostperkg)*mrg
        mat_price = 0
        if self.total_weight >= 500:
            mat_price = self.material_type.kg_price
        if self.total_weight < 500 and self.total_weight >= 200:
            mat_price = self.material_type.kg_price + 5
        if self.total_weight and self.total_weight < 200:
            raise UserError("We Cannot Place Order For Less Then 200KG")
            
        price_for_kg =  (self.product_type.price_per_kg + delivery_charges + mat_price + self.printing_type.cost + self.packing_type.cost + ink_price) * margin_profit
        # Price Per Pc / roll
        if self.micron > 250:
            return {'warning': {'title': "Invalid", 'message': "max micron 250 allowed.......!!"}}
        if self.bag_type.name.name == 'Select type' and price_for_kg:
            self.price_per_pc = self.weight_per_kg * price_for_kg
        else:
            microns_type_obj = self.env['microns.details']
            microns_obj = microns_type_obj.search([('name', '=', self.bag_type.name.name)])
            mm = val = 0
            if self.micron:
                p3 = self.env['inclusions.details'].search([('itype','=','per_glue')])
                p4 = self.env['inclusions.details'].search([('itype','=','per_cour_res_lin')])
                p5 = self.env['inclusions.details'].search([('itype','=','resealable_tape')])
                p6 = self.env['inclusions.details'].search([('itype','=','smpl_zipper')])
                p7 = self.env['inclusions.details'].search([('itype','=','security_tape')])

                if self.micron >= 40 and self.micron <= 250:
                    if self.bag_type.name.name in ['Courrier permanent', 'self adhesive permanent']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width
                        microns_obj[0].write({'microns1' : mm})
                    elif self.bag_type.name.name in ['Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width * 2
                        microns_obj[0].write({'microns1' : mm})
                    elif self.bag_type.name.name in ['Courrier resealable', 'Self adhesive resealable']:
                        mm = 0.015 + (p5.inclusions/100) * self.width
                        microns_obj[0].write({'microns1': mm})
                    elif self.bag_type.name.name in ['Zip lock specimen bag with pouch', 'Zip lock bag']:
                            mm = 0.018 + (p6.inclusions/100) * self.width
                            microns_obj[0].write({'microns1': mm})
                    elif self.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * self.width
                            microns_obj[0].write({'microns1': mm})
                    else:
                        mm = microns_obj.microns1
                        
                elif self.micron >= 25 and self.micron <= 39.5:
                    if self.bag_type.name.name in ['Courrier permanent', 'self adhesive permanent']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width
                        microns_obj[0].write({'microns2' : mm})
                    elif self.bag_type.name.name in ['Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width * 2
                        microns_obj[0].write({'microns2' : mm})
                    elif self.bag_type.name.name in ['Courrier resealable', 'Self adhesive resealable']:
                        mm = 0.015 + (p5.inclusions/100) * self.width
                        microns_obj[0].write({'microns2' : mm})
                    elif self.bag_type.name.name in ['Zip lock specimen bag with pouch', 'Zip lock bag']:
                            mm = 0.018 + (p6.inclusions/100) * self.width
                            microns_obj[0].write({'microns2': mm})
                    elif self.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * self.width
                            microns_obj[0].write({'microns1': mm})
                    else:
                        mm = microns_obj.microns2
                        
                elif self.micron >= 0 and self.micron <= 24.9:
                    if self.bag_type.name.name in ['Courrier permanent', 'self adhesive permanent']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width
                        microns_obj[0].write({'microns3' : mm})
                    elif self.bag_type.name.name in ['Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip']:
                        mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * self.width * 2
                        microns_obj[0].write({'microns3' : mm})
                    elif self.bag_type.name.name in ['Courrier resealable', 'Self adhesive resealable']:
                        mm = 0.015 + (p5.inclusions/100) * self.width
                        microns_obj[0].write({'microns3' : mm})
                    elif self.bag_type.name.name in ['Zip lock specimen bag with pouch', 'Zip lock bag']:
                            mm = 0.018 + (p6.inclusions/100) * self.width
                            microns_obj[0].write({'microns3': mm})
                    elif self.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * self.width
                            microns_obj[0].write({'microns1': mm})
                    else:
                        mm = microns_obj.microns3
                        
                else:
                    return {'warning': {'title': "Invalid", 'message': "max micron 250 allowed.......!!"}}

            if self.lenght:
                if self.lenght >= 30.1 and self.lenght <= 75:
                    value = "medium"
                    val = 1
                elif self.lenght >= 15 and self.lenght <= 30:
                    value = "vsmall"
                    val = 0.6
                elif self.lenght >= 75.1 and self.lenght <= 119.99:
                    value = "large"
                    val = 1.2
                elif self.lenght >= 120 and self.lenght <= 200:
                    value = "X"
                    val = 1.5
                else:
                    return {'warning': {'title': "Invalid", 'message': "Please select accurate size"}}

                if mm and val:
                    size = mm * val
                    self.price_per_pc = self.weight_per_kg * price_for_kg + size
        
        if self.weight_per_kg > 0:
            self.price_per_kg = self.price_per_pc/self.weight_per_kg
        
        #printing plate cost
        self.printing_cost= self.total_printing_area * 0.45  #  set ink_type.printing_plates is change form ink,type table

        # Total PCS
        if self.unit.name == 'Kg':
            if self.weight_per_kg:
                self.total_pcs = self.total_weight / self.weight_per_kg
        if self.unit.name == 'Pcs':
            self.total_pcs = self.qty
        #max Disount Eligiblity
            #it is set default value cahnge it from discount.type table
        if self.bag_type and self.total_weight:
            if self.bag_type.name.name == "Garbage bag" and self.total_weight >= 500.1 and self.total_weight <= 1000:
                self.max_discount = 5
                self.max_discount_allow = 5
            elif self.bag_type.name.name == "Garbage bag" and self.total_weight >= 4999:
                self.max_discount = 10
                self.max_discount_allow = 10
            elif self.total_weight >= 500.1 and self.total_weight <= 1000:
                self.max_discount = 5
                self.max_discount_allow = 10
            elif self.total_weight >= 1001 and self.total_weight <= 4999:
                self.max_discount = 10
                self.max_discount_allow = 10
            elif self.total_weight >= 5000:
                self.max_discount = 20
                self.max_discount_allow = 20
            else:
                self.max_discount = 0
                self.max_discount_allow = 0
        
#                return {'warning': {'title': "Invalid", 'message': "NE"}}

        #Total Price
        if self.unit:
            if self.product_type.name.name == "Stretch Film":
                print "Use table on right side"
                if self.stratch_calculator:
                    if self.unit.name == 'Pcs':
                        per_cart_price = self.qty /float(self.stratch_calculator.pcs_ctn)
                    else:
                        per_cart_price = self.qty /float(self.stratch_calculator.kg_ctn)
                    self.total_price = per_cart_price * self.stratch_calculator.price_ctn
                    self.total_price_stretch = self.total_price
            elif self.unit.name == 'Pcs':
                self.total_price = self.price_per_pc * self.qty
                self.total_price_stretch = self.total_price
            else:
                self.total_price = self.price_per_kg * self.qty
                self.total_price_stretch = self.total_price
        return {'domain' : domain}
        
    @api.multi
    @api.depends('check_product_type','check_material_type','check_stratch_calculator','check_bag_type','check_delivery_location','check_packing_type','check_moq_length','check_ink_weigth','check_total_printing_area','check_micron','check_printing_type','check_printing_area','check_lenght','check_width','check_left','check_right','check_top','check_bottom','check_weight_per_gram','check_weight_per_kg','check_total_weight','check_printing_cost','check_total_pcs')
    def _get_description(self):
        desc = ''
        for line in self:
            if line.check_product_type:
                desc += "Product Type : " + str(line.product_type.name.name) + "\n"
            if line.check_bag_type:
                desc += "Bag Type : " + str(line.bag_type.name.name) + "\n"
            if line.check_material_type:
                desc += "Material : " + str(line.material_type.name.name) + "\n"
            if line.check_delivery_location:
                desc += "Delivery Location : " + str(line.delivery_location.name) + "\n"
            if line.check_packing_type:
                desc += "Packing : " + str(line.packing_type.name) + "\n"
            if line.check_moq_length:
                desc += "MOQ Required in pcs : " + str(line.moq_length) + "\n"
            if line.check_ink_weigth:
                desc += "Ink Weight : " + str(line.ink_weigth) + "\n"
            if line.check_total_printing_area:
                desc += "Total Printing areas cm2  : " + str(line.total_printing_area) + "\n"
            if line.check_micron:
                desc += "Thickness : " + str(line.micron) + " (micron)\n"
            if line.check_printing_type:
                desc += "Printing : " + str(line.printing_type.name) + "\n"
            if line.check_printing_area:
                desc += "Printing Area : " + str(line.printing_area) + "\n"
            if line.check_lenght:
                desc += "Length : " + str(line.lenght) + " cm\n"
            if line.check_width:
                desc += "Width : " + str(line.width) + " cm\n"
            if line.check_left:
                desc += "Left gusset : " + str(line.left) + " cm\n"
            if line.check_right:
                desc += "Right gusset : " + str(line.right) + " cm\n"
            if line.check_top:
                desc += "Top fold : " + str(line.top) + " cm\n"
            if line.check_bottom:
                desc += "Bottom gusset : " + str(line.bottom) + " cm\n"
            if line.check_weight_per_gram:
                desc += "Weight Per Item : " + str(line.weight_per_gram) + " gm\n"
            if line.check_weight_per_kg:
                desc += "Weight Per Item : " + str(line.weight_per_kg) + " kg\n"
            if line.check_total_weight:
                desc += "Total weight : " + str(line.total_weight) + " kg\n"
#            if line.check_price_per_kg:
#                desc += "Price Per Kg : " + str(line.price_per_kg) + "\n"
#            if line.check_price_per_pc:
#                desc += "Price Per Pc/roll : " + str(line.price_per_pc) + "\n"
#            if line.check_printing_cost:
#                desc += "Printing plate Cost : " + str(line.printing_cost) + "\n"
            if line.check_total_pcs:
                desc += "Total : " + str(line.total_pcs) + " pcs\n"
#            if line.check_max_discount:
#                desc += "Max Discount Eligibility : " + str(line.max_discount) + "\n"
#            if line.check_total_price:
#                desc += "Total Price : " + str(line.total_price) + "\n"
            line.description = desc
            line.name1 = desc

    @api.multi
    @api.depends('stratch_calculator', 'printing_area', 'product_type', 'bag_type', 'material_type', 'delivery_location', 'packing_type', 'printing_type', 'unit', 'qty', 'micron', 'lenght', 'width', 'left','right','top','bottom')
    def _get_calculate_prices(self):
        _logger.info('_get_calculate_prices........................')
        for price_cal in self:
            if price_cal.product_type.name.name not in ('Bags','Bags Multi Layer'):
                pa_obj = self.env['bag.type']
                p_ids = pa_obj.search([('name.name','=', 'Select type')])
                if p_ids:
                    price_cal.bag_type = p_ids[0].id
            if price_cal.product_type:
                query = "select mat_id from prod_type_mat_rel where type_id = " + str(price_cal.product_type.id)
                self.env.cr.execute(query)
                mat_ids = [i[0] for i in self.env.cr.fetchall()]
                _logger.info('mat_ids %s', (mat_ids,))
            price_cal.total_printing_area = (price_cal.product_type.calculation_for_print_area)*(price_cal.lenght+price_cal.top+price_cal.bottom)*(price_cal.width+price_cal.left+price_cal.right)*(float(price_cal.printing_area)/100)*(price_cal.printing_type.plates)
            #Ink Weight
            if price_cal.printing_type.name in ('Graphic full', 'Graphic partial'):
                price_cal.ink_weigth = (price_cal.total_printing_area)*(0.0003)*1.22
            else:
                price_cal.ink_weigth = (price_cal.total_printing_area) * (0.0009) * 1.22
            
            if price_cal.printing_type.name == 'no printing':
                price_cal.printing_area = 0
	    _logger.info('initial testing......')
            if price_cal.printing_area > 100:
                return {'warning': {'title': "Invalid", 'message': "It must be less then 100!!"}}
            if price_cal.lenght and price_cal.width and price_cal.material_type and price_cal.micron and price_cal.product_type and price_cal.bag_type:
                eweight = 0
                if price_cal.bag_type and price_cal.bag_type.name.name in ['Draw string']:
                    eweight = (2.5 * price_cal.material_type.density * 0.012 * 2 * price_cal.width)
                    price_cal.bag_type.write({'extra_weight': eweight})
                elif price_cal.bag_type and price_cal.bag_type.name.name in ['Courrier permanent 2x strip','Courrier permanent', 'Courrier resealable']:
                    eweight = (26 * price_cal.material_type.density * 0.004 * price_cal.width)
                    price_cal.bag_type.write({'extra_weight': eweight})
                elif price_cal.bag_type and price_cal.bag_type.name.name in ['Zip lock specimen bag with pouch']:
                    eweight = (16 * price_cal.material_type.density * 0.004 * price_cal.width)
                    price_cal.bag_type.write({'extra_weight': eweight})
                else:
                    eweight = price_cal.bag_type.extra_weight
                price_cal.weight_per_gram = (price_cal.lenght+price_cal.top+price_cal.bottom)*(price_cal.width+price_cal.left+price_cal.right)*(price_cal.micron/10000.0)*(price_cal.material_type.density)*(price_cal.product_type.calculation_for_print_area)+((eweight)+price_cal.ink_weigth)
            
            #Weight Per Bag/Roll Kg
            if price_cal.weight_per_gram:
                price_cal.weight_per_kg = price_cal.weight_per_gram/1000.0
            #MOQ Required in pc/length(cm)
            if price_cal.weight_per_kg > 0:
                price_cal.moq_length = 500.0/ float(price_cal.weight_per_kg)
            #Total weight (Kg)
            if price_cal.weight_per_kg and price_cal.qty:
                if price_cal.unit.name == 'Kg':
                    price_cal.total_weight =price_cal.qty
                if price_cal.unit.name == 'Pcs':
                    price_cal.total_weight =price_cal.weight_per_kg * price_cal.qty

            #Price Per Kg
            if price_cal.total_weight <=3000:
                delivery_charges = price_cal.delivery_location.km1
            elif (price_cal.total_weight >=3001 and price_cal.total_weight <=7000):
                delivery_charges = price_cal.delivery_location.km2
            elif (price_cal.total_weight >=7001 and price_cal.total_weight <=15000):
                delivery_charges = price_cal.delivery_location.km3
            else:
                delivery_charges = 0
    #            return {'warning': {'title': "Invalid", 'message': "NE"}}

            ink_price_per_kg = 0.01 # price per kg is default set please change it form ink.type
            #weigth per kg
            ink_price = 0
            if price_cal.weight_per_kg:
                ink_price = (price_cal.ink_weigth * ink_price_per_kg)/price_cal.weight_per_kg

            margin_profit=1.3
    #        =(VLOOKUP(producttype,filmconversion,2,0)+dlvrychargesperkilo+IF(totalweightkg>=500,VLOOKUP(materialtype,materiallist,2,0),IF(AND(totalweightkg<500,totalweightkg>=200),VLOOKUP(materialtype,materiallist,2,0)+5,"Cannot Make"))+VLOOKUP(printtype,printingprices2,2,0)+VLOOKUP(packing,packingvar,2,0)+inkcostperkg)*mrg
            mat_price = 0
            if price_cal.total_weight >= 500:
                mat_price = price_cal.material_type.kg_price
            if price_cal.total_weight < 500 and price_cal.total_weight >= 200:
                mat_price = price_cal.material_type.kg_price + 5
            if price_cal.total_weight and price_cal.total_weight < 200:
                raise UserError("We Cannot Place Order For Less Then 200KG")

            price_for_kg =  (price_cal.product_type.price_per_kg + delivery_charges + mat_price + price_cal.printing_type.cost + price_cal.packing_type.cost + ink_price) * margin_profit

            # Price Per Pc / roll
            if price_cal.micron > 250:
                return {'warning': {'title': "Invalid", 'message': "max micron 250 allowed.......!!"}}
            if price_cal.bag_type.name.name == 'Select type' and price_for_kg:
                price_cal.price_per_pc = price_cal.weight_per_kg * price_for_kg
            else:
                microns_type_obj = self.env['microns.details']
                microns_obj = microns_type_obj.search([('name', '=', price_cal.bag_type.name.name)])
                mm = val = 0
                if price_cal.micron:
                    
                    p3 = self.env['inclusions.details'].search([('itype','=','per_glue')])
                    p4 = self.env['inclusions.details'].search([('itype','=','per_cour_res_lin')])
                    p5 = self.env['inclusions.details'].search([('itype','=','resealable_tape')])
                    p6 = self.env['inclusions.details'].search([('itype','=','smpl_zipper')])
                    p7 = self.env['inclusions.details'].search([('itype','=','security_tape')])
                    
                    if price_cal.micron >= 40 and price_cal.micron <= 250:
                        if price_cal.bag_type.name.name in ('Courrier permanent', 'self adhesive permanent'):
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width
                            microns_obj[0].write({'microns1' : mm})
                        elif price_cal.bag_type.name.name in ('Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip'):
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width * 2
                            microns_obj[0].write({'microns1' : mm})
                        elif price_cal.bag_type.name.name in ('Courrier resealable', 'Self adhesive resealable'):
                            mm = 0.015 + (p5.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns1': mm})
                        elif price_cal.bag_type.name.name in ('Zip lock specimen bag with pouch', 'Zip lock bag'):
                            mm = 0.018 + (p6.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns1': mm})
                        elif price_cal.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns1': mm})
                        else:
                            mm = microns_obj.microns1

                    elif price_cal.micron >= 25 and price_cal.micron <= 39.5:
                        if price_cal.bag_type.name.name in ['Courrier permanent', 'self adhesive permanent']:
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width
                            microns_obj[0].write({'microns2' : mm})
                        elif price_cal.bag_type.name.name in ['Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip']:
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width * 2
                            microns_obj[0].write({'microns2' : mm})
                        elif price_cal.bag_type.name.name in ['Courrier resealable', 'Self adhesive resealable']:
                            mm = 0.015 + (p5.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns2' : mm})
                        elif price_cal.bag_type.name.name in ['Zip lock specimen bag with pouch', 'Zip lock bag']:
                            mm = 0.018 + (p6.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns2': mm})
                        elif price_cal.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns1': mm})
                        else:
                            mm = microns_obj.microns2

                    elif price_cal.micron >= 0 and price_cal.micron <= 24.9:
                        if price_cal.bag_type.name.name in ['Courrier permanent', 'self adhesive permanent']:
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width
                            microns_obj[0].write({'microns3': mm})
                        elif price_cal.bag_type.name.name in ['Courrier permanent 2x strip', 'Self adhesive permanent 2 X strip']:
                            mm = 0.015 + (p3.inclusions+p4.inclusions)/100 * price_cal.width * 2
                            microns_obj[0].write({'microns3' : mm})
                        elif price_cal.bag_type.name.name in ['Courrier resealable', 'Self adhesive resealable']:
                            mm = 0.015 + (p5.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns3': mm})
                        elif price_cal.bag_type.name.name in ['Zip lock specimen bag with pouch', 'Zip lock bag']:
                            mm = 0.018 + (p6.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns3': mm})
                        elif price_cal.bag_type.name.name == 'Security Bag':
                            mm = 0.015 + (p7.inclusions/100) * price_cal.width
                            microns_obj[0].write({'microns1': mm})
                        else:
                            mm = microns_obj.microns3

                    else:
                        return {'warning': {'title': "Invalid", 'message': "max micron 250 allowed.......!!"}}

                if price_cal.lenght:
                    if price_cal.lenght >= 30.1 and price_cal.lenght <= 75:
                        value = "medium"
                        val = 1
                    elif price_cal.lenght >= 15 and price_cal.lenght <= 30:
                        value = "vsmall"
                        val = 0.6
                    elif price_cal.lenght >= 75.1 and price_cal.lenght <= 119.99:
                        value = "large"
                        val = 1.2
                    elif price_cal.lenght >= 120 and price_cal.lenght <= 200:
                        value = "X"
                        val = 1.5
                    else:
                        return {'warning': {'title': "Invalid", 'message': "Please select accurate size"}}

                    if mm and val:
                        size = mm * val
                        price_cal.price_per_pc = price_cal.weight_per_kg * price_for_kg + size

            if price_cal.weight_per_kg > 0:
                price_cal.price_per_kg = price_cal.price_per_pc/price_cal.weight_per_kg

            #printing plate cost
            price_cal.printing_cost= price_cal.total_printing_area * 0.45  #  set ink_type.printing_plates is change form ink,type table

            # Total PCS
            if price_cal.unit.name == 'Kg':
                if price_cal.weight_per_kg:
                    price_cal.total_pcs = price_cal.total_weight / price_cal.weight_per_kg
            if price_cal.unit.name == 'Pcs':
                price_cal.total_pcs = price_cal.qty
            #max Disount Eligiblity
                #it is set default value cahnge it from discount.type table
            if price_cal.bag_type and price_cal.total_weight:
                if price_cal.bag_type.name.name == "Garbage bag" and price_cal.total_weight >= 500.1 and price_cal.total_weight <= 1000:
                    price_cal.max_discount = 5
                elif price_cal.bag_type.name.name == "Garbage bag" and price_cal.total_weight >= 4999:
                    price_cal.max_discount = 10
                elif price_cal.total_weight >= 500.1 and price_cal.total_weight <= 1000:
                    price_cal.max_discount = 5
                elif price_cal.total_weight >= 1001 and price_cal.total_weight <= 4999:
                    price_cal.max_discount = 10
                elif price_cal.total_weight >= 5000:
                    price_cal.max_discount = 20
                else:
                    price_cal.max_discount = 0

    #                return {'warning': {'title': "Invalid", 'message': "NE"}}

            #Total Price
            if price_cal.unit:
                if price_cal.product_type.name.name == "Stretch Film":
                    print "Use table on right side"
                    if price_cal.stratch_calculator:
                        if price_cal.unit.name == 'Pcs':
                            per_cart_price = price_cal.qty /float(price_cal.stratch_calculator.pcs_ctn)
                        else:
                            per_cart_price = price_cal.qty /float(price_cal.stratch_calculator.kg_ctn)
                        price_cal.total_price = per_cart_price * price_cal.stratch_calculator.price_ctn
                        price_cal.total_price_stretch = price_cal.total_price
                elif price_cal.unit.name == 'Pcs':
                    price_cal.total_price = price_cal.price_per_pc * price_cal.qty
                    price_cal.total_price_stretch = price_cal.total_price
                else:
                    price_cal.total_price = price_cal.price_per_kg * price_cal.qty
                    price_cal.total_price_stretch = price_cal.total_price
           
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.model
    def create(self, vals):
        body_html1=''
        if vals.get('pricelist_type') == '2' and not self._context.get('copy_quote'):
            if vals.get('calc_unit'):
                vals.update({'product_uom' : vals.get('calc_unit')})
            if vals.get('calc_qty'):
                vals.update({'product_uom_qty': vals.get('calc_qty')})
        if vals.get('pricelist_type') == '2' and vals.get('price_m') == True and vals.get('dis_m') == False:
            raise UserError("Please add Correct Final Price")
        obj = super(SaleOrderLine, self).create(vals)
        if obj.order_id.is_reception:
            return obj
        if obj.price_calculator_id.check_printing_cost and obj.printing_price and not obj.sale_line_id:
            prd_obj = self.env['product.product']
            cat_obj = self.env['product.category']
            prd_ids = prd_obj.search([('name', '=', 'Printing Plate')])
            line_field = self.fields_get()
            vals_print = self.default_get(line_field)
            pobj = False
            if prd_ids:
                pobj = prd_ids[0]
            else:
                cat_ids = cat_obj.search([('cat_type','in', ['film'])])
                if cat_ids:
                    vals_p = {
                        'name' : 'Printing Plate',
                        'categ_id' : cat_ids[-1].id,
                        'child_prod_name' : 'Printing Plate',
                        'external_product_number' : 'PRINTPL',
                        'default_code' : 'PRINTPL',
                        'uom_id': obj.product_uom.id,
                        'uom_po_id': obj.product_uom.id,
                    }
                    pobj = prd_obj.create(vals_p)
            price_unit = obj.p_currency_id.compute(obj.printing_price, obj.s_currency_id)
            vals_print.update({'product_id': pobj.id, 'name': pobj.name, 'name1': pobj.name, 'product_uom': pobj.uom_id.id, 'prd_name': 'Printing Cost','pricelist_type': '3', 'p_currency_id': obj.p_currency_id.id, 's_currency_id': obj.s_currency_id.id,'order_id': obj.order_id.id, 'print_product': True, 'price_unit': price_unit,
                               'sale_line_id': obj.id, 'p_currency_id' : obj.order_id.pricelist_id.currency_id.id,
                        's_currency_id' : obj.order_id.currency_id.id})
            obj.write({'sale_line_id': super(SaleOrderLine, self).create(vals_print).id})
        if vals.get('approve_m') != True and obj.product_id.name != 'Deposit Product':
            temp_id = self.env.ref('gt_sale_pricelist.email_template_approve_req')
            if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    # the parameters to encode for the query and fragment part of url
                query = {'db': self._cr.dbname}
                fragment = {
                    'model': 'sale.order',
                    'view_type': 'form',
                    'id': obj.order_id.id,
                }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                text_link = _("""<a href="%s">%s</a> """) % (url,obj.order_id.name)
                name = ''
                if obj.product_id:
                    if obj.product_id.default_code:
                        name = '[' + obj.product_id.default_code + ']'
                    name += ' ' + obj.product_id.name
                if not name:
                   name = obj.name or obj.name1
                body_html1 += """<div>
                         <p> <strong>Discount Requested </strong></p>
                               <p>Dear %sDiscount Requested,<br/>
                                   <b>%s </b>requested for Discount on  <b> %s </b> for  <br/>
                                  <b>Customer Name </b>:%s
                                  <br/>
                               </p>
                       </div>"""%(obj.order_id.team_id.user_id.name or '',obj.order_id.user_id.name or '', text_link, obj.order_id.partner_id.name )
                body_html1 +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial; text-align:center;'><tr><th>Product Name </th><th> Suggested Price</th><th>Lowest Price</th><th>Requested Price </th></tr>"                  
                for line in obj.order_id.order_line:
                    if line.approve_m != True and line.product_id.name != 'Deposit Product':
                             body_html1 +="<tr><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s(%s %s)</td></tr>"%(line.product_id.name, line.fixed_price ,line.p_currency_id.symbol,line.lowest_price if line.lowest_price else 'NA' ,line.p_currency_id.symbol if line.lowest_price else '', str(line.s_discount) + '%' if line.s_discount else 'NA'  ,line.s_price if line.s_price else line.final_price , line.p_currency_id.symbol) 
                body_html1 +="</table>"
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html1, 'sale.order',obj.order_id.id, context=self._context)
                temp_id.write({'body_html': body_html})
                temp_id.send_mail(obj.order_id.id)
        return obj
    
    @api.multi
    def write(self, vals):
        body_html1=''
        if vals.get('pricelist_type') == '2' or vals.get('calc_unit') or vals.get('calc_qty'):
            if vals.get('calc_unit'):
                vals.update({'product_uom': vals.get('calc_unit')})
            if vals.get('calc_qty'):
                vals.update({'product_uom_qty': vals.get('calc_qty')})
        if vals.get('dis_m'):
            data = vals.get('dis_m')
        else:
            data = self.dis_m
        if vals.get('pricelist_type'):
            type = vals.get('pricelist_type')
        else:
            type = self.pricelist_type
        if type == '2' and vals.get('price_m') == True and data == False:
            raise UserError("Please add Correct Final Price")
        super(SaleOrderLine, self).write(vals)
        if self.order_id.is_reception:
            return True
        for obj in self:
            if obj.pricelist_type == '2' and not obj.price_calculator_id.check_printing_cost and not obj.printing_price and obj.sale_line_id and obj.sale_line_id.price_unit != 0.0:
                super(SaleOrderLine, obj.sale_line_id).write({'price_unit': 0.0, 'no_print': True})
#                self.env.cr.execute("delete from sale_order_line where id = " + str(obj.sale_line_id.id))'
            elif obj.pricelist_type == '2' and obj.price_calculator_id.check_printing_cost and obj.printing_price and not obj.sale_line_id:
                prd_obj = self.env['product.product']
                cat_obj = self.env['product.category']
                prd_ids = prd_obj.search([('default_code','=','PRINTPL')],limit=1)
                line_field = self.fields_get()
                vals_print = self.default_get(line_field)
                pobj = packg=False
                if prd_ids:
                    pobj = prd_ids
                    packg = prd_ids.packaging_ids[0].id
                else:
                    cat_ids = cat_obj.search([('name','in', ['film','All'])])
                    if cat_ids:
                        vals_p = {
                            'name' : 'Printing Plate',
                            'categ_id' : cat_ids[-1].id,
                            'child_prod_name' : 'Printing Plate',
                            'external_product_number' : 'PRINTPL',
                            'default_code' : 'PRINTPL',
                            'uom_id': obj.product_uom.id,
                            'uom_po_id': obj.product_uom.id,
                        }
                        pobj = prd_obj.create(vals_p)
                price_unit = obj.p_currency_id.compute(obj.printing_price, obj.s_currency_id)
                vals_print.update({'product_id': pobj.id, 'product_uom': pobj.uom_id.id, 'prd_name': 'Printing Cost',
                                    'pricelist_type': '3', 'p_currency_id': obj.p_currency_id.id,
                                    's_currency_id': obj.s_currency_id.id, 'order_id': obj.order_id.id,
                                    'print_product': True, 'price_unit': price_unit,'sale_line_id': obj.id,
                                    'product_packaging':packg,'name':'Printing Plate'})
                vals_write = {'sale_line_id': super(SaleOrderLine, self).create(vals_print).id}
                super(SaleOrderLine, obj).write(vals_write)
            elif obj.pricelist_type == '2' and obj.price_calculator_id and obj.price_calculator_id.check_printing_cost and obj.sale_line_id and obj.sale_line_id.price_unit == 0.0:
                price_unit = obj.p_currency_id.compute(obj.printing_price, obj.s_currency_id)
                super(SaleOrderLine,obj.sale_line_id).write({'price_unit': price_unit, 'sale_id': obj.sale_line_id.id, 'no_print': False})
#                elif sale_line_id and not obj.price_calculator_id.check_printing_cost:
##                    obj.sale_line_id.unlink()
            if 'approve_m' in vals.keys() and vals['approve_m'] == False and obj.product_id.name != 'Deposit Product':   
                temp_id = self.env.ref('gt_sale_pricelist.email_template_approve_req')
                if temp_id:
                    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    # the parameters to encode for the query and fragment part of url
                    query = {'db': self._cr.dbname}
                    fragment = {
                        'model': 'sale.order',
                        'view_type': 'form',
                        'id': obj.order_id.id,
                    }
                    url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                    text_link = _("""<a href="%s">%s</a> """) % (url,obj.order_id.name)
                    name = ''
                    if obj.product_id:
                        if obj.product_id.default_code:
                            name += '[' + obj.product_id.default_code + ']'
                        name += ' ' + obj.product_id.name
                    if not name:
                        name = obj.name or obj.name1
                    body_html1 += """<div>
    <p> <strong>Discount Requested </strong></p>
    <p>Dear %s,<br/>
        <b>%s </b>requested for Discount on  <b> %s </b> for  <br/>
           <b>Customer Name </b>:%s
    <br/>
    </p>
    </div>"""%(obj.order_id.team_id.user_id.name or '',obj.order_id.user_id.name or '', text_link, obj.order_id.partner_id.name )
                    body_html1 +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial;text-align:center'><tr><th>Product Name </th><th> Suggested Price</th><th>Lowest Price</th><th>Requested Price </th></tr>"                   
                    for line in obj.order_id.order_line:
                        if line.approve_m != True and line.product_id.name != 'Deposit Product':
                            body_html1 +="<tr><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s(%s %s)</td></tr>"%(line.product_id.name, line.fixed_price ,line.p_currency_id.symbol,line.lowest_price if line.lowest_price else 'NA' ,line.p_currency_id.symbol if line.lowest_price else '', str(line.s_discount) + '%' if line.s_discount else 'NA'  ,line.s_price if line.s_price else line.final_price , line.p_currency_id.symbol) 
                    body_html1 +="</table>"
                    body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html1, 'sale.order',obj.order_id.id, context=self._context)
                    temp_id.write({'body_html': body_html})
                    temp_id.send_mail(obj.order_id.id)
        return True
    
    @api.multi
    def unlink(self):
        for sale_line in self:
            if sale_line.print_product and sale_line.sale_line_id and sale_line.sale_line_id.price_calculator_id:
                sale_line.sale_line_id.price_calculator_id.write({'check_printing_cost': False})
            if sale_line.pricelist_type == '2':
                sale_line.sale_line_id.unlink()
        return super(SaleOrderLine, self).unlink()

    @api.multi
    @api.onchange('customer')
    def pricebook_onchange(self):
        for rec in self:
            if rec.customer:
                rec.product_id=False
                rec.pricelist_id=False
                
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        print "Product iD onchange is called..",self.product_id
        domain = {}
        if self.product_id:
            cus_product = self.env['customer.product']
            product_cus = cus_product.search([('product_id', '=', self.product_id.id),
                                                ('pricelist_id','=',self.pricelist_id.id)])
            if product_cus:
                product_cus = product_cus[0]
                if product_cus.to_date and (product_cus.to_date + ' 23:59:59') < self.order_id.date_order:
                    raise ValidationError("Expired Product [%s][%s] %s can't be sold "% (product_cus.ext_product_number, product_cus.int_product_number,self.product_id.name,))
                    
        domain.update({'product_uom': [('unit_type.string', '=', 'product')]})
        if not self.price_calculator_id:
            if self.customer and self.product_id and self.pricelist_type != '3':
                domain.update({'price_line_id': [('customer', 'child_of', self.customer.id), ('product_id', '=', self.product_id.id)]})
            if self.customer and self.pricelist_type != '3' and self.product_id:
                if self.pricelist_type == '4':
                    cust_product_uom_ids = self.env['customer.product'].search([('pricelist_id','=', self.pricelist_id.id), ('product_id','=', self.product_id.id)])
                else:
                    cust_product_uom_ids = self.env['customer.product'].search([('pricelist_id.customer','=', self.customer.id), ('product_id','=', self.product_id.id)])
                if cust_product_uom_ids:
                    domain.update({'product_uom': [('id', 'in', [cust_product_uom_ids[0].uom_id.id])]})
                    self.product_uom = cust_product_uom_ids[0].uom_id.id
                    self.min_qty = cust_product_uom_ids[0].min_qty
                    self.floor_price = cust_product_uom_ids[0].floor_price
            if self.product_id:
                vals = {}
                if not self.product_uom or (self.product_id.uom_id.category_id.id != self.product_uom.category_id.id):
                    vals['product_uom'] = self.product_id.uom_id
                if self.product_uom_qty:
                    vals['product_uom_qty'] = self.product_uom_qty
                elif not self.product_uom_qty:
                    vals['product_uom_qty'] = 1

                product = self.product_id.with_context(lang=self.order_id.partner_id.lang,
                                                        partner=self.order_id.partner_id.id,
                                                        quantity=vals['product_uom_qty'],
                                                        date=self.order_id.date_order,
                                                        pricelist=self.order_id.pricelist_id.id,
                                                        uom=self.product_uom.id)

                if self.pricelist_type in ('1', '4') and self.product_id:
                    name = product.name_get()[0][1]
                    if product.description_sale:
                        name += '\n' + product.description_sale
                    vals['name1'] = name
                
                self._compute_tax_id()

                if self.order_id.pricelist_id and self.order_id.partner_id:
                    vals['tax_id']=self.env['account.tax'].search([('type_tax_use', '=', 'sale')], limit=1).ids
                    vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
                self.update(vals)

        if self.order_id.is_reception:
                   self.update({'name': self.product_id.description_sale})

        if domain:
            return {'domain': domain}
    
    @api.multi
    @api.onchange('price_line_id', 's_currency_id', 'p_currency_id')
    def onchange_priceline(self):
        for line in self:
            if line.price_line_id:
                line.update({'req_discount_type': 'price'})
                if line.s_currency_id and line.p_currency_id:
                    line.fixed_price = line.s_currency_id.compute(line.price_line_id.fixed_price, line.p_currency_id,round=False)
                    line.final_price = line.fixed_price
                if line.p_currency_id == line.s_currency_id:
                    line.currency_check = False
                if line.p_currency_id != line.s_currency_id:
                    line.currency_check = True

    @api.multi
    @api.onchange('pricelist_type')
    def pricelist_type_change(self):
  #CH_N067 add code to quatation customer
        self.customer=False
        if self.pricelist_type == "1" and self.order_id and self.order_id.partner_id:
            self.customer = self.order_id.partner_id.id or False
  #CH_N067 <<
        self.product_uom_qty = 0
        self.pricelist_id =False
        self.price_calculator_id = False
        self.calc_unit = False
        self.calc_price_per_kg = 0
        self.calc_price_per_pcs = 0
        self.calc_qty = 0
        self.product_uom = False
        self.product_id = False
        self.name = ''
        self.name1 = ''
        self.product_uom_qty=0.0
        #self.customer=False
        self.prod_name = ''
        self.n_product_category=False
        self.price_unit=0.0
        self.price_subtotal=0.0
        self.final_price=0.0
        self.min_qty=0.0
        self.fixed_price=0.0
        self.lowest_price=0.0
        self.floor_price=0.0
        self.price_line_id=False
        self.cus_product_line=False
        self.s_discount=0.0
        self.max_discount_allow=0.0
        self.max_discount=0.0
        self.price_discount=0.0
        self.product_packaging=False
        self.n_approved_price_1=0.0
        self.n_show_app_price=False
        self.highest_price=0.0
        self.lowest_price=0.0
        self.approval_status='normal'
        self.n_existing_product='new'
        self.n_film_product_id=False
            
        if self.pricelist_type == '2':
           pobj = self.env['product.product'].search([('name', '=', 'Bags'),('type','=','service')])
           self.product_id = pobj.id
        if self.pricelist_type == '3':
            prd_obj = self.env['product.product']
            cat_obj = self.env['product.category']
            uom_obj = self.env['product.uom']
            prd_ids = prd_obj.search([('default_code', '=', 'GEN')])
            pobj = False
            if prd_ids:
                pobj = prd_ids[0]
                
            else:
                cat_ids = cat_obj.search([('name','=', 'All')])
                uom_ids = uom_obj.sudo().search([('name', '=', 'Pcs')])
                if cat_ids:
                    vals = {
                        'name' : 'Generic Product',
                        'categ_id' : cat_ids[0].id,
                        'child_prod_name' : 'Generic Product',
                        'external_product_number' : 'GENPRD',
                        'default_code' : 'GEN',
                        'uom_id' : uom_ids and uom_ids[0].id,
                        'uom_po_id' : uom_ids and uom_ids[0].id
                    }
                    pobj = prd_obj.create(vals)
            self.product_id = pobj.id
            self.product_uom = pobj.uom_id.id
        if self.pricelist_type =='4':
                    self.customer=self.env['res.partner'].search([('name','=','Generic')],limit=1).id
        
    @api.onchange('product_uom_qty', 'product_uom', 'calc_unit', 'calc_price_per_kg', 'calc_price_per_pcs', 'calc_qty', 'calc_description', 'product_id')
    def product_uom_change(self):
        if self.contract_remain_qty and self.contract_bool:
           if self.product_uom_qty > self.contract_remain_qty:
              raise UserError(("Your Order Qty is Greater than contract Remaining Qty")) 
        else:
            if self.product_uom_qty > self.contract_qty and self.contract_qty:
               raise UserError(("Your Order Qty is Greater than contract Total Qty")) 
        if self.pricelist_type in ['1','4'] and self.order_id.pricelist_id and self.order_id.partner_id and not self.price_calculator_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.customer.id,
                quantity=self.product_uom_qty,
                date_order=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            if self.pricelist_type in ['1','4'] and self.product_id:
                context = self._context.copy()
                context.update({'customer_id': self.customer,'product_id': self.product_id,
                                'do_term':self.order_id.incoterm.id,
                                'pricelist_id':self.pricelist_id.id})
                result = self.pool['product.pricelist']._price_get_multi_line(self._cr, self._uid,
                                 self.order_id.pricelist_id, 
                                 [(product,self.product_uom_qty, self.order_id.partner_id.id),], context=context)
                if result:
                   self.update({'price_line_id': result.get(product.id)[1] or False})
            if self.pricelist_type not in ['1','4']:
                self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
           
        if self.price_calculator_id and self.pricelist_type in ['2']: 
            self.product_uom_qty = self.calc_qty
            self.product_uom = self.calc_unit.id
            self.min_qty = self.calc_moq
            self.name = self.calc_description
            self.name1 = self.calc_description
            self.price_subtotal = self.calc_total_price
            if self.product_uom.name == 'Kg':
                self.price_unit = self.calc_price_per_kg
            else:
                self.price_unit = self.calc_price_per_pcs
            if not self.n_film_product_id: #CH_N068 add code to stop added product name 
                prod_ids = self.env['product.product'].search([('product_tmpl_id','=', self.price_calculator_id.product_type.name.id)])
                if prod_ids:
                        self.product_id = prod_ids[0].id
        if self.pricelist_type != '3':
            self.price_unit= self.final_price   #to make same final price and unit price on product change
            
    @api.multi
    @api.onchange('max_discount', 'price_discount', 'final_price', 's_discount')
    def onchange_discount(self):
        for line in self:
            if line.pricelist_type == '2' and line.req_discount_type == 'per' and line.s_discount <= line.max_discount:
                line.dis_m = True
                line.approve_m = False
                line.approval_status = 'waiting_approval'
                line.no_update = False
            elif line.pricelist_type == '2' and line.req_discount_type == 'price' and line.s_price > line.max_discount:
                line.dis_m = True
                line.approve_m = False
                line.approval_status = 'waiting_approval'
                line.no_update = False
            elif line.pricelist_type == '2' and line.req_discount_type == 'per' and line.s_discount <= line.max_discount:
                line.dis_m = False
                line.approve_m = True
                line.approval_status = 'normal'
            elif line.pricelist_type == '2' and line.req_discount_type == 'price' and line.s_price != 0 and line.s_discount >= line.max_discount:
                line.dis_m = False
                line.approve_m = True
                line.approval_status = 'normal'
            if line.pricelist_type == '2' and line.final_price < line.price_discount:
                line.price_m = True
                line.approve_m = False
                line.price_unit = line.fixed_price
                line.no_update = False
                line.approval_status = 'waiting_approval'
                if line.pricelist_type == '2' and line.s_discount > line.max_discount:
                    line.dis_m = True
                    line.approve_m = False
                    line.no_update = False
                    line.approval_status = 'waiting_approval'
                elif line.pricelist_type == '2' and line.s_discount <= line.max_discount:
                    line.dis_m = False
                    line.approve_m = True
                    line.approval_status = 'normal'
            elif line.pricelist_type == '2' and line.final_price >= line.price_discount:
                line.price_m = False
                line.approve_m = True
                line.approval_status = 'normal'
                line.price_unit = line.final_price
                if line.pricelist_type == '2' and line.s_discount > line.max_discount:
                    line.dis_m = True
                    line.approve_m = False
                    line.approval_status = 'waiting_approval'
                    line.not_update = False
                elif line.pricelist_type == '2' and line.s_discount <= line.max_discount:
                    line.dis_m = False
                    line.approve_m = True
                    line.approval_status = 'normal'
            #CH_N016 add condition (n_approved_price_1 == False)
            if line.pricelist_type in ['1','4'] and line.final_price < line.fixed_price and not line.n_approved_price_1:
                line.price_m = True
                line.approve_m = False
                line.approval_status = 'waiting_approval'
                line.no_update = False
                line.price_unit = line.fixed_price
            elif line.pricelist_type in ['1','4'] and line.final_price >= line.fixed_price and not line.n_approved_price_1:
                line.price_m = False
                line.approve_m = True
                line.approval_status = 'normal'
                line.price_unit = line.final_price
            #CH_N016 add to compare after first approval in customer pricebook start
            elif line.pricelist_type in ['1','4'] and line.final_price < line.n_approved_price_1 :
                line.price_m = True
                line.approve_m = False
                line.approval_status = 'waiting_approval'
                line.no_update = False
                line.price_unit = line.final_price
            #CH_N017 start
            elif line.pricelist_type in ['1','4'] and line.final_price >= line.n_approved_price_1 :
                line.price_m = False
                line.approve_m = True
                line.approval_status = 'normal'
                line.price_unit = line.final_price
            #CH_N017 end
           #CH_N016 end  <<<<<<<<<

    n_approved_price_1 =fields.Float('Approved Price')  #CH_N016        for Customer pricebook
    n_show_app_price= fields.Boolean('Approve boolean',Default=False)   #CH_N017  for Customer pricebook
 
    @api.multi
    @api.depends('fixed_price', 'max_discount', 'calc_unit', 'calc_price_per_kg', 'calc_price_per_pcs','s_discount','price_line_id', 'req_discount_type', 'p_currency_id', 's_currency_id')
    def get_price_discount(self):
        for line in self:
            if line.pricelist_type == '2':
                line.req_discount_type = 'per'
                if line.calc_price_per_pcs:
                    price = 0;price_c = 0
                    if line.req_discount_type:
                        if line.req_discount_type == 'per':
                            price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                            price_c = line.fixed_price_c - line.fixed_price_c * (line.s_discount/100)
                        elif line.req_discount_type == 'price':
                            price = line.s_discount
                            price_c = line.p_currency_id.compute(line.s_discount, line.s_currency_id)
                    else:
                        price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                        
                    line.update({'price_discount': line.fixed_price - line.fixed_price *( line.max_discount /100),
                                 'price_discount_c': line.fixed_price_c - line.fixed_price_c * (line.max_discount/100),
                                 's_price': price, 's_price_c': price_c})
                
                if line.calc_price_per_kg:
                    price = 0; price_c = 0;
                    if line.req_discount_type:
                        if line.req_discount_type == 'per':
                            price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                            price_c = line.fixed_price_c - line.fixed_price_c * (line.s_discount/100)
                            
                        elif line.req_discount_type == 'price':
                            price = line.s_discount
                            
                    else:
                        price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                        price_c = line.p_currency_id.compute(line.s_discount, line.s_currency_id)
                    line.update({'price_discount': line.fixed_price - line.fixed_price *( line.max_discount /100),
                                 'price_discount_c': line.fixed_price_c - line.fixed_price_c * (line.max_discount/100),
                                 's_price': price, 's_price_c': price_c})
            if line.pricelist_type in ['1','4']:
                if line.price_line_id:
                    price = 0;price_c = 0
                    if line.req_discount_type:
                        if line.req_discount_type == 'per':
                            price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                            price_c = line.fixed_price_c - line.fixed_price_c * (line.s_discount/100)
                        elif line.req_discount_type == 'price':
                            price = line.s_discount
                            price_c = line.p_currency_id.compute(line.s_discount, line.s_currency_id) if line.s_currency_id else False
                    else:
                        price = line.fixed_price - line.fixed_price * (line.s_discount/100)
                        
                    line.update({'price_discount': line.fixed_price - line.fixed_price *( line.max_discount /100),
                                 'price_discount_c': line.fixed_price_c - line.fixed_price_c * (line.max_discount/100),
                                's_price': price, 's_price_c': price_c})
        
    @api.multi
    def action_approve(self):
        for line in self:
            rel=sub=''
            if self._context.get('approve'):
               sub +=str(line.order_id.user_id.name)+' Discount Request Approved  ' +str(line.order_partner_id.name) +' '+ str(line.order_id.name)
               rel +='Approved'
            if self._context.get('reject'):
               rel +='Rejected'
               sub +=str(line.order_id.user_id.name)+' Discount Request Rejected  ' +str(line.order_partner_id.name)+'  '+str(line.order_id.name)
            if self._context.get('approve'):
                if line.pricelist_type == '2':
                    line.write({'final_price': line.s_price,'n_show_approval_bool':True})
                    line.write({'price_unit': line.final_price or line.fixed_price, 'price_discount': line.final_price or line.fixed_price})
                    line.write({'approve_m': True, 'approval_status':'approved','not_update': False, 'price_m' : False, 's_discount' : 0, 'max_discount' : line.s_discount, 'dis_m': False})
                else:
                    if line.pricelist_type in ('1','4'):
                        line.write({'n_approved_price_1': line.final_price or line.fixed_price,'n_show_app_price':True})
                    line.write({'price_unit': line.final_price or line.fixed_price})
                    line.write({'approve_m': True, 'approval_status':'approved','not_update': False, 'price_m' : False, 'max_discount' :line.final_price, 'dis_m': False})
            if self._context.get('reject'):
               if line.pricelist_type == '2':
                    line.write({'n_show_approval_bool':True})
                    #line.write({'price_unit': line.fixed_price, })
                    line.write({'approve_m': True, 'approval_status':'approved','not_update': False, 'price_m' : False, 's_discount' : 0,'dis_m': False})
               else:
                    if line.pricelist_type in ('1','4'):
                       line.write({'n_show_app_price':True,'final_price':line.n_approved_price_1})
                    line.write({'price_unit': line.n_approved_price_1 or line.fixed_price})
                    line.write({'approve_m': True, 'approval_status':'approved','not_update': False, 'price_m' : False, 'max_discount' :line.n_approved_price_1, 'dis_m': False})
                    
            temp_id = self.env.ref('gt_sale_pricelist.email_template_approved_req', False)
            if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    # the parameters to encode for the query and fragment part of url
                query = {'db': self._cr.dbname}
                fragment = {
                    'model': 'sale.order',
                    'view_type': 'form',
                    'id': line.order_id.id,
                }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                text_link = _("""<a href="%s">%s</a>""") % (url, line.order_id.name)
                name = ''
                if line.product_id:
                    if line.product_id.default_code:
                        name = '[' + line.product_id.default_code + ']'
                    name += ' ' + line.product_id.name
                if not name:
                    line = line.name or line.name1
                body_html = """<div>
                
    <p><strong>Discount Request %s</strong></p>
    <p>Dear  %s ,<br/>
          <b> %s </b> %s your discount request for quotation: <b> %s </b> for <b> %s </b> <br></br>
          <b>Customer Name :%s</b>
    </p>
                </div>"""% (rel,line.order_id.user_id.name or '', line.order_id.team_id.user_id.name or '', rel,text_link, name, line.order_id.partner_id.name)
                body_html +='<li>Remark:'+str(line.discount_remark)
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',line.order_id.id, context=self._context)
                temp_id.write({'body_html': body_html,'subject':sub})
                temp_id.send_mail(line.order_id.id)
   
        return True
    
    @api.multi
    @api.depends('price_line_id', 'price_calculator_id', 'product_id', 'p_currency_id', 's_currency_id')
    def get_default_price_cur(self):
        for line in self:
            if line.p_currency_id and line.s_currency_id:
                if line.pricelist_type in ['1','4'] and line.price_line_id:
                    line.fixed_price = line.s_currency_id.compute(line.price_line_id.fixed_price, line.p_currency_id,round=False)
                    line.highest_price = line.s_currency_id.compute(line.price_line_id.cus_product_id.highest_price, line.p_currency_id,round=False)
                    line.lowest_price = line.s_currency_id.compute(line.price_line_id.cus_product_id.lowest_price, line.p_currency_id,round=False)
                    line.floor_price = line.s_currency_id.compute(line.price_line_id.cus_product_id.floor_price, line.p_currency_id,round=False)
                if line.pricelist_type == '2' and line.price_calculator_id:
                    #CH_N019 adds below condtion to avoid the updation on this fields on any other onchanges
                    if line.calc_unit.name == 'Kg':
                        line.fixed_price = line.s_currency_id.compute(line.calc_price_per_kg, line.p_currency_id,round=False)
                        line.final_price = line.s_currency_id.compute(line.calc_price_per_kg, line.p_currency_id,round=False)
                        #if line.n_show_approval_bool==False and line.s_discount == 0.0: #not working properly
                         #   line.price_unit = line.s_currency_id.compute(line.calc_price_per_kg, line.p_currency_id)
                    else:
                        line.fixed_price = line.s_currency_id.compute(line.calc_price_per_pcs, line.p_currency_id,round=False)
                        line.final_price = line.s_currency_id.compute(line.calc_price_per_pcs, line.p_currency_id,round=False)
                       # if line.n_show_approval_bool==False and line.s_discount == 0.0:#not working properly
                       #     line.price_unit = line.s_currency_id.compute(line.calc_price_per_pcs, line.p_currency_id)
    
    @api.multi
    @api.depends('price_line_id', 'price_calculator_id', 'product_id')
    def get_default_price(self):
        for line in self:
            if line.pricelist_type in ['1','4'] and line.price_line_id:
                line.fixed_price_c = line.price_line_id.fixed_price
                line.highest_price_c = line.price_line_id.cus_product_id.highest_price
                line.lowest_price_c = line.price_line_id.cus_product_id.lowest_price
                line.floor_price_c = line.price_line_id.cus_product_id.floor_price
            if line.pricelist_type == '2' and line.price_calculator_id:
                if line.calc_unit.name == 'Kg':
                    line.fixed_price_c = line.calc_price_per_kg
                else:
                    line.fixed_price_c = line.calc_price_per_pcs
                
    @api.multi
    @api.depends('price_line_id.cus_product_id.min_qty', 'price_calculator_id.moq_length', 'price_line_id', 'price_calculator_id')
    def get_min_qty(self):
        for line in self:
            if line.pricelist_type in ['1','4'] and line.price_line_id:
                line.min_qty = line.price_line_id.cus_product_id.min_qty
            if line.pricelist_type == '2' and line.price_calculator_id:
                line.min_qty = line.price_calculator_id.moq_length
            
    @api.multi
    @api.depends('price_line_id', 'price_calculator_id', 'price_calculator_id.max_discount')
    def get_discount_per(self):
        for line in self:
            if line.pricelist_type in ['1','4'] and line.price_line_id:
                line.max_discount = line.price_line_id and line.price_line_id.cus_product_id.lowest_price
                line.max_discount_allow = line.price_line_id and line.price_line_id.cus_product_id.lowest_price
            if line.pricelist_type == '2' and line.price_calculator_id:
                line.max_discount = line.price_calculator_id.max_discount
                line.max_discount_allow = line.price_calculator_id.max_discount

    @api.onchange('product_uom_qty', 'product_uom', 'route_id')
    def _onchange_product_id_check_availability(self):
        res = {}; 
        if not self.product_id or not self.product_uom_qty or not self.product_uom:
            self.product_packaging = False
            return res
        if self.product_id.type == 'product' and self.product_uom_qty > 1:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            product_qty = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_uom_qty, self.product_id.uom_id)
            if float_compare(self.product_id.virtual_available, product_qty, precision_digits=precision) == -1:
                is_available = self._check_routing()
                if not is_available:
                    warning_mess = {
                        'title': _('Not enough inventory!'),
                        'message' : _('You plan to sell %.2f %s but you only have %.2f %s available!\nThe stock on hand is %.2f %s.') % \
                            (self.product_uom_qty, self.product_uom.name, self.product_id.virtual_available, self.product_id.uom_id.name, self.product_id.qty_available, self.product_id.uom_id.name)
                    }
                    res.update({'warning': warning_mess})
                    
    @api.multi
    @api.depends('order_id.pricelist_id','price_line_id', 'price_calculator_id')
    def get_default_cur(self):
        for line in self:
            user = self.env['res.users'].sudo().browse(self._uid)
            line.p_currency_id = line.order_id.pricelist_id.currency_id.id
            line.s_currency_id = line.order_id.currency_id.id
            if line.pricelist_type in ['1','4'] and line.price_line_id:
#                line.fixed_price = line.price_line_id.cus_product_id.avg_price
                line.s_currency_id = line.price_line_id.currency_id.id
                
            if line.pricelist_type in ['3'] and line.product_id.name == 'Printing Plate':
                line.s_currency_id = user.company_id.currency_id.id
            if line.pricelist_type == '2' and line.price_calculator_id:
                line.s_currency_id = user.company_id.currency_id.id
            if line.p_currency_id == line.s_currency_id:
                line.currency_check = False
            if line.p_currency_id != line.s_currency_id:
                line.currency_check = True
                
    @api.multi
    @api.depends('price_calculator_id', 'price_calculator_id.printing_cost', 'price_calculator_id.check_printing_cost')
    def get_print_price(self):
        for line in self:
            if line.price_calculator_id:
                if line.price_calculator_id.check_printing_cost:
                    line.printing_price = line.price_calculator_id.printing_cost
                else:
                    line.printing_price = 0
                    
    @api.model
    def defult_currency_user(self):
        if self.pricelist_id and self.pricelist_id.currency_id:
            return self.pricelist_id.currency_id.id
        else:
            return False
        
    #@api.onchange('customer','pricelist_id')
    #def onchange_domain_prod(self):
    #    prd = []
    #    if not self.price_calculator_id:
    #        if self.customer and self.pricelist_type != '3':
    #            prd = []
    #            if self.pricelist_type == '4':
    #                cust_product_ids = self.env['customer.product'].search([('pricelist_id','=', self.pricelist_id.id)])
    #            else:
    #                cust_product_ids = self.env['customer.product'].search([('pricelist_id.customer','=', self.customer.id)])
    #            for prod in cust_product_ids:
    #                prd.append(prod.product_id.id)
                 
     #related field with calculator
    price_calculator_id = fields.Many2one('pricelist.calculater', string="Price Calculator")
    calc_unit = fields.Many2one(related='price_calculator_id.unit', string='Unit', store=True)
    calc_price_per_kg = fields.Float(related='price_calculator_id.price_per_kg', string='Unit Price', store=True)
    calc_price_per_pcs = fields.Float(related='price_calculator_id.price_per_pc', string='Unit Price', store=True)
    calc_qty = fields.Integer(related='price_calculator_id.qty', string='Ordered Quantity',  store=True)
    calc_moq = fields.Float(related='price_calculator_id.moq_length', string='MOQ',  store=True)
    calc_description = fields.Text(related='price_calculator_id.description', string='Description',  store=True)
    calc_total_price = fields.Float(related='price_calculator_id.total_price', string='Total',  store=True)
    price_unit_cal = fields.Float(string="Price")
    max_discount = fields.Float('Discount Approved(%)', dp.get_precision('Product'), compute=get_discount_per, store=True)
    max_discount_allow = fields.Float('Max Discount Allowed(%)', dp.get_precision('Product'), compute=get_discount_per,
                                store=True)
    price_discount = fields.Float('Price After Discount', digits=dp.get_precision('Payment Term'), compute=get_price_discount, multi=True, store=True)
    final_price = fields.Float('Final Price', digits=dp.get_precision('Payment Term'), default=0.0)
    req_discount_type = fields.Selection([('per', '%'), ('price', 'Price')], 'Request Discount in', default="per")
    s_discount = fields.Float('Discount Requested(%)', default=0)
    s_price = fields.Float('Price After Requested Discount', digits=dp.get_precision('Payment Term'), compute=get_price_discount, multi=True, store=True)
    approve_m = fields.Boolean('Approved', default=True)
    dis_m = fields.Boolean('Discount Check', default=False)
    price_m = fields.Boolean('Price Check', default=False)
    approval_status = fields.Selection([('normal', 'Normal'), ('waiting_approval', 'Waiting for Approval'),
                                        ('approved', 'Approved')], string="Approval Status", default='normal')
    min_qty = fields.Float('MOQ')
    fixed_price = fields.Float('Suggested Price', compute=get_default_price_cur, digits=dp.get_precision('Payment Term')) 
    highest_price = fields.Float('Highest Sold Price', compute=get_default_price_cur)
    lowest_price = fields.Float('Lowest Sold Price', compute=get_default_price_cur,digits=dp.get_precision('Payment Term'))
    floor_price = fields.Float('Floor Price', compute=get_default_price_cur,digits=dp.get_precision('Payment Term'))
    fixed_price_c = fields.Float('Customer Sold Price', compute=get_default_price,digits=dp.get_precision('Payment Term'))
    highest_price_c = fields.Float('Highest Sold Price', compute=get_default_price,digits=dp.get_precision('Payment Term'))
    lowest_price_c = fields.Float('Lowest Sold Price', compute=get_default_price,digits=dp.get_precision('Payment Term'))
    floor_price_c = fields.Float('Floor Price', compute=get_default_price,digits=dp.get_precision('Payment Term'))
    prd_name = fields.Char(string="Product Name")
    avg_price = fields.Float('Avg Price',digits=dp.get_precision('Payment Term'))
    high_price = fields.Float('Highest Price',digits=dp.get_precision('Payment Term'))
    low_price = fields.Float('Lowest Price',digits=dp.get_precision('Payment Term'))  
    uom_related = fields.Char(related="product_uom.name")
    p_currency_id = fields.Many2one('res.currency', 'Currency', compute=get_default_cur, store=True, default=defult_currency_user)
    s_currency_id = fields.Many2one('res.currency', 'Currency', compute=get_default_cur, store=True)
    s_price_c = fields.Float('Price After Requested Discount', digits=dp.get_precision('Payment Term'), compute=get_price_discount, multi=True, store=True)
    price_discount_c = fields.Float('Price After Discount Allowed', digits=dp.get_precision('Payment Term'), compute=get_price_discount, multi=True, store=True)
    currency_check = fields.Boolean('Currency Check', compute=get_default_cur, store=True)
    printing_price = fields.Float('Print Price', compute=get_print_price, store=True)
    sale_line_id = fields.Many2one('sale.order.line', 'Printing Line')
    print_product = fields.Boolean('Printing Product', default=False)
    no_print = fields.Boolean('Print Editable', default=False)
    product_domain_ids = fields.Many2many('product.product', 'prod_sale_line_rel', 'line_id', 'prod_id', string="Domain")
    product_type = fields.Selection('Type',related='product_id.product_tmpl_id.type')
    discount_remark=fields.Text('Remark')
    
    @api.multi
    def open_price_calculator(self):
        p_form = self.env.ref('gt_sale_pricelist.calculater_form_view', False)
        name='<span">Pricelist Calculator Details</span>'+'                 '+'<span class="glyphicon glyphicon-asterisk"></span>'
        if p_form:
             return {
                'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'pricelist.calculater',
                'views': [(p_form.id, 'form')],
                'view_id': p_form.id,
                'res_id':self.price_calculator_id.id,
                'target':'new',
              }

    @api.one
    @api.constrains('product_id')
    def _check_product_expiry(self):
        cus_product = self.env['customer.product']
        product = cus_product.search([('product_id', '=', self.product_id.id),
                                       ('pricelist_id','=',self.pricelist_id.id)])
        if product:
            product = product[0]
        if product.to_date and (product.to_date + ' 23:59:59') < self.order_id.date_order:
            raise ValidationError("Product [%s][%s] %s is already expired on %s "% (product.ext_product_number, product.int_product_number,self.product_id.name,datetime.strptime(product.to_date, '%Y-%m-%d').strftime('%m/%d/%Y')))
    
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    '''@api.multi
    def write(self, vals):
        res=super(SaleOrder, self).write(vals)
        body_html1=''
        if vals.get('order_line'):
           body_html1 +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial;text-align:center'><tr><th>Product Name </th><th> Suggested Price</th><th>Lowest Price</th><th>Requested Price </th><th>Remarks </th></tr>"  
           for record in self:
               print"============",self.order_line
               temp_id = self.env.ref('gt_sale_pricelist.email_template_approve_req')
               if temp_id:
                  base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                  query = {'db': self._cr.dbname}
                  fragment = {
                            'model': 'sale.order',
                            'view_type': 'form',
                            'id': record.id,
                         }
                  url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                  text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
                  body_html1 += """<div>
                         <p> <strong>Discount Requested </strong></p>
                             <p>Dear %s,<br/>
                                 <b>%s </b>requested for Discount on  <b> %s </b> for  <br/>
                                    <b>Customer Name </b>:%s
                             <br/>
                         </p> </div>"""%(record.team_id.user_id.name or '',record.user_id.name or '', text_link, record.partner_id.name )
               for ln in vals.get('order_line'):
                   for line in self.env['sale.order.line'].browse(ln[1]):
                         if line.approve_m != True and line.product_id.name != 'Deposit Product':
                            body_html1 +="<tr><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s(%s %s)</td><td>%s</td></tr>"%(line.product_id.name, line.fixed_price ,line.p_currency_id.symbol,line.lowest_price if line.lowest_price else 'NA' ,line.p_currency_id.symbol if line.lowest_price else '', str(line.s_discount) + '%' if line.s_discount else 'NA'  ,line.s_price if line.s_price else line.final_price , line.p_currency_id.symbol, line.discount_remark )
               body_html1 +="</table>"
               body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html1, 'sale.order',record.id, context=self._context)
               temp_id.write({'body_html': body_html})
               temp_id.send_mail(record.id)
        return res'''
    
    @api.multi
    @api.depends('order_line.approve_m','order_line.price_m','order_line.dis_m','order_line')
    def check_update(self):
        for order in self:
            res = False
            for line in order.order_line:
                if not line.approve_m or line.dis_m or line.price_m:
                    res = True
            order.check_approve = res

    @api.multi
    @api.depends('order_line.approve_m', 'order_line.price_m', 'order_line.dis_m', 'order_line')
    def update_approval_status(self):
        for order in self:
            any_waiting = False
            any_approved = False
            for line in order.order_line:
                if line.approval_status == 'waiting_approval':
                    any_waiting = True
                elif line.approval_status == 'approved':
                    any_approved = True
            if any_waiting:
                order.approval_status = 'waiting_approval'
            elif not any_waiting and any_approved:
                order.approval_status = 'approved'
            else:
                order.approval_status = 'normal'

    check_approve = fields.Boolean('Check Approve', compute=check_update, store=True)
    approval_status = fields.Selection([('normal', 'Normal'), ('waiting_approval', 'Waiting for Approval'),
                                        ('approved', 'Approved')], string="Approval Status",
                                       compute=update_approval_status, store=True)
    
    @api.multi
    def action_quotation_send(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        if len(self.order_line) <= 0:
            raise UserError("Add Products")
        for line in self.order_line:
            if not line.approve_m or line.dis_m or line.price_m:
                raise UserError("You can't Send Quotation, Please get Approval  from Manager before Sending Quotation")
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sale', 'email_template_edi_sale')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

        
class AccountPaymentTerm(models.Model):
     _inherit = "account.payment.term"
     
     partner_id = fields.Many2one('res.partner','Customer')

class ProductUom(models.Model):
    _inherit = "product.uom"
    
    price_cal_uom = fields.Boolean(string="Custom Product UOM")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
