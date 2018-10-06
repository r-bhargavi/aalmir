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
from datetime import datetime,date
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import UserError, AccessError
from urlparse import urljoin
from urllib import urlencode
#CH_N065 start >>

class productProduct(models.Model):
    _inherit = 'product.product'
    
    qty_scrapped=fields.Float(compute='action_open_scrap',digits_compute=dp.get_precision('Product Unit of Measure'),string='Quantity Scrapped')
    
    
    @api.multi     
    def action_open_scrap(self):
        print "sdfsdsdsdf"
        for line in self:
            quant_tree = self.env.ref('stock.view_stock_quant_tree', False)
            quant_form = self.env.ref('stock.view_stock_quant_form', False)
            scrap_locations=self.env['stock.location'].search([('scrap_location','=',True)])
            quants_count=self.env['stock.quant'].search([('product_id','=',line.id),('location_id','in',scrap_locations.ids)])
            print "quants_countquants_countquants_count",quants_count
            if quants_count:
                quant_qty=sum(x.qty for x in quants_count)
                print "quant_qtyquant_qty",quant_qty
                line.qty_scrapped=quant_qty
            else:
                line.qty_scrapped=0.0
            
            if quant_tree:
                return {
                    'name':'Scrapped',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'stock.quant',
                    'views': [(quant_tree.id, 'tree'),(quant_form.id, 'form')],
                    'view_id': quant_tree.id,
                    'target': 'current',
                    'domain':[('product_id','=',line.id),('location_id','in',scrap_locations.ids)],
                }
        return True


    @api.v7
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('rm_schedule'):
           if context.get('production'):
              product_qry="select product_id from mrp_production_product_line where rm_type ='stock' and production_id={}".format(context.get('production'))
              cr.execute(product_qry)
              product_ids=[i[0] for i in cr.fetchall()]
              args.extend([('id','in',product_ids)])
        if context.get('order_product'):
            if context.get('sale_id'):
                args=[]
                product_qry="select product_id from sale_order_line where order_id={}".format(context.get('sale_id'))
                cr.execute(product_qry)
                product_ids=[i[0] for i in cr.fetchall()]
                args.extend([('id','in',product_ids)])
        if context.get('contract_product'):
            if context.get('pricelist_id'):
                args=[]
                product_qry="select product_id from customer_product where pricelist_id={}".format(context.get('pricelist_id'))
                cr.execute(product_qry)
                product_ids=[i[0] for i in cr.fetchall()]
                args.extend([('id','in',product_ids)])

        # used in product report
	if context.get('p_report'):
           if context.get('partner_id'):
              args=[]
              pricelist=self.pool.get('product.pricelist').search(cr,uid,[('customer','=',context.get('partner_id'))],context=context)
              prod=[]
              if pricelist:
                 for prl in self.pool.get('product.pricelist').browse(cr, uid, pricelist):
                     for customer_p in prl.cus_products:
                         prod.append(customer_p.product_id.id)
              #product_qry="select product_id from customer_product where pricelist_id=(select id  from product_pricelist where customer={} limit 1)".format(context.get('partner_id'))
              #cr.execute(product_qry)
              #product_ids=[i[0] for i in cr.fetchall()]
              args.extend([('id','in',prod)])
        return super(productProduct,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

# Inherite to update state in calculation
    @api.multi
    def _purchase_count(self):
        domain = [
            ('state', 'in', ['purchase', 'done','sent po']),
            ('product_id', 'in', self.mapped('id')),
        ]
        r = {}
        for group in self.env['purchase.report'].read_group(domain, ['product_id', 'quantity'], ['product_id']):
            r[group['product_id'][0]] = group['quantity']
        for product in self:
            product.purchase_count = r.get(product.id, 0)
        return True
        
    @api.onchange('initial_weight')
    def onchange_weight(self):
    	if self.initial_weight:
    		self.weight=self.initial_weight

    @api.onchange('product_material_type')
    def _hide_type(self): 
    	for rec in self:
    		rec.matstrg = rec.product_material_type.string
    		rec.raw_material_type = False
    		rec.categ_id = False

    @api.multi
    def action_view_reserve(self):
        return self.product_tmpl_id.action_view_reserve()

    @api.multi
    def action_view_mos(self):
        return self.product_tmpl_id.action_view_mos()

    @api.multi
    def action_view_orderpoints(self):
        return self.product_tmpl_id.action_view_orderpoints()

    @api.multi
    def action_view_stock_moves(self):
        return self.product_tmpl_id.action_view_stock_moves()

    @api.multi
    def action_open_quants(self):
        return self.product_tmpl_id.action_open_quants()
    
    @api.multi
    def action_view_po(self):
    	return self.product_tmpl_id.action_view_po()
    	
    @api.multi
    def open_production_request(self):
        for line in self:
            production_tree = self.env.ref('gt_order_mgnt.n_production_request_tree_history', False)
            production_form = self.env.ref('gt_order_mgnt.mrp_production_request_form', False)
            if production_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree, form',
                    'res_model': 'n.manufacturing.request',
                    'views': [(production_tree.id, 'tree'), (production_form.id, 'form')],
                    'view_id': production_tree.id,
                    'target': 'current',
                    'domain':[('n_product_id','=',self.id), ('n_state','not in',('done','cancel'))],
                }
        return True

    @api.multi
    def make_manufacture(self):
        return self.product_tmpl_id.make_manufacture()

    @api.multi
    def write(self,vals):
    	for rec in self:
    		body=""
    		attributes_table=self.env['n.product.discription.value']
		if vals.get('n_production_tolerance'):
			body +="<li> Tolerance Updated From "+str(rec.n_production_tolerance)+" To "+str(vals.get('n_production_tolerance'))+'</li>'

		if vals.get('initil_weight'):
			body +="<li> Gross Weight Updated From "+str(rec.weight)+" To "+str(vals.get('initil_weight'))+'</li>'

		if vals.get('weight'):
			body +="<li> Net Weight Updated From "+str(rec.weight)+" To "+str(vals.get('weight'))+'</li>'
		
		if vals.get('product_hs_code'):
			body +="<li>Hs Code Updated From "+str(rec.product_hs_code)+" To "+str(vals.get('product_hs_code'))+'</li>'

		if vals.get('uom_id'):
			punit=self.env['product.uom'].search([('id','=',vals.get('uom_id'))])
			body +="<li> Unit Updated From "+str(rec.uom_id.name if rec.uom_id else '')+" To "+str(punit.name)+'</li>'

		if vals.get('uom_po_id'):
			punit=self.env['product.uom'].search([('id','=',vals.get('uom_po_id'))])
			body +="<li> Unit Updated From "+str(rec.uom_po_id.name if rec.uom_po_id else '')+" To "+str(punit.name)+'</li>'

	# add code to get history of product changes		
		if vals.get('discription_line'):
			added=''
			update=''
			removed=''
			body +="<li> Specification Updated"
			for line in vals.get('discription_line'):
				if type(line[2]) == dict:
					if line[0]==0:
						unit=''
						if line[2].get('value'):
							unit=self.env['product.uom'].search([('id','=',line[2].get('unit'))])
						attribute=attributes_table.search([('id','=',line[2].get('attribute'))])
						added +='<li><span style="color:green">'+str(attribute.name)+'</span> : value: '+str(line[2].get('value'))+(' Unit : '+(unit.name) if unit else '')+'</li>'
					if line[0]==1:
						unit=''
						if line[2].get('unit'):
							unit=self.env['product.uom'].search([('id','=',line[2].get('unit'))])
						record=self.env['n.product.discription'].browse(line[1])
						attribute=attributes_table.search([('id','=',line[2].get('attribute'))])
						if line[2].get('attribute'):
							update +='<li><span style="color:green">'+str(record.attribute.name)+' <span style="color:black">TO </span>'+str(attribute.name)+': </span>'+(' value: '+str(line[2].get('value')) if line[2].get('value') else '' )+(' Unit : '+(unit.name) if unit else '')+'</li>'
						else:
							update +='<li><span style="color:green">'+record.attribute.name+': </span>'+(' value: '+str(line[2].get('value')) if line[2].get('value') else '' )+(' Unit : '+(unit.name) if unit else '')+'</li>'
				if line[0]==2:
					attrs=self.env['n.product.discription'].browse(line[1])
					removed +='<li><span style="color:green">'+str(attrs.attribute.name)+'</span></li>'
			body += ('<ul> New Speficifation'+added+'</ul>' if added else '')+('<ul>Update Specification'+update+'</ul>' if update else '')+('<ul>Remove Specification'+removed+'</ul>' if removed else '')
			body +="</li>"

		if vals.get('description_sale'):
			body +='<li><span style="color:blue">Sale Description Changed:</span>'+str(vals.get('description_sale'))+'</li>'

		if vals.get('description_purchase'):
			body +='<li><span style="color:blue">Purchase Description Changed:</span>'+str(vals.get('description_purchase'))+'</li>'

		if vals.get('description_picking'):
			body +='<li><span style="color:blue">Delivery Description Changed:</span>'+str(vals.get('description_picking'))+'</li>'

		if vals.get('description_mrp'):
			body +='<li><span style="color:blue">Manufacturing Description Changed:</span>'+str(vals.get('description_mrp'))+'</li>'

		if vals.get('product_material_type'):
			material=self.env['product.material.type'].search([('id','=',vals.get('product_material_type'))])
			if not rec.product_material_type:
				body +="<li>Product Material Type Added "+str(material.name)+"</li>"
			else:
				body +="<li>Product Type Updated From "+str(rec.product_material_type.name)+" TO "+str(material.name)+"</li>"

		if vals.get('raw_material_type'):
			raw=self.env['product.raw.material.type'].search([('id','=',vals.get('raw_material_type'))])
			if not rec.raw_material_type:
				body +="<li>Material Type Added "+str(raw.name)+"</li>"
			else:
				body +="<li>Material Type Updated From "+str(rec.raw_material_type.name)+" TO "+str(raw.name)+"</li>"

		if vals.get('machine_type_ids'):
			body +="<li>Manufacturing type Updated </li>"
		if vals.get('packaging_ids'):
			body +="<li>Packaging Updated </li>"
		if vals.get('seller_ids'):
			body +="<li>Vendors Changed </li>"
		if vals.get('list_price'):
			body +="<li>Selling Price Changed from {} To {} </li>".format(rec.list_price,vals.get('list_price'))
		if body:
			rec.message_post(body=body)
	vals.update({'rental':True})
	return super(productProduct,self).write(vals)
	
