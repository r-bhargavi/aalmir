# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp import api, tools, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
import time
import sys
_logger = logging.getLogger(__name__)

class productTemplate(models.Model):
    _inherit = 'product.template'

    product_material_type = fields.Many2one('product.material.type','Type')
    matstrg = fields.Char('Material String')
    raw_material_type = fields.Many2one('product.raw.material.type','Raw Material Type') 
    rawstrg = fields.Char('Sub Material String',related='raw_material_type.string')
    asset_type = fields.Selection([('company','Company asset'),('client','Client Asset')],'Asset Type')
    asset_code = fields.Char('Asset Code')
    asset_customer = fields.Many2one('res.partner','Customer Name')
    code_access = fields.Boolean('Edit Number',default=False,help='Uncheck This field and the Internal Referance code is editable for administrator')
    internal_name = fields.Char('Internal Name')
    
    @api.multi
    def write(self,vals):
    	vals.update({'code_access':True})			# to make field non editable for other users
    	for rec in self:
    		if rec.default_code =='GEN':
    			if vals.get('name') and vals.get('name')!='Generic Product':
    				raise UserError("You dont have access to change the name of Generic Product")
	return super(productTemplate,self).write(vals)

    @api.model
    def create(self,vals):
	vals.update({'code_access':True})			# to make field non editable for other users
	if not self._context.get('ndefault_code_ctx'):		# to avoid creation of extra record in product
		self = self.with_context({'ndefault_code':vals.get('default_code')})
    	return super(productTemplate,self).create(vals)
    	
