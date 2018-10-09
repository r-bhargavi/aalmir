# Part of Odoo. See LICENSE file for full copyright and licensing details.
#CH03 add on_change to change base currency and converted currency

from openerp import api, fields, models, _
from openerp import fields
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import datetime
import re
from dateutil.relativedelta import relativedelta
import sys
import logging
_logger = logging.getLogger(__name__)
import os

class res_company(models.Model):

    _inherit = "res.company"

    stamp_image = fields.Binary('Stamp')
    invoice_paid_stamp=fields.Binary('Invoice Paid Stamp')
    term_and_condition_1 = fields.Html(string='Tearms and condition')
    term_and_condition_2 = fields.Html(string='Tearms and condition')

    @api.model
    def default_get(self, fields):
        result= super(res_company, self).default_get(fields)
	if self._context.get('company_active'):
           result.update({'company_active':True})
        return result

    @api.model
    def name_search(self,name, args=None, operator='ilike',limit=100): 
        if self._context.get('report_com'):
           companies=self.search([])
           args.append(('id','in',[i.id for i in companies]))
        else:
           companies=self.search([('company_active','=',False)])
           args.append(('id','in',[i.id for i in companies]))
	res=super(res_company,self).name_search(name, args, operator=operator,limit=limit)
    	return res


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.multi
    @api.depends('order_ids','order_ids.amount_total')
    def _get_expected_revenue(self):
        """This method will update the expected revenue of the last created sale/quotation
        	which is active.
        		:return: Update planned revenue value"""
        
        for lead in self:
            recent_order = self.env['sale.order'].search([('opportunity_id','=',lead.id), ('state','!=','cancel')], order='create_date desc', limit=1)
            if not recent_order:
                lead.planned_revenue = 0
            lead.planned_revenue = recent_order.n_base_currency_amount ## CH_025 replace amoun_total to get base currency of quotation

    planned_revenue = fields.Float("Planned Revenue", compute=_get_expected_revenue)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    proforma_quto_bool=fields.Boolean('Is Proforma Invoice?') #add field vml001 
    attend_id = fields.Many2one('res.partner', "Attendee")
    show_delivery_info = fields.Boolean("Show Delivery Info In Quotation", default=True)
    is_trail=fields.Boolean('Is Trial ')
    n_add_sales_product = fields.Selection([('add','Add'),
    					    ('edit','Edit'),
    					    ('done','Done')],"add product", default='done')	
	    # CH_029 add field to check if product of sale is added or not  #CH_N146 change field to selection
   					    
    check_vat=fields.Boolean('Print Customer VAT')
    partner_vat=fields.Char('Customer VAT',related='partner_id.vat')
    tax_documents=fields.Many2many('ir.attachment','customer_tax_sale_documents_rel','sale_id','doc_id','Upload Documents',help='Upload Export Documents if Sale Order Exported')
    
    converted_amount_untaxed = fields.Monetary(string='Converted Total', compute='_get_converted_total_tax')
    converted_amount_taxed = fields.Monetary(string='Converted Total', compute='_get_converted_total_tax')
    show_stamp=fields.Boolean('Show Stamp on Report',default=True)
    customer_name_report=fields.Char('Customer Name on Report',default='Customer Name')
    report_company_name=fields.Many2one('res.company','LetterHead Company Name', default=lambda self: self.env['res.company']._company_default_get('sale.order'))
    print_contract_no=fields.Boolean('Print Contract No. on Report')

    @api.multi
    @api.depends('amount_untaxed', 'report_currency_id','amount_tax')
    def _get_converted_total_tax(self):
        for order in self:
            from_currency = order.pricelist_id.currency_id
            if order.report_currency_id:
                to_currency = order.report_currency_id
            else:
                to_currency = order.pricelist_id.currency_id

            if from_currency and to_currency and order.amount_untaxed:
                order.converted_amount_untaxed = from_currency.compute(order.amount_untaxed, to_currency, round=False)
            if from_currency and to_currency and order.amount_tax:
                order.converted_amount_taxed = from_currency.compute(order.amount_tax, to_currency, round=False)

    #replace Quotation in report vml001
    @api.multi
    @api.onchange('proforma_quto_bool')
    def chnage_note_value(self):
        for record in self:
        	if record.proforma_quto_bool:
			if self.note:
        		   note_data= re.sub('(?i)Quotation','Proforma Invoice',self.note)			  
			   self.note=note_data
        	else:
        		if self.note:
				note_data= re.sub('(?i)Proforma Invoice','Quotation',self.note)                                
			        self.note=note_data
    @api.multi
    def action_confirm(self):
	##CH_N06 start >> add code to open pop-up when click on confirm sale
	if self._context.get('re_call') ==True:
		product_create_flag = False
		n_new_product=[]
		#CH_N09 start >>
		for order in self:
			prod_obj=self.env['product.product']
			for line in order.order_line:
				n_flag=True
				if line.pricelist_type == '2' and line.price_calculator_id.change_bool == True:
					line.product_id=line.n_film_product_id.id
				if line.pricelist_type == '2' and line.price_calculator_id.change_bool == False:
					n_product_name = str(line.price_calculator_id.bag_type.name.name if line.price_calculator_id.bag_type else '')+ " "+str(line.price_calculator_id.product_type.name.name)+" ("+ str(line.price_calculator_id.lenght)+" * "+str(line.price_calculator_id.width)+")  "+str(line.price_calculator_id.printing_type.name)
					n_product_type_id=self.env['product.category'].search([('cat_type','=','film')])					
					exist='new'
					prod_ids=prod_obj.search([('name_template','=',n_product_name)])
					if prod_ids:
						n_flag=False
						exist='exist'
					add_p=True
					if n_product_name == 'Printing Plate':
						add_p=False
					n_val_dic={'n_add_product_bool':add_p,'n_product_name':n_product_name,
					   	'n_sale_line_id':line.id,'n_avg_price':line.price_unit,
					   	'n_min_qty':line.min_qty,'n_description':str(line.name1),
					   	'n_exist':exist,'n_unit':line.price_calculator_id.unit.id,
					   	'n_film_ids':line.price_calculator_id.id,
						'n_product_type':n_product_type_id.id,
	  				   	'n_from_date':datetime.strftime(datetime.now().today(),'%Y-%m-%d'),
					   	'n_to_date':datetime.strftime(datetime.now().today()+relativedelta(years=1),'%Y-%m-%d'),
					   	'weight':line.price_calculator_id.weight_per_kg,
						#'n_type_of_package':line.price_calculator_id.packing_type.id
						'type':'product',
						}

					n_new_product.append((0,0,n_val_dic))
					product_create_flag=True

				if line.pricelist_type == '3' and not line.sale_line_id:
					n_product_name=str(line.prd_name)
					exist='new'
					prod_ids=prod_obj.search([('name_template','=',n_product_name)])
					if prod_ids:
						n_flag=False
						exist='exist'
					add_p=True
					if n_product_name == 'Printing Plate':
						add_p=False
					n_val_dic={'n_add_product_bool':add_p,'n_product_name':n_product_name,
							'n_avg_price':line.price_unit,'n_min_qty':line.product_uom_qty,
							'n_description':str(line.name),'n_exist':exist,
					 	   	'n_unit':line.product_uom.id,
						   'n_product_type':line.n_product_category.id,'n_sale_line_id':line.id,
						   'n_from_date':datetime.strftime(datetime.now().today(),'%Y-%m-%d'),
						   'n_to_date':datetime.strftime(datetime.now().today()+relativedelta(years=1),'%Y-%m-%d'),}

					n_new_product.append((0,0,n_val_dic))
					product_create_flag=True
					#self.env['n.custom.product'].create({'n_custom_line_o2m':})
		context = self._context.copy()
		context.update({'re_call':False,'sale_order_id':self.id})
		form_id = self.env.ref('gt_sale_quotation.n_custom_product_form_view').id
		if product_create_flag:
			if n_new_product:
				self.env['n.custom.product'].search([('n_sale_order_id','=',self.id)]).unlink()
				custom_id=self.env['n.custom.product'].create({'n_custom_line_o2m':n_new_product,'n_sale_order_id':self.id,
				'n_custom_currency_id':self.n_quotation_currency_id.id})
				#CH_N09 end <<
				return {
					'name' :'Product Creation',
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'n.custom.product',
					'view_id': form_id,
					'target': 'new',
					'context': context,
					'res_id': custom_id.id,
				    }
		else:
			#CH_N029 changes in code due to marge >>
			self.n_add_sales_product='done'
			return True
			##<<<<
	elif self._context.get('n_edit_product')==True:
		form_id = self.env.ref('gt_sale_quotation.n_custom_product_form_view').id
		search_id=self.env['n.custom.product'].search([('n_sale_order_id','=',self.id)],limit=1)		
		return {
				'name' :'Product Creation',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'n.custom.product',
				'view_id': form_id,
				'res_id':search_id.id,
				'target': 'new',
			    }
	else:
	## CH_N06 end << 
		for order in self:
		    #CH_N011 start update fields to make readonly >>
		    for line in order.order_line:
		    	if line.pricelist_type == '2':
				line.price_calculator_id.product_bool=False
				line.price_calculator_id.change_bool=True
				line.price_calculator_id.n_state='done'
			
		    #CH_N011 end <<
		    #CH_N020 add to convert amount in base currency start >>
		    if self.amount_total and self.currency_id:
		    	self.n_base_currency_amount=self.currency_id.compute(self.amount_total,self.env.user.company_id.currency_id)
		    #CH_N020 end
		    order.write({'date_order': fields.Datetime.context_timestamp(self, datetime.now())})
		    order.state = 'sale'
		    if order.opportunity_id and not order.opportunity_id.is_contract:
		        sale_ids = self.search([('is_trail','!=',True),('id','!=',order.id),('opportunity_id','=', order.opportunity_id.id)])
			if sale_ids:
		               sale_ids.write({'state': 'cancel'})
		    if self.env.context.get('send_email'):
		        self.force_quotation_send()
		    order.order_line._action_procurement_create()
		    if not order.project_id:
		        for line in order.order_line:
		            if line.product_id.invoice_policy == 'cost':
		                order._create_analytic_account()
		                break

		    if order.opportunity_id:
		        res_vals = {'planned_revenue': self.currency_id.compute(self.amount_total,self.env.user.company_id.currency_id)} #CH_N021 chaneg value in dict to update revenue in pipeline in company curency
		        res_vals.update(self.pool['crm.lead'].on_change_partner_id(self._cr, 1, [], order.partner_id.id)['value'])
		        if order.opportunity_id.is_contract:
		        	sale_opportunit=self.search([('opportunity_id','=',order.opportunity_id.id),('state','in',('sale','done'))])	
		        	planned_revenue=0.0
		        	for oper in sale_opportunit:
		        		planned_revenue += oper.currency_id.compute(oper.amount_total,self.env.user.company_id.currency_id, round=False)
	        		if planned_revenue:
	        			res_vals = {'planned_revenue':planned_revenue}
	        			
		        order.opportunity_id.sudo().write(res_vals)
		        order.opportunity_id.action_set_won()
		    if order.invoice_ids:
		        order.invoice_ids.write({'name': order.name, 'origin' : order.name})
		        for i in order.invoice_ids:
		            i.invoice_line_ids.write({'origin': order.name,})
		if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
		    self.action_done()
		return True
        
    @api.model
    def create(self, vals):
        seq_no=''
        if vals.get('delivery_day_type') == 'Date':
            if vals.get('delivery_date1'):
                d_date = datetime.strptime(vals.get('delivery_date1'), '%Y-%m-%d')
                d_order = datetime.now()
                if d_date and d_date < d_order:
                    raise UserError('Delivery Date must be greater then Quotation Date')
        
        pobj = False
        if not vals.get('opportunity_id'):
            if vals.get('lead_name'):
                name = vals.get('lead_name')
            else:
                pobj = self.env['res.partner'].browse(vals.get('partner_id'))
                name = str(pobj.name) + str(seq_no[-4:])			#change by Vimal
            stage_ids = self.env['crm.stage'].search([('name','=', 'Quoted')])
            res_val = {
                'name' : name,
                'partner_id' : vals.get('partner_id'),
                'email_from' : pobj and pobj.email or False,
                'type' : 'opportunity',
                'stage_id' : stage_ids and stage_ids[0].id or False,
                'stage_2' : False,
                #'planned_revenue': planned_renenue,
                'user_id': vals.get('user_id') or False,
                'team_id': vals.get('team_id') or False,
            }
            res_val.update(self.pool['crm.lead'].on_change_partner_id(self._cr, 1, [], vals.get('partner_id'))['value'])
            lead = self.env['crm.lead'].with_context({'from_so': True}).create(res_val)
            vals.update({'opportunity_id' : lead.id,
                         'user_id':lead.user_id and lead.user_id.id or self._uid})
        else:
            lead = self.env['crm.lead'].browse(vals.get('opportunity_id'))
            vals.update({'user_id':lead.user_id and lead.user_id.id or self._uid})
        
        if vals.get('name', 'New') == 'New':
        	seq_no = self.env['ir.sequence'].next_by_code('sale.order.quotation')
        	name = ''
        	if vals.get('user_id'):
        		user = self.env['res.users'].browse(vals.get('user_id'))
        		name = (user.name[:2]).upper()
        	if vals.get('is_trail'):
        		tr_seq=seq_no.replace('/Q/','/TR/')
        		name +=tr_seq
        	else:
        		name += seq_no
        	vals['name'] = name
        result = super(SaleOrder, self).create(vals)
        return result
        
    @api.multi
    def write(self, vals):
        if vals.get('delivery_day_type') == 'Date' or vals.get('delivery_date1'):
            d_date = datetime.strptime(vals.get('delivery_date1'), '%Y-%m-%d')
            d_order = datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S')
            if d_date and d_order and d_date < d_order:
                raise UserError('Delivery Date must be greater then Quotation Date')
        if vals.get('state') == 'sale' and vals.get('is_trail') != True:
        	vals.update({'name': (self.name).replace('/Q/', '/S/')})
        if vals.get('state') == 'sale' and vals.get('is_trail') == True:
        	vals.update({'name': (self.name).replace('/TR/S/', '/TR/')})
	#CH_N021 chaneg value in dict to update revenue in pipeline in company curency start >>
	#CH_N025 to update only current records
	super(SaleOrder, self).write(vals)
	if len(self)==1:
		if self.state != 'cancel':
			amount_total = vals.get('amount_total') if vals.get('amount_total')  else self.amount_total #CH_N025
			vals={'n_base_currency_amount':self.currency_id.compute(amount_total,self.env.user.company_id.currency_id)}
			if self.opportunity_id:
				self.opportunity_id.planned_revenue=self.currency_id.compute(amount_total,self.env.user.company_id.currency_id)
	#CH_N021 end <<<
        return super(SaleOrder, self).write(vals)
    
    @api.multi
    def preview_quotation(self):
    	for rec in self:
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		return {
		    "type": "ir.actions.act_url",
		    "url": base_url + "/report/pdf/gt_sale_quotation.report_quotation_aalmir1/" + str(rec.id),
		    "target": "new",
		}
        
    @api.multi
    def print_quotation(self):
	if self.lock:
	        self.filtered(lambda s: s.state == 'draft').write({'state': 'sent'})
        return self.env['report'].get_action(self, 'gt_sale_quotation.report_quotation_aalmir1')

    @api.multi
    def do_revised(self):
        data = (self[0].name).split('_')
        name = self[0].name
        if self[0].opportunity_id.id:
            s_ids = self.search([('name','like', name), ('opportunity_id','=', self[0].opportunity_id.id)], order='id desc')
        if s_ids:
            seq = s_ids[0].sudo().revise_sequence + 1
        else:
            seq = self[0].sudo().revise_sequence + 1
        if len(data) > 1:
            name = data[0]
        name = name + '_' + str(seq)
        copy_quotation = self[0].with_context({'copy_quote' : True}).copy(default={'revise_sequence' : seq, 'validity_date' : False, 'state': 'draft', 'name': name, 'lock' : False,'n_hide_currency':False,'n_quotation_currency_id':False})
