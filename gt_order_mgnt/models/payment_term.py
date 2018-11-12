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
from openerp.tools.misc import formatLang
from urllib import urlencode
from urlparse import urljoin
from openerp.exceptions import UserError, ValidationError
import base64
from datetime import datetime, date, timedelta

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
     
    @api.model
    def create(self, vals):
        if self._context.get('request'):
            model=email_to=creat_by=name=''
            model_id=temp_id=0
            obj=False
            request = self.env['account.payment.term.request'].browse(self._context.get('request'))
            request.state = 'approved'
            request.name = vals.get('name')
            request.approve_date = datetime.now()
            request.accountant_id = self.env.uid
            if request.purchase_id:
		   model='purchase.order'
		   model_id=request.purchase_id.id
		   creat_by=request.purchase_id.create_uid.name
                   email_to=request.purchase_id.create_uid.login
                   name=request.purchase_id.name
		   temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_accepted_po')
            else:
		   model='sale.order'
		   model_id=request.quote_id.id
		   creat_by=request.quote_id.user_id.name
                   name=request.quote_id.name
		   temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_accepted')
            if request.quote_id:
              obj = request.quote_id
              email_to=obj.user_id.login
            if request.purchase_id:
               request.purchase_id.write({'payment_term_request':'approve'})
            #obj.write({'payment_term_requested' : True})
            #temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_accepted')
            if temp_id:
                user_obj = self.env['res.users'].browse(self.env.uid)
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                    'model': model,
                    'view_type': 'form',
                    'id': model_id,
                }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                text_link = _("""<a href="%s">%s</a> """) % (url,name)

                body_html = """<div>
        <p> <strong>Payment Term Accepted</strong></p><br/>
        <p>Dear %s,<br/>
            <b>%s </b>accepted Payment Term :  <b> %s </b>for <b>%s </b> <br/>
        </p>
        </div>"""%(creat_by or '', user_obj.name or '',  vals.get('name'), text_link)

                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, model,model_id, context=self._context)
                temp_id.write({'body_html': body_html, 'email_to' :email_to , 'email_from': user_obj.partner_id.email})
                temp_id.send_mail(model_id)
		n_vals={}
		
            res = super(AccountPaymentTerm, self).create(vals)
            if request.purchase_id:
               request.purchase_id.payment_term_id=res.id
            if obj:
		    if obj.state in ('draft','sent'):	#CH_N043  add condition to update when record is in quotation state
		    	n_vals.update({'payment_term_id' : res.id})
		    n_vals.update({'payment_term_requested':False,'visible_request_button':False})
		    obj.write(n_vals)
        else:
        	res = super(AccountPaymentTerm, self).create(vals)
        for rec in res.n_partner_id:
        	if res.name:
        		rec.message_post("<ul style='color:green'> Payment Term Added <li>"+str(res.name)+"</li></ul>")
        return res

    @api.multi
    def write(self,vals):
    	for rec in self:
    		body=''
    		if vals.get('n_partner_id'):
			new_term = []
			if type(vals.get('n_partner_id')[0]) ==list:
				new_term = vals.get('n_partner_id')[0][2]
			elif type(vals.get('n_partner_id')[0])==tuple:
				new_term.append(vals.get('n_partner_id')[0][1])
			exit_term = []
			for line in rec.n_partner_id:
				exit_term.append(line.id)
			n_ids=list(set(new_term).difference(exit_term))
			if n_ids:
				for line1 in n_ids:
					if rec.name:
					   self.env['res.partner'].browse(line1).message_post("<ul style='color:green'> Payment Term Added <li>"+str(rec.name)+"</li></ul>")
			ex_ids=list(set(exit_term).difference(new_term))
			if ex_ids:
				for line2 in ex_ids:
					if rec.name:
					   self.env['res.partner'].browse(line2).message_post("<ul style='color:green'> Payment Term Removed <li>"+str(rec.name)+"</li></ul>")
    	return super(AccountPaymentTerm, self).write(vals)
    
    @api.multi
    def unlink(self):# to check if payment term is not used in ERP before deleting
    	if self.id:
    		if self.env['account.invoice'].search([('payment_term_id','=',self.id),('state','!=','cancel'),('type','=','out_invoice')]):
    			raise UserError("Your Payment Term is used in Invoices, Please make proper changes in that Invoices")
		if self.env['account.invoice'].search([('payment_term_id','=',self.id),('state','!=','cancel'),('type','=','in_invoice')]):
    			raise UserError("Your Payment Term is used in Vendor Bills, Please make proper changes in that Bills")
		if self.env['account.invoice'].search([('payment_term_id','=',self.id),('state','!=','cancel'),('type','=','out_refund')]):
    			raise UserError("Your Payment Term is used in Refund-Invoices, Please make proper changes in that Refund-Invoice")
		if self.env['sale.order'].search([('payment_term_id','=',self.id),('state','!=','cancel')]):
    			raise UserError("Your Payment Term is used in Quotations/SaleOrder, Please make proper changes in that Quotations/SaleOrder")
		if self.env['purchase.order'].search([('payment_term_id','=',self.id),('state','!=','cancel')]):
    			raise UserError("Your Payment Term is used in Purchase Order, Please make proper changes in that Purchase Order")
    	return self(AccountPaymentTerm,self).unlink()
    	
    @api.multi
    def payment_term_create(self):#CH_N130 add for save from button
    	return True
    	