#CH_N065 <<<<
class productTemplateProcess(models.Model):
    _name = 'product.template.process'
    
    process_id=fields.Many2one('mrp.workcenter.process', string='Process Type')
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process" )
    machine = fields.Many2one('machinery', string='Machine', )
    machine_type_ids=fields.Many2many('machinery.type', related='workcenter_id.machine_type_ids')
    capacity_per_cycle=fields.Float('Capacity Per Cycle', compute='changecapacity')
    capacity_per_cycle_option=fields.Float('Capacity Per Cycle')
    time_cycle=fields.Float('Time Cycle', compute='timecycle')
    hour=fields.Integer('Hour')
    minute=fields.Integer('Minute')
    second=fields.Integer('Second')
    unit_id=fields.Many2one('product.uom',string='Unit', related='workcenter_id.product_uom_id')
    product_id=fields.Many2one('product.template')
    time_option=fields.Selection([('1','1x'),('2','2x'),('3','3x'),
                               ('4', '4x'),('5', '5x')], string='Production Output', default='1')
    @api.multi
    @api.onchange('machine')
    def capacityinformation(self):
        for record in self:
            if  record.machine.capacity_per_cycle :
                record.capacity_per_cycle_option=record.machine.capacity_per_cycle
                record.hour=record.machine.hour
                record.minute=record.machine.minute
                record.second=record.machine.second
            else:
                record.hour=0.0
                record.minute=0.0
                record.second=0.0
    @api.multi
    @api.depends('hour','minute','second')
    def timecycle(self):
        for record in self:
            hr=(record.hour * 60 *60)  +(record.minute*60 + record.second)
            record.time_cycle= hr * 0.000277778
    @api.multi
    @api.depends('time_option','capacity_per_cycle_option')
    def changecapacity(self):
        for record in self:
            if record.capacity_per_cycle_option:
               record.capacity_per_cycle= float(record.time_option) * record.capacity_per_cycle_option
    
