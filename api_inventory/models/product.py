# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#CH03 add on_change to change base currency and converted currency

from openerp import api, fields, models, _
from openerp import fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from datetime import datetime,date
import re
from dateutil.relativedelta import relativedelta
from openerp.tools.float_utils import float_round

class productTemplate(models.Model):
	_inherit = "product.template"

	@api.multi
	def open_inventory_location(self):
		order_tree = self.env.ref('api_inventory.product_stock_location_tree', False)
		order_form = self.env.ref('api_inventory.product_stock_location_from', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':'Inventory Location Product',
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'n.warehouse.placed.product',
		    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'domain':['|',('multi_product_ids.product_id','in',product_id),('product_id','in',product_id)],
		    'target': 'current',
		 }
		 
	@api.onchange('sale_ok','purchase_ok')
	def _sale_ok_onchange(self):
		if self.purchase_ok and not self.sale_ok:
			return {'domain':{'uom_id':[('unit_type.string','in',('purchase','product'))]}}
			
	master_btch_count = fields.Char('Master Batches',compute='_get_batches_data')
	batches_count = fields.Char('#Batches',compute='_get_batches_data')
	expenses_count = fields.Char('#Expenses',compute='_get_expense_data')
	mo_count = fields.Char('#Manufacturing',compute='_bom_orders_count_mo')
	mo_count_var = fields.Float('#Manufacturing',compute='_count_mo_var')
        prod_count = fields.Char('#Production Orders',compute='_get_prod_orders_data')
        prod_count_var = fields.Float('#Production Count',compute='_get_prod_orders_data_var')
        customer_name=fields.Char(string='Customer Name')
        in_count = fields.Char('#Incoming Count',compute='_get_in_data')
        in_count_var = fields.Char('#Incoming Count',compute='_get_in_data_var')
	bill_count = fields.Char('#Bills',compute='_get_bill_data')
	bin_location_count = fields.Integer('#Bin Location',compute='_get_batches_data')
	
	@api.multi
	def _get_batches_data(self):
		for res in self:
			product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
			product_id = [p.id for p in product_id]
		
			master_ids = self.env['stock.store.master.batch'].search([('product_id','in',product_id),
							("logistic_state","in",('transit_in',
								'stored','reserved','r_t_dispatch','transit'))])
			res.master_btch_count = str(len(master_ids))+' Pallet'
			batche_ids = self.env['mrp.order.batch.number'].search([('product_id','in',product_id),
							("logistic_state","in",('transit_in',
								'stored','reserved','r_t_dispatch','transit'))])
			pkg_id=self.env['product.packaging'].search([('product_tmpl_id','=',res.id),
									('pkgtype','=','primary')],limit=1)
			string=''
			if pkg_id:
				if pkg_id.uom_id and pkg_id.uom_id.product_type:
					string=pkg_id.uom_id.product_type.name
				else:
					string=pkg_id.uom_id.name
			res.batches_count = str(len(batche_ids))+' '+str(string)
			domain=['|',('multi_product_ids.product_id','in',product_id),('product_id','in',product_id)]
			bin_count = self.env['n.warehouse.placed.product'].search(domain)
			res.bin_location_count= len(bin_count)
	@api.multi
	def _get_expense_data(self):
		for res in self:
			product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
			product_id = [p.id for p in product_id]
		
			expense_ids = self.env['hr.expense'].search([('product_id','in',product_id)])
			res.expenses_count = str(len(expense_ids))
	@api.multi
	def _get_prod_orders_data(self):
            for res in self:
                prod_count=0.0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
                product_id = [p.id for p in product_id]

                prod_req_ids = self.env['n.manufacturing.request'].search([('n_product_id','in',product_id),('n_state','in',['new','draft'])])
                print "prod_req_idsprod_req_idsprod_req_ids",prod_req_ids
                if prod_req_ids:
                    for each in prod_req_ids:
                        prod_count += each.n_order_qty
                res.prod_count=str(prod_count)
	@api.multi
	def _get_prod_orders_data_var(self):
            for res in self:
                prod_count_now=0.0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
                product_id = [p.id for p in product_id]

                prod_req_ids = self.env['n.manufacturing.request'].search([('n_product_id','in',product_id),('n_state','in',['new','draft'])])
                print "prod_req_idsprod_req_idsprod_req_ids",prod_req_ids
                if prod_req_ids:
                    for each in prod_req_ids:
                        prod_count_now += each.n_order_qty
                res.prod_count_var=prod_count_now
	@api.multi
	def _get_in_data(self):
            for res in self:
                prod_count=0.0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
                product_id = [p.id for p in product_id]

                prod_req_ids = self.env['stock.move'].search([('picking_type_id.code','=','incoming'),('product_id','in',product_id),('state','in',['assigned'])])
                print "prod_req_idsprod_req_idsprod_req_ids",prod_req_ids
                if prod_req_ids:
                        prod_count += each.product_uom_qty
                            
                res.in_count=str(prod_count)
	@api.multi
	def _get_in_data_var(self):
            for res in self:
                prod_count=0.0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
                product_id = [p.id for p in product_id]

                prod_req_ids = self.env['stock.move'].search([('picking_type_id.code','=','incoming'),('product_id','in',product_id),('state','in',['assigned'])])
                print "prod_req_idsprod_req_idsprod_req_ids",prod_req_ids
                if prod_req_ids:
                    for each in prod_req_ids:
                        prod_count += each.product_uom_qty
                res.in_count_var=prod_count
	@api.multi
        @api.depends('prod_count')
	def _get_prod_orders_count(self):
            for res in self:
                if res.prod_count:
                    res.prod_count_var=res.prod_count
	@api.multi
        @api.depends('mo_count')
	def _count_mo(self):
            for res in self:
                if res.mo_count:
                    res.mo_count_var=res.mo_count
	@api.multi
	def _get_bill_data(self):
            for res in self:
                product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
                product_id = [p.id for p in product_id]

                inv_line_ids = self.env['account.invoice.line'].search([('product_id','in',product_id)])
                inv_ids=[]
                if inv_line_ids:
                    for each in inv_line_ids:
                        if each.invoice_id.id not in inv_ids:
                            inv_ids.append(each.invoice_id.id)
                    res.bill_count = str(len(inv_ids))

	@api.multi
	def open_master_batches(self):
		order_tree = self.env.ref('api_inventory.master_batches_detail_tree_view', False)
		order_form = self.env.ref('api_inventory.master_batch_form_view', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':"'{}' Batches in Warehouse".format(self.name),
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'stock.store.master.batch',
		    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'domain':[('product_id','in',product_id),("logistic_state","in",('transit_in',
								'stored','reserved','r_t_dispatch','transit'))],
		    'target': 'current',
		 }
                 

	@api.multi
	def open_expenses(self):
		order_tree = self.env.ref('hr_expense.view_expenses_tree', False)
		order_form = self.env.ref('hr_expense.hr_expense_form_view', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':"'{}'Expenses".format(self.name),
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'hr.expense',
		    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'domain':[('product_id','in',product_id)],
		    'target': 'current',
		 }
        @api.multi
        def _bom_orders_count_mo(self):
            Production = self.env['mrp.production']
            res = {}
            for rec in self:
                count=0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
                mo_ids = Production.search([('product_id', '=', product_id.id),('state','not in',['done','cancel'])])
                print "mo_idsmo_idsmo_idsmo_ids",mo_ids
                if mo_ids:
                    print "mo_idsmo_idsmo_ids",mo_ids
                    for each_mo in mo_ids:
                        count+=each_mo.product_qty-each_mo.n_produce_qty
                        print "countcountcountcountcount",count,each_mo.n_request_qty-each_mo.n_produce_qty
            rec.mo_count=str(count)
            return res
        @api.multi
        def _count_mo_var(self):
            Production = self.env['mrp.production']
            for rec in self:
                count=0
                product_id = self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
                mo_ids = Production.search([('product_id', '=', product_id.id),('state','not in',['done','cancel'])])
                print "mo_idsmo_idsmo_idsmo_ids",mo_ids
                if mo_ids:
                    print "mo_idsmo_idsmo_ids",mo_ids
                    for each_mo in mo_ids:
                        count+=each_mo.product_qty-each_mo.n_produce_qty
                        print "countcountcountcountcount",count,each_mo.n_request_qty-each_mo.n_produce_qty
            rec.mo_count_var=count

	@api.multi
	def open_prod_orders(self):
		order_tree = self.env.ref('gt_order_mgnt.n_production_request_tree', False)
		order_form = self.env.ref('gt_order_mgnt.mrp_production_request_form', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':"'{}'Production Orders".format(self.name),
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'n.manufacturing.request',
		    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'domain':[('n_product_id','in',product_id)],
		    'target': 'current',
		 }
	@api.multi
	def open_in_orders(self):
		order_tree = self.env.ref('stock.view_move_tree', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':"'{}'Move IN Orders".format(self.name),
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'stock.move',
		    'views': [(order_tree.id, 'tree')],
		    'view_id': order_tree.id,
		    'domain':[('product_id','in',product_id)],
		    'target': 'current',
		 }
	
	@api.multi
	def open_bills(self):
		order_tree = self.env.ref('account.invoice_supplier_tree', False)
		order_form = self.env.ref('account.invoice_supplier_form', False)
		inv_line_ids = self.env['account.invoice.line'].search([('product_id.product_tmpl_id','=',self.id)])
                acc_inv_ids=[]

                if inv_line_ids:
                    for each in inv_line_ids:
                        if each.invoice_id.id not in acc_inv_ids:
                            acc_inv_ids.append(each.invoice_id.id)
                return {
                    'name':"'{}'Bills".format(self.name),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'account.invoice',
                    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
                    'view_id': order_form.id,
                    'domain':[('id','in',acc_inv_ids)],
                    'target': 'current',
                    }
	

	@api.multi
	def open_child_batches(self):
		order_tree = self.env.ref('api_inventory.batch_details_tree_view', False)
		order_form = self.env.ref('api_inventory.batch_details_form_view', False)
		product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
		product_id = [p.id for p in product_id]
		return {
		    'name':"'{}' Batches in Warehouse".format(self.name),
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'tree',
		    'res_model': 'mrp.order.batch.number',
		    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
		    'view_id': order_form.id,
		    'domain':[('product_id','in',product_id),("logistic_state","in",('transit_in',
								'stored','reserved','r_t_dispatch','transit'))],
		    'target': 'current',
		 }
	
	reordering_min_qty = fields.Float(string="Minimum Stock Qty",compute="_compute_min_stock_qty")	 
	@api.model
	def _compute_min_stock_qty(self):
        	for res in self:
        		for i in res.product_variant_ids.orderpoint_ids.filtered(lambda x: x.active):
				res.reordering_min_qty = i.product_min_qty
			