#CH_N064 >>>
    @api.onchange('advance_per')
    def get_remaining_amount(self):
	for rec in self:
		rec.on_delivery_per=str(100-rec.advance_per )
#CH_N064 <<<<<<     
    @api.multi
    def get_delivery_per(self):
        for rec in self:
            rec.on_delivery_per = 100 - rec.advance_per
             
    advance_per = fields.Float(string="Advance %", default=0.0)
    on_delivery_per = fields.Float(string="On Delivery %", compute=get_delivery_per, default=100)
    approved = fields.Boolean('Approved')
    time_limit_value = fields.Integer(string="Time Limit")
    time_limit_type = fields.Selection([
                                        ('day','Days'),
                                        ('week', 'weeks'),
                                        ('month', 'Months')], string="Time Limit")
    payment_term_depend = fields.Selection([
                                          ('delivery','Delivery'),
                                          ('credit', 'Credit')], string="Payment Term On")
    payment_due = fields.Selection([
                                          ('delvery','Delivery'),
                                          ('invoice', 'Invoice')], string="Payment Due")
    
    #CH_N040 add fields to store multiple customers.
    n_partner_id = fields.Many2many('res.partner','n_partner_payment_rel','partner_id','id','Customer')
    supplier_id = fields.Many2many('res.partner','supplier_partner_payment_rel','supplier_id','id','Supplier')

    n_new_request = fields.Boolean('New Term', help='If checked then it will open wizard on selection for new payment term in Sale order',default=False)  
    n_milestone_request = fields.Boolean('New Term', help='If checked then it will open wizard on selection for new payment term in Sale order',default=False)
    n_standard_term = fields.Boolean('Sale Standard Term', help='If checked then it will Standard payment term for all customres in Sale order',default=False)
    n_purchase_term = fields.Boolean('Purchase Standard Term', help='If checked then it will Standard payment term for all customres in Purchase order',default=False)
    #is_reception = fields.Boolean('Reception Term', help='If checked then it will be payment term for all customres in Mir-Int. Sale orders',default=False)
    company_ids=fields.Many2many('res.company','payment_term_multi_company_rel','term_id','company_id','Company')
    
    @api.one
    def compute(self, value, date_ref=False):
        for record in self:
		if value==1:
	       		date_ref = date_ref or fields.Date.today()
			if record.advance_per:
				return [[date_ref]]
			elif record.time_limit_type:	#record.payment_term_id.payment_term_depend == 'credit':
		              days = record.time_limit_value or 1 
		              if record.time_limit_type == 'week':
		                 days *= 7
		              elif record.time_limit_type == 'month':
		                 days *= 30
		              date_due=datetime.strptime(str(date_ref),'%Y-%m-%d')+timedelta(int(days))
		              return [[date_due]]
			else:
				return [[date_ref]]
		else:
			result = super(AccountPaymentTerm,self).compute(value,date_ref)
			return result[0]
		