class ProductProduct(models.Model):
    _inherit = "product.product"
    
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name') or ''
            code = context.get('display_default_code', True) and d.get('default_code',False) or False
            ecode = d.get('external_product_number', False) or False
            internal_name= d.get('internal_name','') or ''
            if code:
                if ecode:
                    name = '[%s][%s] %s- %s' % (code,ecode,internal_name,name)
                else:
                    name = '[%s] %s- %s' % (code,internal_name,name)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        self.check_access_rights(cr, user, "read")
        self.check_access_rule(cr, user, ids, "read", context=context)

        result = []
        for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                if variant:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                if not sellers:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
            external_product_number = False
            if context.get('partner_id'):
                cust_prod_obj = self.pool.get('customer.product')
                cust_prod_ids = cust_prod_obj.search(cr, user, [('pricelist_id.customer', '=', context.get('partner_id')), ('product_id', '=', product.id)])
                if cust_prod_ids:
                    cpobj = cust_prod_obj.browse(cr, user, cust_prod_ids[0])
                    external_product_number = cpobj.ext_product_number
            internal_name= product.product_tmpl_id.internal_name
            if sellers:
                for s in sellers:
                    seller_variant = s.product_name and (
                        variant and "%s (%s)" % (s.product_name, variant) or s.product_name
                        ) or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or product.default_code,
                              'external_product_number': external_product_number,
                              'internal_name': internal_name,
                              'type': 'product',
                              }
                    temp = _name_get(mydict)
                    if temp not in result:
                        result.append(temp)
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': product.default_code,
                          'external_product_number': external_product_number,
                          'internal_name': internal_name,
                          'type':'product',
                          }
                result.append(_name_get(mydict))
        return result
       
    @api.model
    def create(self, vals):
    	error_string=''
    	try:
		seq_obj = self.env['ir.sequence']
		categ_obj = self.env['product.category']
		template_obj = self.env['product.template']
		product_obj = self.env['product.product']
		cobj = categ_obj.browse(vals.get('categ_id'))
		if not cobj and vals.get('product_tmpl_id'):
			tmpl_id=template_obj.search([('id','=',vals.get('product_tmpl_id'))])
			cobj=tmpl_id.categ_id

        	product_tmpl_id=''
        	if vals.get('product_tmpl_id'):
        		product_tmpl_id=template_obj.search([('id','=',vals.get('product_tmpl_id'))])
        		cobj = product_tmpl_id.categ_id
        	
        	if not cobj:
        		error_string='Please select Product Category'
			raise

		if not vals.get('default_code') and self._context.get('ndefault_code'):
			vals.update({'default_code' :self._context.get('ndefault_code')})
		if product_tmpl_id and not vals.get('default_code'):
			if product_tmpl_id.product_material_type.string in ('product','component'):
			    v=False
			    if cobj.cat_type == 'injection':
			    	while (1):
					v= seq_obj.next_by_code('injection.product.number')
					find_rec=product_obj.search([('default_code','=',v)])
					if not find_rec:
						break
				if v:
				    	vals.update({'default_code' :v})
			    	else:
					error_string='Issue in creation of Internal Number for Injection Product'
					raise
			    elif cobj.cat_type == 'film':
	    			while (1):
					v= seq_obj.next_by_code('film.internal.product.number')
					find_rec=product_obj.search([('default_code','=',v)])
					if not find_rec:
						break
			    	if v:
				    	vals.update({'default_code' :v})
			    	else:
					error_string='Issue in creation of Internal Number for Film Product'
					raise
			    else:
				error_string='Please select Category Film/Injection'
				raise
			#generate default code for Packaging
			elif product_tmpl_id.product_material_type.string=='packaging':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('packaging.internal.number')
				find_rec=product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Packaging Product'
				raise

			#generate default code for Raw material
			elif product_tmpl_id.product_material_type.string=='raw':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('raw.internal.product.number')
				find_rec=product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Raw-Material Product'
				raise

			#generate default code for Other
			elif product_tmpl_id.product_material_type.string=='other':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('other.internal.number')
				find_rec=product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Other Product'
				raise
			
			#generate default code for Asset
			elif product_tmpl_id.product_material_type.string=='asset':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('asset.internal.number')
				find_rec=product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	if product_tmpl_id.raw_material_type.string=='part':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/SPT/'+v})
			    	if product_tmpl_id.raw_material_type.string=='machine':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/MC/'+v})
			    	if product_tmpl_id.raw_material_type.string=='plate':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/PLT/'+v})
			    	if product_tmpl_id.raw_material_type.string=='other':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/OT/'+v})
		    		if product_tmpl_id.raw_material_type.string=='mould':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/ML/'+v})
			#generate default code for Asset
			elif product_tmpl_id.product_material_type.string=='expense':
                            print "asdsscscscdsc===============",self._context
			    v=False
                            v= seq_obj.next_by_code('expense.internal.number')
                            vals.update({'default_code' :v,'asset_code':''})
			else:
				error_string='Material Type of Product is not Found'
				raise
				
		elif vals.get('product_material_type') and not vals.get('default_code'):
			material=self.env['product.material.type'].search([('id','=',vals.get('product_material_type'))])
			if material.string in ('product','component'):
			    v=False
			    if cobj.cat_type == 'injection':
			    	while (1):
					v= seq_obj.next_by_code('injection.product.number')
					find_rec=product_obj.search([('default_code','=',v)])
					if not find_rec:
						break
			    	if not v:
					error_string='Issue in creation of Internal Number for Injection Product'
					raise
			    elif cobj.cat_type == 'film':
	    			while (1):
					v= seq_obj.next_by_code('film.internal.product.number')
					find_rec=product_obj.search([('default_code','=',v)])
					if not find_rec:
						break
			    	if not v:
					error_string='Issue in creation of Internal Number for Film Product'
					raise
			    else:
				error_string='Please select Category Film/Injection'
				raise
				
			    if v:
				    	vals.update({'default_code' :v})
				    	
			elif material.string=='packaging':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('packaging.internal.number')
				find_rec = product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Packaging Product'
				raise

			#generate default code for Raw material packaging
			elif material.string=='raw':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('raw.internal.product.number')
				find_rec = product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Raw-Material Product'
				raise
		
			#generate default code for Other
			elif material.string=='other':
			    v=False
			    while (1):
				v= seq_obj.next_by_code('other.internal.number')
				find_rec = product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	vals.update({'default_code' :v})
			    else:
				error_string='Issue in creation of Internal Number for Other Product'
				raise
			
			#generate default code for Raw material packaging
			if material.string=='asset':
			    material_type=self.env['product.raw.material.type'].search([('id','=',vals.get('raw_material_type'))])
			    v=False
			    while (1):
				v= seq_obj.next_by_code('asset.internal.number')
				find_rec = product_obj.search([('default_code','=',v)])
				if not find_rec:
					break
			    if v:
			    	if material_type.string=='part':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/SPT/'+v})
			    	if material_type.string=='machine':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/MC/'+v})
			    	if material_type.string=='plate':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/PLT/'+v})
			    	if material_type.string=='other':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/OT/'+v})
		    		if material_type.string=='mould':
			    		vals.update({'default_code' :v})
			    		vals.update({'asset_code' :'AMP/ML/'+v})
			    else:
				error_string='Issue in creation of Internal Number for Asset'
				raise
		else:
			data_obj = self.env['ir.model.data']
			material_id = data_obj.get_object_reference('gt_customer_products', 'material_type_data0')
			vals.update({'product_material_type':material_id[1],'matstrg':'product'})
		
		if vals.get('taxes_id'):
		    del vals['taxes_id']
		if vals.get('supplier_taxes_id'):
		    del vals['supplier_taxes_id']
	    	self = self.with_context({'ndefault_code_ctx':True})
		return super(ProductProduct, self).create(vals)
	except Exception as err:
    		if error_string:
    			raise UserError(error_string)
		else:
	    		exc_type, exc_obj, exc_tb = sys.exc_info()
		    	_logger.error("Error in product Internal code Creation {} {}".format(err,exc_tb.tb_lineno))
		    	raise UserError("Error in product Internal code Creation {} {}".format(err,exc_tb.tb_lineno))

    @api.multi
    def write(self, vals):
    	for res in self:
    		error_str=''
	    	try:
			if vals.get('default_code'):
			    product=self.search([('default_code','=',str(vals.get('default_code'))),('id','!=',res.id)])
			    if product:
			    	error_str='Internal Number {} already Exist. '.format(vals.get('default_code'))
			    	raise
		except Exception as e:
			exc_type, exc_obj, exc_tb = sys.exc_info()
	    		_logger.error("API-EXCEPTION..Exception in Product Updation..{} {} {}".format(e,exc_tb.tb_lineno,error_str))
			if error_str:
				raise UserError(error_str)
			else:
				raise UserError('Error in product Updation code Creation {}'.format(e))
	return super(ProductProduct, self).write(vals)
    
    @api.multi
    def _get_prod_pricelist(self):
        for rec in self:
            cust_prod_ids = self.env['customer.product'].search([('product_id','=', rec.id)])
            pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
            rec.pricelist_count = len(pids)
            
    @api.multi
    def open_pricelist(self):
        pids = []
        for rec in self:
            cust_prod_ids = self.env['customer.product'].search([('product_id','=', rec.id)])
            pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
        res = self.env['ir.actions.act_window'].for_xml_id('product', 'product_pricelist_action2')
        res['domain'] = [('id', 'in', pids)]
        return res
            
    external_product_number = fields.Char('External Product Number')
    pricelist_count = fields.Integer(string="Pricelist", compute=_get_prod_pricelist, default=0)