class productTemplate(models.Model):
    _inherit = 'product.template'
        
    
    @api.multi
    def _get_product_profile(self):
    	for rec in self:
    		percentage=100
    		val=''
    		material_string = ''
    		if rec.product_material_type:
			material_string=rec.product_material_type.string
		else:
			percentage -= 3
			val += '<li>Product Material Type</li>'
					
		if material_string in ('raw','asset'):
			if not rec.raw_material_type:
				percentage -= 3
				val += '<li>Raw Material Type</li>'
    		
    		percentage += 0 if rec.default_code else -1
    		val += '<li>Default Code</li>' if not rec.default_code else ''
    		percentage += 0 if rec.categ_id else -1
    		val += '<li>Internal Category</li>' if not rec.categ_id else ''
    		if material_string in ('product','component'):
    			percentage += 0 if rec.description_sale else -3
    			val += '<li>Description on Quotation</li>' if not rec.description_sale else ''
    			percentage += 0 if rec.description_mrp else -3
    			val += '<li>Instruction for Manufacturing</li>' if not rec.description_mrp else ''
			percentage += 0 if rec.n_production_tolerance else -2
    			val += '<li>Product Tolerance</li>' if not rec.n_production_tolerance else ''
    			percentage += 0 if rec.route_ids else -5
    			val += '<li>Routing Of product</li>' if not rec.route_ids else ''
    			bom = self.env['mrp.bom'].search([('product_tmpl_id','=',rec.id)])
			percentage += 0 if bom else -20
	    		val += '<li>Bill of Material </li>' if not bom else ''
    			percentage += 0 if rec.process_ids else -10
    			val += '<li>Manufacturing Process</li>' if not rec.process_ids else ''
    			
    		if material_string =='asset':
    			if rec.raw_material_type.string == 'part' and not rec.machine_id:
    				percentage += -5
    				val += '<li>Part Machine Details</li>'
			if rec.raw_material_type.string == 'plate' and not rec.plate_product_id:
				percentage += -5
    				val += '<li>Printing Plate product</li>'
			if rec.raw_material_type.string == 'machine' :
				if not rec.machinary_id:
					percentage += -5
    					val += '<li>Machine details</li>'
				'''if not rec.time_cycle:
					percentage += -1
    					val += '<li>Machine Time Cycle</li>'
				if not rec.time_efficiency:
					percentage += -1
    					val += '<li>Machine Time Efficiency</li>'
				if not rec.hour:
					percentage += -1
    					val += '<li>Machine Time in Hours</li>'
				if not rec.minute:
					percentage += -1
    					val += '<li>Machine Time in Minutes</li>'
				if not rec.second:
					percentage += -1
    					val += '<li>Machine Time in Second</li>'''
    			
    		percentage += 0 if rec.description_picking else -3
    		val += '<li>Instruction for Logistics</li>' if not rec.description_picking else ''
    		percentage += 0 if rec.weight else -5
    		val += '<li>Weight</li>' if not rec.weight else ''
		percentage += 0 if rec.uom_id else -5
    		val += '<li>Unit</li>' if not rec.uom_id else ''
    		
    		if material_string !='asset':
    			percentage += 0 if rec.packaging_ids else -5
    			val += '<li>Product Packaging</li>' if not rec.packaging_ids else ''
    		
    		percentage += 0 if rec.discription_line else -10
    		val += '<li>Product Description</li>' if not rec.discription_line else ''
    		
		if rec.purchase_ok:
			if not rec.description_purchase:
				percentage -= 3
				val += '<li>Purchase Description</li>'
			if not rec.seller_ids:
				percentage -= 3
				val += '<li>Purchase Vendors</li>'
				
    		rec.progress_rate = percentage
    		rec.progress_value = val
                
    qty_scrapped=fields.Float(compute='action_open_scrap',digits_compute=dp.get_precision('Product Unit of Measure'),string='Quantity Scrapped')
    produce_delay_qty = fields.Integer('Manufacturing Quantity', default=1)
    product_hs_code=fields.Char('Hs Code')
    net_weight=fields.Float('Net Weight')
    production_rqst_id=fields.One2many('production.request.detail', 'product_id')

    manufacturing_rqt_id=fields.One2many('n.manufacturing.request','n_product_id')
    production_count=fields.Float('Production', compute='total_production_qty')
    n_upload = fields.One2many('customer.upload.doc','sale_tmpl_id')	#CH_N065
    trial_orders_count=fields.Integer(compute='total_trial_orders')
    trial_form_count=fields.Integer(compute='total_trial_form')
    customer_pricelist_ids = fields.One2many('customer.product','product_tmpl_id')	#CH_N065
    initial_weight=fields.Float('Initial Weight', digits=dp.get_precision('Stock Weight'))
    
    machine_count = fields.Integer(compute='_compute_machine_count', string='Machines')
    process_ids=fields.One2many('product.template.process' ,'product_id', string="MO Process")
           
    discription_line = fields.One2many('n.product.discription','product_id','Product Discription')
    description_mrp=fields.Text()
    product_upload = fields.One2many('customer.upload.doc','tmpl_id') 
    progress_rate = fields.Integer("Product Profile",compute="_get_product_profile")
    progress_value = fields.Html('Values Not Filled',compute="_get_product_profile",readonly=True)
    #pvinvisible = fields.Boolean('Invisible Progress Details',help="Check this filed to show required details to complete this product profile")
    packaging_uom_id=fields.Many2one('product.uom')
    #purchase_approved_price=fields.Float('Purchase Apporved Price') 
    
    @api.multi     
    def action_open_scrap(self):
        print "sdfsdsdsdf"
        for line in self:
            quant_tree = self.env.ref('stock.view_stock_quant_tree', False)
            quant_form = self.env.ref('stock.view_stock_quant_form', False)
            product_id=self.env['product.product'].search([('product_tmpl_id','=',line.id)])
            scrap_locations=self.env['stock.location'].search([('scrap_location','=',True)])
            quants_count=self.env['stock.quant'].search([('product_id','=',product_id[0].id),('location_id','in',scrap_locations.ids)])
            print "quants_countquants_countquants_count",quants_count
            if quants_count:
                quant_qty=sum(x.qty for x in quants_count)
                print "quant_qtyquant_qty",quant_qty
                line.qty_scrapped=quant_qty
            else:
                line.qty_scrapped=0.0
            
            if quant_tree:
                return {
                    'name':'Scrapped',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'stock.quant',
                    'views': [(quant_tree.id, 'tree'),(quant_form.id, 'form')],
                    'view_id': quant_tree.id,
                    'target': 'current',
                    'domain':[('product_id','=',product_id[0].id),('location_id','in',scrap_locations.ids)],
                }
        return True

    @api.multi
    def create_Product_uom(self):
        for record in self:
            uom_type=[]
            uom_categ=self.env['product.uom.categ'].search([('name','=','Weight')], limit=1)
            if not uom_categ:
               raise UserError(('Default Product UOM Category not found'))
            p_uom_type=self.env['product.uom.type'].search([('string','=','pri_packaging')],limit=1)
            if not p_uom_type:
               raise UserError(('Default Primary Packaging Type not found'))
            s_uom_unit=self.env['product.uom.type'].search([('string','=','sec_packaging')],limit=1)
            if not s_uom_unit:
               raise UserError(('Default Secondary Packaging Unit not found'))
            uom_type.append((4,p_uom_type.id))
            uom_type.append((4,s_uom_unit.id))
            if record.raw_material_type.string =='pallet':
               sec_uom_type=self.env['product.uom.type'].search([('string','=','product_packaging')],limit=1)
               if not sec_uom_type:
                  raise UserError(('Default Secondary Packaging Type not found'))
               uom_type.append((4,sec_uom_type.id))
            product_id=self.env['product.product'].search([('product_tmpl_id','=',record.id)])
            product_uom=self.env['product.uom'].create({'name':record.name,
		                'product_id':product_id.id,'product_type':record.raw_material_type.id,
		                'unit_type':uom_type, 'category_id':uom_categ.id})
            record.packaging_uom_id=product_uom.id
            body='<b>Packaging UOM Created of   '+str(record.name)  +'</b>'
            body +='<li> Packaging UOM: '+str(product_uom.name) +'</li>'
            body +='<li> Created By: '+str(self.env.user.name) +'</li>'
            body +='<li> Created Date: '+str(date.today()) +'</li>' 
            record.message_post(body=body)
            
    @api.multi
    def _compute_machine_count(self):
        for product in self:
            machine=self.env['machinery'].search([('product.product_tmpl_id','=',product.id)])
            if machine:
               product.machine_count = len(machine)
               
    @api.multi
    def open_machine(self):
        for line in self:
            machine_tree = self.env.ref('gt_order_mgnt.machine_view_tree', False)
            machine_form = self.env.ref('gt_order_mgnt.machines_view_form', False)
            if machine_tree:
                return {
                    'name':'Machine',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'machinery',
                    'views': [(machine_tree.id, 'tree'),(machine_form.id, 'form')],
                    'view_id': machine_tree.id,
                    'target': 'current',
                    'domain':[('product.product_tmpl_id','=',self.id)],
                }
        return True
        
    @api.multi
    def total_trial_form(self):
        total=0.0
        for record in self:
            trial=self.env['sale.order.trial.form'].search([('product_id.product_tmpl_id','=',record.id)])
            if trial:
               for tr in trial:
                   total +=1
               record.trial_form_count=total
               
    @api.multi
    def total_trial_orders(self):
        total=0.0
        for record in self:
            trial=self.env['sale.order'].search([('trial_form_id.product_id.product_tmpl_id','=',record.id),('is_trail','=',True)])
            if trial:
               for tr in trial:
                   total +=1
               record.trial_orders_count=total
               
    @api.multi
    def total_production_qty(self):
        for record in self:
	    if record.product_variant_ids:
            	request=self.env['n.manufacturing.request'].search([('n_product_id','=',record.product_variant_ids[0].id), ('n_state','not in',('done','cancel'))])
            	if request:
               		total=sum([ req.n_order_qty for req in request ])
               		record.production_count=total

    @api.multi
    def open_trialform(self):
        for line in self:
            trial_tree = self.env.ref('gt_order_mgnt.view_sale_order_trial_tree_ext', False)
            trial_form = self.env.ref('gt_order_mgnt.view_sale_order_trial_form', False)
            if trial_tree:
                return {
                    'name':'Trail Order Form',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'sale.order.trial.form',
                    'views': [(trial_tree.id, 'tree'),(trial_form.id, 'form')],
                    'view_id': trial_tree.id,
                    'target': 'current',
                    'domain':[('product_id.product_tmpl_id','=',self.id)],
                }
        return True
        
    @api.multi
    def open_trialorders(self):
        for line in self:
            sale_tree = self.env.ref('sale.view_quotation_tree', False)
            sale_form = self.env.ref('sale.view_order_form', False)
            if sale_tree:
                return {
                    'name':'Trail Order Form',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'sale.order',
                    'views': [(sale_tree.id, 'tree'),(sale_form.id, 'form')],
                    'view_id': sale_tree.id,
                    'target': 'current',
                    'domain':[('trial_form_id.product_id.product_tmpl_id','=',self.id)],
                }
        return True
        
    @api.multi
    def open_production_request(self):
        for line in self:
            production_tree = self.env.ref('gt_order_mgnt.n_production_request_tree_history', False)
            production_form = self.env.ref('gt_order_mgnt.mrp_production_request_form', False)
            if production_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree, form',
                    'res_model': 'n.manufacturing.request',
                    'views': [(production_tree.id, 'tree'), (production_form.id, 'form')],
                    'view_id': production_tree.id,
                    'target': 'current',
                    'domain':[('n_product_id','=',self.product_variant_ids.id), ('n_state','not in',('done','cancel'))],
                }
        return True
    
    @api.onchange('product_material_type')
    def _hide_type(self): 
    	for rec in self:
    		rec.matstrg = rec.product_material_type.string
    		rec.raw_material_type = False
    		rec.categ_id = False
    		
