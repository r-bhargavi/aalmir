# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Devintelle Software Solutions (<http://devintelle.com>).
#
##############################################################################
from openerp import api, models, fields, _
import openerp.addons.decimal_precision as dp
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import tools
from datetime import datetime, date
from datetime import timedelta
from openerp import tools
from urllib import urlencode
from urlparse import urljoin
import re
import urlparse
import base64
from openerp.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class ProductPricelist(models.Model):
    _name='product.pricelist'
    _inherit = ['mail.thread','product.pricelist']

    @api.multi
    def write(self, vals):
        str1=""
        if vals.get('name'):
		    str1 += "<li>Name. :- "+str(vals.get('name'))+"</li>"
        if vals.get('currency_id'):
		    str1 += "<li>currency :- "+str(vals.get('currency_id'))+"</li>"     
        if vals.get('customer'):
		    str1 += "<li>Customer :- "+str(vals.get('customer'))+"</li>"
        self.message_post(body=str1)
        return super(ProductPricelist, self).write(vals)

    def _price_rule_get_multi_uom(self, cr, uid, pricelist, products_by_qty_by_partner, uom, context=None):
        _logger.info('_price_rule_get_multi_uom.........')
        print "prcelist now--------------",pricelist
        context = context or {}
        date = context.get('date') and context['date'][0:10] or time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        products = map(lambda x: x[0], products_by_qty_by_partner)
        product_uom_obj = self.pool.get('product.uom')

        if not products:
            return {}

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = categ_ids.keys()

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        cust_p_obj = self.pool.get('customer.product')
        if context.get('pricelist_id',False):
            print "self-------12------------------",self
            cust_prod_ids = cust_p_obj.search(cr, uid, [('pricelist_id','=', context.get('pricelist_id')),('pricelist_id.customer','=', context.get('customer_id').id), ('product_id','=', context.get('product_id').id)])
        elif not context.get('pricelist_id',False) and context.get('line_id',False):
            if context.get('line_id').pricelist_id:
                cust_prod_ids = cust_p_obj.search(cr, uid, [('pricelist_id','=', context.get('line_id').pricelist_id.id),('pricelist_id.customer','=', context.get('customer_id').id), ('product_id','=', context.get('product_id').id)])
        else:
            cust_prod_ids = cust_p_obj.search(cr, uid, [('pricelist_id.customer','=', context.get('customer_id').id), ('product_id','=', context.get('product_id').id)])
        print "cust_prod_idscust_prod_ids",cust_prod_ids
        if cust_prod_ids:
            cobj = cust_p_obj.browse(cr, uid, cust_prod_ids[0])
            item_ids = cobj.item_ids
        else:
            item_ids = []
        items = item_ids
        results = {}
        for product, qty, partner in products_by_qty_by_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = product_uom_obj._compute_qty(
                        cr, 1, context['uom'], qty, product.uom_id.id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call _price_get.
            price = self.pool['product.template']._price_get(cr, uid, [product], 'list_price', context=context)[product.id]
            price_uom_id = qty_uom_id
            flag_term=True
            _logger.info('Items in........{}'.format(items))
            print "aedesfrefergrtg",context
            for rule1 in items:
                if rule1.do_term.id == context.get('do_term'):
                    if qty_in_product_uom >= rule1.min_quantity and qty_in_product_uom <= rule1.qty:
                        flag_term=False
            if flag_term:
                _logger.info('There is no price for delivery term.........{}'.format(context.get('do_term')))
                dp_term_name=self.pool.get('stock.incoterms').browse(cr,uid,[context.get('do_term')]).name
                raise UserError("There is no price for product '{}' of Quantity {} against Delivery Term {} ".format(product.name,qty_in_product_uom,dp_term_name))
                
            for rule in items:
                if rule.do_term.id == context.get('do_term'):
                    if qty_in_product_uom >= rule.min_quantity and qty_in_product_uom <= rule.qty:
                        if is_product_template:
                            if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                                continue
                            if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_ids[0].id == rule.product_id.id):
                                # product rule acceptable on template if has only one variant
                                continue
                        else:
                            if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                                continue
                            if rule.product_id and product.id != rule.product_id.id:
                                continue

                        if rule.categ_id:
                            cat = product.categ_id
                            while cat:
                                if cat.id == rule.categ_id.id:
                                    break
                                cat = cat.parent_id
                            if not cat:
                                continue

                        if rule.base == 'pricelist' and rule.base_pricelist_id:
                            price_tmp = self._price_get_multi(cr, uid, rule.base_pricelist_id, [(product, qty, partner)], context=context)[product.id]
                            ptype_src = rule.base_pricelist_id.currency_id.id
                            price = self.pool['res.currency'].compute(cr, uid, ptype_src, pricelist.currency_id.id, price_tmp, round=False, context=context)
                        else:
                            # if base option is public price take sale price else cost price of product
                            # price_get returns the price in the context UoM, i.e. qty_uom_id
                            price = self.pool['product.template']._price_get(cr, uid, [product], rule.base, context=context)[product.id]

                        convert_to_price_uom = (lambda price: product_uom_obj._compute_price(
                                                    cr, 1, product.uom_id.id,
                                                    price, price_uom_id))

                        if price is not False:
                            if rule.compute_price == 'fixed':
                                price = convert_to_price_uom(rule.fixed_price)
                            elif rule.compute_price == 'percentage':
                                price = (price - (price * (rule.percent_price / 100))) or 0.0
                            else:
                                #complete formula
                                price_limit = price
                                price = (price - (price * (rule.price_discount / 100))) or 0.0
                                if rule.price_round:
                                    price = tools.float_round(price, precision_rounding=rule.price_round)

                                if rule.price_surcharge:
                                    price_surcharge = convert_to_price_uom(rule.price_surcharge)
                                    price += price_surcharge

                                if rule.price_min_margin:
                                    price_min_margin = convert_to_price_uom(rule.price_min_margin)
                                    price = max(price, price_limit + price_min_margin)

                                if rule.price_max_margin:
                                    price_max_margin = convert_to_price_uom(rule.price_max_margin)
                                    price = min(price, price_limit + price_max_margin)
                            suitable_rule = rule
                        _logger.info('Searching in Line is done for price in itemids.........')
                        break
                        
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                price = self.pool['res.currency'].compute(cr, uid, product.currency_id.id, pricelist.currency_id.id, price, round=False, context=context)
            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
        return results
    
    customer = fields.Many2one('res.partner','Customer')
    generic_use = fields.Boolean('Generic Pricebook',default=False)
    contract_use=fields.Boolean('Contract Pricelist',default=False)
    
    @api.onchange('generic_use')
    def generic_use_onchange(self):
        self.contract_use=False
        #self.customer=False
        
    @api.onchange('contract_use')
    def contract_use_onchange(self):
        self.generic_use=False
        
    def _price_get_multi_line(self, cr, uid, pricelist, products_by_qty_by_partner, context=None):
        if context.get('customer_id') and context.get('product_id'):
            res = dict((key, price) for key, price in self._price_rule_get_multi_uom(cr, uid, pricelist, products_by_qty_by_partner, context.get('pricelist_uom'), context=context).items())
        else:
            res = dict((key, price) for key, price in self._price_rule_get_multi(cr, uid, pricelist, products_by_qty_by_partner, context=context).items())
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike',limit=100):
        if self._context.get('pricelist_type')=='1' and self._context.get('customer'):
                ct_bool=False
                if self._context.get('is_contract'):
                    ct_bool=True
                pricelist_ids=self.search([('generic_use','=',False),('contract_use','=',ct_bool),('customer','=',self._context.get('customer'))])
                return [(i.id,i.name) for i in pricelist_ids]
        if self._context.get('pricelist_type')=='4':
                pricelist_ids=self.search([('contract_use','=',False),('generic_use','=',True)])
                return [(i.id,i.name) for i in pricelist_ids]
        return super(ProductPricelist,self).name_search(name, args, operator=operator,limit=limit)
    