class ProductCategory(models.Model):
    _inherit = "product.category"
    
    cat_type = fields.Selection([('all', 'Both'),('film', 'Films and Bags'),
                                ('injection', 'Injection')], string="Type")
    
    active = fields.Boolean('Active',default=True)
    sequence_rel = fields.Many2one('ir.sequence','Sequence')
    
    @api.model
    def name_search(self,name, args=None, operator='ilike',limit=100):
	if self._context.get('opportunity'):
		args=[]
		attributes = self.env['crm.lead'].search([('id','=',self._context.get('opportunity'))])
		if attributes.category:
			args=[('id','in',[attributes.category.id])]

	if self._context.get('product_type'):
		args=[]
                material=self.env['product.material.type'].search([('id','=',self._context.get('product_type'))])
                if material.string in ('product','component'):
                	material=self.search([('cat_type','in',('film','injection'))])
                	args=[('id','in',material._ids)]
                elif material.string=='asset' and self._context.get('sub_type'):
                	sub_material=self.env['product.raw.material.type'].search([('id','=',self._context.get('sub_type'))])
                	if sub_material.string=='plate':
                		material=self.search([('cat_type','=','film')])
                		args=[('id','in',material._ids)]
        		elif sub_material.string=='mould':
        			material=self.search([('cat_type','=','injection')])
                		args=[('id','in',material._ids)]
                	
    	return super(ProductCategory,self).name_search(name, args, operator=operator,limit=limit)
    	                            