#CH_N040 add fields
    n_production_tolerance = fields.Char(string="Production Tolerance (+/-)",default="0" ,help="Default Tolerance is (-/+5)%")
    qty_reserved = fields.Integer('Reserved qty',compute="_get_reserved_qty")
    
    @api.multi
    def _get_reserved_qty(self):
    	for res in self:
    		product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
	    	product_id = [p.id for p in product_id]
    		quants=self.env['stock.quant'].search([('product_id','in',product_id),('reservation_id','!=',False),
    							('location_id.actual_location','=',True)])
		res.qty_reserved = sum([q.qty for q in quants])
    	
    @api.multi
    def action_view_reserve(self):
        for res in self:
	    product_id = self.env['product.product'].search([('product_tmpl_id','=',res.id)])
	    product_id = [p.id for p in product_id]
            reserve_tree = self.env.ref('stock.view_stock_quant_tree', False)
            reserve_form = self.env.ref('stock.view_stock_quant_form', False)
            if reserve_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'stock.quant',
                    'views': [(reserve_tree.id, 'tree'),(reserve_form.id, 'form')],
                    'view_id': reserve_tree.id,
                    'target': 'current',
                    'domain': [('product_id','in',product_id),('reservation_id','!=',False)],
                }
        return True

    @api.model
    def default_get(self,fields):
    	data_obj = self.env['ir.model.data']
        manufacture_route_id = data_obj.get_object_reference('mrp', 'route_warehouse0_manufacture')[1]
        buy_route_id = data_obj.get_object_reference('purchase', 'route_warehouse0_buy')[1]
        rec = super(productTemplate, self).default_get(fields)
        uom=self.env['product.uom'].search([('name','ilike','pcs')],limit=1)
        if uom:
	        rec.update({'uom_id':uom.id})
	rec.update({'type':'product'})
	rec.update({'tracking':'none'})
	rec.update({'purchase_method':'purchase'})
	rec.update({'purchase_requisition':'tenders'})
	rec.update({'invoice_policy':'delivery'})
	rec.update({'route_ids' :[(4,manufacture_route_id),(4,buy_route_id)]})
	return rec