#CH_N040 add name search for filter >>>>
    @api.model
    def name_search(self,name, args=[], operator='ilike',limit=100):
    	ids=[]
    	if self._context.get('sale') or self._context.get('is_contract'):
    		args=[]
                n_id1 = self.search([('n_standard_term','=',True)])
    		ids.extend([i.id for i in n_id1])
	if self._context.get('n_partner_id') and not self._context.get('sale_id'):
		n_id = self.search([('n_partner_id','=',self._context.get('n_partner_id'))])
		ids.extend([i.id for i in n_id])
	if self._context.get('n_partner_id') and self._context.get('sale_id'):
		n_id = self.env['sale.order'].search([('id','=',self._context.get('sale_id'))])
		ids.extend([i.payment_term_id.id for i in n_id])

	if self._context.get('vendor') and self._context.get('partner_id'):
		args=[]
		n_id = self.search(['|',('supplier_id','=',self._context.get('partner_id')),('n_purchase_term','=',True)])
		ids.extend([i.id for i in n_id])
        elif self._context.get('vendor'):
                n_id = self.search([('n_purchase_term','=',True)])
		ids.extend([i.id for i in n_id])
	if ids:
		args.append(('id','in',ids))
	if not args and 'sale_id' in self._context.keys():
		return []
	val=super(AccountPaymentTerm,self).name_search(name, args, operator=operator,limit=limit)
	if self._context.get('sale'):
		n_id = self.search([('n_new_request','=',True)])
		if n_id:
			val.insert(0,(n_id.id,n_id.name))
        if self._context.get('vendor'):
		n_ids = self.search(['|',('n_milestone_request','=',True),('n_new_request','=',True)])
		if n_ids:
                        for n_id in n_ids:
			    val.insert(0,(n_id.id,n_id.name))
	return  val
#CH_N040 end <<

class AccountPaymentTermRequest(models.Model):
    _name = "account.payment.term.request"
    
    @api.multi
    def open_order(self):
        sale_form = self.env.ref('sale.view_order_form', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'views': [(sale_form.id, 'form')],
            'view_id': sale_form.id,
            'res_id' : self.quote_id.id,
        }

    @api.multi
    def create_payment_term(self):
       return {
           'name': 'Payment Term',
           'view_type': 'form',
           'view_mode': 'form',
           'res_model': 'account.payment.term',
           'view_id': self.env.ref('gt_order_mgnt.partner_payment_terms_almir').id,
           'type': 'ir.actions.act_window',
           'context' : {'default_name': self[0].name, 'purchase':True,
           'default_n_partner_id': [[6,0,[self[0].quote_id.partner_id.id]]] if self.quote_id else [],
           'default_supplier_id': [[6,0,[self.customer_id.id]]] if self.purchase_id else [], 
           #'default_n_purchase_term':True if self.purchase_id else False,
           'request' : self.id,'default_advance_per':self.n_percenatge,'show_term_save':True},
	   'target':'new',
	   'flags': {'form': {'options': {'mode': 'edit'}}}
       }