class ProductUom(models.Model):
    _name = "product.uom"
    _inherit = ['product.uom','mail.thread']
    
    unit_type = fields.Many2many('product.uom.type','uom_product_uom_type_rel','unit_id','unit_type_id','Unit Type') 
    product_type=fields.Many2one('product.raw.material.type',string='Product Type')
    product_id=fields.Many2one('product.product',string='Product Name') # for packaging product relation
    
    @api.model
    def name_search(self,name, args=None, operator='ilike',limit=100):
    	new_ids=[]
    	# call from product form
    	if self._context.get('product_uom'):
    		args=[]
    		if self._context.get('sale_ok'):
    			units = self.search([('unit_type.string','=','product')])
			args=[('id','in',list(units._ids))]
    		elif self._context.get('purchase_ok'):
			units = self.search([('unit_type.string','in',('product','purchase'))])
			args=[('id','in',list(units._ids))]
    	if self._context.get('packg_unit') or self._context.get('packg_type'): 
    		if self._context.get('pkg_type') == False:
    			return []
	if self._context.get('packg_unit'):			# check for packaging from product form
		args=[]
		uom_id=self._context.get('uom_id')
		if self._context.get('pkg_type')=='primary' :
			if self._context.get('parent_uom'):
				args=[('id','in',[self._context.get('parent_uom')])]
		elif self._context.get('pkg_type')=='secondary' :
			n_ids=[]
			for rec in self._context.get('packaging_data'):
				if rec[0]==4:
					r_ids = self.env['product.packaging'].search([('id','=',rec[1]),
										('pkgtype','=','primary')])
					if r_ids:
						n_ids.append([r.uom_id.id for r in  r_ids])
				if rec[0] in (1,0) and rec[2]:
					if rec[2].get('uom_id'):
						n_ids.append(rec[2].get('uom_id'))
			units = self.search([('id','in',n_ids),('unit_type.string','=','sec_packaging')])
			args=[('id','in',list(units._ids))]
			
	if self._context.get('packg_type'):
		args=[]
		unit_id = self._context.get('unit_id')
		if self._context.get('material_type'):
			raw_type=self.env['product.material.type'].search([('id','=',self._context.get('material_type'))])
			if raw_type.string=='raw':
				units = self.search([('id','!=',unit_id),('unit_type.string','=','raw_packaging')])
				new_ids.extend(units._ids)
			else:
				if self._context.get('pkg_type')=='primary' :
					units = self.search([('id','!=',unit_id),('unit_type.string','=','pri_packaging')])
					args=[('id','in',list(units._ids))]
				elif self._context.get('pkg_type')=='secondary' :
					units = self.search([('id','!=',unit_id),('unit_type.string','=','product_packaging')])
					args=[('id','in',list(units._ids))]
						
	if self._context.get('attribute'):
		args=[]
		if self._context.get('attrs_id'):
			attributes = self.env['n.product.discription.value'].search([('id','=',self._context.get('attrs_id'))])
			if attributes.units:
				args=[(rec.id,rec.name) for rec in attributes.units]
		return args
		
	if self._context.get('process_packaging'):
		units=self.search([('name','in',('Kg','Pcs','m'))])
		args=[('id','in',list(units._ids))]

	if self._context.get('purchase'):
		if self._context.get('product_id'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))])
			category_id=self.search([('unit_type.string','=','purchase'),
					('category_id','=',product_id.product_tmpl_id.uom_po_id.category_id.id)])
			args=[('id','in',category_id._ids)]
		else:
			return []	

	if self._context.get('reception'):
		if self._context.get('product_id'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))])

			args=[('id','in',[product_id.product_tmpl_id.uom_id.id])]
		else:
			return []
    	return super(ProductUom,self).name_search(name, args, operator=operator,limit=limit)

    @api.model
    def create(self,vals):
	body=''
	if vals.get('name'):
		body+=str('Name: {} \n'.format(vals.get('name')))
	rec= super(ProductUom,self).create(vals)
	if body:
		rec.message_post(body)	
    	return rec

    @api.multi
    def write(self,vals):
    	body=''
    	super(ProductUom,self).write(vals)
    	if vals.get('name'):
		body+=str('Name: {} \n'.format(vals.get('name')))
	if body:
		self.message_post(body)	
    	return True
    	
    @api.model
    def unlink(self):
    	raise UserError("You can not delete Unit of Measure,If you dont't want This unit Please make it inactive")
    	
class ProductUomType(models.Model):
    _name = "product.uom.type"
    
    name = fields.Char('Name')
    string = fields.Char('Internal Name')
    active = fields.Boolean(string="Active")
    description = fields.Char('Description')