#CH_N062 >>> add awating state record in quatations in product form >>
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
                    'domain': [('state', 'in', ['draft', 'sent','awaiting']), ('product_id.product_tmpl_id', '=', self.id)],
            }
#CH_N062<<<
    
    @api.multi
    def action_view_po(self):
    	self.ensure_one()
        po_id_tree = self.env.ref('purchase.purchase_order_line_tree', False)
        if po_id_tree:
            return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'purchase.order.line',
                    'views': [(po_id_tree.id, 'tree')],
                    'view_id': po_id_tree.id,
                    'target': 'current',
                    'domain': [('product_id.product_tmpl_id', '=', self.id)],
            }
            
    @api.multi
    def _trial_count(self):
        for product in self:
	    count=0
	    for rec in self.env['sale.order'].search([('is_trail','=',True),('state', 'in', ('draft', 'sent','awaiting','done'))]):
		for line in rec.order_line:
			if line.product_id.product_tmpl_id.id == product.id:
				count += 1
            product.trial_count = count
    
    trial_count = fields.Integer(compute='_trial_count', string='#Trial Requests')

    @api.multi
    def make_manufacture(self):
       for line in self:
       	    context=self._context.copy()
            mo_form = self.env.ref('gt_order_mgnt.create_manufacturing_order_from_view', False)
            product_id=self.env['product.product'].search([('product_tmpl_id','=',self.id)])
            if mo_form:
            	context.update({'default_product_id':product_id.id,'default_unit':product_id.uom_id.id})
                return {
                    'name':'Create Manufacture Order',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form,',
                    'res_model': 'make.manufacture.order',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'context':context,
                    'target': 'new',
                }
       return True


    @api.multi
    def write(self,vals):
    	for rec in self:
    		body=""
    		product_disc_obj = self.env['n.product.discription']
    		attributes_table=self.env['n.product.discription.value']
    		product_mate_obj = self.env['product.raw.material.type']
    		product_uom = self.env['product.uom']
    		punit=rec.uom_id
		if vals.get('n_production_tolerance'):
			body +="<li> Tolerance Updated From "+str(rec.n_production_tolerance)+" To "+str(vals.get('n_production_tolerance'))+'</li>'
                if vals.get('name'):
			body +="<li> Update In Product Name  "+str(rec.name)+" To "+str(vals.get('name'))+'</li>'
		if vals.get('initil_weight'):
			body +="<li> Gross Weight Updated From "+str(rec.weight)+" To "+str(vals.get('initil_weight'))+'</li>'
		if vals.get('weight'):
			body +="<li> Net Weight Updated From "+str(rec.weight)+" To "+str(vals.get('weight'))+'</li>'
		
		if vals.get('product_hs_code'):
			body +="<li>Hs Code Updated From "+str(rec.product_hs_code)+" To "+str(vals.get('product_hs_code'))+'</li>'
		if vals.get('uom_id'):
			punit=product_uom.search([('id','=',vals.get('uom_id'))])
			body +="<li> Unit Updated From "+str(rec.uom_id.name if rec.uom_id else '')+" To "+str(punit.name)+'</li>'
		if vals.get('uom_po_id'):
			pounit=product_uom.search([('id','=',vals.get('uom_po_id'))])
			body +="<li> Unit Updated From "+str(rec.uom_po_id.name if rec.uom_po_id else '')+" To "+str(pounit.name)+'</li>'
	# add code to get history of product changes		
		if vals.get('discription_line'):
			added=''
			update=''
			removed=''
			body +="<li> Specification Updated"
			for line in vals.get('discription_line'):
				if type(line[2]) == dict:
					if line[0]==0:
						unit=''
						if line[2].get('value'):
							unit=product_uom.search([('id','=',line[2].get('unit'))])
						attribute=attributes_table.search([('id','=',line[2].get('attribute'))])
						added +='<li><span style="color:green">'+str(attribute.name)+'</span> : value: '+str(line[2].get('value'))+(' Unit : '+(unit.name) if unit else '')+'</li>'
					if line[0]==1:
						unit=''
						if line[2].get('unit'):
							unit=product_uom.search([('id','=',line[2].get('unit'))])
						record=product_disc_obj.browse(line[1])
						attribute=attributes_table.search([('id','=',line[2].get('attribute'))])
						if line[2].get('attribute'):
							update +='<li><span style="color:green">'+str(record.attribute.name)+' <span style="color:black">TO </span>'+str(attribute.name)+': </span>'+(' value: '+str(line[2].get('value')) if line[2].get('value') else '' )+(' Unit : '+(unit.name) if unit else '')+'</li>'
						else:
							update +='<li><span style="color:green">'+record.attribute.name+': </span>'+(' value: '+str(line[2].get('value')) if line[2].get('value') else '' )+(' Unit : '+(unit.name) if unit else '')+'</li>'
						
				if line[0]==2:
					attrs=product_disc_obj.browse(line[1])
					removed +='<li><span style="color:green">'+str(attrs.attribute.name)+'</span></li>'
			body += ('<ul> New Speficifation'+added+'</ul>' if added else '')+('<ul>Update Specification'+update+'</ul>' if update else '')+('<ul>Remove Specification'+removed+'</ul>' if removed else '')
			body +="</li>"
		if vals.get('description_sale'):
			body +='<li><span style="color:blue">Sale Description Changed:</span>'+str(vals.get('description_sale'))+'</li>'
		if vals.get('description_purchase'):
			body +='<li><span style="color:blue">Purchase Description Changed:</span>'+str(vals.get('description_purchase'))+'</li>'
		if vals.get('description_picking'):
			body +='<li><span style="color:blue">Delivery Description Changed:</span>'+str(vals.get('description_picking'))+'</li>'
		if vals.get('description_mrp'):
			body +='<li><span style="color:blue">Manufacturing Description Changed:</span>'+str(vals.get('description_mrp'))+'</li>'
		if vals.get('product_material_type'):
			material=product_mate_obj.search([('id','=',vals.get('product_material_type'))])
			if not rec.product_material_type:
				body +="<li>Product Material Type Added "+str(material.name)+"</li>"
			else:
				body +="<li>Product Type Updated From "+str(rec.product_material_type.name)+" TO "+str(material.name)+"</li>"
		if vals.get('raw_material_type'):
			raw=product_mate_obj.search([('id','=',vals.get('raw_material_type'))])
			if not rec.raw_material_type:
				body +="<li>Material Type Added "+str(raw.name)+"</li>"
			else:
				body +="<li>Material Type Updated From "+str(rec.raw_material_type.name)+" TO "+str(raw.name)+"</li>"
		if vals.get('machine_type_ids'):
			body +="<li>Manufacturing type Updated </li>"
		if vals.get('packaging_ids'):
			body +="<li>Packaging Updated </li>"
		if vals.get('seller_ids'):
			body +="<li>Vendors Changed </li>"
		if vals.get('sale_ok'):
			body +="<li>Update Can be Sold {} >> {} </li>".format(rec.sale_ok,vals.get('sale_ok'))
		if vals.get('purchase_ok'):
			body +="<li>Update Can be Purchased {} >> {} </li>".format(rec.purchase_ok,vals.get('purchase_ok'))
		if vals.get('list_price'):
			body +="<li>Selling Price Changed from {} To {} </li>".format(rec.list_price,vals.get('list_price'))
		if vals.get('standard_price'):
			body +="<li>Cost Changed from {} To {} </li>".format(rec.list_price,vals.get('standard_price'))
		if body:
			rec.message_post(body=body)
	vals.update({'rental':True})
	return super(productTemplate,self).write(vals)

  #Asset details
    plate_product_id =  fields.Many2one('product.product','Product') # for printing palte product relation
    machine_id =  fields.Many2many('product.template','product_machine_part_rel','product_id','part_id','Machine') # for machine to part relation
    
    machinary_id = fields.Many2one('machinery','Machine Details')
  # hour = fields.Integer('Hour')
  #  minute = fields.Integer('Minute')
  #  second = fields.Integer('Second')
  #  time_cycle = fields.Float('Time Cycle')
  #  time_efficiency = fields.Float('Efficiency Factor')
  #  time_start = fields.Float('Loading Time(in hour)')
  #  time_stop = fields.Float('Unloading Time(in hour)')
  #  workprocess_ids=fields.One2many('mrp.production.workcenter.line', 'machine_id', string='Schedule Detail')
    
    @api.model
    def create(self,vals):
	vals.update({'rental':True})
    	product=super(productTemplate,self).create(vals)
	if product.product_material_type.string=='asset' and product.raw_material_type.string=='machine':
		machine=self.env['machinery'].create({'name':str(product.name),'assets_no':product.asset_code})
		product.machinary_id=machine.id
    	return product

