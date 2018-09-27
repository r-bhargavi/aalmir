# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from openerp import fields
from urlparse import urljoin
from urllib import urlencode
import openerp.addons.decimal_precision as dp
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta
import logging
import math
from openerp.exceptions import UserError
import sys
_logger = logging.getLogger(__name__)
import os

class stockLocation(models.Model):
	_inherit = "stock.location"

	pre_ck = fields.Boolean('IN-PUT Location',help="by checking this, Current location is refered as IN-PUT Location . It is used to store product in Stock in ROW,Columns and Depth. It shoud be only one location per warehouse")
	actual_location = fields.Boolean("Is Store Location",help='If check this then the Current Location is used for store the products in Row,Columns,Depth', default=False)
	
	location_view=fields.One2many('stock.location.view','location_id','Location View')
	storage_locations = fields.Html('Location View',compute="_create_html_view")
	location_image = fields.Binary(string='Location Image')
	
	@api.multi
	def _create_html_view(self):
		for rec in self:
			pass

	@api.model
	def create(self,vals):
		if vals.get('location_id'):
			location_id=self.search([('id','=',vals.get('location_id'))])
			if location_id.actual_location:
				vals.update({'actual_location':True})
		res = super(stockLocation,self).create(vals)
		self.create_default_location_view()
		return res
	
	@api.multi
	def create_default_location_view(self):
		for res in self:
			if res.actual_location:
				location_view=self.env['stock.location.view']
				series=self.env['location.series.name'].search([('str_id','=','ACL')],limit=1,order="id")
				if not any(i.location_type for i in res.location_view if i.location_type=='transit_in'):
					location_view.create({'name':'TRANSIT - IN','location_type':'transit_in',
						'location_id':res.id,'row':1,'column':1,'depth':1,
						'row_name':series.id,'column_name':series.id,'depth_name':series.id,
						'r_series':'I','c_series':'I','d_series':'I',
						'storage_capacity':1000000,
						'product_type':'multi'})
				if not any(i.location_type for i in res.location_view if i.location_type=='transit_out'):
					location_view.create({'name':'TRANSIT - OUT','location_type':'transit_out',
						'location_id':res.id,'row':1,'column':1,'depth':1,
						'row_name':series.id,'column_name':series.id,'depth_name':series.id,
						'r_series':'O','c_series':'O','d_series':'O',
						'storage_capacity':1000000,
						'product_type':'multi'})
		return True
		
		
	@api.multi
	def write(self,vals):
		if vals.get('location_id') and self.location_id.actual_location:
			location_id=self.search([('id','=',vals.get('location_id'))])
			if location_id.actual_location:
				vals.update({'actual_location':True})
			else:
				_logger.error("Your Previous Location is marked as Storage Location,You must select another Storage Location")
	    			raise UserError("Your Previous Location is marked as Storage Location,\nYou must select another Storage Location as Parent Location")
    		if vals.get('location_id')==False and self.location_id.actual_location:
			_logger.error("Your Previous Location is marked as Storage Location,So you can not set Parent Location blank,You must select another Storage Location")
    			raise UserError("Your Previous Location is marked as Storage Location,\nSo you can not set Parent Location blank,\nYou must select another Storage Location")
		self.create_default_location_view()
		return super(stockLocation,self).write(vals)
	
	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
        	if self._context.get('production_loc'):
			if self._context.get('sale_id'):
				sale=self.env['sale.order'].search([('id','=',self._context.get('sale_id'))])
				if sale and sale.warehouse_id:
					args.extend([('id','in',[sale.warehouse_id.wh_input_stock_loc_id.id])])
		return super(stockLocation,self).name_search(name, args, operator=operator, limit=limit)
        