class productProduct(models.Model):
	_inherit = "product.product"
        

	mo_count = fields.Char('#Manufacturing',compute='_bom_orders_count')
	prod_count = fields.Char('#Production Orders',compute='_prod_orders_count')
	@api.multi
	def _prod_orders_count(self):
            for res in self:
                prod_count=0.0
                prod_req_ids = self.env['n.manufacturing.request'].search([('n_product_id','=',res.id),('n_state','in',['new','draft'])])
                print "prod_req_idsprod_req_idsprod_req_ids",prod_req_ids
                if prod_req_ids:
                    for each in prod_req_ids:
                        prod_count += each.n_order_qty
                res.prod_count=str(prod_count)
	@api.multi
	def open_inventory_location(self):
		return self.product_tmpl_id.open_inventory_location()

	@api.multi
	def open_master_batches(self):
		return self.product_tmpl_id.open_master_batches()
	@api.multi
	def open_expenses(self):
		return self.product_tmpl_id.open_expenses()
	@api.multi
	def open_prod_orders(self):
		return self.product_tmpl_id.open_prod_orders()
	@api.multi
	def open_in_orders(self):
		return self.product_tmpl_id.open_in_orders()
	@api.multi
	def open_bills(self):
		return self.product_tmpl_id.open_bills()

	@api.multi
	def open_child_batches(self):
		return self.product_tmpl_id.open_child_batches()

	@api.model
	def name_search(self,name, args=None, operator='ilike', limit=100):
		''' function to show product from multi store product location'''
		if self._context.get('multi_loc'):
			if self._context.get('store_id'):
				store_ids=self.env['store.multi.product.data'].search([('store_id','=',self._context.get('store_id'))])
				args=[('id','in',[rec.product_id.id for rec in store_ids])]
				return super(productProduct,self).name_search(name, args, operator=operator, limit=limit)
			return []
			
		result = super(productProduct,self).name_search(name, args, operator=operator, limit=limit)
		## code to show product on internal name
		if name:
			new_ids = self.search([('internal_name','ilike',str(name))])
			if new_ids:
		        	result += new_ids.name_get()
	    	return result
		
	# inherite method to restrict quantity to show only  in store location
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
		loc_id=self.pool.get('stock.location').search(cr,uid,[('actual_location','=',True)])
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
			#domain + [('location_id', operator, location_ids)], # coment it to get location
			domain + [('location_id','in',loc_id)],
			domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
			domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)]
		    )
        @api.multi
        def _bom_orders_count(self):
            Production = self.env['mrp.production']
            res = {}
            count=0
            for product_id in self:
                mo_ids = Production.search([('product_id', '=', product_id.id),('state','not in',['done','cancel'])])
                print "mo_idsmo_idsmo_idsmo_ids",mo_ids
                if mo_ids:
                    for each_mo in mo_ids:
                        count+=each_mo.n_request_qty-each_mo.n_produce_qty
            product_id.mo_count=str(count)
            return res

    ## inherite code to update forcasting 
	@api.v7
	def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
		context = context or {}
		field_names = field_names or []

		domain_products = [('product_id', 'in', ids)]
		domain_quant, domain_move_in, domain_move_out = [], [], []
		domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations(cr, uid, ids, context=context)
		domain_move_in += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft'))] + domain_products
		domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state', 'not in', ('done', 'cancel', 'draft','dispatch','transit','delivered'))] + domain_products
		domain_quant += domain_products

		if context.get('lot_id'):
		    domain_quant.append(('lot_id', '=', context['lot_id']))
		if context.get('owner_id'):
		    domain_quant.append(('owner_id', '=', context['owner_id']))
		    owner_domain = ('restrict_partner_id', '=', context['owner_id'])
		    domain_move_in.append(owner_domain)
		    domain_move_out.append(owner_domain)
		if context.get('package_id'):
		    domain_quant.append(('package_id', '=', context['package_id']))

		domain_move_in += domain_move_in_loc
		domain_move_out += domain_move_out_loc
		moves_in = self.pool.get('stock.move').read_group(cr, uid, domain_move_in, ['product_id', 'product_qty'], ['product_id'], context=context)
		moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)

		domain_quant += domain_quant_loc
		quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
		quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

		moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
		moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))
		res = {}
		ctx = context.copy()
		ctx.update({'prefetch_fields': False})
		for product in self.browse(cr, uid, ids, context=ctx):
		    id = product.id
		    qty_available = float_round(quants.get(id, 0.0), precision_rounding=product.uom_id.rounding)
                    print "qty_availableqty_availableqty_available",qty_available
		    incoming_qty = float_round(moves_in.get(id, 0.0), precision_rounding=product.uom_id.rounding)
		    outgoing_qty = float_round(moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
		    virtual_available = float_round(quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0), precision_rounding=product.uom_id.rounding)
                    print "incoming_qtyincoming_qty",incoming_qty,outgoing_qty,virtual_available
		    res[id] = {
		        'qty_available': qty_available,
		        'incoming_qty': incoming_qty,
		        'outgoing_qty': outgoing_qty,
		        'virtual_available': virtual_available,
		    }
		return res

