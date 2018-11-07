# -*- coding: utf-8 -*-
##############################################################################
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
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
import json
import logging
_logger = logging.getLogger(__name__)

class RawMaterailPricelist(models.Model):
	_name = 'raw.material.pricelist'
	_inherit = ['mail.thread']

	def _get_currency(self):
		return self.env['res.currency'].search([('name','=','USD')]).id
		
    	product_id=fields.Many2one('product.product',"Product",domain=[('product_material_type.string','=','raw'),('sale_ok','=',True)],required="1")
    	product_tmpl_id=fields.Many2one('product.template',related='product_id.product_tmpl_id',store=True)
    	product_uom=fields.Many2one('product.uom',related='product_id.uom_id')
    	stock_qty=fields.Float('On-Hand',compute="_get_onhande_qty")
	base_price=fields.Float('Purchase Cost',default=0.0)
	qty_range_1=fields.Float('<300',default=0.0)
	qty_range_8=fields.Float('301-1000',default=0.0)
	qty_range_9=fields.Float('1001-3000',default=0.0)
	qty_range_2=fields.Float('301-3000',default=0.0)
	qty_range_3=fields.Float('3001-10000',default=0.0)
	qty_range_4=fields.Float('10001-15000',default=0.0)
	qty_range_5=fields.Float('15001 >',default=0.0)
	qty_range_6=fields.Float('Half Truck(15T)',default=0.0)
	qty_range_7=fields.Float('Full Truck(25T)',default=0.0)
	discount=fields.Float('Discount(%)')
	currency_id = fields.Many2one('res.currency', string="Currency",default=_get_currency)
	msq=fields.Float('MSQ')
	change_data=fields.Boolean('Change')
	active = fields.Boolean('Active',default=True)
	
	_sql_constraints = [('unique_product_constra', 'unique(product_id)', 'You Can not Add same product Multiple Times') ]
	 
    	@api.multi
	def _get_onhande_qty(self):
    		for res in self:
			if res.product_id:
	    			quants=self.env['stock.quant'].sudo().search([('product_id','=',res.product_id.id),
    								('location_id.actual_location','=',True)])
				res.stock_qty = sum([q.qty for q in quants])

	@api.multi
	def action_open_purchase_line(self):
		tree = self.env.ref('purchase.purchase_order_line_tree', False)
		return {'name':'Purchase Details',
		        'type': 'ir.actions.act_window',
		        'view_type': 'form',
		        'view_mode': 'tree,',
		        'res_model': 'purchase.order.line',
		        'views': [(tree.id, 'tree')],
		        'view_id': tree.id,
		        'target': 'new',
		        'domain':[('product_id','=',self.product_id.id)],
			}

	@api.multi
	def change_currency(self):
		tree = self.env.ref('api_raw_material.view_change_rm_currency', False)
		context=self._context.copy()
		context.update({'default_rm_pricelist_id':self.id})
		return {'name':'Currency Change',
		        'type': 'ir.actions.act_window',
		        'view_type': 'form',
		        'view_mode': 'form,',
		        'res_model': 'change.pricelist.currency',
		        'views': [(tree.id, 'form')],
		        'view_id': tree.id,
		        'target': 'new',
		        'context':context,
			}

	
	@api.multi
	def write(self,vals):
		body = '<b> Values updated</b> <ul>'
		vals.update({'change_data':True})
		if vals.get('product_id',False):
			if self.search([('product_id','=',vals['product_id']),('active','in',(True,False))]):
				raise UserError("You Can not Add same product Multiple Times")
			product_id= self.env['product.product'].search([('id','=',vals.get('product_id'))])
			body += '<li>Product Name : [{}]{} </li>'.format(product_id.default_code,product_id.name)
		if vals.get('currency_id',False):
			currency_id= self.env['res.currency'].search([('id','=',vals.get('currency_id'))])
			body += '<li>Currency :{} </li>'.format(currency_id.name)
		if vals.get('base_price',False):
			body += '<li>Purchase Price : {} </li>'.format(vals.get('base_price'))
		if vals.get('qty_range_1',False):
			body += '<li>Bellow 300 : {} </li>'.format(vals.get('qty_range_1'))
		if vals.get('qty_range_2',False):
			body += '<li>301-3000 : {} </li>'.format(vals.get('qty_range_2'))
		if vals.get('qty_range_3',False):
			body += '<li>3001-10000 : {} </li>'.format(vals.get('qty_range_3'))
		if vals.get('qty_range_4',False):
			body += '<li>10001-15000 : {} </li>'.format(vals.get('qty_range_4'))
		if vals.get('qty_range_5',False):
			body += '<li>15001 above : {} </li>'.format(vals.get('qty_range_5'))	
		if vals.get('qty_range_6',False):
			body += '<li>Half Truck(15T) : {} </li>'.format(vals.get('qty_range_6'))	
		if vals.get('qty_range_7',False):
			body += '<li>Full Truck(25T) : {} </li>'.format(vals.get('qty_range_7'))	
		if vals.get('qty_range_8',False):
			body += '<li>Full Truck(25T) : {} </li>'.format(vals.get('qty_range_8'))	
		if vals.get('qty_range_9',False):
			body += '<li>Full Truck(25T) : {} </li>'.format(vals.get('qty_range_9'))	
		if vals.get('discount',False):
			body += '<li>Discount(%) : {} </li>'.format(vals.get('discount'))
		if vals.get('msq',False):
			body += '<li>MSQ(%) : {} </li>'.format(vals.get('msq'))	
		if 'active' in vals.keys():
			body += '<li>Active : {} </li>'.format(vals.get('active'))	
		rec = super(RawMaterailPricelist,self).write(vals)
		self.message_post(body)
		return rec

	@api.model
	def create(self,vals):
		if vals.get('product_id'):
			if self.search([('product_id','=',vals['product_id']),('active','in',(True,False))]):
				raise UserError("You Can not Add same product Multiple Times")
		vals.update({'change_data':True})
		return super(RawMaterailPricelist,self).create(vals)
		
