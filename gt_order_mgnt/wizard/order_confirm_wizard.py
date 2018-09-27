# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime
import time
class OrderConfirmWizard(models.Model):
    _name = 'order.confirm.wizard'
    
   
    @api.onchange('lpo_receipt_date', 'signed_quote_receipt_date', 'pop_receipt_date', 'email_confirmation_date')
    def onchange_receipt_date_change(self):
        if self.lpo_receipt_date:
            lpo_receipt_date = datetime.strptime(self.lpo_receipt_date, '%Y-%m-%d').date()
            if lpo_receipt_date < date.today():
                raise UserError("Receipt Date greater or equal to today") 
        
        if self.signed_quote_receipt_date:
            signed_quote_receipt_date = datetime.strptime(self.signed_quote_receipt_date, '%Y-%m-%d').date()
            if signed_quote_receipt_date < date.today():
                raise UserError("Signed Quote Receipt Date greater or equal to today") 
        
        if self.pop_receipt_date:
            pop_receipt_date = datetime.strptime(self.pop_receipt_date, '%Y-%m-%d').date()
            if pop_receipt_date < date.today():
                raise UserError("Pop Receipt Date greater or equal to today") 
    
        if self.email_confirmation_date:
            email_confirmation_date = datetime.strptime(self.email_confirmation_date, '%Y-%m-%d').date()
            if email_confirmation_date < date.today():
                raise UserError("Email Confirmation Date greater or equal to today") 
    
    @api.onchange('lpo_issue_date')
    def onchange_lpo_issue_date_change(self):
        if self.lpo_issue_date and self.lpo_receipt_date:
            lpo_issue_date = datetime.strptime(self.lpo_issue_date, '%Y-%m-%d').date()
            lpo_receipt_date = datetime.strptime(self.lpo_receipt_date, '%Y-%m-%d').date()
            if lpo_issue_date >  lpo_receipt_date: #CH_N036 reverse the condition 
                raise UserError("Issue Date must be greater or equal to Receipt Date") 

    #CH_N036 add methods to fill todays data start >>>
    @api.onchange('lpo_document')
    def onchange_lpo_document(self):
	if self.lpo_document:
		if not self.lpo_issue_date:
			self.lpo_issue_date= date.today()
		if not self.lpo_receipt_date:
			self.lpo_receipt_date= date.today()

    @api.onchange('signed_quote_receipt_doc')
    def onchange_signed_quote(self):
	if self.signed_quote_receipt_doc:
		if not self.signed_quote_number:
			if self._context.get('active_id'):
				sarch_ids=self.env['sale.order'].search([('id','=',self._context.get('active_id'))],limit=1)
				self.signed_quote_number=sarch_ids.name
		if not self.signed_quote_receipt_date:
			self.signed_quote_receipt_date= date.today()

    @api.onchange('email_uploaded_document')
    def onchange_email_document(self): 
	if self.email_uploaded_document and not self.email_confirmation_date:
		self.email_confirmation_date= date.today()

    @api.onchange('pop_uploaded_document')
    def onchange_pop_document(self):    
	if self.pop_uploaded_document and not self.pop_receipt_date:
		self.pop_receipt_date=date.today()
    #CH_N036 end <<

    @api.one
    def done(self):
    	obj = self.n_sale_order
        if obj.contract_id:
           self.contract_id=obj.contract_id.id
        if self.lpo_issue_date and self.lpo_receipt_date:
            lpo_issue_date = datetime.strptime(self.lpo_issue_date, '%Y-%m-%d').date()
            lpo_receipt_date = datetime.strptime(self.lpo_receipt_date, '%Y-%m-%d').date()
            if lpo_issue_date >  lpo_receipt_date:	#CH_N036 reverse the condition 
                raise UserError("Issue Date must be less or equal to Receipt Date") 

        flag = 0
	check_flag1=check_flag2=check_flag3=check_flag4=False
	if self.lpo_number:
		check_flag1=True
	if self.lpo_receipt_date:
		check_flag2=True
	if self.lpo_issue_date:
		check_flag3=True
	if self.lpo_document:
		check_flag4=True
	
	if check_flag1== True and check_flag2== True and check_flag3 == True and check_flag4==True:	
            obj.lpo_name = self.lpo_name
            obj.lpo_number = self.lpo_number
            obj.lpo_receipt_date = self.lpo_receipt_date
            obj.lpo_issue_date = self.lpo_issue_date
            obj.lpo_document = self.lpo_document
	    obj.lpo = True
	    flag = 1

	if check_flag1== False and check_flag2== False and check_flag3 == False and check_flag4==False:
		obj.lpo = False

	if (check_flag1 == True or check_flag2 == True or check_flag3 == True or check_flag4==True) and (check_flag1 == False or check_flag2 == False or check_flag3 == False or check_flag4==False):
		raise UserError("Please Fill all the fields for LPO document Upload") 

	check_flag1=check_flag2=check_flag3=check_flag4=False
	if self.signed_quote_receipt_doc:
		check_flag1=True
	if self.signed_quote_number:
		check_flag2=True
	if self.signed_quote_receipt_date:
		check_flag3=True
	
	if check_flag1== False and check_flag2== False and check_flag3 == False:
		obj.signed_quote = False

	if (check_flag1 == True or check_flag2 == True or check_flag3 == True) and (check_flag1 == False or check_flag2 == False or check_flag3 == False):
		raise UserError("Please Fill all the fields for Sign Quotations document Upload") 

	if check_flag1== True and check_flag2== True and check_flag3 == True:
            obj.signed_quote_name = self.signed_quote_name
            obj.signed_quote_number = self.signed_quote_number
            obj.signed_quote_receipt_date = self.signed_quote_receipt_date
            obj.signed_quote_receipt_doc = self.signed_quote_receipt_doc
            obj.signed_quote = True
            flag = 1

        check_flag1=check_flag2=check_flag3=check_flag4=False
	if self.pop_receipt_name:
		check_flag1=True
	if self.pop_receipt_date:
		check_flag2=True
	if self.pop_uploaded_document:
		check_flag3=True
	if check_flag1== True and check_flag2== True and check_flag3 == True:
            obj.pop_receipt_name = self.pop_receipt_name
            obj.pop_receipt_date = self.pop_receipt_date
            obj.pop_uploaded_document = self.pop_uploaded_document
            obj.pop = True
            flag = 1

	if check_flag1== False and check_flag2== False and check_flag3 == False:
		obj.pop = False

	if (check_flag1 == True or check_flag2 == True or check_flag3 == True) and (check_flag1 == False or check_flag2 == False or check_flag3 == False):
		raise UserError("Please Fill all the fields for POP document Upload") 
 
	check_flag1=check_flag2=check_flag3=check_flag4=False
	if self.email_uploaded_name:
		check_flag1=True
	if self.email_confirmation_date:
		check_flag2=True
	if self.email_uploaded_document:
		check_flag3=True

        if check_flag1== True and check_flag2== True and check_flag3 == True:
            obj.email_uploaded_name = self.email_uploaded_name
            obj.email_confirmation_date = self.email_confirmation_date
            obj.email_uploaded_document = self.email_uploaded_document
            obj.email = True
            flag = 1

	if check_flag1== False and check_flag2== False and check_flag3 == False:
		obj.email = False

	if (check_flag1 == True or check_flag2 == True or check_flag3 == True) and (check_flag1 == False or check_flag2 == False or check_flag3 == False):
		raise UserError("Please Fill all the fields for Email Upload") 

        if flag == 0 :#and not self._context.get('from_awaiting'):
	    if obj.state not in ('awaiting','sale','done'):
	    	if not obj.sale_lop_documents:
            		raise UserError("Please Add one of the Document")
	for line in self.n_uploaded_documents:
		if not line.name:
			raise UserError("Please upload customer document") 
	for line2 in self.n_product_documents:
		if not line2.name:
			raise UserError("Please upload product document")
	for line3 in self.sale_lpo_documents:
		if not line3.name:
			raise UserError("Please upload LPO document")

	if self.lpo_number:
            #number=self.env['customer.upload.doc'].search([('lpo_number', '=',self.lpo_number),('lpo_receipt_date','=',self.lpo_receipt_date),('lpo_issue_date','=',self.lpo_issue_date),('sale_id_lpo','=',obj.id)])
            number=self.env['customer.upload.doc'].search([('lpo_number', '=',self.lpo_number)])
            if number:
               raise UserError(_("This LPO Number %s Already exist in Sale Order -: %s for %s." )%(number.lpo_number,number.sale_id_lpo.name, number.sale_id_lpo.partner_id.name))
               '''number.write({'n_upload_doc':self.lpo_document,
				'name': self.lpo_name,
                                'lpo_number': self.lpo_number,
				'lpo_receipt_date': self.lpo_receipt_date,
				'lpo_issue_date': self.lpo_issue_date})'''
               
            else:
               self.write({'sale_lpo_documents': [(0, 0, {
				'sale_id_lpo':obj.id,
				'n_upload_doc':self.lpo_document,
				'name': self.lpo_name,
                                'lpo_number': self.lpo_number,
				'lpo_receipt_date': self.lpo_receipt_date,
				'lpo_issue_date': self.lpo_issue_date,
				'lpo ': True})]})
               rec_ids=self.env['customer.upload.doc'].search([('lpo_number','=',self.lpo_number)])
               if rec_ids:   
                  for n_rec in obj.order_line:
                      n_rec.lpo_documents=rec_ids.ids        				
	if obj.state=='sent':
		for n_rec in obj.order_line:
			# to update product id in product document on confirm sale
			rec_ids=self.env['customer.upload.doc'].search([('sale_line','=',n_rec.id)])
			rec_ids.write({'product_id':n_rec.product_id.id})
		if not self._context.get('from_awaiting'):
		    res = obj.action_confirm_by_sale_person()
		    if self._context.get('contract'):
			sale_form = self.env.ref('sale.view_order_form', False)
		    	if sale_form:
		           return {
				   'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'sale.order',
				    'views': [(sale_form.id, 'form')],
				   'view_id': sale_form.id,
				   'res_id':obj.id,
				   'target': 'new',
			    	}
		    return res
	return True
   	
    @api.multi
    def write(self,vals):
    	body=''
    	attachment=[]
    	for rec in self:
    	    if vals.get('lpo_number') or vals.get('lpo_receipt_date') or vals.get('lpo_issue_date') or vals.get('lpo_name'):
    	    	body+="<li>PO Details</li>"
    		if vals.get('lpo_number'):
    			if rec.lpo_number:
				body+="<ul><li>Number :"+str(rec.lpo_number)+" changed to "+str(vals.get('lpo_number'))+"</li></ul>"
			else:
				body+="<ul><li>Number :"+str(vals.get('lpo_number'))+"</li></ul>"
				
		if vals.get('lpo_receipt_date'):
    			if rec.lpo_receipt_date:
				body+="<ul><li>Receipt Date :"+str(rec.lpo_receipt_date)+" changed to "+str(vals.get('lpo_receipt_date'))+"</li></ul>"
			else:
				body+="<ul><li>Receipt Date :"+str(vals.get('lpo_receipt_date'))+"</li></ul>"
				
		if vals.get('lpo_issue_date'):
    			if rec.lpo_issue_date:
				body+="<ul><li>Issue Date :"+str(rec.lpo_issue_date)+" changed to "+str(vals.get('lpo_issue_date'))+"</li></ul>"
			else:
				body+="<ul><li>Issue Date :"+str(vals.get('lpo_issue_date'))+"</li></ul>"
				
		if vals.get('lpo_name'):
    			if rec.lpo_name:
				body+="<ul><li>Document :"+str(rec.lpo_name)+" changed to "+str(vals.get('lpo_name'))+"</li></ul>"
			else:
				body+="<ul><li>Document :"+str(vals.get('lpo_name'))+"</li></ul>"
			attachment.append((vals.get('lpo_name'),vals.get('lpo_document')))
			
	###QUOTATION				
    	    if vals.get('signed_quote_number') or vals.get('signed_quote_receipt_date') or vals.get('signed_quote_name'):
    	     	body+="<li>Quotation Details</li>"
		if vals.get('signed_quote_number'):
    			if rec.signed_quote_number:
				body+="<li>Number :"+str(rec.signed_quote_number)+" changed to "+str(vals.get('signed_quote_number'))+"</li>"
			else:
				body+="<li>Number :"+str(vals.get('signed_quote_number'))+"</li>"
			
		if vals.get('signed_quote_receipt_date'):
    			if rec.signed_quote_receipt_date:
				body+="<ul><li>Date :"+str(rec.signed_quote_receipt_date)+" changed to "+str(vals.get('signed_quote_receipt_date'))+"</li></ul>"
			else:
				body+="<ul><li>Date :"+str(vals.get('signed_quote_receipt_date'))+"</li></ul>"
		if vals.get('signed_quote_name'):
    			if rec.signed_quote_name:
				body+="<ul><li>Document :"+str(rec.signed_quote_name)+" changed to "+str(vals.get('signed_quote_name'))+"</li></ul>"
			else:
				body+="<ul><li>Document :"+str(vals.get('signed_quote_name'))+"</li></ul>"
			attachment.append((vals.get('signed_quote_name'),vals.get('signed_quote_receipt_doc')))
			
	### EMAIL
    	    if vals.get('email_confirmation_date') or vals.get('email_uploaded_name'):
    	     	body+="<li>Email Details</li>"
		if vals.get('email_confirmation_date'):
    			if rec.email_confirmation_date:
				body+="<li>Date :"+str(rec.email_confirmation_date)+" changed to "+str(vals.get('email_confirmation_date'))+"</li>"
			else:
				body+="<li>Date:"+str(vals.get('email_confirmation_date'))+"</li>"
		if vals.get('email_uploaded_name'):
    			if rec.email_uploaded_name:
				body+="<ul><li>Document :"+str(rec.email_uploaded_name)+" changed to "+str(vals.get('email_uploaded_name'))+"</li></ul>"
			else:
				body+="<ul><li>Document :"+str(vals.get('email_uploaded_name'))+"</li></ul>"
			attachment.append((vals.get('email_uploaded_name'),vals.get('email_uploaded_document')))
						
	###POP
    	    if vals.get('pop_receipt_date') or vals.get('pop_receipt_name'):
    	     	body+="<li>POP Details</li>"

		if vals.get('pop_receipt_date'):
    			if rec.pop_receipt_date:
				body+="<li>POP Date::"+str(rec.pop_receipt_date)+" changed to "+str(vals.get('pop_receipt_date'))+"</li>"
			else:
				body+="<li>POP Date:"+str(vals.get('pop_receipt_date'))+"</li>"
		if vals.get('pop_receipt_name'):
    			if rec.pop_receipt_name:
				body+="<ul><li>Document :"+str(rec.pop_receipt_name)+" changed to "+str(vals.get('pop_receipt_name'))+"</li></ul>"
			else:
				body+="<ul><li>Document :"+str(vals.get('pop_receipt_name'))+"</li></ul>"
			attachment.append((vals.get('pop_receipt_name'),vals.get('pop_uploaded_document')))
			
    	    if body:				
    	    	rec.n_sale_order.message_post(body,attachments=attachment)
    	return super(OrderConfirmWizard,self).write(vals)
    	
    state_bool = fields.Boolean()  
    lpo = fields.Boolean(string="PO",)
    lpo_name = fields.Char(string='PO Name')
    lpo_number = fields.Char(string='PO Number')
    lpo_receipt_date = fields.Date(string='PO Receipt Date')
    lpo_issue_date = fields.Date(string='PO Issued Date')
    lpo_document = fields.Binary(string='PO uploaded Document', default=False , attachment=True) #CH_N036 make field to store file in filesystem
    
    signed_quote = fields.Boolean(string="Signed Quote")
    signed_quote_name = fields.Char(string='Signed Quotation Name')
    signed_quote_number = fields.Char(string='Signed Quotation Number')
    signed_quote_receipt_date = fields.Date(string='Signed Quotation Receipt Date')
    signed_quote_receipt_doc = fields.Binary(string='Signed Quotation uploaded Document', default=False ,attachment=True) #CH_N036 make field to store file in filesystem
    
    pop = fields.Boolean(string="POP")
    pop_receipt_name = fields.Char(string='POP uploaded Name')
    pop_receipt_date = fields.Date(string="POP Receipt Date")
    pop_uploaded_document = fields.Binary(string='POP uploaded Document', default=False, attachment=True) #CH_N036 make field to store file in filesystem
    
    email = fields.Boolean(string="Email")
    email_uploaded_name = fields.Char(string='Email Uploaded Name')
    email_confirmation_date = fields.Date(string="Email Confirmation Date")
    email_uploaded_document = fields.Binary(string='Email Uploaded Document', default=False , attachment=True) #CH_N036 make field to store file in filesystem
    
