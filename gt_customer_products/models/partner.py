# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_tax_link(self):
	for rec in self:
		rec.validate_vat_number=rec.company_id.tax_validation
    
    @api.model
    def _get_tax_link(self):
    	for rec in self:
    		rec.validate_vat_number = rec.company_id.tax_validation
    	
    product_ids = fields.One2many('customer.product', 'customer_id', string="Products")
    validate_vat_number = fields.Char('Validate',compute="_get_tax_link")
    
class resCompany(models.Model):
	_inherit = 'res.company'
	
	tax_validation = fields.Char('Tax Validation',help="Enter a link to validate customer/supplier VAT number with Goverment portal")
    
class CustomerProduct(models.Model):
    _name = "customer.product"
    _inherit = ['mail.thread']

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            if not self.ext_product_number:
                self.ext_product_number = self.product_id.external_product_number
            if not self.product_description:
                self.product_description = self.product_id.name
            if self.product_id.packaging_ids:
                for pack in self.product_id.packaging_ids:
		    if pack.pkgtype == 'primary':
		       self.product_packaging=pack.id
            else:
		self.product_packaging=False

    @api.model
    def create(self, vals):
	product_type='new'
	low_price=0.0
	n_ids=False
	if vals.get('n_product_type'):	# api product type
		product_type=vals.get('n_product_type')
	if vals.get('n_calculator_id'):
		n_ids=vals.get('n_calculator_id')
	if vals.get('avg_price'):
		if vals.get('currency_id'):
			currency_id=self.env['res.currency'].search([('id','=',vals.get('currency_id'))])
			low_price=currency_id.compute(vals.get('avg_price'),self.env.user.company_id.currency_id)
			vals.pop('currency_id')
	#CH_N019 change in code end
        
        prod_obj = self.env['product.product']
        categ_obj = self.env['product.category']
        tmpl_obj = self.env['product.template']
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
          
        if not vals.get('valid_from'):
            vals.update({'valid_from' : fields.Date.context_today})
        if not vals.get('to_date'):
            vals.update({'to_date': (datetime.strptime(vals.get('valid_from'), '%Y-%m-%d') + relativedelta(months=6)).strftime('%Y-%m-%d')})
        default_code = False
        categ_id = vals.get('product_type')	# get product category
        if vals.get('int_product_number'):
            default_code = vals.get('int_product_number')
            cate_obj = self.env['product.category']
            if default_code[0] == '2':
                c_ids = cate_obj.search([('cat_type', '=', 'injection')])
                if c_ids:
                    categ_id = c_ids[0].id
            elif default_code[0] == '1':
                c_ids = cate_obj.search([('cat_type', '=', 'film')])
                if c_ids:
                    categ_id = c_ids[0].id
	weight=0.0
	if vals.get('weight'):
		weight=vals.get('weight')
		vals.pop('weight')
        pv_id = False
        
        data_obj = self.env['ir.model.data']
        material_id = vals.pop('material_id',False)
        raw_material_type = vals.pop('sub_type_id',False)
        if vals.get('type')=='service':
		mat_str = data_obj.get_object_reference('gt_customer_products','material_type_data8')
		material_id = self.env['product.material.type'].search([('id','=',mat_str[1])])
	elif not material_id and vals.get('type')=='product':
		mat_str = data_obj.get_object_reference('gt_customer_products','material_type_data0')
		material_id = self.env['product.material.type'].search([('id','=',mat_str[1])])
        if default_code or vals.get('product_id'):
            if vals.get('product_id'):
                pv_id = prod_obj.browse(vals.get('product_id'))
                vals.update({'existing_product' : True})
            else:
                p_ids = prod_obj.search([('default_code', '=', default_code)])
                if p_ids:
                    pv_id = p_ids[0]
                    vals.update({'existing_product' : True})
                else:
                    pv_id = prod_obj.create({
				        'name' : vals.get('product_name'),
				        'description_sale' : vals.get('product_description'),
				        'description_sale' : vals.get('product_description'),
				        'categ_id' : categ_id,
				        'external_product_number' : vals.get('ext_product_number'),
				        'type' : vals.get('type'),
				        'default_code' : default_code,
				        'uom_id' : vals.get('uom_id'),
				        'uom_po_id' : vals.get('uom_id'),
					'lowest_price':low_price,		#CH_N010 #CH_N019 change in fields
					'n_product_type': product_type,		#CH_N011 #CH_N019 change in fields
					'n_calculator_id':n_ids,
					'weight':weight,
					'product_material_type':material_id.id,'matstrg':material_id.string,
					'raw_material_type':raw_material_type.id if raw_material_type else False,
                    })
        else:
            pv_id = prod_obj.create({
                'name' : vals.get('product_name'),
                'description_sale' : vals.get('product_description'),
                'categ_id' : categ_id,
                'external_product_number' : vals.get('ext_product_number'),
                'type' : vals.get('type'),
                'default_code' : default_code,
                'uom_id' : vals.get('uom_id'),
                'uom_po_id' : vals.get('uom_id'),
		'lowest_price':low_price,		#CH_N010 #CH_N019 change in fields
		'n_product_type':product_type,		#CH_N011 #CH_N019 change in fields
		'n_calculator_id':n_ids,
		'weight':weight,
		'product_material_type':material_id.id,'matstrg':material_id.string,
		'raw_material_type':raw_material_type.id if raw_material_type else False,
           })
        if vals.get('type_of_packaging') and vals.get('qty_per_package'):
            unit_o = uom_obj.sudo().browse(vals.get('uom_id'))
            p_obj = uom_obj.sudo().browse(vals.get('type_of_packaging'))
            name = str(vals.get('qty_per_package')) + unit_o.name + '/' + p_obj.name
	
            pkg_ids=self.env['product.packaging'].create({'pkgtype':'primary','name':name,'uom_id':vals.get('type_of_packaging'),'qty':str(vals.get('qty_per_package')),'product_tmpl_id':pv_id.product_tmpl_id.id,'unit_id':unit_o.id})
            
            u_ids = uom_obj.sudo().search([('name', '=', name)])
            puom=None
            if u_ids:
                puom = u_ids[0]
            vals.update({'product_id' : pv_id.id,
            		'product_packaging':pkg_ids.id if pkg_ids else False,
			'pkg_editable':True,})
        #CH_N020 update product_id in pricelist_items
        #CH_N024 change code to remove write methods from create
        if vals.get('item_ids'):
        	n_item_ids=vals.get('item_ids')
        	if n_item_ids[0] and isinstance(n_item_ids[0][2], dict):
        		n_item_ids[0][2].update({'product_id': pv_id.id,'product_tmpl_id':pv_id.product_tmpl_id.id})
        		vals.update({'item_ids':n_item_ids})
        
        vals.update({'product_id' : pv_id.id, 'int_product_number' : pv_id.default_code})
        if vals.get('bom_id'):
            bobj = bom_obj.browse(vals.get('bom_id'))
            bobj.write({'product_id': pv_id.id})
        if vals.get('initial_weight'):
        	vals.pop('initial_weight')
        res = super(CustomerProduct, self).create(vals)
        body='<b>Customer Product Create in Pricelist:  </b>'
	body +='<li> Product Name : '+str(res.product_id.name) +'</li>'
        body +='<li>External Number:'+str(res.ext_product_number)+'</li>'
        body +='<li> Packaging : '+str(res.product_packaging.name) +'</li>'
        body +='<li> Qty Per Packaging : '+str(res.qty_per_package) +'</li>'
	body +='<li> Customer Selling Price : '+str(res.avg_price) +'</li>'
	body +='<li> Lowest Selling Price : '+str(res.lowest_price) +'</li>'
	body +='<li> Floor Price: '+str(res.floor_price) +'</li>'
        body +='<li> Validity Period:- '+str(res.valid_from)+" --TO--"+str(res.valid_from) +'</li>'
	body +='<li> Created By  : '+str(res.env.user.name) +'</li>'
	body +='<li> Created Date  : '+str(date.today()) +'</li>'
	#res.pricelist_id.message_post(body=body)
        res.message_post(body=body)
        return res
    
    @api.depends('item_ids', 'item_ids.qty', 'item_ids.min_quantity')
    @api.multi
    def get_line_qty(self):
        for line in self:
            if line.item_ids:
                qty_list =  [l1.qty for l1 in line.item_ids]
                qty_list.sort()
                line.qty = qty_list[-1]
            else:
                line.qty = 1
                
    '''@api.multi
    @api.constrains('avg_price', 'lowest_price', 'floor_price')
    def _check_prices(self):
        for line in self:
            if line.avg_price and line.floor_price and line.avg_price < line.floor_price:
                raise ValidationError('[%s] - Customer Sold Price must be higher than Floor Price '%(line.int_product_number,))
            if line.lowest_price and line.avg_price and line.lowest_price > line.avg_price:
                raise ValidationError('[%s] - Lowest Price must be lower than Customer Sold Price' %(line.int_product_number,))
            if line.lowest_price and line.floor_price and line.lowest_price < line.floor_price:
                raise ValidationError('{} - Lowest Price {}  must be greater than Floor Price {} '.format(line.int_product_number,line.lowest_price,line.floor_price))'''
        
    @api.depends('pricelist_id', 'pricelist_id.currency_id')
    @api.multi
    def get_currency(self):
        for line in self:
            if line.pricelist_id:
                line.currency_id = line.pricelist_id.currency_id.id
                
    @api.multi
    def get_lowest_sold_price(self):
        for line in self:
            if line.product_id:
		##CH_N04 start >>> state in query to get only sale order
		n_company_currency=self.env.user.company_id.id
		self.env.cr.execute("select min(price_unit),p_currency_id from sale_order_line where state in ('sale','done') and product_id = %s group by p_currency_id "% (line.product_id.id, ))
                val = self.env.cr.fetchall()
                if val:
		    if len(val)==1 and val[0][0]==n_company_currency:
                    	n_lowest_price = val[0][0]
		    else:
			n_price_list=[]
			for rec in val:
			        n_price = self.env['res.currency'].browse(rec[1]).compute(rec[0],self.env.user.company_id.currency_id)
				n_price_list.append(n_price)
			n_lowest_price=min(n_price_list)
		    #CH_N019 start add lowset price to product
		    if line.product_id.product_tmpl_id.lowest_price > n_lowest_price:
			line.product_id.product_tmpl_id.lowest_price=n_lowest_price
		    #CH_N019 end
		    line.lowest_price =self.env.user.company_id.currency_id.compute(n_lowest_price,line.pricelist_id.currency_id)
		##CH_N04 end <<<<
                else:
                    line.lowest_price = line.avg_price
            else:
                line.lowest_price = line.avg_price
    
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist',ondelete="cascade")
    item_ids = fields.One2many('product.pricelist.item', 'cus_product_id','Priceline',copy=True)
    customer_id = fields.Many2one('res.partner', string="Customer")
    product_id = fields.Many2one('product.product', string='Product')
    product_tmpl_id = fields.Many2one('product.template',string="Product")
    product_type = fields.Many2one('product.category',string="Product Category")
    uom_id = fields.Many2one('product.uom',related='product_id.uom_id', string="Unit", required=True)
    int_product_number = fields.Char(string='Internal Number')
    ext_product_number = fields.Char('External Number')
    product_name = fields.Char('Name')
    product_description = fields.Char('Description')
    
    currency_id = fields.Many2one('res.currency',compute=get_currency, store=True, string="Currency")
    highest_price = fields.Float(string='Highest Sold Price')
    lowest_price = fields.Float(string='Lowest Selling Price', compute=get_lowest_sold_price)
    floor_price = fields.Float(string="Floor Price")
    avg_price = fields.Float('Customer Selling Price')
    
    type_of_packaging = fields.Many2one('product.uom', string='Types of Packaging')
    qty_per_package = fields.Integer(string='Quantity per packing')
    bom_id = fields.Many2one('mrp.bom', string="BOM")
    existing_product = fields.Boolean(string="Existing Product" , default=True)
    valid_from = fields.Date('Valid From', default=fields.Date.context_today)
    to_date = fields.Date('To', default=fields.Date.context_today)
    
    min_qty = fields.Float('MOQ', digits_compute=dp.get_precision('Product'))
    qty = fields.Float('MOQ', digits_compute=dp.get_precision('Product'), compute=get_line_qty, store=True)
    
    product_packaging = fields.Many2one('product.packaging',string="Packaging")
    pkg_editable = fields.Boolean(string="Packaging Editable",default=False)