class productPackging(models.Model):
    _inherit = 'product.packaging'
    
    weight=fields.Float('Weight', compute='pack_weight')
   
    @api.multi
    @api.depends('uom_id','qty','unit_id')
    def pack_weight(self): 
	for record in self:
		if record.qty and record.uom_id and record.unit_id:
			if record.pkgtype == 'primary':
				if record.unit_id.name.upper() =='KG':
					record.weight= record.qty + record.uom_id.product_id.weight
				else:
					record.weight=(record.qty * record.product_tmpl_id.weight)+record.uom_id.product_id.weight
			if record.pkgtype == 'secondary':
				pack=self.env['product.packaging'].search([('product_tmpl_id','=',record.product_tmpl_id.id),('pkgtype','=','primary'),('uom_id','=',record.unit_id.id)], limit=1)
				primary=0.0
				if pack and pack.unit_id.name.upper() =='KG':
					primary =pack.qty + pack.uom_id.product_id.weight
				else:
					primary = (pack.qty * record.product_tmpl_id.weight)+pack.uom_id.product_id.weight
				record.weight=(primary * record.qty)+record.uom_id.product_id.weight
		else:
       			record.weight=0.0

    @api.model
    def get_unit(self):
        if self._context.get('product_tmpl_id'):
            product = self.env['product.product'].search([('product_tmpl_id','=',self._context.get('product_tmpl_id'))])
            return product.uom_id.category_id.id