class ProductTemplate(models.Model):
    _inherit = "product.template"   
    
    @api.onchange('categ_id')
    def _hide_calculator(self):
        for rec in self:
            flag=False
            if rec.categ_id.cat_type != 'injection':
                flag=True
            rec.hide_calculator=flag
            
    min_qty = fields.Float('Min Qty')
    #CH_N019 move and change in fields from prodcut_product to prodct_template  start >>> 
    lowest_price = fields.Float(string='Lowest Sold Price',digits=(16,4),readonly=True)
    n_product_type =fields.Selection([('new','New Product'),('custom', 'Custom Product'),('film', 'Film Product')], 'Product Entry Type',default='new')
    n_calculator_id = fields.Many2one('pricelist.calculater', string="Price Calculator")
    hide_calculator = fields.Boolean(compute='_hide_calculator')
    #end >>> 

    ##CH_N04 start >>> to show quotation button
    @api.multi
    @api.depends('product_variant_ids.quotation_count')
    def _quotation_count(self):
        for product in self:
            product.quotation_count = sum([p.quotation_count for p in product.product_variant_ids])
    
    quotation_count = fields.Integer(compute='_quotation_count', string='# Quotations')
    
    @api.multi
    def open_filmcalculator(self):
        form_id = self.env.ref('gt_sale_pricelist.calculater_form_view', False)
        data={}
        if form_id:
            data= {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pricelist.calculater',
                    'views': [(form_id.id, 'form')],
                    'view_id': form_id.id,
                    'target': 'new',
            }
        if self.n_calculator_id:
            data.update({'res_id':self.n_calculator_id.id,'context':{'from_mrp':True}})
        else:
            uom=self.env['product.uom'].search([('name','=','Kg')],limit=1)
            if not uom:
                raise UserError("There is no Kg Unit Found")
            data.update({'context':{'from_mrp':True,'default_qty':200,'default_unit':uom.id}})
        return data
            
    #CH_N60 change code to show specific form >>>
    @api.multi
    def n_action_view_quotations(self):
        self.ensure_one()
        sale_id_tree = self.env.ref('sale.view_order_line_tree', False)
        if sale_id_tree:
            return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'sale.order.line',
                    'views': [(sale_id_tree.id, 'tree')],
                    'view_id': sale_id_tree.id,
                    'target': 'current',
                    'domain': [('state', 'in', ['draft', 'sent']), ('product_id.product_tmpl_id', '=', self.id)],
            }

    @api.multi
    def action_view_sales(self):
        sale_id_tree = self.env.ref('sale.view_order_line_tree', False)
        if sale_id_tree:
            return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'sale.order.line',
                    'views': [(sale_id_tree.id, 'tree')],
                    'view_id': sale_id_tree.id,
                    'target': 'current',
                    'domain': [('state', 'in', ['sale', 'done']), ('product_id.product_tmpl_id', '=', self.id)],
            }
    ##CH_N04 end <<<

    ### CH_N06 Start >>>
    @api.multi
    def n_get_prod_pricelist(self):
        for rec in self:
            produt_id=self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
            cust_prod_ids = self.env['customer.product'].search([('product_id','in', [p_id.id for p_id in produt_id])])
            pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
            rec.n_pricelist_count = len(pids)
    
    n_pricelist_count = fields.Integer(string="Customers", compute=n_get_prod_pricelist, default=0)

    @api.multi
    def n_open_pricelist(self):
        pids = []
        for rec in self:
            produt_id=self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
            cust_prod_ids = self.env['customer.product'].search([('product_id','in', [p_id.id for p_id in produt_id])])
            pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
        res = self.env['ir.actions.act_window'].for_xml_id('product', 'product_pricelist_action2')
        res['domain'] = [('id', 'in', pids)]
        return res    
    ##CH_N06 End <<<

