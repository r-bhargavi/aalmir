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

class pricelist_calculater(models.Model):
    _inherit = 'pricelist.calculater'
    
    @api.multi
    def save_mrp_calculator(self):
    	print "vvvvvvvvvvvvv",self._context.get('active_id')
    	product_id= self.env['product.product'].search([('id','=',self._context.get('active_id'))])
    	flag=True
    	if not product_id:
    		flag=False
    		product_id= self.env['product.template'].search([('id','=',self._context.get('active_id'))])
    	for rec in self:
		uom_id=self.env['product.uom'].search([('name','=ilike','cm')], limit=1)
		product_id.initial_weight = rec.weight_per_kg
		product_id.weight = rec.weight_per_kg
		#product_id.ink_weight = rec.ink_weigth/rec.qty
		product_id.n_calculator_id=rec.id
		update=''
		create=''
		if not uom_id:
			raise UserError('Please Define cm unit in Unit of Measure.')
## Product Type
		if rec.product_type:
			att_id=self.env['n.product.discription.value'].search([('string','=','product_type')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.product_type.name.name):
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.product_type.name.name)+' </li>'
				attribute.value= rec.product_type.name.name
			elif not attribute:
				nid=self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.product_type.name.name)})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.product_type.name.name)+' </li>'
## Type Of Bags
		if rec.bag_type:
			att_id=self.env['n.product.discription.value'].search([('string','=','type_of_bag')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.bag_type.name.name): 
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.bag_type.name.name)+' </li>'
				attribute.value= rec.bag_type.name.name
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.bag_type.name.name)})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.bag_type.name.name)+' </li>'
## Length
		if rec.lenght:
			att_id=self.env['n.product.discription.value'].search([('string','=','length')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.lenght):
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.lenght)+' </li>'
				attribute.value= rec.lenght
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.lenght),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.lenght)+' </li>'
## Width
		if rec.width:
			att_id=self.env['n.product.discription.value'].search([('string','=','width')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.width):
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.width)+' </li>'
				attribute.value= rec.width
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.width),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.width)+' </li>'
## Left
		if rec.left:
			att_id=self.env['n.product.discription.value'].search([('string','=','lgusset')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.left):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.left)+' </li>'
				attribute.value= rec.left
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.left),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.left)+' </li>'
## Right
		if rec.right:
			att_id=self.env['n.product.discription.value'].search([('string','=','rgusset')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.right):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.right)+' </li>'
				attribute.value= rec.right
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.right),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.right)+' </li>'
## TOP
		if rec.top:
			att_id=self.env['n.product.discription.value'].search([('string','=','topfold')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.top):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.top)+' </li>'
				attribute.value= rec.top
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.top),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.top)+' </li>'
## Bottom
		if rec.bottom:
			att_id=self.env['n.product.discription.value'].search([('string','=','bgusset')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.bottom):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.bottom)+' </li>'
				attribute.value= rec.bottom
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.bottom),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.bottom)+' </li>'
## Printing Area(%)			
		if rec.printing_area:
			p_uom_id=self.env['product.uom'].search([('name','=ilike','Percentage(%)')],limit=1)
			att_id=self.env['n.product.discription.value'].search([('string','=','printing_area')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) !=str(rec.printing_area):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.printing_area)+' </li>'
				attribute.value= rec.printing_area
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.printing_area),'unit':p_uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.printing_area)+' </li>'
## Micron
		if rec.micron:
			mac_uom_id=self.env['product.uom'].search([('name','=ilike','micron')],limit=1)
			att_id=self.env['n.product.discription.value'].search([('string','=','thickness')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) !=str(rec.micron):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.micron)+' </li>'
				attribute.value= rec.micron
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.micron),'unit':mac_uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.micron)+' </li>'
## Printing 
		if rec.printing_type:
			att_id=self.env['n.product.discription.value'].search([('string','=','printing_type')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) !=str(rec.printing_type.name):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.printing_type.name)+' </li>'
				attribute.value= rec.printing_type.name
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.printing_type.name)})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.printing_type.name)+' </li>'
## Material type
		if rec.material_type:
			att_id=self.env['n.product.discription.value'].search([('string','=','material')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.material_type.name.name) :
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.material_type.name.name)+' </li>'
				attribute.value= rec.material_type.name.name
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.material_type.name.name)})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.material_type.name.name)+' </li>'
## Total Printing area (cm2)
		if rec.total_printing_area:
			att_id=self.env['n.product.discription.value'].search([('string','=','total_printing_area')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.total_printing_area):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.total_printing_area)+' </li>'
				attribute.value= rec.total_printing_area
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.total_printing_area),'unit':uom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.total_printing_area)+' </li>'
## Ink Weight
		if rec.ink_weigth:
			inkuom_id=self.env['product.uom'].search([('name','=ilike','Pcs')],limit=1)
			att_id=self.env['n.product.discription.value'].search([('string','=','inkweight')],limit=1)
			attribute =self.env['n.product.discription'].search([('product_id','=',product_id.id),('attribute','=',att_id.id)])
			if attribute and attribute.attribute.id == att_id.id and str(attribute.value) != str(rec.ink_weigth/rec.total_pcs):
				
				update +='<li>'+str(attribute.attribute.name)+' '+str(attribute.value)+' >> '+str(rec.ink_weigth/rec.total_pcs)+' </li>'
				attribute.value= rec.ink_weigth/rec.qty
			elif not attribute:
				self.env['n.product.discription'].create({'product_id': product_id.id,
					'attribute':att_id.id,'value':str(rec.ink_weigth/rec.total_pcs),'unit':inkuom_id.id})
				create+='<li>'+str(att_id.name)+' Value : '+str(rec.ink_weigth/rec.qty)+' </li>'
		if update:
			update = '<ul><span style="color:green">Specification updated</span>'+update+'</ul>'
		if create:
			create = '<ul><span style="color:green">Specification updated</span>'+create+'</ul>'
		if update or create:
			if flag:
				product_id.product_tmpl_id.message_post(body='<ul>Specification </ul><ul>'+create+'</ul><ul>'+update+'</ul>')	
			product_id.message_post(body='<ul>Specification </ul>'+create+update)
    	return True
    