#CH_N053 add name search for filter >>>>
    @api.model
    def name_search(self, name, args=None, operator='ilike',limit=100):
	if self._context.get('sale_line'):
		if self._context.get('film_product'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('film_product'))]).product_tmpl_id.id
			packaging = self.search([('product_tmpl_id','=',product_id)])
			args=[('id','in',[i.id for i in packaging])]		
		elif self._context.get('templ_id'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('templ_id'))]).product_tmpl_id.id
			if self._context.get('pricelist_id'):
				packaging = self.env['customer.product'].search([('pricelist_id','=',self._context.get('pricelist_id')),('product_id','=',self._context.get('templ_id')),('product_packaging','!=',False)])
				args=[('id','in',[i.product_packaging.id for i in packaging])]
			else:
		    		packaging = self.search([('product_tmpl_id','=',product_id),('pkgtype','=','primary')])
				args=[('id','in',[i.id for i in packaging])]	
		else:
			return []
			
	if self._context.get('stock_mrp_request'):
		product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))]).product_tmpl_id.id
    		packaging = self.search([('product_tmpl_id','=',product_id)])
		args=[('id','in',[i.id for i in packaging])]
	if self._context.get('sale_reception'):
		args=[]
		if self._context.get('product_id'):
			product_id=self.env['product.product'].search([('id','=',self._context.get('product_id'))]).product_tmpl_id.id
			packaging = self.search([('product_tmpl_id','=',product_id),('pkgtype','=','primary')])
			args=[('id','in',[i.id for i in packaging])]
    	return super(productPackging,self).name_search(name, args, operator=operator, limit=limit)
#CH_N053 end <<

#CH_N for reserve quantity show 
class reserveProductQty(models.Model):
    _name = "n.reserve.productqty"

    @api.multi
    def get_pending_qty(self): 
	for rec in self:
    		rec.reserve_qty = rec.sale_reserve_qty-rec.qty_delivered
    
    name = fields.Char(string="Name")
    product_id = fields.Many2one("product.product", string="Product Name")
    order_id =  fields.Many2one("sale.order", string="Sale Name") 
    order_partner_id = fields.Many2one("res.partner", string="Customer")
    line_id =  fields.Many2one("sale.order.line", string="sale line")
    salesman_id = fields.Many2one("res.users", string="salesperson")
    reserve_qty = fields.Integer('Reserve qty', compute = get_pending_qty,)
    sale_reserve_qty = fields.Integer('Reserve qty', default=0.0)
    qty_delivered = fields.Integer('Reserve qty', default=0.0)
    
class ProductDiscription(models.Model):
    _name = "n.product.discription"
	
    product_id = fields.Many2one('product.template', 'Product Name')
    attribute = fields.Many2one('n.product.discription.value', 'Attributes')
    name=fields.Char('Product Discription')	
    value=fields.Char('Product Discription')
    unit = fields.Many2one('product.uom', 'Unit')
    complete_id=fields.Many2one('mrp.complete.date')
    user_id=fields.Many2many('res.users','discription_user_rel','value_id','uid','Users')
    
    @api.multi
    def write(self, vals):
        return super(ProductDiscription, self).write(vals)

    @api.model
    def create(self, vals):
        ids=super(ProductDiscription, self).create(vals)
        if not vals.get('unit'):
        	ids.unit=False
        return ids

	
class ProductDiscriptionValue(models.Model):
    _name = "n.product.discription.value"

    name=fields.Char('Name',required=True)
    string= fields.Char('Internal Name',help="name used for internal purpose")	
    units=fields.Many2many('product.uom','discription_value_unit_rel','value_id','unit_id','Units')
    user_id=fields.Many2many('res.users','discription_value_user_rel','value_id','uid','Users')
    active = fields.Boolean('Active', help="If the active field is set to False, it will allow you to hide the Type without removing it.",default=True)
    
class MakeManufactureOrder(models.TransientModel):
    _name = "make.manufacture.order"
    
    product_id = fields.Many2one('product.product','Product')
    unit = fields.Many2one('product.uom','Unit')
    quantity = fields.Float('Quantity')
    date = fields.Date('Date')
    packaging = fields.Many2one('product.packaging','Packaging')
    note = fields.Text(string="Note")
    request_type=fields.Selection([('stock','From Stock'),('sale','From MO'),
    				   ('raw',' '),('contract',' ')],string="Request Type",
                                    default='stock',)
    #request_type=fields.Selection([('mo','MO'),('stock','Stock')], default='stock', string='Request Type')
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.')
    sale_id=fields.Many2one('sale.order', string='Sale Order No.', related='production_id.sale_id')
    
    @api.multi
    def process(self):
    	for rec in self:
    		self.env['n.manufacturing.request'].create({'n_product_id':rec.product_id.id if rec.product_id else  self._context.get('active_id'),
    							    'n_unit':rec.unit.id,
    							    'n_category':rec.product_id.categ_id.id,
    							    'n_delivery_date':rec.date,
    							    'n_packaging':rec.packaging.id,
    							    'n_order_qty':rec.quantity,
    							    'request_type':rec.request_type,
    							    'n_Note':rec.note,
                                                            'n_sale_line':rec.sale_id.id,
                                                            'n_mo_number':rec.production_id.id,
    							    'n_state':'draft'})
    	return True
    	
