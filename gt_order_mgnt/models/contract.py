# -*- coding: utf-8 -*-

from openerp import fields, models ,api, _
from datetime import datetime,timedelta, date
from openerp.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp

class SaleOrder(models.Model):
	_inherit='sale.order'

	@api.model
	def create(self,vals):
		rec = super(SaleOrder,self).create(vals)
		if rec.is_contract and rec.contract_id:
			if not rec.contract_id.tax_bool:
				for line in rec.order_line:
					line.tax_id=False
		return rec

class CustomerContract(models.Model):
    _name = 'customer.contract'
    _inherit = ['mail.thread']
    
    @api.multi
    @api.onchange('customer_id')
    def onchange_partner_id(self):
        if not self.customer_id:
            self.update({
                'invoice_id': False,
                'delivery_id': False,
              #  'payment_term_id': False,
            })
            return

        addr = self.customer_id.address_get(['delivery', 'invoice'])
        values = {
           'pricelist_id': False,
           'payment_term_id':False,
            'invoice_id': addr['invoice'],
            'delivery_id': addr['delivery'],
        }
        self.update(values)
        
    @api.v7
    def copy_new_contract_mgt(self, cr, uid, ids, context=None):
        list_l=[]
        sh_l=[]
        for rec in self.browse(cr, uid, ids, context):
             for line in rec.contract_line:
                list_l.append((0,0,{'product_id':line.product_id.id, 'product_type':line.product_type.id,
                                    'uom_id':line.uom_id.id, 'package_uom_id':line.package_uom_id.id,
					'product_packaging':line.product_packaging.id if line.product_packaging else False}))
             for sh in rec.schedule_ids:
                 sh_l.append((0,0,{'product_id':sh.product_id.id, 'product_qty':sh.product_qty,
                                  'schedule_date':sh.schedule_date, 'note':sh.note }))
             res=self.copy(cr,uid, rec.id, {'contract_id':rec.id, 'name':str(rec.name),
                                          
                                           'contract_line':list_l,'schedule_ids':sh_l},context) 
             rec.message_post(body='Renew Contract from Old:' + str(rec.name))
             return {
            'name': 'Custmer Contract',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'customer.contract',
            'view_id': False,
            'domain': [('contract_id','=',rec.id)],
            'type': 'ir.actions.act_window',
            'target' : 'current',
            #'context': {'default_active_id' : rec.id},
        }
        
    @api.multi
    def open_contract_history(self):
        for line in self:
            contract_tree = self.env.ref('gt_order_mgnt.customer_contract_tree_view', False)
            contract_form = self.env.ref('gt_order_mgnt.customer_contract_form_view', False)
            if contract_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'customer.contract',
                    'views': [(contract_tree.id, 'tree'), (contract_form.id, 'form')],
                    'view_id': contract_tree.id,
                    'target': 'current',
                    'domain':[('contract_id','=',line.id)],
                }
        return True 
        
    @api.multi
    def open_sales_history(self):
        for line in self:
            sale_tree = self.env.ref('sale.view_quotation_tree', False)
            sale_form = self.env.ref('sale.view_order_form', False)
            if sale_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'sale.order',
                    'views': [(sale_tree.id, 'tree'), (sale_form.id, 'form')],
                    'view_id': sale_tree.id,
                    'target': 'current',
                    'domain':[('id','=',line.sale_id.ids), ('contract_id','=',line.id)],
                }
        return True
        
    @api.multi
    def open_delivery_history(self):
        for line in self:
            stock_tree = self.env.ref('stock.vpicktree', False)
            stock_form = self.env.ref('stock.view_picking_form', False)
            if stock_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'stock.picking',
                    'views': [(stock_tree.id, 'tree'), (stock_form.id, 'form')],
                    'view_id': stock_tree.id,
                    'target': 'current',
                    'domain':[('sale_id','=',line.sale_id.ids)],
                }
        return True
        
    @api.multi
    def open_production_request_history(self):
        for line in self:
            pr_tree = self.env.ref('gt_order_mgnt.n_production_request_tree', False)
            if pr_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'n.manufacturing.request',
                    'views': [(pr_tree.id, 'tree')],
                    'view_id': pr_tree.id,
                    'target': 'current',
                    'domain':[('contract_id','=',line.id)],
                }
        return True
        
    @api.multi
    def open_mrp_history(self):
        total=0.0
        for line in self:
            total +=1
            mrp_tree = self.env.ref('mrp.mrp_production_tree_view', False)
            mrp_form = self.env.ref('mrp.mrp_production_form_view', False)
            if mrp_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'mrp.production',
                    'views':[(mrp_tree.id, 'tree')],
                    'view_id': mrp_tree.id,
                    'target': 'current',
                    'domain':['|',('sale_id','=',line.sale_id.ids),('contract_id','=',line.id)],
                }
        return True
        
    @api.multi
    def open_PO_history(self):
        for line in self:
            po_tree = self.env.ref('purchase.purchase_order_tree', False)
            po_form = self.env.ref('purchase.purchase_order_form', False)
            if po_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'purchase.order',
                    'views':[(po_tree.id, 'tree')],
                    'view_id': po_tree.id,
                    'target': 'current',
                    'domain':[('contract_id','=',line.id)],
                }
        return True
        
    @api.multi
    def open_invoice_history(self):
        for line in self:
            account_tree = self.env.ref('account.invoice_tree', False)
            account_form = self.env.ref('account.invoice_form', False)
            if account_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'account.invoice',
                    'views': [(account_tree.id, 'tree'), (account_form.id, 'form')],
                    'view_id': account_tree.id,
                    'target': 'current',
                    'domain':[('sale_id','=',line.sale_id.ids)],
                }
        return True
        
    name= fields.Char(string="Contract Number")
    contract_id= fields.Many2one('customer.contract', string='Parent Number')
    customer_id= fields.Many2one('res.partner', string='Customer')
    lpo_base=fields.Boolean('LPO Base')
    schedule_base=fields.Boolean('Schedule Base')
    price= fields.Float(string="Total Contract Price", compute='total_contract_amount')
    lead_time= fields.Integer(string="Lead Time")
    expiry_date = fields.Date(string="Expiry Date")
    issue_date= fields.Date(string="Issue Date")
    copy_of_contract = fields.Binary(string="Copy of Contract")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Term", )
    invoice_id= fields.Many2one('res.partner', string="Invoice Address")
    delivery_id= fields.Many2one('res.partner', string="Delivery Address")
    terms_and_condition= fields.Text(string="Teerms and Condition")
    schedule_ids= fields.One2many('contract.schedule', 'contract_id', string="Products")
    contract_qty= fields.Integer('Quantity')
    remaining_qty= fields.Integer('Remaining Quantity')
    pricelist_id= fields.Many2one('product.pricelist', string='Pricelist')
    product_id = fields.Many2one('product.product', string='Product')
    pipeline_id = fields.Many2one('crm.lead','Pipeline', domain=[('type','=','opportunity')],readonly=True)
    lpo_document = fields.Binary('LPO Document')
    lpo_number= fields.Char('LPO Number')
    lpo_receipt_date= fields.Date('LPO Receipt Date')
    lpo_issue_date= fields.Date('LPO Issue Date')
    sale_id= fields.One2many('sale.order', 'contract_id', string="Sale Order")
    user_id= fields.Many2one('res.users', 'SalesPerson' , default=lambda self: self.env.user)
    uploaded_documents= fields.Many2many('ir.attachment','contract_attachment_rel','contract_doc','id','Contract Documents')
    contract_line= fields.One2many('contract.product.line', 'cont_id', string="Products", copy=True)  
    contract_name= fields.Char('Contract Name' )
    external_number= fields.Char('External Number',help='Referance number for customer')
    order_confirm_documents= fields.One2many('order.confirm.wizard','contract_id')
    visible_request_button= fields.Boolean(string='Visible Button', default=False)
    state= fields.Selection([('draft', 'Draft'),('contract', 'Contracted'),('sale','Sale ordered'),('Done','Done')],
                          string="State", readonly=True , track_visibility='onchange', default='draft')

    tax_bool=fields.Boolean('Tax Apply.?',default=True)
    customer_vat=fields.Char('Customer VAT',related='customer_id.vat')

    @api.onchange('issue_date')
    def contract_onchange(self):
    	if self.issue_date:
    		self.expiry_date = datetime.strptime(self.issue_date,'%Y-%m-%d')+timedelta(days=365)
     
    @api.multi
    def lock_cotract(self):
    	for rec in self.contract_line:
    		if not rec.contract_qty:
    			raise UserError(("Please Enter Quantity of {} product".format(rec.product_id.name))) 
    	self.state='contract'
    	return True 

    @api.multi
    def unlock_cotract(self):
        if self.state == 'contract':
    	   self.state='draft'
    	return True 
    	                    
    @api.multi
    @api.onchange('payment_term_id')
    def n_payment_term(self):
	if self.payment_term_id.n_new_request:
		self.visible_request_button=True
	else:
		self.visible_request_button=False
	 
    @api.multi
    def show_payment_term(self):
	if self.payment_term_id and self.visible_request_button:
		form_id = self.env.ref('gt_order_mgnt.request_payment_term_wizard_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'request.payment.term.wizard',
		    'views': [(form_id.id, 'form')],
		    'view_id': form_id.id,
		    'target':'new',
		} 

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('customer.contract') or 'New'
        result = super(CustomerContract, self).create(vals)
        return result
        
    @api.multi
    @api.onchange('pricelist_id')
    def product_onchnage(self):
	li=[]
        sh_list=[]
        for record in self:
            for rec in record.pricelist_id:
               if rec.cus_products:
                   for cus in rec.cus_products:
			li.append((0,0,{'product_type':cus.product_type.id, 'cont_id':self.id,
					'ext_product_number':cus.ext_product_number,
                                       	'product_id':cus.product_id.id, 'uom_id':cus.uom_id.id,
                               	'product_packaging':cus.product_packaging.id if cus.product_packaging else False,
				       'sale_price':cus.avg_price}))
                        if record.schedule_base:
                           sh_list.append((0,0,{ 'contract_id':self.id,'product_id':cus.product_id.id}))  
        self.contract_line=li
        self.schedule_ids=sh_list
         
    @api.multi
    def sale_order_wizard(self):
        lst=[]
        wiz_form = self.env.ref('gt_order_mgnt.contract_sale_wizard', False)
        if self.contract_line:
           for rec in self.contract_line:
               if rec.state not in ('cancel','stop'):
		       lst.append(({'product_id':rec.product_id.id,'uom_id':rec.uom_id.id,'qty':0,
		                     'contract_qty':rec.contract_qty-rec.order_qty if (rec.contract_qty-rec.order_qty)>1 else 0,
		                     'remaining_qty':rec.contract_qty-rec.order_qty if (rec.contract_qty-rec.order_qty)>1 else 0,
		                     'product_packaging':rec.product_packaging.id,'sale_price':rec.sale_price,
		                      'line_id':rec.id}))
		                       
        if wiz_form:
		context = self._context.copy()
		context.update({'default_sale_line':lst, 'default_contract_id':self.id}) 
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'contract.sale.wizard',
                    'view_id': wiz_form.id,
                    'target': 'new',
                    'context': context,
                }

    @api.multi 
    def add_product_wizard(self):
    	wiz_form = self.env.ref('gt_order_mgnt.contract_add_product_wizard', False)
	for rec in self:
		product_ids=[i.product_id.id for i in rec.contract_line]
		flag=True
		lst=[]
		context = self._context.copy()
		for line in rec.pricelist_id.cus_products:
			if line.product_id.id not in product_ids:
				flag=False
		 		lst.append((0,0,{'product_id':line.product_id.id,'cus_id':line.id}))
 		if flag:
 			raise UserError("There is no extra product defined in contract pricelist,\n Please add product in pricelist first.")
		context.update({'default_product_line':lst, 'default_contract_id':self.id}) 
		return {
		    'name':'Add Products',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'contract.add.product.wizard',
                    'view_id': wiz_form.id,
                    'target': 'new',
                    'context': context,
                }  

    @api.multi 
    def status_operation_wizard(self):
    	wiz_form = self.env.ref('gt_order_mgnt.contract_product_operation_wizard', False)
	for rec in self:
		flag=True
		lst=[]
		context = self._context.copy()
		for line in rec.contract_line:
			flag=False
			prv_status = line.status if line.status in ('stop','cancel') else False
	 		lst.append((0,0,{'product_id':line.product_id.id,'prv_status':prv_status,
	 				'status':prv_status,'contract_line_id':line.id}))
 		if flag:
 			raise UserError("Product is not found")
		context.update({'default_product_line':lst, 'default_contract_id':self.id})
		return {
		    'name':'Update Product State',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'contract.add.product.wizard',
                    'view_id': wiz_form.id,
                    'target': 'new',
                     'context': context,
                }     
                                  
    '''@api.multi
    def create_sale_order_contract(self):
        for record in self:
	    n_dic=[]
            for rec in record.contract_line:
                line = self[0]
	        context = self._context.copy()
                if rec.select_data : 
	           n_dic.append((0, 0, { 'product_id':rec.product_id.id,'invoice_status':'no', 'approve_m':True,
                             'price_m':True,'pricelist_type':'1','customer':self.customer_id.id,
                             'product_uom':rec.uom_id.id, 
                             'procurement_ids':[], 'qty_invoiced':0.0,
                             'qty_delivered_updateable':True,'contract_bool':True,
                             'contract_remain_qty':rec.remaining_qty, 'contract_qty':rec.contract_qty,
                             'open_qty':rec.reserve_qty,'product_packaging':rec.product_packaging.id,
                             'state':'draft', 'not_update':False,
                             'name':rec.product_id.name ,'name1':rec.product_id.description_sale}))
                rec.select_data=False
	    context.update({'default_partner_id':self.customer_id.id, 
                             'partner_shipping_id':self.delivery_id.id, 'partner_invoice_id':self.invoice_id.id,
                             'default_payment_term_id':self.payment_term_id.id,
                              'default_n_quotation_currency_id':self.quotation_currency_id.id,
                              'default_user_id':self.user_id.id,'default_is_contract':True,
                             'default_validity_date':self.expiry_date, 'default_contract_id':self.id,
                              'default_order_line':n_dic,'n_ctx':True, 'origin':self.name})   
               
            mo_form = self.env.ref('sale.view_order_form', False)
            if mo_form:
                    return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'current',
                   'context': context,
                  
             }'''
   