#        self[0].state = 'cancel'
        for line in copy_quotation.order_line:
            if line.price_calculator_id:
                price_calc_2 = line.price_calculator_id.copy()
                line.write({'price_calculator_id': price_calc_2.id})
        sale_form = self.env.ref('sale.view_order_form', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'views': [(sale_form.id, 'form')],
            'view_id': sale_form.id,
            'res_id' : copy_quotation.id,
            'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
        }
    
    @api.multi
    def _get_revision_count(self):
        for rec in self:
            data = (rec.name).split('/')
            if len(data) > 4:
                name = (data[4]).split('_')
                if len(name) >= 1:
                    name = name[0]
                    vr_ids = self.search([('name','like', name),('id','!=',rec.id),
            				  ('id','>',rec.id),('opportunity_id','=',rec.opportunity_id.id)])
                    if vr_ids:
                        rec.revision_count = len(vr_ids)
    
    @api.multi
    def action_revisions(self):
    	for res in self:
		ids = []
		data = (res.name).split('/')
		if len(data) > 4:
		    name = (data[4]).split('_')
		    if len(name) >= 1:
		        name = name[0]
		        vr_ids = self.search([('name','like', name),('id','!=',res.id),
		        		      ('id','>',res.id),('opportunity_id','=',res.opportunity_id.id)])
		        if vr_ids:
		           ids = vr_ids.ids     
		return {
		    'name': 'Quotation',
		    'view_type': 'form',
		    'view_mode': 'tree,form',
		    'res_model': 'sale.order',
		    'view_id': False,
		    'domain': [('id','in', ids)],
		    'type': 'ir.actions.act_window',
		    'target' : 'current',
		    'context': {'default_active_id' : res.id},
		}
        
    @api.multi
    def make_lock(self):
	#CH_029 add code to check if there is any product to create if yes the make boolean True start >>
	if self.delivery_day_type != 'Date':
            if not self.delivery_day or not self.delivery_day_type or not self.delivery_day_3:
                raise UserError(("Please Add Delivery Date details..!!"))
        if self.delivery_day_type == 'Date':
            if not self.delivery_date1:
                raise UserError(("Please Add Delivery Date...!!"))
        
        if not self.payment_term_id:
            raise UserError(("Please Add Payment Term...!!"))
        if not self.validity_date:
            raise UserError(("Please Add Expiry Date...!!"))
        for line in self[0].order_line:
            if not line.approve_m or line.dis_m or line.price_m:
                raise UserError("You can't Issue the Quotation which is not approved by Manager")


	for order in self:
		n_flag='done'
		product_create_flag = False
		for line in order.order_line:
			if line.pricelist_type == '2' and line.price_calculator_id.change_bool == False:
				product_create_flag=True

			if line.pricelist_type == '3' and not line.sale_line_id:
				product_create_flag=True
			
			if line.pricelist_type in ('1','4') and not line.n_approved_price_1:
    				product = line.product_id.with_context(lang=order.partner_id.lang,
								partner=order.partner_id.id,
								quantity=line.product_uom_qty,
								date_order=order.date_order,
								pricelist=order.pricelist_id.id,
								uom=line.product_uom.id,
								fiscal_position=self.env.context.get('fiscal_position'))
            
    				context = self._context.copy()
				context.update({'customer_id': line.customer, 'product_id': line.product_id,
						'do_term':order.incoterm.id})
				result = self.pool['product.pricelist']._price_get_multi_line(self._cr, self._uid,
						 order.pricelist_id, [(product,line.product_uom_qty,
						 order.partner_id.id),], context=context)
				if result:
				   line.price_line_id = result.get(product.id)[1] or False
				   if line.fixed_price > line.price_unit:
					   line.final_price = line.fixed_price
					   line.price_unit = line.fixed_price
		   	elif line.pricelist_type in ('1','4'):
		   		i_flag=True
		   		for item in line.pricelist_item_ids:
		   			if item.do_term.id == order.incoterm.id:
		   				if line.product_uom_qty >= item.min_quantity and line.product_uom_qty <= item.qty:
							i_flag=False
				if i_flag:
					raise UserError(("Ordered qty {} is not found of delivery term {} for Product ' {}'".format(line.product_uom_qty,order.incoterm.id,line.product_id.name)))
		if product_create_flag:
			n_flag='add'
		
		n_custom_ids=self.env['n.custom.product'].search([('n_sale_order_id','=',order.id)])
		if n_custom_ids and n_custom_ids.n_custom_line_o2m:
			n_custom_ids.unlink()
		order.n_add_sales_product= n_flag 
	#CH_029 end <<<

        body_html = """<div><b>Issued</b></div>
<div>Quotation Issued by <strong>${object.user_id.name}</strong>
</div>
"""
        body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order', self.id, context={})
        msg_id = self.message_post(body_html)
        self.write({'lock': True,'n_hide_currency':False})
        return True
        
    @api.multi
    def make_unlock(self):
        body_html = """<div><b>Unlock</b></div>
<div>Quotation Unlocked by <strong>${user.name}</strong>
</div>
"""
        body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order', self.id, context={})
        msg_id = self.message_post(body_html)
        self.write({'lock': False,'n_hide_currency':True})
        return True
        
    #CH03 start >>
    @api.multi
    @api.onchange('n_quotation_currency_id')
    def _get_quotation_currency(self):
	if self.n_quotation_currency_id:
		price_list_id=self.env['product.pricelist'].search([('name','ilike','public'),('currency_id','=',self.n_quotation_currency_id.id),('company_id','=',self.company_id.id)])
		if not price_list_id:
			raise UserError(_("Please Create pricelist for "+str(self.n_quotation_currency_id.name)+" currency.......!!"))
        	self.pricelist_id=price_list_id
		self.report_currency_id=self.n_quotation_currency_id.id
		self.n_hide_currency =True
		
    #CH03 end <<<
    @api.multi
    @api.depends('order_line.price_unit', 'report_currency_id','order_line.product_uom_qty', 'order_line.converted_price')
    def _get_converted_total(self):
        for order in self:
            from_currency = order.pricelist_id.currency_id
            if order.report_currency_id:
                to_currency = order.report_currency_id
            else:
                to_currency = order.pricelist_id.currency_id

            if from_currency and to_currency and order.amount_total:
                order.converted_amount_total = from_currency.compute(order.amount_total, to_currency, round=False)
	#CH_N021 add code to store amount in company base currency start 
	    if order.amount_total and order.currency_id:
		n_base_currency_amount=order.currency_id.compute(order.amount_total,self.env.user.company_id.currency_id)
        #CH_N021
    