class ProductProduct(models.Model):
    _inherit = "product.product"
 
    min_qty = fields.Float('Min Qty')

    ##CH_N04 start >>> to show quotation button    
    @api.multi
    def _quotation_count(self):
        r = {}
        domain = [
            ('state', 'in', ['draft', 'sent']),
            ('product_id', 'in', self.ids),
        ]
        for group in self.env['sale.report'].read_group(domain, ['product_id', 'product_uom_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_uom_qty']
        for product in self:
            product.quotation_count = r.get(product.id, 0)
        return r

    quotation_count = fields.Integer(compute='_quotation_count', string='# Quotations')
    ##CH_N04 end<<

    #CH_N012 start >>
    @api.model
    def name_search(self,name, args=None, operator='ilike',limit=100):
        if self._context.get('film_cust_check')=='customer' :
            if self._context.get('film_customer'):
                args=[]
                product_qry="select id from product_product where product_tmpl_id in (select id from product_template where n_product_type='film') and id in (select product_id from customer_product where pricelist_id in (select id from product_pricelist where customer={}))".format(self._context.get('film_customer'))
                self.env.cr.execute(product_qry)
                product_ids=[i[0] for i in cr.fetchall()]
                args.extend([('id','in',product_ids)])
        if self._context.get('pricelist_type') in ('4','1') and self._context.get('pricelist'): 
            product_ids=self.env['customer.product'].search([('pricelist_id','=',self._context.get('pricelist'))])
            args=[('id','in',[i.product_id.id for i in product_ids])]
            print "............",product_ids
        return super(ProductProduct,self).name_search(name, args, operator=operator,limit=limit)
		#CH_N031 end
    #CH_N012 end
    
    @api.onchange('categ_id')
    def _hide_calculator(self):
        return self.product_tmpl_id._hide_calculator()
            
    @api.multi
    def open_filmcalculator(self):
        return self.product_tmpl_id.open_filmcalculator()
            
    #CH_N60 change code to show specific form >>>
    @api.multi
    def n_action_view_quotations(self):
        return self.product_tmpl_id.n_action_view_quotations()

    @api.multi
    def action_view_sales(self):
        return self.product_tmpl_id.action_view_sales()

    @api.multi
    def n_open_pricelist(self):
        return self.product_tmpl_id.n_open_pricelist()

class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item" 
    _order ="do_term,id"
    
    @api.one
    @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        if self.categ_id:
            self.name = _("Category: %s") % (self.categ_id.name)
        elif self.product_tmpl_id:
            self.name = '[' + self.product_tmpl_id.name + ']'
        elif self.product_id:
            self.name = self.product_id.display_name.replace('[%s]' % self.product_id.code, '')
        else:
            self.name = _("All Products")
        name = self.name
        if self.min_quantity:
            name += ' Min [%s]' %str(self.qty) + ' Qty [%s]' %str(self.min_quantity)
        if self.fixed_price:
            name += (" Pr [%s] %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
        if self.compute_price == 'fixed':
            self.price = self.fixed_price
        elif self.compute_price == 'percentage':
            self.price = self.percent_price
        else:
            self.price = abs(self.price_discount)
        if self.price_discount:
            name += _(" Dis %s%%") % (abs(self.price_discount))
        self.name = name

    #functional fields used for usability purposes
    name = fields.Char(compute='_get_pricelist_item_name_price', string='Name', multi='item_name_price', help="Explicit rule name for this pricelist line.")
    price = fields.Char(compute='_get_pricelist_item_name_price', string='Price', multi='item_name_price', help="Explicit rule name for this pricelist line.")
    price = fields.Float('Unit Price with Disc.')
    floor_price = fields.Float('Floor Price')
    uom_id = fields.Many2one('product.uom', string="Unit")
    line_id = fields.Many2one('sale.order.line', string="Discount Items")
    copy_price_list = fields.Boolean(string="Copy")
    customer = fields.Many2one('res.partner',string='Customer')
    qty = fields.Integer('Max Qty', default=10000)
    do_term = fields.Many2one('stock.incoterms', 'Delivery Term')
    
    @api.model
    def create(self, vals):
        vals.update({'applied_on' : '0_product_variant'})
        res = super(ProductPricelistItem, self).create(vals)
        return res

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    item_ids = fields.One2many('product.pricelist.item', 'customer', 'Items')

    @api.multi
    def copy_pricelist(self):
        for rec in self:
            for pl in rec.item_ids:
                if pl.copy_price_list:
                    pl.copy({'price_discount':0, 'min_qty':0, 'copy_price_list' : False})
                    pl.copy_price_list = False
    
    @api.one
    def view_pricelist(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('dev_custom_pricelist.action_open_customer_pricelist_report_custom')
        form_view_id = imd.xmlid_to_res_id('dev_custom_pricelist.product_pricelist_form_report')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
        }
        if self.property_product_pricelist:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.property_product_pricelist.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

  #CH_N050 start >>
    @api.model
    def name_search(self, name, args=None, operator='ilike',limit=100):
        '''Inherite Method to get Invoice and Delivery Address in sales order according to context
           if invoice in context then get all invoice address of customer if invoice address not found show customer address 
           if delivery in context then get all delivery address of customer if delivery address not found show customer address'''
           
        if self._context.get('new_data')=='pricelist' :
                cust_ids=self.env['product.pricelist'].search([('customer','!=',False),('generic_use','=',False),('generic_use','=',False)])
                args=[('id','in',[i.customer.id for i in cust_ids])]
        if self._context.get('default_type')=='invoice':
            if self._context.get('partner_id'):
                partner_id=self.search([('parent_id','=',self._context.get('partner_id')),('type','in',('invoice','delivery','other'))])
                if not partner_id:
                        partner_id=self.search([('id','=',self._context.get('partner_id'))])
                args=[('id','in',[i.id for i in partner_id])]
            else:
                return []
        if self._context.get('default_type')=='delivery':
            if self._context.get('incoterm'):
                    term_id=self.env['stock.incoterms'].search([('id','=',self._context.get('incoterm'))])
                    if term_id.code == 'EXF':
                        partner_id= self.search([('parent_id','=',self.env.user.company_id.partner_id.id),('type','=','delivery')])
                        if not partner_id:
                            partner_id = self.env.user.company_id.partner_id
                        args=[('id','in',[i.id for i in partner_id])]
                    else:
                        partner_id=self.search([('parent_id','=',self._context.get('partner_id')),('type','in',('invoice','delivery','other'))])
                        if not partner_id:
                            partner_id=self.search([('id','=',self._context.get('partner_id'))])
                        args=[('id','in',[i.id for i in partner_id])]
            elif self._context.get('partner_id'):
                partner_id=self.search([('parent_id','=',self._context.get('partner_id')),('type','in',('invoice','delivery','other'))])
                if not partner_id:
                    partner_id=self.search([('id','=',self._context.get('partner_id'))])
                args=[('id','in',[i.id for i in partner_id])]
            else:
                return []
        return super(ResPartner,self).name_search(name, args, operator=operator,limit=limit)
    
    @api.model
    def default_get(self,fields):
        ''' Inherite this method to set current company generic pricelist in customer'''
        rec = super(ResPartner, self).default_get(fields)
        company_obj=self.env['res.company']
        pricelist_obj=self.env['product.pricelist']
        if rec.get('company_id') and rec.get('property_product_pricelist'):
            company_id=company_obj.search([('id','=',rec.get('company_id'))])
            pricelist_id = pricelist_obj.search([('id','=',rec.get('property_product_pricelist'))])
            if pricelist_id.company_id != company_id.id:
                new_id=pricelist_obj.search([('company_id','=',company_id.id),
                                            ('customer','=',False)],order='id',limit=1)
                if new_id:
                    rec['property_product_pricelist']=new_id.id
        return rec

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.multi
    @api.depends('product_id')
    def get_discount_lines(self):
        _logger.info('API-code.. add pricelist_item_ids.. to sale line')
        for line in self:
            if line.product_id and line.customer:
#                cust_prod_ids = self.env['customer.product'].search([('product_id','=', line.product_id.id), ('pricelist_id.customer','=',line.customer.id),('pricelist_id.contract_use','=',False)])
                cust_prod_ids = self.env['customer.product'].search([('product_id','=', line.product_id.id), ('pricelist_id','=',line.pricelist_id.id),('pricelist_id.customer','=',line.customer.id)])
                if cust_prod_ids:
                    if cust_prod_ids[0].item_ids:
                        line.pricelist_item_ids = [(6,0,list(cust_prod_ids[0].item_ids._ids))]
                    if len(cust_prod_ids[0].item_ids) > 0:
                        line.pricelist_check = True
                    else:
                        line.pricelist_check = False
                else:
                    _logger.info('API-code.. add pricelist_item_ids.. cust_prod_ids not found')
                    
                        
    @api.onchange('name', 'name1')
    def onchange_name(self):
        if self.name1 and self.name1 != self.name:
            self.name = self.name1
        else:
            self.name1 = self.name

    #CH_N018 start >> to calculate currency in company currency
    @api.multi
    @api.depends('final_price')
    def get_convert_currency(self):
        for line in self:
            line.converted_company_price = line.p_currency_id.compute(line.final_price,self.env.user.company_id.currency_id)
   # CH_N018 end <<

    ##CH_N06 start 
    @api.multi
    @api.onchange('n_film_product_id')
    def n_getfilm_id(self):
        #CH_N010 statr  code to calculate film calculator amounts >>>
        pricelist=self.env['pricelist.calculater']
        if self.n_film_product_id.n_calculator_id:
            for rec in self.n_film_product_id.n_calculator_id:
                if not self.price_calculator_id: 
                    res_ids=pricelist.create({'product_type':rec.product_type.id,'bag_type':rec.bag_type.id,
                                'check_product_type':rec.check_product_type,
                                'material_type':rec.material_type.id,'check_material_type':rec.check_material_type,
                                'delivery_location':rec.delivery_location.id,
                                'check_delivery_location':rec.check_delivery_location,
                                'packing_type':rec.packing_type.id,'check_packing_type':rec.check_packing_type,
                                'unit':rec.unit.id,'qty':rec.qty,'moq_length':rec.moq_length,
                                'check_moq_length':rec.check_moq_length,
                                'ink_weigth':rec.ink_weigth,'check_ink_weigth':rec.check_ink_weigth,
                                'total_printing_area':rec.total_printing_area,
                                'check_total_printing_area':rec.check_total_printing_area,
                                'micron':rec.micron,'check_micron':rec.check_micron,
                                'printing_type':rec.printing_type.id,'check_printing_type':rec.check_printing_type,
                                'printing_area':rec.printing_area,
                                'check_printing_area':rec.check_printing_area,'lenght':rec.lenght,
                                'check_lenght':rec.check_lenght,
                                'width':rec.width,'check_width':rec.check_width,'left':rec.left,
                                'check_left':rec.check_left,'right':rec.right,
                            'check_right':rec.check_right,'top':rec.top,'check_top':rec.check_top,'bottom':rec.bottom,
                            'check_bottom':rec.check_bottom,'total_price_stretch':rec.total_price_stretch,
                            'check_weight_per_gram':rec.check_weight_per_gram,
                            'check_weight_per_kg':rec.check_weight_per_kg,
                            'check_total_weight':rec.check_total_weight,
                            'check_printing_cost':rec.check_printing_cost,
                            'check_total_pcs':rec.check_total_pcs,'max_discount':rec.max_discount,
                            'description':rec.description,'n_state':'qty_change',
                            'product_bool':True,'change_bool':True })
                    self.price_calculator_id=res_ids
                else:
                    self.price_calculator_id.write({'product_type':rec.product_type.id,'bag_type':rec.bag_type.id,
                                'check_product_type':rec.check_product_type,
                                'material_type':rec.material_type.id,'check_material_type':rec.check_material_type,
                                'delivery_location':rec.delivery_location.id,
                                'check_delivery_location':rec.check_delivery_location,
                                'packing_type':rec.packing_type.id,'check_packing_type':rec.check_packing_type,
                                'unit':rec.unit.id,'qty':rec.qty,'moq_length':rec.moq_length,
                                'check_moq_length':rec.check_moq_length,
                                'ink_weigth':rec.ink_weigth,'check_ink_weigth':rec.check_ink_weigth,
                                'total_printing_area':rec.total_printing_area,
                                'check_total_printing_area':rec.check_total_printing_area,
                                'micron':rec.micron,'check_micron':rec.check_micron,
                                'printing_type':rec.printing_type.id,'check_printing_type':rec.check_printing_type,
                                'printing_area':rec.printing_area,
                                'check_printing_area':rec.check_printing_area,
                                'lenght':rec.lenght,'check_lenght':rec.check_lenght,
                                'width':rec.width,'check_width':rec.check_width,'left':rec.left,
                                'check_left':rec.check_left,'right':rec.right,
                                'check_right':rec.check_right,'top':rec.top,
                                'check_top':rec.check_top,'bottom':rec.bottom,
                                'check_bottom':rec.check_bottom,'total_price_stretch':rec.total_price_stretch,
                                'check_weight_per_gram':rec.check_weight_per_gram,
                                'check_weight_per_kg':rec.check_weight_per_kg,
                                'check_total_weight':rec.check_total_weight,
                                'check_printing_cost':rec.check_printing_cost,
                                'check_total_pcs':rec.check_total_pcs,'max_discount':rec.max_discount,
                                'description':rec.description,
                                'n_state':'qty_change','product_bool':True,'change_bool':True,'n_hide':False})
       #CH_N010 end << 
    ##CH_N06 end

    pricelist_type = fields.Selection([('1', 'Customer Pricebook'),('4', 'Generic Pricebook'),('2', 'Film Calculator'), 
                                       ('3', 'Custom Product')], 'Price Type')
    customer = fields.Many2one('res.partner', 'Pricebook')
    price_line_id = fields.Many2one('product.pricelist.item', 'Price Line')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist')
    not_update = fields.Boolean('Update')
    pricelist_item_ids = fields.One2many('product.pricelist.item', 'line_id', string="Discount Lines", compute="get_discount_lines")
    pricelist_check = fields.Boolean(string="Check", compute="get_discount_lines")
    name1 = fields.Text('Name')
    n_film_product_id = fields.Many2one("product.product", "Product") #CH_N06 add field
    #n_film_cust_product_bool = fields.Boolean('Customer',Default=False,help="When you check this field the product list show only this customer products")
    n_existing_product =fields.Selection([('new','New Product'),('customer', 'Re-Calculate')], 'Existing Product',default='new') #CH_N017 add selection field
    converted_company_price = fields.Float('In AED', compute=get_convert_currency, store=True) #CH_N018
    n_product_category = fields.Many2one("product.category", "Product Category")    #CH_N041 add field 

class CrmTeam(models.Model): 
    _inherit = 'crm.team'
    
    @api.multi
    def get_waiting_for_approvals(self):
        for team in self:
            orders = self.env['sale.order'].search([('team_id','=',team.id),('state','=','draft'), ('approval_status', '=', 'waiting_approval')])
            team.waiting_orders = len(orders)
        return True

    @api.multi
    def get_approved_orders(self):
        for team in self:
            orders = self.env['sale.order'].search([('team_id','=',team.id),('state','=','draft'), ('approval_status', '=', 'approved')])
            team.approved_order = len(orders)
        return True
        
    waiting_orders = fields.Integer('# Pending Orders', compute=get_waiting_for_approvals)
    approved_order = fields.Integer('# Approved Order', compute=get_approved_orders)
    
    @api.multi
    def show_discount_requested(self):
        pass
    @api.multi
    def show_approve_discount(self):
        pass
        
class MailMessage(models.Model):
    _inherit = "mail.message"
    
    @api.model
    def create(self, vals):
        body = vals.get('body')
        if body.__contains__('sale.order') and body.__contains__('res_id'):
            if not vals.get('model') and not vals.get('res_id'):
                vals.update({'model': 'sale.order',})
                list1 = re.findall(r'(https?://[^\s]+)', vals['body'])
                for l1 in list1:
                    parsed = urlparse.urlparse(l1.replace('#','?'))
                    if urlparse.parse_qs(parsed.query).get('model'):
                        vals.update({'model': urlparse.parse_qs(parsed.query)['model'][0], 'res_id': int(urlparse.parse_qs(parsed.query)['id'][0].replace('"', ''))})
        mail_id = super(MailMessage, self).create(vals)
        lead_vals = vals.copy()
        if vals.get('model') == 'sale.order' and vals.get('res_id'):
            sale = self.env['sale.order'].sudo().browse(vals['res_id'])
            if sale.opportunity_id:
                body_html = vals.get('body')
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                    # the parameters to encode for the query and fragment part of url
                query = {'db': self._cr.dbname}
                fragment = {
                    'model': 'sale.order',
                    'view_type': 'form',
                    'id': sale.id,
                }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                text = _("""<p><a href="%s">%s Sale Document</a></p>""") % (url,sale.name)
                
                
                lead_vals.update({'model': 'crm.lead', 'res_id': sale.opportunity_id.id, 'message_type': 'comment'})
                lead_vals.update({'message_id': ''})
                if mail_id.tracking_value_ids:
                    for line in mail_id.tracking_value_ids:
                        res = line.read([])[0]
                        if line.field_type in ['many2one','selection']:
                            body_html += "<p> <strong>. %s:  %s --&gt; %s <strong></p>"%(line.field_desc, str(res.get('old_value_char')), str(res.get('new_value_char')))
                        else:
                            body_html += "<p> <strong>. %s:  %s --&gt; %s <strong></p>"%(line.field_desc, str(res.get('old_value_'+line.field_type)), str(res.get('new_value_'+line.field_type)))
                lead_vals['tracking_value_ids'] = []
                body_html = tools.append_content_to_html(body_html, ("<div><p>%s</p></div>" % text), plaintext=False)
                lead_vals.update({'body': body_html, 'partner_ids': [(6,0, [])]})
                super(MailMessage, self).create(lead_vals)
        return mail_id
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
    