class ContractProductLine(models.Model):
    _name="contract.product.line"
    
    product_type = fields.Many2one('product.category', string="Product Category")
    product_id = fields.Many2one('product.product', string='Product')
    uom_id = fields.Many2one('product.uom', string="Unit")
    product_packaging = fields.Many2one('product.packaging',string="Packaging") # in User replace for below 
    package_uom_id = fields.Many2one('product.uom', string="Packaging") #not in 
    cont_id=fields.Many2one('customer.contract')
    partner_id=fields.Many2one('res.partner',related="cont_id.customer_id",string='Customer')
    select_data=fields.Boolean('Select')
    ext_product_number=fields.Char('External No.')
    contract_qty = fields.Integer('Total Contract Quantity')
    order_qty = fields.Integer('Order  Quantity', compute='total_sold_quantity' )
    sale_qty=fields.Float('Delivered Qty', compute='total_delivered_qty')
    sale_price=fields.Float('Sale Price', digits_compute=dp.get_precision('Product Price'))
    remaining_qty=fields.Integer('Remaining Qty', compute='remaining_cont_qty')
    product_msq=fields.Integer('Minimum Stock Qty',compute='compute_msq_qty')
    qty_avl_open=fields.Float("Qty Available in Stock", compute='total_open_stock_qty')
    qty_avl=fields.Float('Qty Available in Stock', related='product_id.qty_available')
    total_pr_qty=fields.Float('Total Production Qty', compute='total_production_qty')
    reserve_qty=fields.Float('Reserve Qty in Stock', compute='total_reserve_qty', )
    production_bool=fields.Boolean('PR Rqest', compute='production_request')
    sale_id=fields.Many2one('sale.order', string='sale')
    total_reserved_qty=fields.Float('Total Reserve', compute='total_reserve_qty_pr')
    production_id=fields.Many2one('n.manufacturing.request', string="Production Request")
    state=fields.Selection([('draft', 'Draft'),('process','In Process'),
    			    ('completed','Completed'),('stop','Stop'),('cancel','Cancel')],
                            string="State",readonly=True ,track_visibility='onchange',default='draft',
                            compute='sale_orderqty_complete')
    status = fields.Selection([('stop','Stop'),('cancel','Cancel')],string='Opeartion')                      
    reserve_from_stock=fields.Float('Reserve from Stock')
    
    @api.multi
    def compute_msq_qty(self):
 	for res in self:
    		 for i in res.product_id.orderpoint_ids.filtered(lambda x: x.active):
			res.product_msq = i.product_min_qty
			break
    		 else:
    		 	res.product_msq = 0
    @api.multi
    def total_delivered_qty(self):
        for record in self:
            total=0.0
            sale_line= self.env['sale.order.line'].search([('order_id.contract_id','=',record.cont_id.id),('product_id', '=',record.product_id.id),('n_status_rel.n_string','=','delivered')])
            if sale_line:
               for line in sale_line:
                   total += line.product_uom_qty
               record.sale_qty=total
               
    @api.multi
    @api.depends('contract_qty','order_qty','status')
    def sale_orderqty_complete(self):
       for record in self:
       	   if record.status == 'stop':
       	   	record.state = 'stop'
       	   elif record.status == 'cancel':
       	   	record.state = 'cancel'
           elif not record.order_qty:
               record.state ='draft'
           elif record.contract_qty and record.order_qty:
              if record.contract_qty == record.order_qty:
                 record.state='completed'
              if record.remaining_qty:
                 record.state='process'
                 
    @api.multi
    def total_reserve_qty_pr(self):
        for record in self:
            total1=0.0
            rqst_done=self.env['n.manufacturing.request'].search([('con_pro_id','=',record.id),('contract_id','=',record.cont_id.id), ('n_state','in',('done','cancel'))])
            if rqst_done:
               for rqd in rqst_done:
                   total1 +=rqd.n_order_qty
               record.total_reserved_qty=total1
    @api.multi
    def reserve_do_contract(self):
        po_form = self.env.ref('gt_order_mgnt.sale_reserve_history', False)
        if po_form:
            context = self._context.copy()
            context.update({'default_avl_qty':self.qty_avl_open, 'default_contract_id':self.cont_id.id,'n_status':'reserve',
                           'default_res_qty':self.qty_avl_open, 'total_avl_qty':self.reserve_qty
				}) 
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'reserve.history',
                'view_id': po_form.id,
                'target': 'new',
                'context': context
            }
  
    @api.multi
    @api.depends('product_msq', 'reserve_qty')
    def production_request(self):
        for record in self:
            if record.reserve_qty <= record.product_msq:
               record.production_bool=True

    @api.multi
    @api.depends('qty_avl','reserve_qty')
    def total_open_stock_qty(self):
        for record in self:
            total=0.0
            if record.qty_avl and record.reserve_qty:          
                  record.qty_avl_open = (record.qty_avl) - record.reserve_qty
            else:
                  record.qty_avl_open = record.qty_avl
                  
    @api.multi
    def total_sold_quantity(self):
        for record in self:
            total=0.0
            sale_line= self.env['sale.order.line'].search([('order_id.contract_id','=',record.cont_id.id),('product_id', '=',record.product_id.id),('state','!=','cancel')])
            if sale_line:
               for line in sale_line:
                   total +=line.product_uom_qty
               record.order_qty =total
            
    @api.multi
    @api.depends('contract_qty', 'order_qty')
    def remaining_cont_qty(self):
        for record in self:
            if record.contract_qty and record.order_qty:
               record.remaining_qty = record.contract_qty - record.order_qty
            elif not record.order_qty:
            	record.remaining_qty = record.contract_qty
               
    @api.multi
    def total_reserve_qty(self):
        for record in self:
            total1=0.0
            rqst_done=self.env['n.manufacturing.request'].search([('con_pro_id','=',record.id),('contract_id','=',record.cont_id.id), ('n_state','in',('done','cancel'))])
            sale_line= self.env['sale.order.line'].search([('order_id.contract_id','=',record.cont_id.id),('product_id', '=',record.product_id.id),('state','=','sale')])
            if rqst_done:
               for rqd in rqst_done:
                   total1 +=rqd.n_order_qty
               record.reserve_qty += total1
            if sale_line:
               for line in sale_line:
                   history=self.env['reserve.history'].search([('n_reserve_Type','=','so'),('contract_id','=',record.cont_id.id)])
                   his_total=0.0
                   for his in history:
                       his_total +=his.res_qty
                   if record.reserve_qty and line.qty_delivered:
                      record.reserve_qty -=his_total
          
    @api.multi
    def total_production_qty(self):
        for record in self:
            total=0.0
            rqst_id=self.env['n.manufacturing.request'].search([('con_pro_id','=',record.id),('contract_id','=',record.cont_id.id), ('n_state','not in',('done','cancel'))])
            if rqst_id:
               for rq in rqst_id:
                   total +=rq.n_order_qty
               record.total_pr_qty=total
            
    @api.multi
    def create_production_request(self):
        line = self[0]
        mo_form = self.env.ref('gt_order_mgnt.n_production_request_form', False)
        if mo_form:
		context = self._context.copy()
		res_id=context.update({'default_contract_id':self.cont_id.id,'default_n_sale_line':self.sale_id.id,
				'default_n_order_qty':self.remaining_qty,'default_n_product_id':self.product_id.id,
                                 'default_n_state':'draft','default_n_packaging':self.product_packaging.id,
                                 'default_n_unit':self.uom_id.id,
				'default_n_category':self.product_type.id,'default_remaining_contract_qty':self.remaining_qty,
                                 'default_con_pro_id':self.id,'default_n_default_code':self.product_id.default_code,}) 
                line.production_rqst=True
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'n.manufacturing.request',
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
                    'flags': {'form': {'options': {'mode': 'edit'}}}
                }
                