#    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', default=get_payment_term)
#    match_payment_term = fields.Boolean(string='Payment Term match', default=False)
    add_documents = fields.Boolean(string="Add Documents")
    
#CH_N038 add fields to add Documents >>>
    #n_uploaded_document = fields.Many2many('ir.attachment','customer_attachment_rel','n_customer_doc','id','Customer Document')    
    #n_product_document = fields.Many2many('ir.attachment','product_attachment_rel','n_product_doc','id','Product Document')
    n_uploaded_documents = fields.One2many('customer.upload.doc','sale_wizard_customer','Customer Document')    
    n_product_documents = fields.One2many('customer.upload.doc','sale_wizard_product','Product Document')
    sale_lpo_documents = fields.One2many('customer.upload.doc','sale_wizard_sale','LPO Document') 
    n_sale_order = fields.Many2one('sale.order','Sale Order')	#CH_N046
    contract_id=fields.Many2one('customer.contract')

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    @api.multi
    def _create_invoice(self, order, so_line, amount):
	#update code for sale reception manual invoice
	if order and order.is_reception:
		return super(SaleAdvancePaymentInv,self)._create_invoice(order, so_line, amount)

	order.due_payment='pending'			#CH_N030 to set confirm button visibilty for advance payment
        inv_obj = self.env['account.invoice']
        inv_payment = self.env['account.payment']
        ir_property_obj = self.env['ir.property']
        '''account_id = False
        if self.product_id.id:
            account_id = self.product_id.property_account_income_id.id
        if not account_id:
            prop = ir_property_obj.get('property_account_income_categ_id', 'product.category')
            prop_id = prop and prop.id or False
            account_id = order.fiscal_position_id.map_account(prop_id)
        if not account_id:
            raise UserError(
                _('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
                    (self.product_id.name,))'''
       
        if self.amount <= 0.00:
            raise UserError(_('The value of the down payment amount must be positive.'))
        if self.advance_payment_method == 'percentage':
            amount =order.converted_amount_total * self.amount / 100   #Change default field to new field CH_N044
            name = _("Advance payment of %s(%s),%s%%") % (order.name,order.converted_amount_total, self.amount)
        else:
            amount = self.amount
            name = _('Advance Payment')
	#lpo_id=self.env['customer.upload.doc'].search([('lpo_number','=',order.lpo_number),('sale_id_lpo','=',order.id)],limit=1)
        #lst=[]	
        print"aaaaaaaaaaa",amount
        journal=self.env['account.journal'].search([('name','=','Cash')],limit=1)
        method=self.env['account.payment.method'].search([('code','=','manual')], limit=1)
        payment=inv_payment.create({'payment_type':'inbound',
                            'partner_type':'customer',
                            'partner_id':order.partner_id.id,
                            'communication':name,
                            'journal_id':journal.id,
                            'currency_id':order.report_currency_id.id,
                            'payment_method_id':method.id,
                            'amount':amount,
                            'sale_currency_id':order.report_currency_id.id,
                            'sale_amount':amount,
                            'sale_id':order.id,
                            'internal_note':name,
                            'payment_from':'advance'})

        order.payment_id=payment.id
        order.advance_paid_amount="Advance Payment  "+ str(amount) + str(order.report_currency_id.name) +" is not received in Accounts."
        print"____________-",payment
        #if self.amount == 100.0:
           #print"TTTTTTTTTTTTTTTTTTTTT",amount, order.amount_tax
          # amount=sum(line.price_subtotal for line in order.order_line)
       
        '''for ln in order.order_line:
            if ln.product_id.name != 'Deposit Product':
		    lst.append((0, 0, {
			'name': ln.product_id.name,
			'origin': order.name,
			'account_id': account_id,
			'price_unit':ln.price_unit ,
			'quantity': ln.product_uom_qty,
			'discount': 0.0,
			'uom_id': ln.product_uom.id,
			'product_id': ln.product_id.id,
			'sale_line_ids': [(6, 0, [so_line.id])],
			'invoice_line_tax_ids': [(6, 0, [x.id for x in  ln.tax_id])],
			'account_analytic_id': order.project_id.id or False,
			    }))'''
       #tax= [(6, 0, [x.id for x in  order.order_line[0].tax_id])] if order.order_line[0].tax_id else False
        '''invoice = inv_obj.create({
            
	    'name': order.client_order_ref or order.name,
	    'origin': order.name,
	    'type': 'out_invoice',
	    'reference': False,
            'advance_invoice':True,
	    'account_id': order.partner_id.property_account_receivable_id.id,
	    'partner_id': order.partner_invoice_id.id,
            'invoice_due_date':date.today(),
            'payable_amount':amount,
            'payable_discount':name,
            'order_line':lst,
	    'invoice_line_ids': [(0, 0, {
		'name': name,
		'origin': order.name,
		'account_id': account_id,
		'price_unit': amount,
		'quantity': 1.0,
		'discount': 0.0,
		'uom_id': self.product_id.uom_id.id,
		'product_id': self.product_id.id,
		'sale_line_ids': [(6, 0, [so_line.id])],
		'invoice_line_tax_ids': tax,
		'account_analytic_id': order.project_id.id or False,
		    })],
            'currency_id': order.n_quotation_currency_id.id,
            'payment_term_id': order.payment_term_id.id,
            'fiscal_position_id': order.fiscal_position_id.id or order.partner_id.property_account_position_id.id,
            'team_id': order.team_id.id,
	    'user_id':order.user_id.id,
	    'document_id':order.sale_lop_documents[0].id if order.sale_lop_documents else False,
	    'n_lpo_receipt_date':order.lpo_receipt_date,
            'n_lpo_issue_date':order.lpo_issue_date,
	    'n_lpo_name':order.lpo_name,
	    'n_lpo_document':order.lpo_document,
	    'state':'draft',
            'sale_id':order.id,
	    'document_id':lpo_id.id if lpo_id else False,
	    })'''
        '''if order.payment_term_id.advance_per == 100:
           for line in order.order_line:
               line.write({'qty_invoiced':line.product_uom_qty})'''
        #invoice.compute_taxes()
        return True

    @api.multi
    def create_invoices(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
	if sale_orders and sale_orders.is_reception:
		return super(SaleAdvancePaymentInv,self).create_invoices()
        if self.advance_payment_method == 'delivered': 
            pass
            #sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
           pass
           # sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            #if not self.product_id:
                #vals = self._prepare_deposit_product()
                #self.product_id = self.env['product.product'].create(vals)
                #self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting', self.product_id.id)
            pass
            sale_line_obj = self.env['sale.order.line']
            print"TTTTTTTTTTTTT",sale_orders.order_line
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_total * self.amount / 100
                else:
                    amount = self.amount
                #if self.product_id.invoice_policy != 'order':
                   # raise UserError(_('The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'))
                #if self.product_id.type != 'service':
                  #  raise UserError(_("The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."))
                '''so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, self.product_id.taxes_id.ids)],
                })'''
                self._create_invoice(order,  sale_line_obj, amount)
        #if self._context.get('open_invoices', False):
           # return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}

#CH_N064 add class for store upload documents from sales order
class customerUploadDoc(models.Model):
	_name = 'customer.upload.doc'
        _rec_name = "lpo_number"

	@api.model
	def create(self,vals):
		if vals.get('sale_wizard_customer'):
			order_id=self.env['order.confirm.wizard'].search([('id','=',vals.get('sale_wizard_customer'))])
			if order_id:
				vals.update({'customer_id':order_id.n_sale_order.partner_id.id,'sale_id':order_id.n_sale_order.id})
			
		if vals.get('sale_wizard_product'):
			order_id=self.env['order.confirm.wizard'].search([('id','=',vals.get('sale_wizard_product'))])
                        line=order_id.n_sale_order.order_line.search([('id','=',vals.get('sale_line'))])
			if order_id: 
				vals.update({'customer_id':order_id.n_sale_order.partner_id.id,
                                'sale_tmpl_id':line.product_id.product_tmpl_id.id,'sale_id_product':order_id.n_sale_order.id})
                if vals.get('sale_wizard_sale'):
			order_id=self.env['order.confirm.wizard'].search([('id','=',vals.get('sale_wizard_sale'))])
			if order_id:
				vals.update({'customer_id':order_id.n_sale_order.partner_id.id,'sale_id_lpo':order_id.n_sale_order.id})

		return super(customerUploadDoc,self).create(vals)
		
        @api.multi
        def delete_lpo(self):
            if self._context.get('sale_lpo'):
               self.unlink()
               return { 'type': 'ir.actions.client', 'tag': 'reload', }

	name = fields.Char(string='Document Name')
	state= fields.Selection([('draft','Draft'),('done','Done')],default='draft')
	#n_customer_doc = fields.Binary(string='Uploaded Document', default=False , attachment=True)
	n_upload_doc = fields.Binary(string='Uploaded Document', default=False , attachment=True)
	sale_wizard_customer = fields.Many2one('order.confirm.wizard', string='sale wizard',)
	sale_wizard_product = fields.Many2one('order.confirm.wizard', string='sale wizard',)
        sale_wizard_sale = fields.Many2one('order.confirm.wizard', string='sale wizard',)
	product_id = fields.Many2one('product.product', string='Product Name',)
        sale_tmpl_id=fields.Many2one('product.template')
        tmpl_id=fields.Many2one('product.template')
	product_tmpl_id = fields.Many2one('product.template', string='Product Name',related='product_id.product_tmpl_id')
	customer_id = fields.Many2one('res.partner', string='Customer')
	sale_id = fields.Many2one('sale.order', string='Sale Order') #customer_doc id
	sale_id_product = fields.Many2one('sale.order', string='Sale Order') #product_doc_id
	sale_id_lpo = fields.Many2one('sale.order', string='Sale Order') #LPO_doc_id
	request_term_id = fields.Many2one('request.payment.term.wizard', string='Request Term')
	payment_term_id = fields.Many2one('account.payment.term.request', string='Payment Term')
	
	sale_line = fields.Many2one('sale.order.line', string='Product Desc') #to get film and custom product
        lpo = fields.Boolean(string="LPO")
	lpo_number = fields.Char(string='LPO Number')
	lpo_receipt_date = fields.Date(string='LPO Receipt Date')
	lpo_issue_date = fields.Date(string='LPO Issued Date')

	@api.multi
	def name_get(self):
		res=super(customerUploadDoc,self).name_get()
		if self._context.get('doc_name'):
			ids_lst=[]
			for line in res:
				ids_lst.append(line[0])
			if ids_lst:
				res=[]
				for rec in self.search([('id','in',ids_lst)]):
					res.append((rec.id,str(rec.lpo_number)))
		return res

