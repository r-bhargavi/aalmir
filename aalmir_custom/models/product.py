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

			
class productProduct(models.Model):
	_inherit = "product.product"
        
        @api.multi
        def n_get_prod_pricelist(self):
            for rec in self:
                produt_id=self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
                cust_prod_ids = self.env['customer.product'].search([('product_id','in', [p_id.id for p_id in produt_id])])
                pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
                rec.n_pricelist_count = len(pids)


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


        @api.multi
        def n_get_prod_pricelist(self):
            for rec in self:
                produt_id=self.env['product.product'].search([('product_tmpl_id','=',rec.id)])
                cust_prod_ids = self.env['customer.product'].search([('product_id','in', [p_id.id for p_id in produt_id])])
                pids = [o.pricelist_id.id for o in cust_prod_ids if o.pricelist_id]
                rec.n_pricelist_count = len(pids)
    
        
        @api.multi
        def _purchase_count(self):
            for product in self:
                product.purchase_count = sum([p.purchase_count for p in product.product_tmpl_id.product_variant_ids])
            return True
	
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



        
        purchase_count = fields.Integer(compute='_purchase_count', string='# Purchases')

        master_btch_count = fields.Char('Master Batches',compute='_get_batches_data')
	batches_count = fields.Char('#Batches',compute='_get_batches_data')
	bin_location_count = fields.Integer('#Bin Location',compute='_get_batches_data')
        n_pricelist_count = fields.Integer(string="Customers", compute=n_get_prod_pricelist, default=0)
        quotation_count = fields.Integer(compute='_quotation_count', string='# Quotations')
        