class productPackging(models.Model):
    _inherit = 'product.packaging'
    
    @api.model
    def name_search(self,name, args=None, operator='ilike', limit=100):
    	# fOR STORE Opeartion currenlty not in use
	if self._context.get('primary'):
		if self._context.get('product_id'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))])
			packg=self.search([('pkgtype','=','primary'),('product_tmpl_id','=',product_id.product_tmpl_id.id)])
                	return [(rec.id,rec.name) for rec in packg]
        	return []
        	
	# use in picking operation(input -> stock)
	if self._context.get('secondary'):
		if self._context.get('product_id') and self._context.get('primary_packaging'):
			primary_packaging = self.search([('id','=',self._context.get('primary_packaging'))])
			product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))])
			packg=self.search([('pkgtype','=','secondary'),('unit_id','=',primary_packaging.uom_id.id),
						('product_tmpl_id','=',product_id.product_tmpl_id.id)])
                	return [(rec.id,rec.name) for rec in packg]
        	return []
    	return super(productPackging,self).name_search(name, args, operator=operator, limit=limit)
    
    @api.multi	
    def write(self,vals):
    	for res in self:
		if res.product_tmpl_id:
    			if vals.get('qty') :
    				store =self.env['n.warehouse.placed.product'].search([('Packaging_type','=',res.id)])
				store_1 =self.env['store.multi.product.data'].search([('Packaging_type','=',res.id)])
    				if store or store_1:
    					raise UserError(_("Packaging used in store, You can't Decrease the packaging quantity"))
    				sale =self.env['sale.order.line'].search([('product_packaging','=',res.id),
    									 ('order_id.state','=','done')])
    				if sale:
    					raise UserError(_("Packaging used in done sale order, You can't change the \
    					 packaging quantity, please add new packaging or contact administrator"))
				operation =self.env['stock.pack.operation'].search(['|',('secondary_pack','=',res.id),
								('packaging_id','=',res.id),
								 ('picking_id.state','in',('done','delivered'))])
    				if operation:
    					raise UserError(_("Packaging used in Delivery order which is Dispatched,\
    						 You can't change the packaging quantity, please add new packaging \
    						 or contact Administrator"))
    					
			if vals.get('uom_id') and res.uom_id:
				uom_id=self.env['product.uom'].search([('id','=',vals.get('uom_id'))])
				sale =self.env['sale.order.line'].search([('product_packaging','=',res.id),
    									 ('order_id.state','=','done')])
			 	store =self.env['n.warehouse.placed.product'].search([('Packaging_type','=',res.id)])
				store_1 =self.env['store.multi.product.data'].search([('Packaging_type','=',res.id)])
				if uom_id and (sale or store or store_1): 
					if set(uom_id.unit_type.mapped('string'))-set(res.uom_id.unit_type.mapped('string')):
						raise UserError(_("You can't change the packaging Type Unit which are different Unit type, please add new Packaging or contact administrator"))
						
    	return super(productPackging,self).write(vals)

    @api.multi	
    def unlink(self):
    	for res in self:
		if res.product_tmpl_id:
			store =self.env['n.warehouse.placed.product'].search([('Packaging_type','=',res.id)])
			store_1 =self.env['store.multi.product.data'].search([('Packaging_type','=',res.id)])
			if store or store_1:
				raise UserError(_("Packaging used in store, You can't Delete Packaging"))
			operation =self.env['stock.pack.operation'].search(['|',('secondary_pack','=',res.id),
								('packaging_id','=',res.id),
								 ('picking_id.state','in',('done','delivered'))])
			if operation:
				raise UserError(_("Packaging used in Delivery/Receving, You can't Delete Packaging"))
    	return super(productPackging,self).unlink()
    