#    notes = fields.Text(string='Notes', placeholder="Notes")
#    valid_date = fields.Date(string='Quotation Valid Till')
    lock = fields.Boolean(string='Lock')
    revise_sequence = fields.Integer('Revise Sequence', default=0)
    revision_count = fields.Integer(string='Revision History', compute='_get_revision_count', readonly=True)
    delivery_date_on = fields.Char(string='Delivery Date')
    delivery_date1 = fields.Date(string="Delivery Date", default=fields.Date.context_today)
    delivery_day = fields.Integer(string="Delivery Date")
    delivery_day_type = fields.Selection([('days', 'Days'),
                                          ('weeks', 'Weeks'),
                                          ('months', 'Months'),
                                          ('Date', 'Date')], string="Delivery Type")
    delivery_day_3 = fields.Selection([('receipt_of_payment', 'Receipt of Payment'),
                                       ('confirmed_purchase_order','Confirmed Purchase Order')],
                                        string="Delivery Terms")
    report_currency_id = fields.Many2one('res.currency', string="Converted Currency")

    converted_amount_total = fields.Monetary(string='Converted Total', compute='_get_converted_total')
    display_con = fields.Boolean(string="Display")
    lead_name = fields.Char(string='Lead Name')
#    from_preview = fields.Boolean(string="Preview")
    n_quotation_currency_id = fields.Many2one('res.currency', string="Quotation Currency")
    n_show_convert_currency = fields.Boolean(string="Convert Currency?",default=False)
    n_hide_currency	= fields.Boolean(string="hide Currency?",default=False)
    n_base_currency_amount = fields.Float('Total In AED', digits=(16,5), default=0.0)  #CH_020 add field to store value in base currency 

    @api.onchange('incoterm')
    def incoterm_onchange(self):
    	for res in self:
    	    if res.incoterm:
    		for line in res.order_line:
    			if line.pricelist_type in ('1','4'):
    				product = line.product_id.with_context(
					lang=res.partner_id.lang,
					partner=res.partner_id.id,
					quantity=line.product_uom_qty,
					date_order=res.date_order,
					pricelist=res.pricelist_id.id,
					uom=line.product_uom.id,
					fiscal_position=self.env.context.get('fiscal_position')
				    )
            
    				context = self._context.copy()
				context.update({'customer_id': line.customer, 'product_id': line.product_id,'do_term':res.incoterm.id})
				result = self.pool['product.pricelist']._price_get_multi_line(self._cr, self._uid, res.pricelist_id, [(product,line.product_uom_qty, res.partner_id.id),], context=context)
				if result:
				   line.price_line_id = result.get(product.id)[1] or False
				   line.final_price = line.fixed_price
				   line.price_unit = line.fixed_price
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_uom_qty = fields.Float(string='Quantity', digits=(16,0), required=True,default=1.0)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Payment Term'), default=0.0)
    #price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True, digits=dp.get_precision('Payment Term'))
    converted_price = fields.Float('Converted Price', digits=dp.get_precision('Payment Term'), default=0.0)#, compute="_get_converted_data")
    converted_subtotal = fields.Float(string='Converted Subtotal',digits=dp.get_precision('Payment Term'), default=0.0)#, compute="_get_converted_data")
    display_con = fields.Boolean(string="Display")
    lock = fields.Boolean(related="order_id.lock", string='Lock', store=True)
    converted_currency_id = fields.Many2one('res.currency', 'Currency', related='order_id.report_currency_id', store=True)
    n_show_convert_currency= fields.Boolean(string="Convert Currency?", related='order_id.n_show_convert_currency')

    @api.depends('qty_min_check', 'product_uom_qty')
    @api.multi
    def check_product_min_qty(self):
        for line in self:
            if line.pricelist_type == '2':
                if line.price_calculator_id.moq_length <= line.price_calculator_id.total_pcs:
                    line.qty_min_check = True
                else:
                    line.qty_min_check = False
            else:
                if line.product_uom_qty >= line.min_qty:
                    line.qty_min_check = True
                else:
                    line.qty_min_check = False
                    
    qty_min_check = fields.Boolean(string="Quantity is Minimun", compute="check_product_min_qty")
    n_show_approval_bool=fields.Boolean(string="Show Approval Discount",Default=False)
    
  #CH_N111 add code to calculate converted price on save and create >>
    @api.multi
    def write(self,vals):
	for rec in self:
		price_unit=vals.get('price_unit') if vals.get('price_unit') else rec.price_unit
		product_qty=vals.get('product_uom_qty') if vals.get('product_uom_qty') else vals.get('calc_qty') if vals.get('calc_qty') else rec.product_uom_qty
		from_currency= rec.order_id.pricelist_id.currency_id 
		to_currency = rec.order_id.report_currency_id
		if from_currency and to_currency:
			vals.update({'converted_price':from_currency.compute(price_unit,to_currency,round=False)})
			vals.update({'converted_subtotal': from_currency.compute(price_unit*product_qty, to_currency, round=False)})
		else:
			vals.update({'converted_price':price_unit})
			vals.update({'converted_subtotal':price_unit*product_qty})
	return super(SaleOrderLine,self).write(vals)

    @api.model
    def create(self,vals):
      #CH_N147 add code to avoid duplicate records on preview button >>>>
      	qty=vals.get('calc_qty') if vals.get('calc_qty') else vals.get('product_uom_qty')
    	if vals.get('order_id'):
		exit_ids=self.search([('order_id','=',vals.get('order_id')),('product_id','=',vals.get('product_id')),('name','=',vals.get('name')),('product_uom_qty','=',qty),('price_unit','=',vals.get('price_unit')),('product_uom','=',vals.get('product_uom'))])
		if exit_ids:
			return exit_ids
	#<<<		
	order_id=vals.get('order_id')
	if order_id:
		sale_id=self.env['sale.order'].search([('id','=',order_id)])
		from_currency = sale_id.pricelist_id.currency_id 
		to_currency = sale_id.report_currency_id
		if from_currency and to_currency :
			vals.update({'converted_price':from_currency.compute(vals.get('price_unit'),to_currency, round=False)})
			vals.update({'converted_subtotal':from_currency.compute(vals.get('price_unit')*qty,to_currency, round=False)})
		else:
			vals.update({'converted_price':vals.get('price_unit')})
			vals.update({'converted_subtotal':(vals.get('price_unit')*qty)})
	return super(SaleOrderLine,self).create(vals)
  #CH_N111<<

