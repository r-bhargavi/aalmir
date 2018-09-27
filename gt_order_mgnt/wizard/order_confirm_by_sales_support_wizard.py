# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import json
class orderInvoice(models.TransientModel):
    _name='order.invoice.wizard'
    name=fields.Char('Name')
    wizard_id=fields.Many2one('order.confirm.by.sales.support.wizard')

class OrderConfirmBySalesSupportWizard(models.TransientModel):
    _name = 'order.confirm.by.sales.support.wizard'
    
    @api.model
    def default_get(self,fields):
        rec = super(OrderConfirmBySalesSupportWizard, self).default_get(fields)
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        if obj:
        	rec.update({'warehouse_id':obj.warehouse_id.id})
	return rec
    
    @api.model
    def get_payment_term(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        return obj.payment_term_id and obj.payment_term_id.id or False

    @api.model
    def get_customer_delivery_date(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        line=obj.order_line.search([('order_id','=',obj.id),('n_client_date','!=',False)], limit=1)       
        return line.n_client_date  or False
    
    @api.model
    def get_customer(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            return obj.partner_id and obj.partner_id.id or False
        return False
    
    @api.model
    def get_customer_credit(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            from_currency = obj.partner_id.credit_currency_id if obj.partner_id.credit_currency_id else self.env.user.company_id.currency_id
	    to_currency = obj.report_currency_id if obj.report_currency_id else obj.n_quotation_currency_id
            return from_currency.compute(obj.partner_id.credit_limit,to_currency) or False   #CH_N103 add currency converter
        return False

    @api.model
    def get_customer_credit_appr(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            if obj.payment_id.state =='posted':
               return 'approve'
            else:
               return obj.cr_state if obj.cr_state else False
        return False

    @api.model
    def get_customer_credit_reason(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            return obj.cr_note if obj.cr_note else False
        return False

    @api.model
    def get_order_total(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            amount = obj.n_quotation_currency_id.compute(obj.amount_total,obj.report_currency_id)
            invoice=self.env['account.invoice'].search([('sale_id', '=', obj.id),('state','in',('open','paid'))])
            total=amount
	#CH_N103 ADD currecny converter >>>
            for ln in invoice:
                total -= ln.currency_id.compute((ln.amount_total -ln.residual),obj.report_currency_id)
            if obj.payment_id.state =='posted':
               total -= obj.payment_id.currency_id.compute((obj.payment_id.amount),obj.report_currency_id)
            return total #if total else amount
	#CH_N103 <<<<<
        return False
    
    @api.model
    def get_currency(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
	    return obj.report_currency_id			#CH_N103 get report currency(convert currency) in wizard 
        return False

    @api.model
    def get_invoice_count(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
	    return  1 if obj.payment_term_id.advance_per else 0 #obj.invoice_count			
        return False

    @api.model
    def check_payment_term(self):
	if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
	    flag=False
            if obj.payment_id:
	       if obj.due_payment in ('half_payment'):
                  if obj.payment_term_id.advance_per ==100:
                      flag=False
                  else:
                      flag=True
            return flag
    
    @api.model
    def get_customer_pending_total_amount(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            credit_currency_id=obj.partner_id.credit_currency_id if obj.partner_id.credit_currency_id else self.env.user.company_id.currency_id
            total=0.0
            partner_id=[obj.partner_id.id]
            for prtn in self.env['res.partner'].search([('parent_id','=',obj.partner_id.id)]):
                partner_id.append(prtn.id)
            invoice=self.env['account.invoice'].search([('state','=','open'),('partner_id','in',tuple(partner_id))],order="id")
            if invoice:
               pay=0.0
               for inv in invoice:
                   total += inv.currency_id.compute((inv.residual_new1),credit_currency_id)  #inv.residual_new1
            return total
        return False  

    @api.model
    def get_sale_uninvoice(self):
        if self._context.get('active_id'):
            total_sale=0.0
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            sale=self.env['sale.order'].search([('partner_id', '=', obj.partner_id.id),('state','in',('sale','awaiting')),('id','!=',obj.id)])
            if sale:
               for saleamt in sale:
                   total_sale +=saleamt.n_quotation_currency_id.compute(saleamt.amount_total,saleamt.report_currency_id) #CH_N103 add convert currency
                   invoice=self.env['account.invoice'].search([('sale_id','=',saleamt.id),('state','in',('open','paid'))])
                   total_inv=0.0
                   for inv in invoice:
                   	total_inv  += inv.currency_id.compute(inv.amount_total,saleamt.report_currency_id)   #CH_N103 add convert currency
                   total_sale -=total_inv
            return  total_sale
        return False
   
    @api.model
    def check_stop_delivery(self):
	if self._context.get('active_id'):
		search_id=self.env['res.partner.credit'].search([('sale_id','=',self._context.get('active_id')),('state','=','approve')],limit=1)
		if search_id.stop_delivery:
			return True
		else:
			return False

    @api.model
    def get_warehose(self):
    	if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
	    return obj.warehouse_id if obj.warehouse_id.id else False
        return False
    			
    @api.model
    @api.depends('total_credit_pending','customer_credit')
    def has_limitcheck(self):
        for record in self:
         	if record.total_credit_pending:
		    obj = self.env['sale.order'].browse(self._context.get('active_id'))
		    if  record.customer_credit < record.total_credit_pending and record.cr_state != 'approve':
                        if obj.payment_id:
                           if obj.due_payment in ('half_payment','done'):
                               if obj.payment_term_id.advance_per ==100:
                                  record.has_limit= False 
                               else:
                                  record.has_limit= False
                           else:
                               record.has_limit= True 
                        else:
                          print"___---------",
		          record.has_limit= True
		    elif record.cr_state != 'approve':
			n_date=date.strftime(datetime.strptime(record.customer_id.from_date,'%Y-%m-%d'), '%Y-%m-%d') if record.customer_id.from_date else ''    
			n_date1=date.strftime(datetime.strptime(record.customer_id.to_date,'%Y-%m-%d'), '%Y-%m-%d ') if record.customer_id.to_date else '' 
			todate=date.strftime(date.today(),'%Y-%m-%d')
			if  todate >= n_date  and todate <= n_date1:
		          record.has_limit= False
			else:
			  record.has_limit= True
		    else:
			record.has_limit= False
    
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', default=get_payment_term)
    payment_term_depend = fields.Selection([('delivery', 'Delivery'),
                                            ('credit', 'Credit')],
                                           related='payment_term_id.payment_term_depend',
                                           string="Payment Term Demand")
    match_payment_term = fields.Boolean(string='Payment Term Match', default=False)
    match_credit_limit = fields.Boolean(string='Credit Limit Match', default=False)
    document_match = fields.Boolean(string='Document(LPO/Signed Quotation/POP/Email Match )', default=False)
    customer_id = fields.Many2one('res.partner', string='Customer', default=get_customer)
    customer_credit = fields.Float(string='Credit Limit', default=get_customer_credit)
    customer_pending_invoice=fields.Float('Credit Expected to be paid by Delivery Date', compute='get_customer_pending_amount')
    customer_pending_total_invoice=fields.Float('Total Credit Pending', default=get_customer_pending_total_amount, readonly=True)
    total_credit_pending=fields.Float( compute='total_pending_credit_amt', help="Total Credit Pending Amount + Current Sale order Pending Amount + Total Uninvoice sale Order Amount")
    customer_delivery_date=fields.Date('Current Order Delivery Date' ,default=get_customer_delivery_date)
    order_total = fields.Float(string="Order Amount", default=get_order_total)
    has_limit = fields.Boolean(string="Has Limit?", compute='has_limitcheck')
    credit_expr = fields.Boolean(string="Credit Expr?", compute='credit_amount_test')
    currency_id = fields.Many2one('res.currency', string="Currency", default=get_currency)
    n_force_confirm = fields.Boolean('force confirm',default=check_payment_term)
    invoice_count=fields.Integer(default=get_invoice_count)
    invoice_policy=fields.Selection([('auto', 'Auto Invoice'),('manual',' Manual Invoice')],string='Invoice Policy')
    total_sale_pending_amount=fields.Float(compute='total_sale_amt', string="Total Sale order Pending Amount")
    cr_state=fields.Selection([('request', 'Requested'),('approve','Approved'), ('reject','Reject')], 
            string='Status', default=get_customer_credit_appr)
    cr_note=fields.Text('Reason', default=get_customer_credit_reason)
    uninvoice_saleorder=fields.Float(default=get_sale_uninvoice,readonly=True)
    stop_delivery = fields.Boolean('Stop Delivery',default=check_stop_delivery)
    warehouse_id = fields.Many2one('stock.warehouse',string="Order Deliverd from Warehouse")

    @api.multi
    def request_credit(self):
        for record in self:
            if self._context.get('active_id'):
               obj = self.env['sale.order'].browse(self._context.get('active_id'))
               record.customer_id.write({'cr_state':'request'})
               record.customer_id.message_post(body='Request for customer credit '+' '+ 'Sale Order No.:'+str(obj.name))
               obj.message_post(body='Request for customer credit '+' '+ 'Customer Name:'+str(record.customer_id.name))
               credit=self.env['res.partner.credit'].search([('sale_id', '=',obj.id),('state', '=','request')])
	       credit_data_credit_ask = 0.0
               if record.cr_state != 'request':
                  credit_data=record.customer_id.write({'crdit_ids': [(0, 0, {
				'sale_id': obj.id,
				'sale_amount': obj.amount_total,
				'credit_ask': 0.0,
				'inv_paid': 0.0 ,
                                'partner_id':obj.partner_id.id,
                                'state':'request',
                                'wizard_id':record.id
		               })]})
                  record.cr_state='request'
                  
                  obj.cr_state='request'
               
               else:
                   obj.message_post(body='Already sent Request for Credit Unblock to Accountant. '+' '+ 'Sale Order No.:'+str(obj.name))
               temp_id = self.env.ref('gt_order_mgnt.email_template_customer_credit_sale')
               if temp_id:
			recipient_partners=''
			group = self.env['res.groups'].search([('name', '=', 'Adviser')])
                        group_id = self.env.ref('base.group_sale_manager', False)
                        val=group.users - group_id.users
			for recipient in val:
    				recipient_partners +=str(recipient.login)+","

			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
			query = {'db': self._cr.dbname}
			fragment = {
			    'model': 'res.partner',
			    'view_type': 'form',
			    'id': obj.partner_id.id,
			}
			url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
			body_html = """<div>
    <p> <strong>Request has been sent to accountant for credit unblock </strong></p><br/>
    <p>Dear Sir/Madam,<br/>
	Your sale order No-:<b> %s  \n</b> Customer Name-:'%s ' </p>
    </div>"""%(obj.name or '',obj.partner_id.name or  '',)
                        body_html +='<li>Sale Order Amount:'+str(obj.amount_total) +str(obj.n_quotation_currency_id.name) +'</li>'
                        body_html +='<li>credit Ask:'+str(credit_data_credit_ask) +str(obj.n_quotation_currency_id.name)+'</li>'
			body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'res.partner',obj.partner_id.id, context=self._context)
			
			temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': self.env.user.login})
			temp_id.send_mail(obj.partner_id.id)  
    @api.multi
    @api.depends('customer_id')
    def total_sale_amt(self):
        for record in self:
            sale=self.env['sale.order'].search([('partner_id','=', record.customer_id.id),('state','=', 'sale')])
            if sale:
               sale_total=0.0
               total_val=0.0
               for order in sale:
                   sale_total += order.n_quotation_currency_id.compute(order.amount_total,record.currency_id) 
                   for inv_val in order.invoice_ids:
                       if inv_val.state in ('open', 'paid'):
                          total_val += inv_val.currency_id.compute((inv_val.amount_total - inv_val.residual),order.report_currency_id)
               if total_val:
                      record.total_sale_pending_amount= sale_total - total_val
               else:
                     record.total_sale_pending_amount=sale_total
                       
    @api.multi
    @api.depends('total_credit_pending','customer_credit')
    def credit_amount_test(self):
        for record in self:
            if record.total_credit_pending:
		    obj = self.env['sale.order'].browse(self._context.get('active_id'))
		    n_date=date.strftime(datetime.strptime(record.customer_id.from_date,'%Y-%m-%d'), '%Y-%m-%d') if record.customer_id.from_date else ''    
		    n_date1=date.strftime(datetime.strptime(record.customer_id.to_date,'%Y-%m-%d'), '%Y-%m-%d ') if record.customer_id.to_date else '' 
		    todate=date.strftime(date.today(),'%Y-%m-%d')
		    if  todate >= n_date  and todate <= n_date1:
		          record.credit_expr=False
		    else:
		        
		       #record.has_limit=False 
		        record.credit_expr=True

    @api.multi
    @api.depends('customer_delivery_date')
    def get_customer_pending_amount(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
	    if obj:
		    invoice=self.env['account.invoice'].search([('partner_id', '=',obj.partner_id.id),('state','not in',('paid','cancel','draft'))])  #CH_N103 add draft condition
		    total=0.0
		    for inv in invoice:
		        date_inv = inv.payment_date_inv if inv.payment_date_inv else inv.date_invoice
	           	if date_inv <= self.customer_delivery_date:
		              total += inv.currency_id.compute((inv.residual_new1),obj.report_currency_id) #inv.amount_total  #CH_N103 add residual_new1 and comment amount_total and add convert currency code
		    self.customer_pending_invoice = total

    @api.depends('customer_pending_invoice','order_total')
    def total_pending_credit_amt(self):
        for record in self:
            record.total_credit_pending= record.customer_pending_total_invoice + record.order_total + record.uninvoice_saleorder

    @api.one
    def confirm(self):
        order = self.env['sale.order']
	n_custom = self.env['n.custom.product']
        invoice_val=self.env['account.invoice']
        account_line=self.env['account.invoice.line']
        obj = order.browse(self._context.get('active_id'))
	n_custom_obj= n_custom.search([('n_sale_order_id','=',obj.id)],limit=1)
        if (not self.match_payment_term and not self.document_match) and not self._context.get('force_confirm'):
            raise UserError("Please check Payment Term and Documents") 
        elif not self.document_match and not self._context.get('force_confirm'):
            raise UserError("Please check Documents checkbox") 
        elif not self.match_payment_term and not self._context.get('force_confirm'):
            raise UserError("Please check Payment Term checkbox") 
        elif not self.invoice_policy and not self._context.get('force_confirm') and self.invoice_count !=1:
            raise UserError("Please Select Invoice policy")  
        if obj.contract_id: 
           for rec in obj.contract_id:
               for cont in rec.contract_line:
                   if cont.reserve_qty:
                      line=obj.order_line.search([('product_id','=',cont.product_id.id)])                  
                      for ln in obj.order_line:
                          if ln.product_id.id == cont.product_id.id:
                              self.env['reserve.history'].create({'sale_line':ln.id,'res_qty':cont.reserve_qty,
                                     'n_avl_qty':cont.reserve_qty,'n_total_avl_qty':cont.reserve_qty,
                                     'contract_id':obj.contract_id.id,
                                     'n_status':'reserve','n_reserve_Type':'so'})
                              ln.reserved_qty=cont.reserve_qty
                              ln.available_qty =ln.available_qty - cont.reserve_qty
                              
        if self._context.get('force_confirm'):
            obj.write({'force_confirm' : True})
            user_obj = self.env['res.users'].browse(self.env.uid)
            temp_id = self.env.ref('gt_order_mgnt.email_template_for_force_payment')
            if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                    'model': 'sale.order',
                    'view_type': 'form',
                    'id': obj.id,
                }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                text_link = _("""<a href="%s">%s</a> """) % (url,obj.name)
                body_html ='<b> Sale Order Details: '+str(text_link) +'</b>'
                body_html +='<li> Sale Order No: '+str(text_link) +'</li>'
                body_html +='<li> Customer  Name: '+str(obj.partner_id.name) +'</li>'
		body_html +='<li>Sale Order Amount: '+str(obj.amount_total) + str(obj.n_quotation_currency_id.name)+'</li>'
		body_html +='<li>Payment Term: '+str(obj.payment_term_id.name) +'</li>' 
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',obj.id, context=self._context)
                temp_id.write({'body_html': body_html})
                temp_id.send_mail(obj.id)
               # msg_id = obj.message_post(body_html)
        obj.match_payment_term = self.match_payment_term
        obj.document_match = self.document_match
	#CH_N054 >>> add code for take first status as new on sale confirm
	new_id=self.env['sale.order.line.status'].search([('n_string','=','new')],limit=1)
	if new_id:
		for line in obj.order_line:
			if line.product_id.name not in ('Advance Payment','Deposit Product'):
				line.n_status_rel = [(4,new_id.id)]
	#CH_N054
	n_custom_obj.n_confirm_product()
        obj.action_confirm()
        if obj.state =='done':
           obj.write({'state' : 'sale'})
	obj.write({'force_date':date.today()})
	if obj.opportunity_id:
		if obj.is_contract:
			obj.opportunity_id.write({'is_contract':True,'contract_name':obj.contract_id.name})
	
        if self.invoice_policy:
           if self.invoice_policy == 'auto':
              obj.write({'auto_invoice' : True})
           if self.invoice_policy == 'manual':
              obj.write({'auto_invoice' : False})
        else:
           if self.payment_term_id.advance_per:#self.payment_term_id.advance_per != 100:
              adavance_amount=obj.converted_amount_total * self.payment_term_id.advance_per / 100
              obj.write({'full_invoice' : True,'auto_invoice':False})
              invoice_search=invoice_val.search([('sale_id', '=', obj.id)])
              journal_id = invoice_val.default_get(['journal_id'])['journal_id']
	      lpo_id=self.env['customer.upload.doc'].search([('sale_id_lpo','=',obj.id)])
              lpo_val=[(4, lpo.id) for lpo in lpo_id]
              invoice =invoice_val.create({'partner_id':obj.partner_id.id,
					'partner_invoice_id':obj.partner_invoice_id.id,
					'name': obj.name,  'origin': obj.name,
					'type': 'out_invoice','journal_id': journal_id,
					'n_lpo_receipt_date':obj.lpo_receipt_date,
                                        'n_lpo_issue_date':obj.lpo_issue_date,
                                        'n_lpo_document':obj.lpo_document,
                                        'currency_id':obj.n_quotation_currency_id.id,
                                        'company_id':obj.company_id.id,
					'user_id':obj.user_id and obj.user_id.id,    
					'team_id': obj.team_id.id, 'sale_id':obj.id,
					'account_id':obj.partner_invoice_id.property_account_receivable_id.id,
					'payment_term_id': obj.payment_term_id.id,
					'fiscal_position_id': obj.fiscal_position_id.id or  obj.partner_invoice_id.property_account_position_id.id, 
					'document_id':lpo_val, })

	      if obj.payment_id:
	              obj.payment_id.invoice_ids=[(6, 0, [x.id for x in invoice])]
        	      invoice.payment_ids=[(6, 0, [x.id for x in obj.payment_id])]

              for line in obj.order_line:
                if line.product_id.name != 'Deposit Product':
                   account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
                   inv_line=account_line.create({'invoice_id':invoice.id,'product_id':line.product_id.id, 
                           'quantity':line.product_uom_qty, 'lpo_documents':line.lpo_documents,
                           'uom_id':line.product_uom.id,
                           'name':line.product_id.name, 
                           'price_unit':line.price_unit,
                           'account_id': line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id})
                   inv_line.write({'sale_line_ids': [(6, 0, [line.id])],'invoice_line_tax_ids': [(6, 0, [x.id for x in  line.tax_id])]})
              
              invoice.compute_taxes()  
              invoice.date_due=invoice.payment_date_inv
              invoice.write({'payable_amount':(adavance_amount),
                 'payable_discount':str(obj.payment_term_id.advance_per) + "% Adavance of SO:"})
               
	for n_rec in obj.order_line:
                if n_rec.contract_bool: 
                   n_rec.pending_qty=(n_rec.product_uom_qty - n_rec.reserved_qty) if n_rec.product_uom_qty > n_rec.reserved_qty else (n_rec.reserved_qty - n_rec.product_uom_qty)
                else:
		    n_rec.pending_qty=n_rec.product_uom_qty
		rec_ids=self.env['customer.upload.doc'].search([('sale_line','=',n_rec.id)])
		rec_ids.write({'product_id':n_rec.product_id.id,'state':'done'})
		# instruction button in all modules
		process_ids=self.env['process.instruction.line'].search([('sale_line','=',n_rec.id)])
		process_ids.write({'product_id':n_rec.product_id.id})
	self.env['res.partner.credit'].search([('sale_id','=',obj.id),('state','=','request')]).write({'state':'cancel'})
        return True