class ProductTemplate(models.Model):
    _inherit='product.template'

    recp_pricelist = fields.One2many('raw.material.pricelist','product_tmpl_id', string='Material Pricelist')
    
class SaleOrderLine(models.Model):
    _inherit='sale.order.line'
    
    recp_pricelist_ids = fields.Many2many('raw.material.pricelist.sale','sale_order_line_material_pricelist','sale_line_id',
    					'raw_marerial_id',string='Material Pricelist',cascade=True) # for spot
    recp_pricelist_book = fields.Many2many('raw.material.pricelist.sale','sale_order_line_material_pricelist','sale_line_id',
    					'raw_marerial_id',string='Material Pricelist',cascade=True) # for Book
    buying_type = fields.Selection([('book', 'Booking'),('spot', 'On The Spot')],string="Buying Type",default='spot')
    #product_type = fields.Many2one('product.material.type',string="Product Type",default='raw')
    
    @api.onchange('product_id','buying_type','fixed_price')
    def onchange_product_id(self):
	prlist_id = self.env['raw.material.pricelist'].search([('product_id', '=', self.product_id.id)])
	if self.product_id and prlist_id and self.order_id.is_reception:
		if not self.order_id.n_quotation_currency_id:
			raise UserError("Please Select Quotation Currency")
		base_price = prlist_id.currency_id.compute(prlist_id.base_price,self.order_id.n_quotation_currency_id)
		self.final_price = base_price if not self.fixed_price else self.fixed_price
		self.price_unit = base_price if not self.fixed_price else self.fixed_price
		 
		vals = {'pricelist_id':prlist_id.id,'product_id':self.product_id.id,
			'base_price':base_price,
			'qty_range_1':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_1,self.order_id.n_quotation_currency_id),
			'qty_range_2':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_2,self.order_id.n_quotation_currency_id),
			'qty_range_3':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_3,self.order_id.n_quotation_currency_id),
			'qty_range_4':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_4,self.order_id.n_quotation_currency_id),
			'qty_range_5':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_5,self.order_id.n_quotation_currency_id),
			'qty_range_6':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_6,self.order_id.n_quotation_currency_id),
			'qty_range_7':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_7,self.order_id.n_quotation_currency_id),
			'qty_range_8':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_8,self.order_id.n_quotation_currency_id),
			'qty_range_9':prlist_id.currency_id.compute(prlist_id.base_price + prlist_id.qty_range_9,self.order_id.n_quotation_currency_id),
			'stock_qty':prlist_id.stock_qty}
			      
		if self.buying_type == 'spot':
			if not self.product_uom_qty:
				self.product_uom_qty = 300 
			if not self.recp_pricelist_ids or type(self.recp_pricelist_ids[0].id)!=int:
				self.recp_pricelist_ids = [(0,0,vals)]
			else:
				new_id = self.recp_pricelist_ids[0].id
				self.recp_pricelist_ids = [(1,new_id,vals)]
	        elif self.buying_type == 'book':
	        	if not self.product_uom_qty:
        			self.product_uom_qty = 15000
			if not self.recp_pricelist_book or type(self.recp_pricelist_book[0].id)!=int:
				self.recp_pricelist_book = [(0,0,vals)]
			else:
				new_id = self.recp_pricelist_book[0].id
				self.recp_pricelist_book = [(1,new_id,vals)]
				
	elif self.product_id and not prlist_id and self.order_id.is_reception:
		if self.recp_pricelist_ids:
			self.recp_pricelist_ids = []
		if self.recp_pricelist_boo:
			self.recp_pricelist_book = []

    @api.onchange('final_price')
    def get_approval_data(self):
    	for line in self:
    		if line.order_id.is_reception:
    			if self.final_price < self.price_discount: #and self.n_show_approval_bool==False:
    				line.price_m = True
			else:
				line.price_unit = line.final_price
				line.price_m = False
			
    @api.onchange('s_discount')
    def get_discount_approval_data(self):
    	for line in self:
    		if line.order_id.is_reception:
			if self.max_discount < self.s_discount and self.max_discount_allow < self.s_discount:
				line.dis_m = True
				line.approve_m = False
			else:
				line.dis_m = False
				line.approve_m = True

    @api.multi
    def write(self,vals):
    	res = super(SaleOrderLine,self).write(vals)
	for  rec in self:
		if rec.order_id.is_reception:
			if rec.buying_type =='book' and rec.product_uom_qty <15000:
				raise UserError('Please Enter Minimum quantity in Case of Booking the order')
			if vals.get('s_discount',False) and vals.get('s_discount') > rec.max_discount:
				rec.send_discount_mail()
			product_qty = self.env['product.uom']._compute_qty_obj(rec.product_uom,rec.product_uom_qty, rec.product_id.uom_id)
            		pricelist_id = self.env['raw.material.pricelist'].search([('product_id', '=', rec.product_id.id)])
            		if pricelist_id.msq > (pricelist_id.stock_qty-product_qty) and rec.state in ('draft','sent') :
            			raise UserError("This [%s]%s couldn't be sold as it's current stock is %.2f %s.\n After selling %.2f %s the remaining stock will be %.2f %s that is lower than MSQ of %.2f %s. You can maximum sell upto %.2f %s "%(rec.product_id.default_code,rec.product_id.name,pricelist_id.stock_qty, rec.product_uom.name,rec.product_uom_qty, rec.product_id.uom_id.name, pricelist_id.stock_qty-product_qty, rec.product_id.uom_id.name,pricelist_id.msq, rec.product_uom.name,pricelist_id.stock_qty-pricelist_id.msq, rec.product_uom.name))
	return res

    @api.model
    def create(self,vals):
    	rec = super(SaleOrderLine,self).create(vals)
	if rec.order_id.is_reception:
		if rec.buying_type =='book' and rec.product_uom_qty <15000:
			raise UserError('Please Enter Minimum quantity in Case of Booking the order')
		if vals.get('s_discount',False) and vals.get('s_discount') > rec.max_discount:
			rec.send_discount_mail()
		product_qty = self.env['product.uom']._compute_qty_obj(rec.product_uom,rec.product_uom_qty, rec.product_id.uom_id)
            	pricelist_id = self.env['raw.material.pricelist'].search([('product_id', '=', rec.product_id.id)])
            	if pricelist_id.msq > (pricelist_id.stock_qty-product_qty) and rec.state in ('draft','sent') :
            		raise UserError("This [%s]%s couldn't be sold as it's current stock is %.2f %s.\n After selling %.2f %s the remaining stock will be %.2f %s that is lower than MSQ of %.2f %s. You can maximum sell upto %.2f %s "%(rec.product_id.default_code,rec.product_id.name,pricelist_id.stock_qty, rec.product_uom.name,rec.product_uom_qty, rec.product_id.uom_id.name, pricelist_id.stock_qty-product_qty, rec.product_id.uom_id.name,pricelist_id.msq, rec.product_uom.name,pricelist_id.stock_qty-pricelist_id.msq, rec.product_uom.name))
                    
	return rec

    @api.multi
    def send_discount_mail(self):
    	'''send mail to manager in case of sale reception'''
	#if vals.get('approve_m') != True and obj.product_id.name != 'Deposit Product':
	for line in self:
		temp_id = self.env.ref('gt_sale_pricelist.email_template_approve_req')
		if temp_id:
		        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		            # the parameters to encode for the query and fragment part of url
		        query = {'db': self._cr.dbname}
		        form_view = self.env.ref('gt_order_mgnt.view_sale_reception_form_api',False)
		        fragment = {
		            'model': 'sale.order',
		            'view_type': 'form',
		            'views' : [(form_view.id,'form')],
	    		    'view_id': form_view.id,
		            'id': line.order_id.id,
		        }
		        url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
		        text_link = _("""<a href="%s">%s</a> """) % (url,line.order_id.name)
		        name = ''
		        if line.product_id:
		            name = ' [{}]{}'.format(line.product_id.default_code,line.product_id.name)
		        if not name:
		           name = line.name or line.name1
		        body_html1 = """<div>
		                 <p> <strong>Discount Requested </strong></p>
		                       <p>Dear %s,<br/>
		                           <b>%s </b>requested for Discount on  <b> %s </b> for  <br/>
		                          <b>Customer Name </b>:%s
		                          <br/>
		                       </p>
		               </div>"""%(line.order_id.team_id.user_id.name or '',line.order_id.user_id.name or '', text_link, line.order_id.partner_id.name )
		        body_html1 +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial; text-align:center;'><tr><th>Product Name </th><th> Suggested Price</th><th>Requested Price </th></tr>"                  
		        for rec in line.order_id.order_line:
		            if rec.approve_m != True :
		                     body_html1 +="<tr><td>(%s)%s</td><td>%s %s</td><td>%s(%s %s)</td></tr>"%(rec.product_id.default_code,rec.product_id.name, rec.fixed_price,line.currency_id.symbol,str(line.s_discount) + '%' if line.s_discount else '' ,rec.s_price if rec.s_price else rec.final_price , rec.currency_id.symbol) 
		        body_html1 +="</table>"
		        body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html1, 'sale.order',line.order_id.id, context=self._context)
		        temp_id.write({'body_html': body_html})
		        temp_id.send_mail(line.order_id.id)
		        line.approval_status='waiting_approval'

    @api.multi
    def action_approve(self):
    	for line in self:
		if line.order_id.is_reception:
			rel=sub=''
           		if self._context.get('approve'):
               			sub +=str(line.order_id.user_id.name)+' Discount Request Approved  ' +str(line.order_partner_id.name) +' '+ str(line.order_id.name)
               			rel +='Approved'
               			line.write({'final_price': line.s_price,'price_discount': line.s_price,
               					'n_show_approval_bool':True,'price_unit': line.s_price })
				line.write({'approve_m': True, 'approval_status':'approved','not_update': False, 'price_m' : False, 's_discount' : 0, 'max_discount' : line.s_discount, 'dis_m': False})
            		if self._context.get('reject'):
               			rel +='Rejected'
               			sub +=str(line.order_id.user_id.name)+' Discount Request Rejected  ' +str(line.order_partner_id.name)+'  '+str(line.order_id.name)
				line.write({'approve_m': True, 'approval_status':'normal','not_update': False, 'price_m' : False, 's_discount' : 0, 'dis_m': False})
            			line.write({'n_show_approval_bool':True})
                    
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
				  	<b> %s </b> %s your discount request for quotation: <b> %s </b> for <b> %s </b><br></br>
					  <b>Customer Name :%s</b>
				    </p>
				</div>"""% (rel,line.order_id.user_id.name or '', line.order_id.team_id.user_id.name or '', rel,text_link, name, line.order_id.partner_id.name)
				body_html +='<li>Remark:'+str(line.discount_remark)
				body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',line.order_id.id, context=self._context)
				temp_id.write({'body_html': body_html,'subject':sub})
				temp_id.send_mail(line.order_id.id)
		else:
			return super(SaleOrderLine,self).action_approve()

    @api.multi
    @api.depends('fixed_price', 'max_discount', 'calc_unit', 'calc_price_per_kg', 'calc_price_per_pcs','s_discount','price_line_id', 'req_discount_type', 'p_currency_id', 's_currency_id')
    def get_price_discount(self):
	'''Inherite this method to update functionality '''
	for line in self:
		if line.order_id.is_reception:
			line.req_discount_type = 'per'
                    	price = line.fixed_price - (line.fixed_price/100)* line.s_discount
                    	line.price_discount = line.fixed_price - (line.fixed_price/100) * line.max_discount
            		line.update({'s_price': price})
		else:
			super(SaleOrderLine,self).get_price_discount()


    @api.multi
    @api.depends('price_line_id','product_uom_qty','price_calculator_id', 'product_id', 'p_currency_id', 's_currency_id','buying_type')
    def get_default_price_cur(self):
        for line in self:
		if line.order_id.is_reception and line.product_id:
			pricelist_id = self.env['raw.material.pricelist'].search([('product_id', '=', line.product_id.id)])
			
			if pricelist_id:
				new_price = pricelist_id.base_price
				if line.product_uom_qty and line.buying_type =='book':
					if line.product_uom_qty >= 15000 and line.product_uom_qty <25000:
						new_price += pricelist_id.qty_range_6
					if line.product_uom_qty > 300 and line.product_uom_qty <=1000:
						new_price += pricelist_id.qty_range_8
					if line.product_uom_qty > 1000 and line.product_uom_qty <=3000:
						new_price += pricelist_id.qty_range_9
					elif line.product_uom_qty >= 25000:
						new_price += pricelist_id.qty_range_7
				elif line.product_uom_qty and line.buying_type =='spot':
					if line.product_uom_qty  <=300:
						new_price += pricelist_id.qty_range_1
					elif line.product_uom_qty > 300 and line.product_uom_qty <=3000:
						new_price += pricelist_id.qty_range_2
					elif line.product_uom_qty > 3000 and line.product_uom_qty <=10000:
						new_price += pricelist_id.qty_range_3
					elif line.product_uom_qty > 10000 and line.product_uom_qty <=15000:
						new_price += pricelist_id.qty_range_4
					elif line.product_uom_qty > 15000:
						new_price += pricelist_id.qty_range_5
					elif line.product_uom_qty > 300 and line.product_uom_qty <=1000:
						new_price += pricelist_id.qty_range_8
					elif line.product_uom_qty > 1000 and line.product_uom_qty <=3000:
						new_price += pricelist_id.qty_range_9
				line.fixed_price = pricelist_id.currency_id.compute(new_price,line.order_id.n_quotation_currency_id)
                else:
			super(SaleOrderLine,self).get_default_price_cur()


    @api.multi
    @api.depends('price_line_id','price_calculator_id', 'price_calculator_id.max_discount','product_id')
    def get_discount_per(self):
        for line in self:
            if line.order_id.is_reception and line.product_id:
            	pricelist_id = self.env['raw.material.pricelist'].search([('product_id', '=', line.product_id.id)])
                line.max_discount_allow = pricelist_id.discount
            else:
            	super(SaleOrderLine,self).get_discount_per()

    fixed_price = fields.Float('Suggested Price', compute=get_default_price_cur, digits=dp.get_precision('Payment Term'))
    s_price = fields.Float('Price After Requested Discount', digits=dp.get_precision('Payment Term'),
    			 compute=get_price_discount, multi=True, store=True)
    price_discount = fields.Float('Price After Discount', digits=dp.get_precision('Payment Term'),
    			 compute=get_price_discount, multi=True, store=True)
    max_discount_allow = fields.Float('Max Discount Allowed(%)', dp.get_precision('Product'), compute=get_discount_per,
                                store=True)

    @api.onchange('product_uom_qty')
    def reception_onchange_product_id_check_availability(self):
        if self.product_id.type == 'product' and self.order_id.is_reception:
            product_qty = self.env['product.uom']._compute_qty_obj(self.product_uom, self.product_uom_qty, self.product_id.uom_id)
            pricelist_id = self.env['raw.material.pricelist'].search([('product_id', '=', self.product_id.id)])
            if pricelist_id.msq and pricelist_id.msq >= (pricelist_id.stock_qty-product_qty):
            	warning_mess = {
                        'title': _('Not enough inventory!'),
                        'message' : _("This [%s]%s couldn't be sold as it's current stock is %.2f %s.\n After selling %.2f %s the remaining stock will be %.2f %s that is lower than MSQ of %.2f %s. You can maximum sell upto %.2f %s ") % \
                            (self.product_id.default_code,self.product_id.name,pricelist_id.stock_qty, self.product_uom.name,rec.product_uom_qty, self.product_id.uom_id.name, pricelist_id.stock_qty-product_qty, self.product_id.uom_id.name,pricelist_id.msq, self.product_uom.name,pricelist_id.stock_qty-pricelist_id.msq, self.product_uom.name)
                    }
           	return {'warning': warning_mess}
        
	
class RawMaterailPricelistSale(models.Model):
	#Show data in sale order line after calculating price on condition
	_name = 'raw.material.pricelist.sale'

 	pricelist_id =fields.Many2one('raw.material.pricelist',"Pricelist")
    	product_id =fields.Many2one('product.product',"Product")
    	product_tmpl_id =fields.Many2one('product.template',related='product_id.product_tmpl_id')
    	product_uom =fields.Many2one('product.uom',related='product_id.uom_id')
    	stock_qty =fields.Float('On-Hand',compute="_get_onhande_qty")
	base_price =fields.Float('Purchase Cost(1Kg)')
	qty_range_1 =fields.Float('Qty Till 300')
	qty_range_2 =fields.Float('Qty 301_1000')
	qty_range_3 =fields.Float('Qty 3001_10000')
	qty_range_4 =fields.Float('Qty 10001_15000')
	qty_range_5 =fields.Float('Qty 15001')
	qty_range_6 =fields.Float('Half Truck(15T)')
	qty_range_7 =fields.Float('Full Truck(25T)')
	qty_range_8 =fields.Float('Qty 1001_2000')
	qty_range_9 =fields.Float('Qty 2001-3000')
	currency_id =fields.Many2one('res.currency',related='pricelist_id.currency_id')
	
    	@api.multi
	def _get_onhande_qty(self):
    		for res in self:
    		    if res.product_id:
	    		quants=self.env['stock.quant'].sudo().search([('product_id','=',res.product_id.id),
    								('location_id.actual_location','=',True)])
			res.stock_qty = sum([q.qty for q in quants])

class rawMaterilaPriceUpdate(models.Model):
	#Show data in sale order line after calculating price on condition
	_name = 'raw.material.price.update'

 	pricelist_id=fields.Many2many('raw.material.pricelist','raw_materila_bilk_rel','bulk_id','pricelist_id',"Pricelist")
    	product_id=fields.Many2many('product.product','product_raw_material_bulk_rel','materila_id','product_id',"Products")
	base_price=fields.Float('Purchase Cost(1Kg)')
	qty_range_1=fields.Float('Qty Till 300')
	qty_range_2=fields.Float('Qty 301_1000')
	qty_range_8=fields.Float('Qty 1001_2000')
	qty_range_9=fields.Float('Qty 2001-3000')
	qty_range_3=fields.Float('Qty 3001_10000')
	qty_range_4=fields.Float('Qty 10001_15000')
	qty_range_5=fields.Float('Qty 15001')
	qty_range_6=fields.Float('Half Truck(15T)')
	qty_range_7=fields.Float('Full Truck(25T)')

	@api.multi
	def update_price(self):
		pass
		