class ContractSchedule(models.Model):
    _name = 'contract.schedule'
    customer_product=fields.Many2one('customer.product', string="Product")
    select_bool=fields.Boolean('Select')
    product_id=fields.Many2one('product.product', string="Product")
    product_qty=fields.Float('Product Qty')
    event_id=fields.Many2one('calendar.event', string="Calendar Event")
    schedule_date=fields.Datetime('Schedule Date')
    
    note=fields.Text('Note')
    contract_id = fields.Many2one('customer.contract', string="Contract") 
    
    @api.multi
    def create_calenar_event(self):
        for record in self:
            subject="%s %s"%(record.contract_id.name , record.contract_id.customer_id.name) 
            event=self.env['calendar.event'].create({'name':subject, 'start_date':record.schedule_date,
                                               'description':record.note, 'start':record.schedule_date, 'stop':record.schedule_date})
            record.select_bool=True
            record.event_id=event.id

class ContractSaleWizard(models.TransientModel):
    _name='contract.sale.wizard'

    delivery_term=fields.Many2one('stock.incoterms', string='Delivery Terms')
    sale_line=fields.One2many('contract.sale.wizard.line','wizard_id')
    contract_id=fields.Many2one('customer.contract', 'Contract No.')
    delivery_date=fields.Date('Delivery Date',required=True)
    validate_bool = fields.Boolean('Delivery Date')
    
    @api.onchange('delivery_term')
    def do_term_onchange(self):
    	for line in self.sale_line:
    	    if self.delivery_term:
    		for res in self.contract_id.pricelist_id.cus_products:
    			if line.product_id.id == res.product_id.id and line.qty > 0:
    				price=0.0
    				for item in res.item_ids:
    					if self.delivery_term.id==item.do_term.id:
						if line.qty >= item.min_quantity and line.qty <= item.qty:
							price=item.fixed_price
				if price:
					line.sale_price=price
				else:
					raise UserError("There is no price defined for product '{}' against delivery term {} for quantity {} ".format(res.product_id.name,self.delivery_term.name,line.qty))
    					
    @api.multi
    def create_sale_order(self):
        for record in self:
	    n_dic=[]
	    if record.sale_line == []:
	    		raise UserError("No records to proceed.!")
            flag=True
            for rec in record.sale_line:
                line = self[0]
	        context = self._context.copy()
	        if rec.check:
	        	if not rec.qty:
	        		raise UserError("There is no quantity entered for product '{}'".format(rec.product_id.name))
	        	flag=False
	        	price_line_id=False
	        	product = rec.product_id.with_context(
					lang=record.contract_id.customer_id.lang,
					partner=record.contract_id.customer_id.id,
					quantity=rec.qty,
					date_order=record.delivery_date,
					pricelist=record.contract_id.pricelist_id.id,
					uom=rec.uom_id.id,
					fiscal_position=self.env.context.get('fiscal_position')
				    )
            
	        	result = self.pool['product.pricelist']._price_get_multi_line(self._cr, self._uid, record.contract_id.pricelist_id, [(product,rec.qty, record.contract_id.customer_id.id),], context=context)
	        	price_unit=0.0
		        if result:
		           	price_line_id=result.get(rec.product_id.id)[1] or False
		           	if price_line_id:
		           		price_unit=self.env['product.pricelist.item'].browse([price_line_id]).fixed_price
           		price_unit=0.0
           		if record.delivery_term:
		    		for res in record.contract_id.pricelist_id.cus_products:
		    			if rec.product_id.id == res.product_id.id:
		    				
		    				for item in res.item_ids:
		    					if record.delivery_term.id==item.do_term.id:
								if rec.qty >= item.min_quantity and rec.qty <= item.qty:
									price_unit=item.fixed_price
			if not price_unit:
				raise UserError("There is no price defined for product '{}' against delivery term {} for quantity {} ".format(rec.product_id.name,record.delivery_term.name,rec.qty))
						
			n_dic.append((0, 0, { 'product_id':rec.product_id.id,'invoice_status':'no', 'approve_m':True,
		                     'price_m':False,'pricelist_type':'1','customer':record.contract_id.customer_id.id,
		                     'product_uom':rec.uom_id.id, 
		                     'procurement_ids':[], 'qty_invoiced':0.0,
		                     'qty_delivered_updateable':True,'contract_bool':True,
		                     'product_uom_qty':rec.qty,'final_price':rec.sale_price,
		                     'product_packaging':rec.product_packaging.id,'lock':True,
		                     'price_unit':price_unit,'fixed_price':price_unit,
		                     'state':'draft', 'not_update':False,
		                     'name':rec.product_id.name ,'name1':rec.product_id.description_sale,
		                     'price_line_id':price_line_id}))
                 	
	    vals={'partner_id':record.contract_id.customer_id.id,'state':'sent',
                             'partner_shipping_id':record.contract_id.delivery_id.id,
                             'incoterm':record.delivery_term.id,'lock':True,
                             'partner_invoice_id':record.contract_id.invoice_id.id,
                             'payment_term_id':record.contract_id.payment_term_id.id,
                              'n_quotation_currency_id':record.contract_id.pricelist_id.currency_id.id,
                              'report_currency_id':record.contract_id.pricelist_id.currency_id.id,
                              'user_id':record.contract_id.user_id.id,'is_contract':True,
                             'validity_date':record.contract_id.expiry_date, 
                              'contract_id':record.contract_id.id,'pricelist_id':record.contract_id.pricelist_id.id,
                              'delivery_date1':record.delivery_date,'delivery_day_type':'Date',
                              'order_line':n_dic,'origin':record.contract_id.name}

            if flag:
            	raise UserError("No record selected")
            
            exist_sale=self.env['sale.order'].search([('contract_id','=',record.contract_id.id)],limit=1)
            if exist_sale:
            	vals.update({'opportunity_id':exist_sale.opportunity_id.id})
            sale=self.env['sale.order'].with_context({'n_ctx':True}).create(vals) 
	    for line in sale.order_line:
		line.onchange_priceline()   
		           
            record.contract_id.state='sale'
            
            res_id=self.env['order.confirm.wizard'].search([('n_sale_order','=',sale.id)])
            if not res_id:
			res_id=self.env['order.confirm.wizard'].create({'n_sale_order':sale.id,'add_documents':False, })
            if sale.state in ('awaiting', 'sale'):
			res_id.write({'add_documents':True, })
            if sale.state in ('sale'):
			res_id.write({'state_bool':True})
            else:
		        res_id.write({'state_bool':False})
            if not sale.payment_term_id.n_new_request and not sale.visible_request_button:
		form_id = self.env.ref('gt_order_mgnt.order_confirm_wizard_form_view1', False)
		context = self._context.copy()
		context.update({'contract':True})
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'order.confirm.wizard',
		    'views': [(form_id.id, 'form')],
		    'view_id': form_id.id,
		    'res_id':res_id.id,
		    'context':context,
		    'target':'new',
		}
		
    @api.multi
    def product_validate(self):
        for record in self:
            if record.sale_line == []:
	    		raise UserError("No records to proceed.!")
	    
	    flag=True		
	    for line in record.sale_line:
	    	if not line.check:
		    line.unlink()
		    
	    	elif line.check:
	    	    context = self._context.copy()
		    if not line.qty:
		    	raise UserError("There is no quantity entered for product '{}'".format(line.product_id.name))
	    	
		    flag=False
		    price_line_id=False
		    product = line.product_id.with_context(lang=record.contract_id.customer_id.lang,
							   partner=record.contract_id.customer_id.id,
							   quantity=line.qty,
							   date_order=record.delivery_date,
							   pricelist=record.contract_id.pricelist_id.id,
							   uom=line.uom_id.id,
							   fiscal_position=self.env.context.get('fiscal_position'))
		    
		    result = self.pool['product.pricelist']._price_get_multi_line(self._cr, self._uid, record.contract_id.pricelist_id, [(product,line.qty, record.contract_id.customer_id.id),], context=context)
		    price_unit=0.0
		    if result:
			price_line_id=result.get(line.product_id.id)[1] or False
		    	if price_line_id:
		    		price_unit=self.env['product.pricelist.item'].browse([price_line_id]).fixed_price
		   		price_unit=0.0
		   		if record.delivery_term:
			    		for res in record.contract_id.pricelist_id.cus_products:
			    			if line.product_id.id == res.product_id.id:
			    				current_date=date.today()
			    				print "kkkkkkkkkkkkkk",current_date,res.valid_from,
			    				if str(res.to_date) < str(current_date):
			    					raise UserError("Product '{}' validity is expired on {} ".format(line.product_id.name,res.to_date))
			    				for item in res.item_ids:
			    					if record.delivery_term.id==item.do_term.id:
									if line.qty >= item.min_quantity and line.qty <= item.qty:
										price_unit=item.fixed_price
				if not price_unit:
					raise UserError("There is no price defined for product '{}' against delivery term {} for quantity {} ".format(line.product_id.name,record.delivery_term.name,line.qty))
				else:
					line.sale_price = price_unit
					
            if flag:
            	raise UserError("No record selected")
            record.validate_bool = True
        return {  "type": "ir.actions.do_nothing",}

    @api.multi
    def send_back(self):
        for record in self:
		record.validate_bool = False
		products=[]
		for line in record.sale_line:
			products.append(line.product_id.id)
		lst=[]	
		for rec in record.contract_id.contract_line:
			if rec.product_id.id not in products:
			       lst.append((0,0,{'product_id':rec.product_id.id,'uom_id':rec.uom_id.id,'qty':0,
				     'contract_qty':rec.contract_qty-rec.order_qty if (rec.contract_qty-rec.order_qty)>1 else 0,
				     'remaining_qty':rec.contract_qty-rec.order_qty if (rec.contract_qty-rec.order_qty)>1 else 0,
				     'product_packaging':rec.product_packaging.id,'sale_price':rec.sale_price,
				      'line_id':rec.id})) 
		record.sale_line=lst
	return {"type":"ir.actions.do_nothing"}
	    