##CH_N043 start code to marge customer in existing payment term
    @api.multi
    def merge_payment_term(self):
       return {
           'name': 'Payment Term',
           'view_type': 'form',
           'view_mode': 'form',
           'res_model': 'account.payment.term.request',
           'view_id': self.env.ref('gt_order_mgnt.account_payment_term_merge_view').id,
           'type': 'ir.actions.act_window',
	   'target':'new',
           'res_id' : self.id,
       }

    @api.multi
    def n_merge_customer(self):
	self.state = 'update'
	self.approve_date = datetime.now()
	self.accountant_id = self.env.uid
        if self.quote_id:
            self.quote_id.payment_term_requested=True
            self.quote_id.visible_request_button=False
            self.quote_id.payment_term_requested=False
            if self.quote_id.state in ('draft','sent'):  #CH_N043 add condition to update when record is in quotation state
        	self.quote_id.payment_term_id=self.n_payment_term.id
        elif self.purchase_id:
            self.purchase_id.payment_term_bool_moved0=True
            self.purchase_id.visible_request_button=False
            self.purchase_id.payment_term_requested=False
            if self.purchase_id.state in ('draft','sent'):  #CH_N043 add condition to update when record is in quotation state
        	self.purchase_id.payment_term_id=self.n_payment_term.id
	
        for rec in self:
	    ids=[rec.customer_id.id] if rec.customer_id else []
	    for res in rec.n_payment_term.n_partner_id:
		ids.append(res.id)
	    rec.n_payment_term.n_partner_id=[(6,0,ids)]
	temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_accepted')
        if temp_id:
            user_obj = self.env['res.users'].browse(self.env.uid)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            if self.quote_id:
                fragment = {
                    'model': 'sale.order',
                    'view_type': 'form',
                    'id': self.quote_id.id,
                }
            elif self.purchase_id:
                 fragment = {
                    'model': 'purchase.order',
                    'view_type': 'form',
                    'id': self.purchase_id.id,
                }
                
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            if self.quote_id:
                text_link = _("""<a href="%s">%s</a> """) % (url,self.quote_id.name)
                username=self.quote_id.user_id.name
                email=self.quote_id.user_id.email
                id=self.quote_id.id

            elif self.purchase_id:
                self.purchase_id.write({'payment_term_request':'approve'})
                text_link = _("""<a href="%s">%s</a> """) % (url,self.purchase_id.name)
                username=self.sales_person_id.name
                email=self.sales_person_id.email
                id=self.purchase_id.id
            body_html = """<div>
    <p> <strong>Payment Term Merge</strong></p><br/>
    <p>Dear %s,<br/>
        <b>%s </b>Payment Term :  <b> %s </b>for <b>%s </b> <br/>
    </p>
    </div>"""%(username or '', user_obj.name or '',  self.name, text_link)

            body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',self.quote_id.id, context=self._context)
            temp_id.write({'body_html': body_html, 'email_to' :email , 'email_from': user_obj.partner_id.email})
            temp_id.send_mail(id)
	return True
	
#CH_N043 <<<	

    @api.one
    def reject_payment_term(self):
        model=creat_by=name=''
        model_id=temp_id=0
        if self.purchase_id:
           model='purchase.order'
           model_id=self.purchase_id.id
           name=self.purchase_id.name
           creat_by=self.purchase_id.create_uid.name
           temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_rejected_po')
        else:
           model='sale.order'
           model_id=self.quote_id.id
           name=self.quote_id.name
           creat_by=self.quote_id.user_id.name
           temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_rejected')
        self.state = 'rejected'
        self.approve_date = datetime.now()
        self.accountant_id = self.env.uid
        if self.quote_id:
            self.quote_id.write({'payment_term_requested' : False,'visible_request_button':True})
        else:
            self.purchase_id.write({'payment_term_request' : 'reject'})
        if temp_id:
            user_obj = self.env['res.users'].browse(self.env.uid)
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
                'model': model,
                'view_type': 'form',
                'id': model_id,
            }
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,name)

            body_html = """<div>
    <p> <strong>Payment Term Rejected</strong></p><br/>
    <p>Dear %s,<br/>
        <b>%s </b>rejected Payment Term :  <b> %s </b>for <b>%s </b> <br/>
    </p>
    </div>"""%(creat_by or '', user_obj.name or '',  self.name, text_link)

            body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, model,model_id, context=self._context)
            temp_id.write({'body_html': body_html, 'email_to' : self.quote_id.user_id.email, 'email_from': user_obj.partner_id.email})
            temp_id.send_mail(model_id)
        return True

    @api.model
    def get_customer_credit(self):
	for rec in self:
	    if rec.state == 'requested':
		    if rec.customer_id:
			rec.credit_allowed=rec.customer_id.currency_id.compute(rec.customer_id.credit_limit,rec.currency_id)
    
    name = fields.Char(string='Name')
    quote_id = fields.Many2one('sale.order', string="Quotation")
    customer_id = fields.Many2one('res.partner', string='Customer')
    sales_person_id = fields.Many2one('res.users', string="Requested by")
    accountant_id = fields.Many2one('res.users', string="Accountant")
    state = fields.Selection([('requested', 'Requested'),('approved', 'Approved'), ('rejected','Rejected'),('update','Update')], string="State", default=False)
    approve_date = fields.Date(string='Approved Date')
    rejected_date = fields.Date(string='Rejected Date')
    requested_date = fields.Date(string='Requested Date')
    credit_profile_doc_name = fields.Char(string='Credit Profile Doc Name')  #CH_N036 make field to store file in filesystem
    credit_profile_doc = fields.One2many('customer.upload.doc','payment_term_id',string="Upload Credit Profile") #CH_N067
    n_payment_term = fields.Many2one('account.payment.term','Payment Terms')
    n_percenatge = fields.Float(string="Credit Percentage")
    n_sale_amount = fields.Float(string="Quotation Amount")
    credit_allowed=fields.Float('Credit Allowed',compute=get_customer_credit)
  # add fields #CH_N104 
    credit_required_amount = fields.Float(string="Credit Required")
    currency_id = fields.Many2one('res.currency','Currency')
    request_type = fields.Selection([('sale','Sale'),('purchase','Purchase')])
    purchase_id = fields.Many2one('purchase.order', string="Quotation")

    @api.multi
    def credit_increase_amount(self):
        for line in self:
            move_form = self.env.ref('gt_order_mgnt.customer_credit_form_ac', False)
            if move_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'views': [(move_form.id, 'form')],
                    'view_id': move_form.id,
                    'target': 'current',
                    'res_id':self.customer_id.id,
                }

        return True