class res_bank(models.Model):
    _inherit = 'res.bank'

    iban_number = fields.Char(string="IBAN Number", size=34)

class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    active_account = fields.Boolean(string="Active")
    #currency_id = fields.Many2one('res.currency', string="Currency")
    iban_number = fields.Char(string="IBAN Number", size=34)

class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.depends('order_ids', 'order_ids.state', 'order_ids.lock')
    @api.multi
    def get_quote(self):
        for line in self:
            sale_ids = self.env['sale.order'].search([('opportunity_id', '=', line.id), ('state', 'in', ['draft', 'sent'])])
            if sale_ids:
                line.check_quote = True
            if not sale_ids:
                line.check_quote = False
        return

    check_quote = fields.Boolean('Check Quote', compute=get_quote, store=True)

class ProductUom(models.Model):
    _inherit = "product.uom"

    @api.model
    def get_uom_categ(self):
        if self._context.get('product_id'):
            product = self.env['product.product'].sudo().browse(self._context.get('product_id'))
            return product.uom_id.category_id.id
        
    @api.model
    def create(self, vals):
        if self._context.get('product_id'):
            product = self.env['product.product'].sudo().browse(self._context.get('product_id'))
            vals.update({'category_id': product.uom_id.category_id.id})
        return super(ProductUom, self).create(vals)

    category_id = fields.Many2one('product.uom.categ', 'Unit of Measure Category', default=get_uom_categ)