class ProductUom(models.Model):
    _inherit = "product.uom"
    
    @api.model
    def name_search(self,name, args=None, operator='ilike',limit=100):
	# not in use
	if self._context.get('release'):
		if self._context.get('release_product'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('release_product'))])
			packg = self.env['product.packaging'].search([('product_tmpl_id','=',product_id.product_tmpl_id.id)])
			if packg:
				return [(rec.unit_id.id,rec.unit_id.name) for rec in packg]
		return []

	# bin location storage unit	
	if self._context.get('store_unit'):
		units = self.search([('unit_type.string','=','store')])
		args=[('id','in',list(units._ids))]
    	return super(ProductUom,self).name_search(name, args, operator=operator,limit=limit)
		    
class procurementOrder(models.Model):
    _inherit = "procurement.order"
    
    @api.model
    def run_moq_schudular(self):
    	'''Function to Send Mail to Logistics Manager AND Sale Support,
    	    When Available Quantity in below minimum stock Quantity '''
    	mail_obj = self.env['mail.mail']
    	inventory_vals=contract_vals={}
    	contract_vals['subject'] = "Contract Minimum Stock Quantity Alert" 
	contract_vals['email_from'] = str(self.env.user.email)
	contract_vals['reply_to'] = ''
	contract_falg = invnetory_flag =False
	cbody_html = '''<table border="1" solid="1"> <th>Contract</th>
					<th>Product Name</th>
					<th>Qty in Stock</th>
					<th>Minimum Stock Qty</th>
					<th>Unit</th>'''
	contract_ids= self.env['contract.product.line'].search([('product_id','!=',False),('cont_id','!=',False),
    						('cont_id.state','in',('contract','sale')),
    						('cont_id.expiry_date','>',date.today())])
	for crct in contract_ids:
		if crct.remaining_qty > 0 and crct.qty_avl < crct.product_msq:
			if crct.remaining_qty > crct.qty_avl:
				contract_falg = True
              			cbody_html += '<tr><td> {} </td>'.format(crct.cont_id.name)
              			cbody_html += '<td> [{}]{} </td>'.format(crct.product_id.default_code,crct.product_id.name)
              			cbody_html += "<td align='center'> {} </td>".format(crct.product_id.qty_available)
              			cbody_html += "<td align='center'> {} </td>".format(crct.product_msq)
              			cbody_html += "<td> {} </td>".format(crct.uom_id.name)
              			cbody_html += '</tr>'

	contract_vals['body_html'] = cbody_html+'</table>' 
	if contract_vals and contract_falg:
		recipient_partners = []
		group_id = self.env['ir.model.data'].get_object_reference('api_inventory','group_contract_msq_alert')[1]
		for usr in self.env['res.groups'].search([('id', '=',group_id)]).users:
			recipient_partners.append(str(usr.login))
		contract_vals['email_to'] = ",".join(recipient_partners)
		if recipient_partners:
	         	cmsg_id = mail_obj.create(contract_vals)
 			if cmsg_id:
        	 		cmsg_id.send()
        
        ibody_html= '''<table border="1" solid="1"> 
					<th>Product Name</th>
					<th>Qty in Stock</th>
					<th>Minimum Stock Qty</th>
					<th>Warehouse</th>
					<th>Unit</th>'''
								
	orderpoint_ids = self.env['stock.warehouse.orderpoint'].search([('active','=',True)])
	inventory_vals['subject'] = "Warehouse Minimum Stock Quantity Alert" 
	inventory_vals['email_from'] = str(self.env.user.email)
	inventory_vals['reply_to'] = ''
	for pro in orderpoint_ids:
		if pro.product_id.qty_available < pro.product_min_qty:
			invnetory_flag = True
              		ibody_html += '<tr>'
              		ibody_html += '<td> [{}]{} </td>'.format(pro.product_id.default_code,pro.product_id.name)
              		ibody_html += "<td align='center'> {} </td>".format(pro.product_id.qty_available)
              		ibody_html += "<td align='center'> {} </td>".format(pro.product_min_qty)
              		ibody_html += '<td> {} </td>'.format(pro.warehouse_id.name)
              		ibody_html += '<td> {} </td>'.format(pro.product_uom.name)
              		ibody_html += '</tr>'
              		
	inventory_vals['body_html'] = ibody_html+'</table>'
	if inventory_vals and invnetory_flag:
		recipient_partners = []
		group_id = self.env['ir.model.data'].get_object_reference('api_inventory','group_inventory_msq_alert')[1]
		for usr in self.env['res.groups'].search([('id', '=',group_id)]).users:
			recipient_partners.append(str(usr.login))
			
		inventory_vals['email_to'] = ",".join(recipient_partners)
		if recipient_partners:
	         	imsg_id = mail_obj.create(inventory_vals)
        	 	if imsg_id :
        	 		imsg_id.send()
         		
         		