class stockLocationview(models.Model):
	_name = "stock.location.view"

	@api.model
    	def default_get(self, fields):
		res = super(stockLocationview,self).default_get(fields)
		series=self.env['location.series.name']
		active_id = self._context.get('active_id')
		if active_id:
		    res = {'location_id': active_id}
	    	uom_id=self.env['product.uom'].search([('unit_type.string','=','store')],limit=1,order="id")
	    	if uom_id:
	    		res.update({'uom_id':uom_id.id})
    		row=series.search([('str_id','=','NUM')],limit=1,order="id")
    		if row:
    			res.update({'row_name':row.id})
    		column=series.search([('str_id','=','ROM')],limit=1,order="id")
		if column:
    			res.update({'column_name':column.id})
    		depth=series.search([('str_id','=','ACL')],limit=1,order="id")
		if depth:
    			res.update({'depth_name':depth.id})
		return res
        
        location_type = fields.Selection([('store','Physical Location'),('transit_in','Transit-IN'),
        				  ('transit_out','Transit-OUT')],'Location Type',default='store')
        				  
	name=fields.Char('Name',required=1)
	location_id=fields.Many2one('stock.location','Location Name',ondelete='cascade')
	row = fields.Integer('No of Row(X)')
	row_name = fields.Many2one("location.series.name","Row Series")
	r_series=fields.Char('Row Start',help="Row Series Start from, if not then default according to type of series")
	r_str_id=fields.Char('R String',related="row_name.str_id",)
	column = fields.Integer('No of Column(Y)')
	column_name = fields.Many2one("location.series.name","Column Series")
	c_series=fields.Char('Column Start',help="Colulmn Series Start from, if not then default according to type of series")
	c_str_id=fields.Char('C String',related="column_name.str_id",)
	depth = fields.Integer('No of Depth(Z)')
	depth_name = fields.Many2one("location.series.name","Depth Series")
	d_series=fields.Char('Depth From',help="Depth Series Start from, if not then default according to type of series")
	d_str_id=fields.Char('D String',related="depth_name.str_id",)
	readonly_bool = fields.Selection([('row','Row'),('rc','Row Column'),('rcd','Row Column Depth')],"Series bool")
	storage_capacity = fields.Integer('Capacity',help="Sotrage capicity of each Cell , In Pallets.",default=1)
	uom_id = fields.Many2one('product.uom',"Unit")

	product_type = fields.Selection([('single','Single Product'),('multi','Multi Product')],'Product Type')
	storage_locations = fields.Html('Location View',compute="_create_html_view")
	dimentional_view = fields.Char('3-D view')
	company_id = fields.Many2one('res.company', string='Company', required=True,
        	default=lambda self: self.env['res.company']._company_default_get('stock.location.view'))
        	
	@api.multi
	@api.onchange('row_name')
	def r_series_start(self):
		if self.row_name:
			if self.row_name.str_id.upper()=='ASL':
				self.r_series='a'
			elif self.row_name.str_id.upper()=='ACL':
				self.r_series='A'
			elif self.row_name.str_id.upper()=='NUM':
				self.r_series='1'
			elif self.row_name.str_id.upper()=='ROM':
				self.r_series='i'
	@api.multi
	@api.onchange('column_name')
	def c_series_start(self):
		if self.column_name:
			if self.column_name.str_id.upper()=='ASL':
				self.c_series='a'
			elif self.column_name.str_id.upper()=='ACL':
				self.c_series='A'
			elif self.column_name.str_id.upper()=='NUM':
				self.c_series='1'
			elif self.column_name.str_id.upper()=='ROM':
				self.c_series='i'
	@api.multi			
	@api.onchange('depth_name')
	def d_series_start(self):
		if self.depth_name:
			if self.depth_name.str_id.upper()=='ASL':
				self.d_series='a'
			elif self.depth_name.str_id.upper()=='ACL':
				self.d_series='A'
			elif self.depth_name.str_id.upper()=='NUM':
				self.d_series='1'
			elif self.depth_name.str_id.upper()=='ROM':
				self.d_series='i'
				
	@api.model
	def create(self,vals):
		try:
			row=column=depth=False
			series=self.env['location.series.name']
			if vals.get('location_type') == 'transit_in':
				if self.search([('location_id','=',vals['location_id']), \
		    				('location_type','=','transit_in')]):
					raise ValueError("API-EXCEPTION..Transit-IN area should be only one per Location Warehouse")
	    		if vals.get('location_type') == 'transit_out':
				if self.search([('location_id','=',vals['location_id']), \
		    				('location_type','=','transit_out')]):
					raise ValueError("API-EXCEPTION..Transit-IN area should be only one per Location Warehouse")
			    		 
			if vals.get('row_name'):
				row=series.search([('id','=',vals.get('row_name'))])
				if row.str_id in ('ASL','ACL'):
					if vals.get('row') > 26 :
						raise ValueError("Please Enter value less than 26 for Alphabetic series Row")
				
					if vals.get('r_series'):
						if row.str_id =='ASL':
							if ord(vals.get('r_series')) not in range(97,123):
								raise ValueError("Please Enter value in a..z for Small Alphabetic series")
							if (ord(vals.get('r_series'))+vals.get('row')) > 123:
								raise ValueError("Please Enter value less than {} for Alphabetic series Row you series is going beyond The Small Alphabetic Range ".format(vals.get('row')))
								
						elif row.str_id=='ACL':
							if ord(vals.get('r_series')) not in range(65,91):
								raise ValueError("Please Enter value in A..Z for Capital Alphabetic series")
								
							if (ord(vals.get('r_series'))+vals.get('row')) > 91:
								raise ValueError("Please Enter value less than {} for Alphabetic series Row you series is going beyond The Capital Alphabetic Range ".format(vals.get('row')))
								
					elif row.str_id =='ASL':
						vals.update({'r_series':'a'})
					elif row.str_id =='ACL':
						vals.update({'r_series':'A'})
						
				elif row.str_id=='NUM':
					if vals.get('r_series'):
						if not vals.get('r_series').isdigit():
							raise ValueError("Please Enter value in numeric value for Number series")
					else:
						vals.update({'r_series':'0'})
				elif row.str_id=='ROM':
					vals.update({'r_series':'i'})
						
			if vals.get('column_name'):
				column=series.search([('id','=',vals.get('column_name'))])
				if column.str_id in ('ASL','ACL'):
					if vals.get('column') > 26 :
						raise ValueError("Please Enter value less than 26 for Alphabetic series Column")
					if vals.get('c_series'):
						if column.str_id =='ASL':
							if ord(vals.get('c_series')) not in range(97,123):
								raise ValueError("Please Enter value in a..z for Small Alphabetic Column series")
							if (ord(vals.get('c_series'))+vals.get('column')) > 123:
								raise ValueError("Please Enter value less than {} for Alphabetic series Column you series is going beyond The Small Alphabetic Range ".format(vals.get('column')))
								
						elif column.str_id=='ACL':
							if ord(vals.get('c_series')) not in range(65,91):
								raise ValueError("Please Enter value in A..Z for Capital Alphabetic Column series")
							if (ord(vals.get('c_series'))+vals.get('column')) > 91:
								raise ValueError("Please Enter value less than {} for Alphabetic series Column you series is going beyond The Capital Alphabetic Range ".format(vals.get('column')))
								
					elif column.str_id =='ASL':
						vals.update({'c_series':'a'})
					elif column.str_id =='ACL':
						vals.update({'c_series':'A'})
						
				elif column.str_id=='NUM':
					if vals.get('c_series'):
						if not vals.get('c_series').isdigit():
							raise ValueError("Please Enter value in numeric value for Number series")
					else:
						vals.update({'c_series':'0'})
				elif column.str_id=='ROM':
					vals.update({'c_series':'i'})
				
			if vals.get('depth_name'):
				depth=series.search([('id','=',vals.get('depth_name'))])
				if depth.str_id in ('ASL','ACL'):
					if vals.get('depth') > 26 :
						raise ValueError("Please Enter value less than 26 for Alphabetic series Depth")
					if vals.get('d_series'):
						if depth.str_id =='ASL':
							if ord(vals.get('d_series')) not in range(97,123):
								raise ValueError("Please Enter value in a..z for Small Alphabetic Depth series")
								
							if (ord(vals.get('d_series'))+vals.get('depth')) > 123:
								raise ValueError("Please Enter value less than {} for Alphabetic series Depth you series is going beyond The Small Alphabetic Range ".format(vals.get('depth')))
								
						elif depth.str_id=='ACL':
							if ord(vals.get('d_series')) not in range(65,91):
								raise ValueError("Please Enter value in A..Z for Capital Alphabetic Depth series")
							if (ord(vals.get('d_series'))+vals.get('depth')) > 91:
								raise ValueError("Please Enter value less than {} for Alphabetic series Depth you series is going beyond The Capital Alphabetic Range ".format(vals.get('depth')))
								
					elif depth.str_id =='ASL':
						vals.update({'d_series':'a'})
					elif depth.str_id =='ACL':
						vals.update({'d_series':'A'})
						
				elif depth.str_id=='NUM':
					if vals.get('d_series'):
						if not vals.get('d_series').isdigit():
							raise ValueError("Please Enter value in numeric value for Number series")
							
					else:
						vals.update({'d_series':'0'})
				elif depth.str_id=='ROM':
					vals.update({'d_series':'i'})
			if vals['location_type'] =='store':
				if row.str_id ==column.str_id or column.str_id == depth.str_id or depth.str_id == row.str_id:
					raise ValueError('Please select difference series for Storage Name')
					
			ids=super(stockLocationview, self).create(vals)
			ids.calculate_structure()
			return ids
		except Exception as err:
    			exc_type, exc_obj, exc_tb = sys.exc_info()
    			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	    		_logger.error("API-EXCEPTION..Exception in Create Storage Location {} {} {}".format(err,fname,exc_tb.tb_lineno))
	    		raise UserError("API-EXCEPTION..Exception in Create Storage Location {}".format(err))

	@api.multi
	def write(self,vals):
		print ".-.-------------.........",vals
		super(stockLocationview, self).write(vals)
		print "------"
		if not vals.get('readonly_bool'):
			print "llllllllllllllllll------"
			self.calculate_structure()
		return True

	@api.multi
	def unlink(self):
		for rec in self:
			search_id=self.env['n.warehouse.placed.product'].search([('n_location_view','=',rec.id),
								('product_id','!=',False)])
			search_multi_id=self.env['store.multi.product.data'].search([
								('store_id.n_location_view','=',rec.id),
								('product_id','!=',False)])
			if search_id or search_multi_id:
				raise UserError("You can't delete this record, storage location which are related to this are not empty,if you want to delete this record empty that location first")
		return super(stockLocationview, self).unlink()
		
	@api.multi
	def calculate_structure(self):
		try:
		    for rec in self:
		    	if rec.storage_capacity <=0:
		    		raise ValueError('Please Enter Storage Capacity')
	    		if rec.row <=0 or rec.column <=0 or rec.depth <=0 :
		    		raise ValueError('Please Enter Values in ROW/COLUMN/DEPTH')
		    	if rec.location_type =='store':
				if rec.row_name.str_id == rec.column_name.str_id or rec.column_name.str_id == rec.depth_name.str_id or rec.depth_name.str_id == rec.row_name.str_id:
					raise ValueError('Please select difference series for Storage Name')
					
			flag='rsc'
			warehouse=self.env['stock.warehouse'].search([('lot_stock_id','=',rec.location_id.id)],limit=1)
			for row in range(rec.row):
				n_row=0
				if rec.row_name.str_id == 'ASL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'ACL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'NUM':
					n_row=int(rec.r_series)+row
				elif rec.row_name.str_id == 'ROM':
					n_row=self.int_to_roman(row+1)
				flag='row'
				for column in range(rec.column):
					n_column=0
					if rec.column_name.str_id == 'ASL':
						n_column=chr(ord(rec.c_series)+column)
					elif rec.column_name.str_id == 'ACL':
						n_column=chr(ord(rec.c_series)+column)
					elif rec.column_name.str_id == 'NUM':
						n_column=int(rec.c_series)+column
					elif rec.column_name.str_id == 'ROM':
						n_column=self.int_to_roman(column+1)
					flag='rc'
					for depth in range(rec.depth):
						n_depth=0
						if rec.depth_name.str_id == 'ASL':
							n_depth=chr(ord(rec.d_series)+depth)
						elif rec.depth_name.str_id == 'ACL':
							n_depth=chr(ord(rec.d_series)+depth)
						elif rec.depth_name.str_id == 'NUM':
							n_depth=int(rec	.d_series)+depth
						elif rec.depth_name.str_id == 'ROM':
							n_depth=self.int_to_roman(depth+1)
						search_id=self.env['n.warehouse.placed.product'].search([
								('n_warehouse','=',warehouse.id),
								('n_location','=',rec.location_id.id),
								('n_location_view','=',rec.id),
								('n_row','=',str(n_row)),
								('n_column','=',str(n_column)),
								('n_depth','=',str(n_depth)),
								])
								
						if not search_id:
							self.env['n.warehouse.placed.product'].create({
								'n_warehouse':warehouse.id,
								'n_location':str(rec.location_id.id),
								'n_location_view':str(rec.id),
								'n_row':str(n_row),
								'n_column':str(n_column),
								'n_depth':str(n_depth),
								'max_qty':rec.storage_capacity,
								'qty_unit':rec.uom_id.id,
								})
						flag='rcd'
			rec.readonly_bool=flag
		except Exception as err:
    			exc_type, exc_obj, exc_tb = sys.exc_info()
	    		_logger.error("API-EXCEPTION..Exception in Create Storage Location {} {}".format(err,exc_tb.tb_lineno))
	    		raise UserError("API-EXCEPTION..Exception in Create Storage Location {} {}".format(err,exc_tb.tb_lineno))
				
	def int_to_roman(self,input):
		ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
		nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','i')
		result = ""
		for i in range(len(ints)):
		      count = int(input / ints[i])
		      result += nums[i] * count
		      input -= ints[i] * count
		return result 
	
	#not in use >>>>start	
	@api.multi  
	def change_series(self):
		context = self._context.copy()
		order_form = self.env.ref('api_inventory.change_series_form', False)
		name=''
		context.update({'default_location_id':self.id})
		if self._context.get('row'):
    			name='Change Row Series'
    			context.update({'default_previous_series':self.row_name.id,'default_ntype':'row'})
    		if self._context.get('column'):
    			name='Change Column Series'
    			context.update({'default_previous_series':self.column_name.id,'default_ntype':'column'})
		if self._context.get('depth'):
    			name='Change Depth Series'
    			context.update({'default_previous_series':self.depth_name.id,'default_ntype':'depth'})	
    		if name and order_form:	
			return {
			    'name':name,
			    'type': 'ir.actions.act_window',
			    'view_type': 'form',
			    'view_mode': 'form',
			    'res_model': 'change.series',
			    'views': [(order_form.id, 'form')],
			    'view_id': order_form.id,
			    'context':context,
			    'target': 'new',
			 }
	 #<<<end

	@api.multi
	def _create_html_view(self):
		for rec in self:
		    view =''
		    warehouse=self.env['stock.warehouse'].search([('lot_stock_id','=',rec.location_id.id)],limit=1)
		    loc_id=self.env['n.warehouse.placed.product'].search([('n_warehouse','=',warehouse.id),
									  ('n_location','=',rec.location_id.id)])
		    if loc_id and rec.row and rec.column and rec.depth:
		    	view +='<table style="width:100%" border="0"> <tr>'
    			view +='<td style="background-color:white;width:15%;font-size:100%;text-align:center"><b>  Location is Empty </b></td>'
    			view +='<td style="width:5%"></td>'
    			view +='<td style="background-color:green;width:15%;font-size:100%;text-align:center"> <font color="white"><b> Location is Fully Occupied </font> </b></td>'
    			view +='<td style="width:5%"> </td>'
    			view +='<td style="background-color:LimeGreen;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Location is Partially Occupied </font> </b></td>'
    			view +='<td style="width:5%"></td>'
    			view += '<td style="background-color:red;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Location under Maintenance </font> </b></td>'
    			view +='<td style="width:5%"></td>'
    			view += '<td style="background-color:black;width:15%;font-size:100%;text-align:center"> <font color="white"><b>  Location Not in Use </font> </b></td>'
			view += '</tr></table><p> <p>'
				
	    		for r in range(1):
	    			view +='<table style="width:100%" border="1"> <tr>'
	    			view += '<td style="width:2%"></td>'
	    			per=98/rec.depth
 				for d in range(rec.depth):
					view += '<td style="width:'+str(per)+'"%;text-align:center"> <b>Depth - '+str(d+1)+'</b></td>'
				view += '</tr></table><p> <p>'
					
	    		for row in range(rec.row):
	    			view +='<b><li>Row '+str(row+1)+' </li></b><p><p>\
		    			<table style="width:100%" border="1">'
				n_row=0
				if rec.row_name.str_id == 'ASL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'ACL':
					n_row=chr(ord(rec.r_series)+row)
				elif rec.row_name.str_id == 'NUM':
					n_row=int(rec.r_series)+row
				elif rec.row_name.str_id == 'ROM':
					n_row=self.int_to_roman(row+1)
				
				for column in range(rec.column):
					view +='<tr>'
					n_column=0
					if rec.column_name.str_id == 'ASL':
						n_column=chr(ord(rec.c_series)+column)
					elif rec.column_name.str_id == 'ACL':
						n_column=chr(ord(rec.c_series)+column)
					elif rec.column_name.str_id == 'NUM':
						n_column=int(rec.c_series)+column
					elif rec.column_name.str_id == 'ROM':
						n_column=self.int_to_roman(column+1)
					
					view +='<td width=2% align="center"> <font color="black"> <h4>'+str(n_column)+'</h4></td>'
				    	for depth in range(rec.depth):
						n_depth=0
						if rec.depth_name.str_id == 'ASL':
							n_depth=chr(ord(rec.d_series)+depth)
						elif rec.depth_name.str_id == 'ACL':
							n_depth=chr(ord(rec.d_series)+depth)
						elif rec.depth_name.str_id == 'NUM':
							n_depth=int(rec.d_series)+depth
						elif rec.depth_name.str_id == 'ROM':
							n_depth=self.int_to_roman(depth+1)
					
						search_id=self.env['n.warehouse.placed.product'].search([
								('n_warehouse','=',warehouse.id),
								('n_location','=',rec.location_id.id),
								('n_location_view','=',rec.id),
								('n_row','=',str(n_row)),
								('n_column','=',str(n_column)),
								('n_depth','=',str(n_depth)),
								('max_qty','=',rec.storage_capacity)])
						per=98.0/rec.depth
						if search_id:
							base_url = self.env['ir.config_parameter'].get_param('web.base.url')
					                query = {'db': self._cr.dbname}
					                fragment = {
								'model': 'n.warehouse.placed.product',
								'view_type': 'form',
                      						'target': 'new',
								'id': search_id.id,
								}
						        url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
							if search_id.product_id:
								if search_id.state=='full':
									view +='<td width="'+str(per)+'%" style="background-color:green;" > <font color="white">'
								else :
									view +='<td width="'+str(per)+'%" style="background-color:LimeGreen;" > <font color="white">'
								text_link = _("""<a style="background-color:DarkSeaGreen;"  href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
								view +='<h3 >'+str(text_link)+'</h3>'
								if search_id.product_id:
									view +='<ul><li>['+str(search_id.product_id.default_code)+'] '+str(search_id.product_id.name)+'</li>'
								if search_id.total_quantity:
									view +='<li>'+str(search_id.total_quantity)+str(search_id.total_qty_unit.name)+'</li>'
								if search_id.Packaging_type:
									view +='<li>'+str(search_id.Packaging_type.name)+'</li></ul></font>'
							elif search_id.multi_product_ids:
								if search_id.state=='full':
									view +='<td width="'+str(per)+'%" style="background-color:green;" > <font color="white">'
								else :
									view +='<td width="'+str(per)+'%" style="background-color:LimeGreen;" > <font color="white">'
								text_link = _("""<a href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
								view +='<h3>'+str(text_link)+'</h3>'
								if search_id.max_qty > 10:
									view +='<table style="width:100%"><tr>'
									td=1
									for store_p1 in search_id.multi_product_ids:
									     if store_p1.product_id:
										view +='<td><ul><li> ['+str(store_p1.product_id.default_code)+'] '+str(store_p1.product_id.name)+'</li>'
									     if store_p1.total_quantity:
										view +='<li>'+str(store_p1.total_quantity)+str(store_p1.total_qty_unit.name)+'</li>'
									     if store_p1.Packaging_type:
										view +='<li>'+str(store_p1.Packaging_type.name)+'</li></td>'
									     if td >4:
									     	view += '</ul></tr><p><tr>'
									     	td=1
									     else:
									     	td+=1
									view +='</tr></table>'
								else:
								     for store_p in search_id.multi_product_ids:
									if store_p.product_id:
										view +='<ul><li>['+str(store_p.product_id.default_code)+'] '+str(store_p.product_id.name)+'</li>'
									if store_p.total_quantity:
										view +='<li>'+str(store_p.total_quantity)+str(store_p.total_qty_unit.name)+'</li>'
									if store_p.Packaging_type:
										view +='<li>'+str(store_p.Packaging_type.name)+'</li></ul><p>'
								view +='</font>'
							elif search_id.state=='maintenance':
								view +='<td width="'+str(per)+'%" style="background-color:red;">'
								text_link = _("""<a href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
								view +='<h3>'+str(text_link)+'</h3>'
							
							elif search_id.state=='no_use':
								view +='<td width="'+str(per)+'%" style="background-color:black;">'
								text_link = _("""<a href="%s" >%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
								
							else:
								view +='<td width="'+str(per)+'%">'
								text_link = _("""<a href="%s">%s</a> """) % (url,str(n_row)+str(n_column)+str(n_depth))
								view +='<h3>'+str(text_link)+'</h3>'
							view +='</td>'
					view +='</tr>'
				view +='</table><p><p>'
		    rec.storage_locations=view
		    
	@api.multi
	def show_view(self):
		view_form = self.env.ref('api_inventory.stock_location_view_form', False)
		view_tree = self.env.ref('api_inventory.stock_location_view_tree', False)
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        	self.dimentional_view = 'localhost/drage_cube.html'
		if view_form:
		    return {
		    	'name':'Storage Location View',
		        'type': 'ir.actions.act_window',
		        'view_type': 'form',
		        'view_mode': 'form',
		        'res_model': 'stock.location.view',
		        'views': [(view_form.id, 'form'),(view_tree.id, 'tree')],
		        'view_id': view_form.id,
		        'target' : 'current',
		        'res_id' :self.id,
		    }


class locationSeriesName(models.Model):
	_name = "location.series.name"

	name = fields.Char(string="Name")
	str_id	= fields.Char(string="Code")
	value = fields.Char('Value')
	
class changeSeries(models.TransientModel):
	_name = "change.series"
	
	previous_series = fields.Many2one("location.series.name","Pervious Series")
	new_series = fields.Many2one("location.series.name","New Series")
	location_id = fields.Many2one("stock.location","Location")
	ntype = fields.Selection([('row','Row'),('column','Column'),('depth','Depth')],"Type")
	
	@api.multi
	def update_series(self):
		for rec in self:
			if rec.ntype == 'row':
				rec.location_id.row_name=rec.new_series.id
			if rec.ntype == 'column':
				rec.location_id.column_name=rec.new_series.id
			if rec.ntype == 'depth':
				rec.location_id.depth_name=rec.new_series.id
				