class ResUser(models.Model):
    _inherit = 'res.users'

    designation = fields.Char("Designation on Quotation")

#CH_NO8 start >>
class n_custom_product(models.Model):
	_name = "n.custom.product"
	
	n_custom_line_o2m =fields.One2many('n.custom.product.line','n_line_id','Custom product line')
	n_sale_order_id =fields.Many2one('sale.order','Sale Order')
	n_custom_currency_id = fields.Many2one('res.currency', string="Currency")
	n_add_product =fields.Boolean('Add',Default=False) #CH_029 add boolean to to check if product is add or not
	n_add_rec =fields.Boolean('Add',Default=False) #CH_029 add boolean to to check if product is add or not
	
	#CH_029 add save method to make boolean false when product are save to create after sale conformation
	@api.multi
	def save_product(self):
		self.n_sale_order_id.n_add_sales_product='edit'
		#CH_N052>>>
		for line in self:
			for rec in line.n_custom_line_o2m:
				if rec.n_add_product_bool and rec.product_type !='service':
					if not rec.n_type_of_package :
						raise UserError('Please define packaging type ')
					if not rec.n_qty_per_package:
						raise UserError('Please define quantity per packaging')
					#if rec.n_sale_line_id.product_uom_qty%rec.n_qty_per_package>0 :
					#	raise UserError('This product is packaged by {}. You should sell in multiplication of that'.format(rec.n_qty_per_package))
						
		#CH_N052<<<
		if self.n_custom_line_o2m ==[]:
			self.n_sale_order_id.n_add_sales_product='done'
		return True
	#CH_029 <<< end

	@api.multi
	def n_confirm_product(self):
	    error_string=''
	    try:
		#CH_N09 start>>>
		pricelist_obj = self.env['product.pricelist']
		customer_obj = self.env['customer.product']
		for rec in self:
		    if not rec.n_add_rec:
			pricelist_id=pricelist_obj.search([('customer','=',rec.n_sale_order_id.partner_id.id),
						('currency_id','=',rec.n_custom_currency_id.id),('active','=',True),
						('contract_use','=',False),('generic_use','=',False)],limit=1)
			
			if not pricelist_id:
				n_cust_name=str(rec.n_sale_order_id.partner_id.name)+" Pricelist"
				vals={'name':n_cust_name,'customer':rec.n_sale_order_id.partner_id.id,
					'active':True,'company_id':self.env.user.company_id.id,'currency_id':rec.n_custom_currency_id.id}
				pricelist_id=pricelist_obj.create(vals)

			for line in rec.n_custom_line_o2m:
                             print "line-----------------",line
			     if line.n_add_product_bool:
				line_product_type = line.n_product_type
				material_id = sub_type_id = False
				while line_product_type.parent_id:
					if not sub_type_id:
						sub_type_id = self.env['product.raw.material.type'].search([('name','=',line_product_type.name)],limit=1) 
					elif not material_id:
						material_id = self.env['product.material.type'].search([('name','=',line_product_type.name)],limit=1)
					line_product_type = line_product_type.parent_id
				if sub_type_id and not material_id:
					material_id = sub_type_id
					sub_type_id = False
				vals={'pricelist_id':pricelist_id.id,'product_type':line_product_type.id,
				      'ext_product_number':line.n_ext_product_no,'product_name':line.n_product_name,
				      'product_description':line.n_description,'avg_price':line.n_avg_price,
				      'min_qty':line.n_min_qty,'uom_id':line.n_unit.id,
				      'type_of_packaging':line.n_type_of_package.id,'type':line.product_type,
				      'qty_per_package':line.n_qty_per_package,
				      'product_id':line.n_sale_line_id.product_id.id,
				      'material_id':material_id,'sub_type_id':sub_type_id,
				      'valid_from':line.n_from_date,'to_date':line.n_to_date,'n_product_type':'custom',
				      'currency_id':rec.n_custom_currency_id.id if rec.n_custom_currency_id else False,
				      'item_ids':[[0, False, {'do_term':rec.n_sale_order_id.incoterm.id,
				           'min_quantity': 1, 'fixed_price': line.n_avg_price, 'qty': line.n_min_qty}]]}
                                print "valsvalsvalsvals cust ids----",vals
				cust_ids=customer_obj.create(vals)
				
				if line.n_film_ids:
					self.env['sale.order.line'].sudo().browse(line.n_sale_line_id.id).write({
					'product_id': cust_ids.product_id.id,'n_film_product_id':cust_ids.product_id.id,
					'product_packaging':cust_ids.product_packaging.id})
					cust_ids.product_id.write({'n_calculator_id':line.n_film_ids.id,
							     'n_product_type':'film','weight':line.weight,
							     'initial_weight':line.weight})
					uom_id=self.env['product.uom'].search([('name','=','cm')])
					
					if not uom_id:
						raise UserError('Please Define cm unit in Unit of Measure.')
			## Product Type
					if line.n_film_ids.product_type:
						att_id=self.env['n.product.discription.value'].search([('string','=','product_type')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.product_type.name.name)})
			## Type Of Bags
					if line.n_film_ids.bag_type:
						att_id=self.env['n.product.discription.value'].search([('string','=','type_of_bag')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.bag_type.name.name)})
			## Length
					if line.n_film_ids.lenght:
						att_id=self.env['n.product.discription.value'].search([('string','=','length')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.lenght),'unit':uom_id.id})
			## Width
					if line.n_film_ids.width:
						att_id=self.env['n.product.discription.value'].search([('string','=','width')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.width),'unit':uom_id.id})
			## Left
					if line.n_film_ids.left:
						att_id=self.env['n.product.discription.value'].search([('string','=','lgusset')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.left),'unit':uom_id.id})
			## Right
					if line.n_film_ids.right:
						att_id=self.env['n.product.discription.value'].search([('string','=','rgusset')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.right),'unit':uom_id.id})
			## TOP
					if line.n_film_ids.top:
						att_id=self.env['n.product.discription.value'].search([('string','=','topfold')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.right),'unit':uom_id.id})
			## Bottom
					if line.n_film_ids.bottom:
						att_id=self.env['n.product.discription.value'].search([('string','=','bgusset')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.right),'unit':uom_id.id})
			## Printinh Area			
					if line.n_film_ids.printing_area:
						p_uom_id=self.env['product.uom'].search([('name','=','%')])
						att_id=self.env['n.product.discription.value'].search([('string','=','printing_area')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.right),'unit':p_uom_id.id})
			## Micron
					if line.n_film_ids.micron:
						mac_uom_id=self.env['product.uom'].search([('name','=','micron')])
						att_id=self.env['n.product.discription.value'].search([('string','=','thickness')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.micron),'unit':mac_uom_id.id})
			## Printing 
					if line.n_film_ids.printing_type:
						att_id=self.env['n.product.discription.value'].search([('string','=','printing_type')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.printing_type.name)})
			## Material type
					if line.n_film_ids.material_type:
						att_id=self.env['n.product.discription.value'].search([('string','=','material')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.material_type.name.name)})

			## Total Printing area
					if line.n_film_ids.total_printing_area:
						att_id=self.env['n.product.discription.value'].search([('string','=','total_printing_area')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.total_printing_area),'unit':uom_id.id})
			## Ink Weight
					if line.n_film_ids.ink_weigth:
						att_id=self.env['n.product.discription.value'].search([('string','=','inkweight')],limit=1)
						self.env['n.product.discription'].create({'product_id': cust_ids.product_id.product_tmpl_id.id,'attribute':att_id.id,'value':str(line.n_film_ids.ink_weigth/line.n_film_ids.total_pcs)})
				else:
					self.env['sale.order.line'].sudo().browse(line.n_sale_line_id.id).write({'product_id': cust_ids.product_id.id,'product_packaging':cust_ids.product_packaging.id})
		    rec.n_add_rec=True
		#CH_N09 end <<<<
		return True
	    except Exception as err:
    		if error_string:
    			raise UserError(error_string)
		else:
	    		exc_type, exc_obj, exc_tb = sys.exc_info()
	    		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		    	_logger.error("API-ERROR : Add product on Confirm sale {} {} {}".format(err,fname,exc_tb.tb_lineno))
		    	raise UserError("Exception in Add product on Confirm sale {} {} {} \n Please Contact administrator ".format(err,fname,exc_tb.tb_lineno))