#CH_N019 add fields to view data in custom product
    n_product_type =fields.Selection([('new','New Product'),('custom', 'Custom Product'),('film', 'Film Product')], 'Product Entry Type',default='new')
    n_calculator_id = fields.Many2one('pricelist.calculater', string="Price Calculator") 

    qty_available = fields.Float(string="On Hand",related='product_id.qty_available')
    
    '''@api.onchange('avg_price', 'floor_price', 'lowest_price')
    def onchange_prices(self):
        if self.item_ids:
           for line in self.item_ids[0]:#add avg_price value in first item_ids line if
               if line:
                  line.fixed_price=self.avg_price
        if not self.lowest_price and self.avg_price:
            self.lowest_price = self.avg_price
        if self.floor_price and self.avg_price and self.avg_price < self.floor_price:
            raise UserError('Floor Price should be lower then Customer sold Price')
        if self.lowest_price and self.avg_price and self.lowest_price > self.avg_price:
            raise UserError('Lowest Price must be lower than Customer Sold Price')
        if self.lowest_price and self.floor_price and self.lowest_price < self.floor_price:
            raise UserError('Floor Price should be lower then Lowest Price')'''

    @api.onchange('item_ids', 'item_ids.qty')
    def onchange_pricelist_items(self):
        if self.item_ids:
            qty_list = [line.qty or 1 for line in self.item_ids]
            qty_list.sort()
            self.qty = qty_list[-1] or 1

    @api.one
    @api.constrains('valid_from', 'to_date')
    def _check_product_expiry(self):
        if self.valid_from and self.to_date:
            if self.valid_from > self.to_date:
                raise ValidationError('Validity start date must be less than the End Date')
        return True
            
    @api.onchange('valid_from', 'to_date')
    def onchange_validity(self):
        if self.valid_from and self.to_date:
            if self.valid_from > self.to_date:
                raise ValidationError('Validity start date must be less than the End Date')
        if self.valid_from == self.to_date or not self.to_date:
            self.to_date = (datetime.strptime(self.valid_from, '%Y-%m-%d') + relativedelta(months=6)).strftime('%Y-%m-%d')

    @api.multi
    def write(self,vals):
	str1=""
	if vals.get('product_description'):
		str1 += "<li>Product Desc. :- "+str(vals.get('product_description'))+"</li>"
	if vals.get('avg_price'):
		str1 += "<li>Customer Sold Price :- "+str(vals.get('avg_price'))+"</li>"
	if vals.get('min_qty'):
		str1 += "<li>MOQ :- "+str(vals.get('min_qty'))+"</li>"
        if vals.get('ext_product_number'):
                str1 += "<li>External Number :- "+str(vals.get('ext_product_number'))+"</li>"
	#if vals.get('product_packaging'):
		#str1 += "<li>Packaging  :- "+str(vals.get('product_packaging'))+"</li>"
	if vals.get('valid_from') or vals.get('to_from'):
		str1 += "<li>Validity Period :-"+str(vals.get('valid_from'))+ " --To-- " +(str(vals.get('to_from')) if vals.get('to_from') else '')+"</li>" 
	if vals.get('floor_price'):
		str1 += "<li>Floor Price :- "+str(vals.get('floor_price'))+"</li>"
	if str1:
                self.message_post(body=str1)
	return super(CustomerProduct,self).write(vals)  
                           