class product_supplierinfo(models.Model):
    _name = "product.supplierinfo"
    _inherit=['mail.thread','product.supplierinfo']
    new_price=fields.Float('Price For Request')
    state=fields.Selection([('request','request'),('approved','Approved'),('rejected','Rejected')],
     default='approved')

    @api.model
    def default_get(self,fields):
        res = super(product_supplierinfo, self).default_get(fields)
        product_name=self.env['product.template'].search([('id','=',res.get('product_tmpl_id'))])
        
        res['product_name']=product_name.name
        return res

    @api.multi
    @api.onchange('product_tmpl_id')
    def product_name_val(self):
        if self.product_tmpl_id:
           self.product_name=self.product_tmpl_id.name
        else:
           self.product_name=''
     
    @api.multi
    def approved_send(self):
        for record in self:
            template_ids = self.env.ref('gt_order_mgnt.email_template_for_supplier_price_approved')
            if template_ids:    
		recipient_partners=self.create_uid.login
		base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		query = {'db': self._cr.dbname}
		fragment = {
			'model': 'product.supplierinfo',
			'view_type': 'form',
			'id': record.id,
			}
		url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
		text_link = _("""<a href="%s">%s</a> """) % (url,record.name.name)
		body='<b>Approved Supplier Product Price  </b>'
		body +='<li> Vendor Pricelist: '+str(text_link) +'</li>'
		body +='<li> Product  Name: '+str(self.product_tmpl_id.name) +'</li>' 
		body +='<li> Old Price: '+str(self.price) +str(self.currency_id.name)+'</li>'
		body +='<li> New Price: '+str(self.new_price) +str(self.currency_id.name)+'</li>'
		body +='<li> Requested By: '+str(self.env.user.name) +'</li>'
		body +='<li> Requested Date: '+str(date.today()) +'</li>'
		template_ids.write({'body_html':body})
		values = template_ids.generate_email(self.id)
		values['email_to'] = recipient_partners
		self.sent_mail=True
		self.write({'state': 'approved', 'price':self.new_price, 'new_price':0.0})
		mail_mail_obj = self.env['mail.mail']
		msg_id = mail_mail_obj.create(values) 
		msg_id.send()  
		return msg_id   
    @api.multi
    def request_send(self):
        for record in self:
            template_ids = self.env.ref('gt_order_mgnt.email_template_for_supplier_price_request')
            if template_ids:    
		recipient_partners=''
                group = self.env['res.groups'].search([('name', '=', 'Manager Email')])
                for recipient in group.users:
                    recipient_partners +=str(recipient.login)+','
		base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		query = {'db': self._cr.dbname}
		fragment = {
			'model': 'product.supplierinfo',
			'view_type': 'form',
			'id': record.id,
			}
		url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
		text_link = _("""<a href="%s">%s</a> """) % (url,record.name.name)
		body='<b>Request For Supplier Product Price  </b>'
		body +='<li> Vendor Pricelist: '+str(text_link) +'</li>'
		body +='<li> Product  Name: '+str(self.product_tmpl_id.name) +'</li>' 
		body +='<li> Old Price: '+str(self.price) +str(self.currency_id.name)+'</li>'
		body +='<li> New Price: '+str(self.new_price) +str(self.currency_id.name)+'</li>'
		body +='<li> Requested By: '+str(self.env.user.name) +'</li>'
		body +='<li> Requested Date: '+str(date.today()) +'</li>'
		template_ids.write({'body_html':body})
		values = template_ids.generate_email(self.id)
		values['email_to'] = recipient_partners
		self.sent_mail=True
		self.write({'state': 'request'})
		mail_mail_obj = self.env['mail.mail']
		msg_id = mail_mail_obj.create(values) 
		msg_id.send()  
		return msg_id   

class make_procurement(models.Model):
    _inherit = 'make.procurement'

    @api.multi
    def purchaserequest(self):
       for record in self:
           rq_data=self.env['stock.purchase.request']
           reqst_search=rq_data.search([('product_id','=',record.product_id.id ), ('p_state','in',('draft','requisition'))], limit=1)
           if reqst_search:
                  line=self.env['stock.purchase.request.line'].create({'product_id':record.product_id.id,
                          'qty':record.qty, 'uom_id':record.uom_id.id,
                           'required_date':record.date_planned,'purchase_request_id':reqst_search.id})
                  body='<b>Purchase Request Sent From Product:  </b>'
                  body +='<ul><li> Purchase Request No. : '+str(reqst_search.name) +'</li></ul>'
                  body +='<ul><li> Product Name : '+str(reqst_search.product_id.name) +'</li></ul>'
                  body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
                  body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
                  record.product_id.message_post(body=body)
                  record.product_id.product_tmpl_id.message_post(body=body)
                  reqst_search.message_post(body=body)
           else:
                  request=rq_data.create({'product_id':record.product_id.id })
                  body='<b>Purchase Request Sent From Product:  </b>'
                  body +='<ul><li> Purchase Request No. : '+str(request.name) +'</li></ul>'
                  body +='<ul><li> Product Name : '+str(request.product_id.name) +'</li></ul>'
                  body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
                  body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
                  record.product_id.message_post(body=body)
                  record.product_id.product_tmpl_id.message_post(body=body)
                  request.message_post(body=body)
                  if request:
                     line=self.env['stock.purchase.request.line'].create({'product_id':record.product_id.id,
                          'qty':record.qty, 'uom_id':record.uom_id.id, 
                            'required_date':record.date_planned,'purchase_request_id':request.id})    