class credit_profile_customer(models.Model):
    _name = "credit.profile.customer"
    
    name = fields.Char(string="Name")
    attchment_id = fields.Many2one("ir.attachment", string="Credit Profile Attachment")

class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

class accountPayment(models.Model):
    _name='account.payment'
    _inherit=['account.payment','mail.thread']

    sale_id = fields.Many2one('sale.order', 'Sale Order No.')
    sale_amount=fields.Float('Requested Amount', digits=(4,2))
    sale_currency_id=fields.Many2one('res.currency')
    internal_note=fields.Text('Remarks on Receipt',track_visibility='always')
    payment_from=fields.Selection([('manual','Manual'),('advance','Advance Sale Order'),('invoice','Invoice Payment'),('multi','Multi Payment')], default='manual', string='Payment From')

    @api.multi
    def print_advance_payment_receipt(self):
        if self.state =='posted':
            return self.env['report'].get_action(self.sale_id, 'gt_order_mgnt.report_payment_sale_report')
        return False

    @api.multi
    def print_payment_receipt(self):
        return self.env['report'].get_action(self.sale_id, 'gt_order_mgnt.report_payment_account')
        return False

    @api.multi
    def print_sale_order(self):
        if self.sale_id:
            return self.env['report'].get_action(self.sale_id, 'gt_sale_quotation.report_quotation_aalmir1')
        return False

    @api.multi
    def post(self):
        res=super(accountPayment,self).post()
        recipient_partners=[]
        template_ids=False
        if self.sale_id:
                amount=0.0
                if self.sale_currency_id.id != self.currency_id.id and self.sale_currency_id:
                   from_currency =self.currency_id 
                   to_currency = self.sale_currency_id
                   amount=from_currency.compute(self.amount,to_currency) 
                else:
                   amount=self.amount
                cheque_status=''
                if self.cheque_status:
                   cheque_status="Cheque Status: " + str(dict(self.fields_get(allfields=['cheque_status'])['cheque_status']['selection'])[self.cheque_status])
		if int(self.sale_amount) <= int(amount):
		   self.sale_id.due_payment='done'
		   self.sale_id.advance_paid_amount="Advance Amount Fully Paid  "+ str(self.amount)+ str(self.currency_id.symbol)+" of "+ str(self.sale_amount)+str(self.sale_currency_id.symbol)+'\n'+str(cheque_status)
		else:
		   self.sale_id.due_payment='half_payment'
		   self.sale_id.advance_paid_amount="Advance Amount Paid "+ str(self.amount)+ str(self.currency_id.symbol)+ " of "+ str(self.sale_amount)+str(self.sale_currency_id.symbol)+'\n'+str(cheque_status)
                recipient_partners.append(self.sale_id.user_id.login)
                group_search = self.env['res.groups'].search([('name', 'in',('Sales Support Email','Register Payment Email'))])
		for group in group_search:
                     for recipient in group.users:
			if recipient.login not in recipient_partners:
            			recipient_partners.append(str(recipient.login))
		body='<b>Advance Payment Details({}):</b>'.format(self.env.user.company_id.name)
		body +='<li> Customer  Name: '+str(self.partner_id.name) +'</li>'
                body +='<li> Payment Receipt No.: '+str(self.name) +'</li>'
                body +='<li> Sale Order No: '+str(self.sale_id.name) +'</li>' 
                body +='<li> Sale order Amount: '+str(self.sale_id.converted_amount_total) + str(self.sale_currency_id.symbol)+'</li>'
                body +='<li> Payment Method: '+str(self.journal_id.name) +'</li>'
                if self.payment_method:
                   body +='<li> Received Type: '+str(dict(self.fields_get(allfields=['payment_method'])['payment_method']['selection'])[self.payment_method]) +'</li>' 
                if self.cheque_status:
                   body +='<li> Cheque Status: '+str(dict(self.fields_get(allfields=['cheque_status'])['cheque_status']['selection'])[self.cheque_status])+'</li>'
		body +='<li> Due Amount: '+str(self.sale_amount) + str(self.sale_currency_id.symbol)+'</li>'
                
		body +='<li> Received Amount: '+str(self.amount) + str(self.currency_id.symbol)+'</li>'
                body +='<li> Payment Date: '+str(self.payment_date)+'</li>'
		body +='<li> Registered On: '+str(date.today())+'</li>'
                template_ids = self.env.ref('gt_order_mgnt.email_template_for_advance_payment_paid')
                template_ids.write({'body_html':body})
                values = template_ids.generate_email(self.sale_id.id)
        else:
            if not self.expense_id:
                    bill,internal=False,False
                    if self.partner_type=='supplier':
                            bill = True
                    elif self.partner_type == False:
                            internal =True

                    subject='API-ERP Invoice Payment Alert:'
                    group = self.env['res.groups'].sudo().search([('name', '=', 'Register Payment Email')])
                    if bill:
                            subject='API-ERP Bill Payment Alert:'
                            group = self.env['res.groups'].sudo().search([('name', '=', 'Bill Payment Email')])
                    if internal:
                            subject='API-ERP Internal Payment Alert:'
                    for recipient in group.users:
                        if self.env.user.company_id.id in recipient.company_ids._ids:
                            if recipient.login not in recipient_partners:
                                    recipient_partners.append(str(recipient.login))

                    body = '<b><h3>{}</h3> '.format(self.env.user.company_id.name)
                    body +='Payment Received : </b>' if self.partner_type =='customer' else '<b>Payment Paid :</b>'
                    if self.partner_id:
                            body +='<li> Customer  Name: ' +(self.partner_id.name) +'</li>'  if self.partner_type =='customer' else '<li> Vendor  Name: ' +(self.partner_id.name) +'</li>'
                    if bill or internal:
                            body +='<li> Payment Voucher No.: '+str(self.name) +'</li>'
                    else:
                            body +='<li> Payment Receipt No.: '+str(self.name) +'</li>'
                    body +='<li> Payment Method: '+str(self.journal_id.name) +'</li>'
                    if self.payment_method:
                       body +='<li> Received Type: '+str(dict(self.fields_get(allfields=['payment_method'])['payment_method']['selection'])[self.payment_method]) +'</li>'  if self.partner_type =='customer' else '<li> Paid Type: '+str(dict(self.fields_get(allfields=['payment_method'])['payment_method']['selection'])[self.payment_method]) +'</li>'
                    if self.cheque_status:
                       body +='<li> Cheque Status: '+str(dict(self.fields_get(allfields=['cheque_status'])['cheque_status']['selection'])[self.cheque_status])+'</li>'

                    body +='<li> Received Amount: '+str(self.amount) + str(self.currency_id.symbol)+'</li>' if self.partner_type =='customer' else '<li> Paid Amount: '+str(self.amount) + str(self.currency_id.symbol)+'</li>'
                    body +='<li> Payment Date: '+str(self.payment_date)+'</li>'
                    body +='<li> Registered On: '+str(date.today())+'</li>'
                    type_p=''

                    if self.communication:
                       body +='<li> Remarks: '+  str(self.communication)+'</li>'
                       if self.partner_type =='customer':
                          type_p='  Payment Received for Invoice of  '
                          body +='<br></br>' 
                          if self.invoice_ids:

                             body +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial; text-align:center;'><tr><th>Invoice Number </th><th> Sale order</th><th>Total Amount</th><th>Due Amount </th><th>Status</th></tr>"

                       if self.partner_type =='supplier':  
                          type_p='  Bill Paid for   ' 
                          if self.invoice_ids: 
                             body +="<table class='table table-bordered' style='border: 1px solid #9999;width:80%; height: 50%;font-family:arial; text-align:center;'><tr><th>Bill Number </th><th> Purchase order</th><th>Total Amount</th><th>Due Amount </th><th>Status </th></tr>"

                    if self.invoice_ids:
                       for invoice in self.invoice_ids: 
                           if invoice.sale_id:
                                    recipient_partners.append(str(invoice.sale_id.user_id.login))
                           body +="<tr><td>%s</td><td>%s</td><td>%s %s</td><td>%s %s </td><td>%s</td></tr>"%(invoice.number, invoice.origin ,invoice.amount_total, invoice.currency_id.symbol, invoice.residual, invoice.currency_id.symbol, invoice.state) 
                           invoice.message_post(body=body)

                       if self.payment_from != 'multi':
                          self.payment_from='invoice' 
                       subject +=str(self.amount)+ str(self.currency_id.symbol) + str(type_p)+ str(self.partner_id.name)
                    if not self.invoice_ids:
                       subject +=str(self.amount)+ str(self.currency_id.symbol) + str(type_p)+' against for '  +  str(self.partner_id.name)
                    template_ids = self.env.ref('gt_order_mgnt.email_template_for_register_payment_received1')
                    template_ids.write({'body_html':body, 'lang':self.partner_id.lang,'subject':subject})
                    values = template_ids.generate_email(self.id)
            print "llllllllllllllllllllllllllllll",recipient_partners
        if template_ids and recipient_partners:
	   if self.env.user.login in recipient_partners:
		recipient_partners.remove(self.env.user.login)
	   values['email_to'] = ",".join(set(recipient_partners))
	   mail_mail_obj = self.env['mail.mail']
	   msg_id = mail_mail_obj.create(values) 
	   Attachment = self.env['ir.attachment']
	   attachment_ids = values.pop('attachment_ids', [])
	   attachments = values.pop('attachments', []) 
           attachment=[]

           if self.uploaded_document:
               attachments.append((self.doc_name,self.uploaded_document))
           if self.invoice_ids:
                  report_obj = self.pool.get('report')
                  
                  for inv in self.invoice_ids:
                      data=report_obj.get_pdf(self._cr, self._uid, inv.ids,
                              'gt_order_mgnt.report_invoice_aalmir',  context=self._context)
                      val  = base64.encodestring(data)
                      rep_name='Invoice:'+str(inv.number)+'.pdf'
                      attachments.append((rep_name,val))
                      data1=report_obj.get_pdf(self._cr, self._uid, inv.ids,
                              'stock_merge_picking.report_payment',  context=self._context)
                      val1  = base64.encodestring(data1)
		      rep_name1=''
		      if inv.type in ('out_invoice','out_refund'):
                      	rep_name1='Payment-Receipt:'+str(inv.number)+'.pdf'
		      else:
			rep_name1='Payment-Voucher:'+str(inv.number)+'.pdf'
                      attachments.append((rep_name1,val1))
                      
	   attachment_data={} 
           if attachments:
		   for attachment in attachments: 
		       attachment_data = {
				        'name': attachment[0],
				        'datas_fname': attachment[0],
				        'datas': attachment[1],
				        'res_model': 'mail.message',
				        'res_id': msg_id.mail_message_id.id,
                                        'type':'binary',
				        
				          }
		       attachment_ids.append(Attachment.create(attachment_data).id)
		   if attachment_ids:
		      values['attachment_ids'] =[(4, attachment_ids)]# [(6, 0, attachment_ids)]
		      msg_id.write({'attachment_ids':[(4, attachment_ids)]}) #[(6, 0, attachment_ids)],
				            
	   msg_id.send()
           if self.cheque_status == 'cleared':
              for line in self.cheque_details:
              	  if not line.reconcile_date:
	                  line.reconcile_date = date.today()
    		          line.user_id = self.env.user.id
	          elif line.reconcile_date and self.payment_date and line.reconcile_date < self.payment_date:
	          	raise UserError("Please Enter Reconcile date less than payment date")
           else:
           	 for line in self.cheque_details:
              	 	line.reconcile_date=False
           msg_id.res_id=self.id
        return res
    