class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    
    @api.multi
    def write(self,vals):
	str1=""
        
	if vals.get('fixed_price') or vals.get('min_quantity') or vals.get('qty') or vals.get('do_term'):
		str1 += "<li>Fixed Price :- "+(str(vals.get('fixed_price')) if vals.get('fixed_price') else str(self.fixed_price))+"</li>"
		str1 += "<li>Min Qty :-  "+ (str(vals.get('min_quantity')) if vals.get('min_quantity') else str(self.min_quantity))+"</li>"
		str1 += "<li>Max Qty  :-"+ (str(vals.get('qty')) if vals.get('qty') else str(self.qty))+"</li>"
                term=self.env['stock.incoterms'].search([('id','=',vals.get('do_term'))])
		str1 += "<li>Delivery Term  :-"+(str(term.name) if term else str(self.do_term.name))+"</li>"
	if str1:
           self.cus_product_id.message_post(body=str1)
	return super(ProductPricelistItem,self).write(vals)  
    
    @api.multi
    @api.onchange('min_quantity', 'qty')
    def onchange_qty(self):
        if self.qty < self.min_quantity:
            raise UserError('Max Quantity must be greater than Minimum') 
        
    @api.onchange('do_term')
    @api.multi
    def onchange_doterm(self):
    	if self.do_term and self.min_quantity==1 and self.qty==10000:
    		qty=0
    		for line in self:
    			if self.do_term.id==line.do_term.id and qty > line.qty:
				qty=line.qty
		self.min_quantity =qty+1  
		          
    @api.model
    def create(self, vals):
        if vals.get('cus_product_id'):
            cus_product = self.env['customer.product'].browse(vals['cus_product_id'])
            vals.update({'pricelist_id': cus_product.pricelist_id.id,
            		 'currency_id':cus_product.pricelist_id.currency_id.id})
        return super(ProductPricelistItem, self).create(vals)
    
    @api.one
    @api.constrains('qty', 'min_quantity')
    def _check_product_expiry(self):
        if self.qty < self.min_quantity:
            raise ValidationError('Max Quantity must be greater than Minimum')

    @api.one
    @api.constrains('qty', 'min_quantity','do_term','cus_product_id')
    def _check_quantity(self):
    	if self.cus_product_id:
    		for line in self.cus_product_id.item_ids:
    			print "....",line.id,line.qty,line.min_quantity,line.do_term,line.cus_product_id
    			if self.id != line.id:
    				if self.do_term.id == line.do_term.id:
    					if line.min_quantity == self.min_quantity or line.qty == self.qty:
    						raise ValidationError('{},  {} Price for Quantity range {} - {} is already exist.'.format(self.cus_product_id.product_id.name,self.do_term.name,self.min_quantity,self.qty))
					if line.min_quantity <= self.min_quantity and line.qty >= self.min_quantity:
    						raise ValidationError('{},  {} Price for Quantity range {} - {} is Conflecting.'.format(self.cus_product_id.product_id.name,self.do_term.name,self.min_quantity,self.qty))
    					if line.min_quantity <= self.min_quantity and line.qty >= self.min_quantity:
    						raise ValidationError('{},  {} Price for Quantity range {} - {} is Conflecting..'.format(self.cus_product_id,product_id.name,self.do_term.name,self.min_quantity,self.qty))
					if self.qty <= line.qty and self.qty >= line.min_quantity:
						raise ValidationError('{},  {} Price for Quantity range {} - {} is already exist..'.format(self.cus_product_id.product_id.name,self.do_term.name,self.min_quantity,self.qty))
        #if self.qty < self.min_quantity:
    	#raise ValidationError('Max Quantity must be greater than Minimum')

    @api.model
    def get_price(self):
         return self._context.get('highest_price') or 1  
         
    pricelist_id = fields.Many2one('product.pricelist',string='Pricelist')
    cus_product_id = fields.Many2one('customer.product',string='Customer Product',ondelete='cascade')
    min_quantity = fields.Integer('Min. Quantity', default=1)
    currency_id = fields.Many2one('res.currency',string="Currency")
    fixed_price = fields.Float('Price', default=get_price)
    