class productPackging(models.Model):
    _inherit = 'product.packaging'

    unit_id = fields.Many2one('product.uom','Unit')
    uom_id = fields.Many2one('product.uom','Unit Type')
    pkgtype = fields.Selection([('primary','Primary'),('secondary','Secondary')],'Types')

    @api.multi
    @api.onchange('pkgtype')
    def product_unit(self):
        for record in self:
            if record.product_tmpl_id.uom_id:
               if record.pkgtype == 'primary':
                  record.unit_id=record.product_tmpl_id.uom_id.id
               else:
                  record.unit_id=False

    @api.multi
    @api.onchange('uom_id','qty','unit_id')
    def get_name(self):
	for line in self:
		uom_name=qty=category=''
		if line.unit_id:
			uom_name=line.unit_id.name
		if line.qty:
			qty=int(line.qty)
		if line.uom_id:
			category=line.uom_id.name if not line.uom_id.product_type else line.uom_id.product_type.name
		line.name = str(str(qty)+str(uom_name)+"/"+str(category))

    @api.model
    def create(self,vals):
	if vals.get('unit_id') == vals.get('uom_id'):
		raise UserError("Please Select Different Unit and Packaging Types")
	if vals.get('unit_id') and vals.get('product_tmpl_id') and vals.get('pkgtype')=='secondary':
		prod_id = self.env['product.template'].search([('id','=',vals.get('product_tmpl_id'))])
		if prod_id:
			if vals.get('unit_id') == prod_id.uom_id.id:
				raise UserError("Please Select Parimary Packaging Type in Secondary Unit for quantity {}".format(vals.get('qty')))
		uom_id = self.env['product.uom'].search([('id','=',vals.get('uom_id'))])
		if uom_id and 'store' not in uom_id.unit_type.mapped('string'):
			raise UserError("Please Select Storage Unit in Secondary Packaging Type for quantity {}".format(vals.get('qty')))
	if vals.get('unit_id') and vals.get('product_tmpl_id') and vals.get('pkgtype')=='primary':
		prod_id = self.env['product.template'].search([('id','=',vals.get('product_tmpl_id'))])
		if prod_id:
			if vals.get('unit_id') != prod_id.uom_id.id:
				raise UserError("Please Select only Product Unit as Primary Packaging unit")
    	return super(productPackging,self).create(vals)

    @api.multi
    def write(self,vals):
    	super(productPackging,self).write(vals)
	for rec in self:
    		if rec.unit_id.id and rec.uom_id.id:
			if rec.unit_id.id == rec.uom_id.id:
				raise UserError("Please Select Different Unit and Packaging Types {}".format(rec.product_tmpl_id.name))
		if rec.pkgtype=='secondary':
			if rec.unit_id.id == rec.product_tmpl_id.uom_id.id:
				raise UserError("Please Select Parimary Packaging Type in Secondary Unit for quantity {}".format(rec.qty))
			if 'store' not in rec.uom_id.unit_type.mapped('string'):
				raise UserError("Please Select Storage Unit in Secondary Packaging Type for quantity {}".format(rec.qty))
		if rec.pkgtype=='primary':
			if rec.unit_id.id != rec.product_tmpl_id.uom_id.id:
				raise UserError("Please Select only Product Unit as Primary Packaging unit")
	return True

class productMaterialType(models.Model):
    _name = "product.material.type"

    name = fields.Char('Name',help="Material type name", required=True, translate=True)
    string= fields.Char('Internal Name',help="Material type name", required=True,)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the Type without removing it.")

class productRawMaterialType(models.Model):
    _name = "product.raw.material.type"

    main_id =  fields.Many2one("product.material.type", string="Material Type")
    name = fields.Char('Name',help="Raw Material type name", required=True, translate=True)
    string= fields.Char('Internal Name',help="Raw Material type name", required=True,)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the Raw  Material Type without removing it.")

    @api.model
    def name_search(self, name, args=None, operator='ilike',limit=100):
	if self._context.get('material_type'):
		args=[]
		if self._context.get('material_type')[0][2]:
			raw_material = self.search([('main_id','in',self._context.get('material_type')[0][2])])._ids
			args=[('id','in',raw_material)]
    	return super(productRawMaterialType,self).name_search(name, args, operator=operator, limit=limit)

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"
    
    @api.model
    def create(self, vals):
        customer = False
        if vals.get('customer'):
            customer = self.env['res.partner'].browse(vals.get('customer'))
        if not vals.get('name'):
            vals.update({'name': customer.name + "'s Pricelist"})
        if vals.get('item_ids'):
        	vals.pop('item_ids')
        res=super(ProductPricelist, self).create(vals) 
        if customer and res:
            customer.write({'property_product_pricelist' : res.id})
    	return res