class ContractSaleWizard(models.TransientModel):
    _name='contract.sale.wizard.line'
    
    @api.multi
    @api.depends('qty')
    def remaining_cont_qty(self):
        for record in self:
            if record.qty and record.contract_qty:
               record.remaining_qty = (record.contract_qty - record.qty) if (record.contract_qty - record.qty)>1 else 0

    @api.onchange('qty')
    def do_term_onchange(self):
    	for line in self:
    	    if line.wizard_id.delivery_term:
    		for res in line.wizard_id.contract_id.pricelist_id.cus_products:
    			if line.product_id.id == res.product_id.id:
    				price=0.0
    				for item in res.item_ids:
    					if line.wizard_id.delivery_term.id==item.do_term.id:
						if line.qty >= item.min_quantity and line.qty <= item.qty:
							price=item.fixed_price
				if price:
					line.sale_price=price
				else:
					raise UserError("There is no price defined for product '{}' against delivery term {} for quantity {} ".format(res.product_id.name,line.wizard_id.delivery_term.name,line.qty))

    check=fields.Boolean('Check',default=False)           
    wizard_id=fields.Many2one('contract.sale.wizard')
    product_id=fields.Many2one('product.product', 'Product')
    qty=fields.Float('Qty')
    contract_qty = fields.Integer('Contract Quantity')
    remaining_qty=fields.Integer('Remaining Contract Qty', compute='remaining_cont_qty')
    uom_id=fields.Many2one('product.uom', 'Unit')
    product_packaging = fields.Many2one('product.packaging',string="Packaging")
    sale_price=fields.Float('Price')
    line_id = fields.Many2one('contract.product.line','Product line')
   