class ProductPricelist(models.Model):
    _inherit = "product.pricelist"
    
    cus_products = fields.One2many('customer.product', 'pricelist_id' , 'Customer Products')
    
class CrmTeam(models.Model):
    _inherit = 'crm.team'
        
    @api.multi
    def get_expiring_product(self):
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        max_date = (datetime.now() - timedelta(days=7)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        for obj in self:
            products = self.env['customer.product'].search([('to_date', '>', min_date), ('to_date', '<=', max_date)])
            obj.exp_prod = len(products)
    
    @api.multi
    def get_exp_products(self):
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        for obj in self:
            products = self.env['customer.product'].search([('to_date', '<=', min_date)])
            obj.exp_prods = len(products)
    
    @api.multi
    def action_exp_prod(self):
        lead = self[0]
        res = self.env['ir.actions.act_window'].for_xml_id('gt_customer_products', 'action_customer_product_tree_view_expiring')
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        max_date = (datetime.now() - timedelta(days=7)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        prod = self.env['customer.product'].search([('to_date', '>', min_date), ('to_date', '<=', max_date)])
        res['domain'] = "[('id', 'in', %s)]"%(prod and str(tuple(prod.ids)) or '(False,)')
        return res
    
    @api.multi
    def action_expd_prod(self):
        lead = self[0]
        res = self.env['ir.actions.act_window'].for_xml_id('gt_customer_products', 'action_customer_product_tree_view_expired')
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        prod = self.env['customer.product'].search([('to_date', '<=', min_date)])
        res['domain'] = "[('id', 'in', %s)]"%(prod and str(tuple(prod.ids)) or '(False,)')
        return res
    
    exp_prod = fields.Integer('#Expiring Products', compute =get_expiring_product)
    exp_prods = fields.Integer('#Expired Products', compute = get_exp_products)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.onchange('cus_product_line')
    def onchange_cus_product(self):
        if self.cus_product_line:
            self.high_price = self.cus_product_line.highest_price
            self.low_price = self.cus_product_line.lowest_price
            self.avg_price = self.cus_product_line.avg_price
            self.min_qty = self.cus_product_line.min_qty
            
    @api.multi
    @api.depends('pricelist_type', 'price_line_id.qty', 'price_line_id.cus_product_id.min_qty', 'price_calculator_id.moq_length', 'price_line_id', 'price_calculator_id')
    def get_min_qty(self):
        for line in self:
            if line.pricelist_type in ['1','4']:
                cust_product_ids = self.env['customer.product'].search([('pricelist_id.customer','=', line.customer.id), ('product_id','=',line.product_id.id)])
                if cust_product_ids:
                    line.min_qty = cust_product_ids[0].min_qty
            if line.pricelist_type == '2' and line.price_calculator_id:
                line.min_qty = line.price_calculator_id.moq_length
    
    cus_product_line = fields.Many2one('customer.product')
    min_qty = fields.Float('MOQ', compute=get_min_qty, store=True)
    
