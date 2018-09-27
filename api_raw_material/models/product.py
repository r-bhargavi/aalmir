# -*- coding: utf-8 -*-
# copyright reserved

from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp

class ProductTemplate(models.Model):
	_inherit ='product.template'
	
	total_wastage_qty=fields.Float(compute='cal_wastage')
        check_grinding=fields.Boolean('Grinding Product', default=False)
        grinding_product_id=fields.Many2one('product.product')
        check_scrap=fields.Boolean('Scrap Product', default=False)
        scrap_product_id=fields.Many2one('product.product')
        check_produced_wastage=fields.Boolean('Product Produces Wastage ?',default=False)

        @api.multi
        @api.onchange('check_produced_wastage')
        def clear_checks(self):
        	for record in self:
                    if not record.check_produced_wastage:
                       record.check_grinding=False
                       record.check_scrap=False
                       record.grinding_product_id=''
                       record.scrap_product_id='' 
        @api.multi
        def cal_wastage(self):
		for record in self:
                    if record.product_material_type.string in ('grinding','scrap'):
                       wastage_batch=self.env['mrp.order.batch.number'].search([('wastage_product.product_tmpl_id','=',record.id),('request_state','=','requested')]) 
                       if wastage_batch:
                          record.total_wastage_qty=sum(line.product_qty for line in wastage_batch)
	@api.model
	def create(self,vals):
		res = super(ProductTemplate,self).create(vals)
		if res.route_ids:
			data_obj = self.env['ir.model.data']
			f_route_id = data_obj.get_object_reference('api_raw_material', 'film_rm_route')[1]
			i_route_id = data_obj.get_object_reference('api_raw_material', 'injection_rm_route')[1]
			if res.categ_id.cat_type=='film':
				res.route_ids=[(4,f_route_id),(3,i_route_id)]
			elif res.categ_id.cat_type=='injection':
				res.route_ids=[(3,f_route_id),(4,i_route_id)]
		return res
		
	@api.multi
        def open_wastage(self):
        	for line in self:
        		wastage_tree = self.env.ref('api_raw_material.mrp_wastage_btach_tree', False)
			if wastage_tree:
				return {
				    'name':'Wastage Details',
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'tree,',
				    'res_model': 'mrp.order.batch.number',
				    'views': [(wastage_tree.id, 'tree')],
				    'view_id': wastage_tree.id,
				    'target': 'current',
				    'domain':[('wastage_product.product_tmpl_id','=',self.id),('request_state','=','requested')],
				}
        		return True  

class productProduct(models.Model):
    _inherit='product.product'

    @api.multi
    def open_wastage(self):
        	for line in self:
        		wastage_tree = self.env.ref('api_raw_material.mrp_wastage_btach_tree', False)
			if wastage_tree:
				return {
				    'name':'Wastage Details',
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'tree,',
				    'res_model': 'mrp.order.batch.number',
				    'views': [(wastage_tree.id, 'tree')],
				    'view_id': wastage_tree.id,
				    'target': 'current',
				    'domain':[('wastage_product','=',self.id),('request_state','=','requested')],
				}
        		return True   
        		
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('wastage') and context.get('used_type'):
           if context.get('used_type') == 'grinding':
              products=self.search(cr,uid,[('product_material_type.string','=','grinding')])
              args.extend([('id','in',products)])
           else:
              products=self.search(cr,uid,[('product_material_type.string','=','scrap')])
              args.extend([('id','in',products)])
        
        if context.get('is_reception'):
        	'''Add code to show only raw material price products..'''
		pids= []
		ids = self.pool.get('raw.material.pricelist').search(cr,uid,[('product_id','!=',False)],context=context)
		for x in self.pool.get('raw.material.pricelist').browse(cr,uid,ids,context=context):
			pids.append(x.product_id.id)
		args=[('id','in',pids)]
        return super(productProduct,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    @api.v7
    def _get_domain_locations(self,cr, uid, ids, context=None):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        context = context or {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')

        location_ids = []
        if context.get('location', False):
            if isinstance(context['location'], (int, long)):
                location_ids = [context['location']]
            elif isinstance(context['location'], basestring):
                domain = [('complete_name','ilike',context['location'])]
                if context.get('force_company', False):
                    domain += [('company_id', '=', context['force_company'])]
                location_ids = location_obj.search(cr, uid, domain, context=context)
            else:
                location_ids = context['location']
        else:
            if context.get('warehouse', False):
                if isinstance(context['warehouse'], (int, long)):
                    wids = [context['warehouse']]
                elif isinstance(context['warehouse'], basestring):
                    domain = [('name', 'ilike', context['warehouse'])]
                    if context.get('force_company', False):
                        domain += [('company_id', '=', context['force_company'])]
                    wids = warehouse_obj.search(cr, uid, domain, context=context)
                else:
                    wids = context['warehouse']
            else:
                wids = warehouse_obj.search(cr, uid, [], context=context)

            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.view_location_id.id)
    
    
        operator = context.get('compute_child', True) and 'child_of' or 'in'
        domain = context.get('force_company', False) and ['&', ('company_id', '=', context['force_company'])] or []
        locations = location_obj.browse(cr, uid, location_ids, context=context)
        loc_id=self.pool.get('stock.location').search(cr,uid,[('quality_ck_loc','!=',True)])
        if operator == "child_of" and locations and locations[0].parent_left != 0:
            loc_domain = []
            dest_loc_domain = []
            for loc in locations:
                if loc_domain:
                    loc_domain = ['|'] + loc_domain  + ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain = ['|'] + dest_loc_domain + ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]
                else:
                    loc_domain += ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain += ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]
	    
            return (
                domain + [('location_id','in',loc_id)],
                domain + ['&'] + dest_loc_domain + ['!'] + loc_domain,
                domain + ['&'] + loc_domain + ['!'] + dest_loc_domain
            )
        else:
            return (
                #domain + [('location_id', operator, location_ids)],
                domain + [('location_id','in',loc_id)],
                domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
                domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)])