class n_custom_product_line(models.Model):
	_name = "n.custom.product.line"

	n_line_id = fields.Many2one('n.custom.product','Custom product')
	
	n_product_name = fields.Char(string="Product Name")
	n_avg_price = fields.Float('Price',digits=(16,4))
	n_min_qty = fields.Float('MOQ')
	
	#CH_N09 start >>
	product_type = fields.Selection([('service','Service'),('product','Stockable Product')],'Type')
	n_add_product_bool =fields.Boolean('Add',Default=True)
	n_product_type = fields.Many2one('product.category','Category')
	n_description = fields.Char(string="Description")
	n_unit =fields.Many2one('product.uom',"Unit")
	n_type_of_package = fields.Many2one('product.uom', string='Packaging', domain=[('unit_type.string','=','pri_packaging')])
	n_qty_per_package = fields.Integer(string='Qty/Packing')
	n_ext_product_no = fields.Char(string="External No.")
	#CH_N09 end <<
	
	#CH_N010 start >>
	n_from_date = fields.Date('Valid From', default=fields.Date.context_today)
	n_to_date = fields.Date('To', default=fields.Date.context_today)
	n_film_ids = fields.Many2one('pricelist.calculater', string="Price Calculator")
	#CH_N017
	n_exist=fields.Selection([('new','New Product'),('exist', 'Existing')], 'Existing Product')
	#CH_N050
	n_sale_line_id =fields.Many2one('sale.order.line','Sale Order')
	weight = fields.Float('Weight',digits=dp.get_precision('Payment Term'))
##CH_N08 end <<

	@api.onchange('n_product_name')
	def _check_product_name(self):
		prod_obj=self.env['product.product']
		for res in self:
			if res.n_product_name:
				prod_ids=prod_obj.search([('name_template','=',res.n_product_name)])
				if prod_ids:
					res.n_exist='exist'
				else:
					res.n_exist='new'