class ContractproductWizard(models.TransientModel):
	_name='contract.add.product.wizard'

	product_line = fields.One2many('contract.add.product.line.wizard','line_id','Product')
	contract_id = fields.Many2one('customer.contract', 'Contract No.')

  # Function to add product in existing Products list	
	@api.multi
	def add_product(self):
		flag=True
		for res in self.product_line:
			if res.qty >0 :
				flag=False
				cus_id=res.cus_id
				self.env['contract.product.line'].create({'product_type':cus_id.product_type.id,
					 'cont_id':self.contract_id.id,'ext_product_number':cus_id.ext_product_number,
					 'product_id':cus_id.product_id.id,'uom_id':cus_id.uom_id.id,
					 'product_packaging':cus_id.product_packaging.id if cus_id.product_packaging else False,
					 'sale_price':cus_id.avg_price,'contract_qty':res.qty})
		if flag:
			raise UserError("Please Enter Quantity in at least one product to proceed..!")
		return True

  # Function to change the state of products
	@api.multi
	def operation_validate(self):
		for res in self.product_line:
			if res.contract_line_id.remaining_qty != res.contract_line_id.contract_qty and res.status=='cancel':
				raise UserError("You already Process some of the quantity, Now you can only stop creating sales order of product '{}' ".format(res.product_id.name))
			else:
				res.contract_line_id.status = res.status
		return True

class ContractproductLineWizard(models.TransientModel):
	_name='contract.add.product.line.wizard'
	
	line_id = fields.Many2one('contract.add.product.wizard', 'Order')
	product_id = fields.Many2one('product.product', 'Product')
	qty = fields.Float('Qty')
	cus_id = fields.Many2one('customer.product', 'cus_id')
	
	prv_status = fields.Selection([('stop','Stop'),('cancel','Cancel')],string='Opeartion')
	status = fields.Selection([('stop','Stop'),('cancel','Cancel')],string='Opeartion')
	contract_line_id = fields.Many2one('contract.product.line', 'Products')
		
