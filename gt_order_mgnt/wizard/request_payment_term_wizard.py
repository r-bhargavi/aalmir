# -*- coding: utf-8 -*-
from openerp import api, fields, models, _, modules
from openerp.exceptions import UserError, ValidationError
from datetime import datetime,date
from urlparse import urljoin
from urllib import urlencode

class RequestPaymentTermWizard(models.Model):
    _name = 'request.payment.term.wizard'

    @api.multi
    def send_credit_profile(self):
        sobj = self.env['sale.order'].browse(self._context.get('active_id')) 
        obj_1 = self.env['credit.profile.customer']
        o_ids = obj_1.search([('name','=', 'Credit_profile')])
        if not o_ids:
            data = obj_1.create({'name' : 'Credit_profile'})
        else:
            data = o_ids[0]
        attach_pool = self.env["ir.attachment"]
        attach_ids = attach_pool.search([('res_model', '=', 'credit.profile.customer'), ('name', '=', 'Credit_profile'), ('res_id', '=', data.id)])
        if attach_ids:
            attachment = attach_ids[0]
        else:
            pdf = modules.get_module_path('gt_order_mgnt') + "/credit_profile_pdf/credit_profile_pdf.pdf"
            f = open(pdf, 'rb')
            image_base64 = f.read()
            attachment = attach_pool.create({
                'res_model' : 'credit.profile.customer',
                'name' : 'Credit_profile',
                'filename' : 'credit_profile.pdf',
                'res_id' : data.id,
                'datas' : image_base64
            })
        ir_model_data = self.env['ir.model.data']
	template_id = False
        try:
            template_id = ir_model_data.get_object_reference('gt_aalmir_coldcalling', 'email_send_comment')[1]
        except ValueError:
            template_id = False
        compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': sobj.id,
            'default_auto_delete':False,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            #'default_partner_ids': [(6, 0, sobj.partner_id.id)],
            'default_subject': ' ',
            'default_attachment_ids' : [(6,0, [attachment.id])]
        })
 
        res = {
            'name' : 'Mail',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
        return res
    
    @api.model
    def get_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/credit_profile_form/'
        return url
    
    @api.model
    def get_payment_term(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id')) if not self._context.get('from_purchase') else self.env['purchase.order'].browse(self._context.get('active_id'))
            return obj.payment_term_id and obj.payment_term_id.id or False
        return False
    
    @api.model
    def get_customer(self):
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id')) if not self._context.get('from_purchase') else self.env['purchase.order'].browse(self._context.get('active_id'))
            return obj.partner_id and obj.partner_id.id or False
        return False
    
    @api.model
    def get_customer_credit(self):
	amount=0.0
        if self._context.get('active_id'):
            obj = self.env['sale.order'].browse(self._context.get('active_id')) if not self._context.get('from_purchase') else self.env['purchase.order'].browse(self._context.get('active_id'))
            if obj.partner_id:
		amount=obj.partner_id.currency_id.compute(obj.partner_id.credit_limit,obj.currency_id)
        return amount
    
    @api.onchange('order_total')
    def get_remaining_amount(self):
	if self._context.get('active_id'):
                if self._context.get('from_purchase'):
                   obj = self.env['purchase.order'].browse(self._context.get('active_id')) 
                   for rec in self:
			if rec.order_total > 100 :
			   rec.order_total=00.0
			   raise UserError('Please Enter proper value for advance in percentage')
			rec.n_remaining_amount=str((100-rec.order_total ))+"%("+str((obj.amount_total/100)*(100-rec.order_total))+")"+str(obj.currency_id.name)
                else:
			obj = self.env['sale.order'].browse(self._context.get('active_id')) 
			for rec in self:
				if rec.order_total > 100 :
					rec.order_total=00.0
					raise UserError('Please Enter proper value for advance in percentage')
				rec.n_remaining_amount=str((100-rec.order_total ))+"%("+str((obj.converted_amount_total/100)*(100-rec.order_total))+")"+str(obj.report_currency_id.name)
		return False
    
    @api.multi
    def _get_other_pending(self):
	obj = self.env['sale.order'].browse(self._context.get('active_id')) if not self._context.get('from_purchase') else self.env['purchase.order'].browse(self._context.get('active_id'))
	previous_pending=0.0 
	invoice=self.env['account.invoice'].search([('partner_id', '=',obj.partner_id.id),('state','not in',('paid','cancel'))])
	for line in invoice :
                print"=============",line, line.amount_total
		amount=0.0
		if line.residual: 
			 amount= line.residual
		else:
			amount = line.amount_total
		previous_pending += line.currency_id.compute(amount,obj.report_currency_id) if not self._context.get('from_purchase') else line.currency_id.compute(amount,obj.currency_id)
	return previous_pending

    @api.multi
    def _get_currency(self):
        if not self._context.get('from_purchase'):
		obj = self.env['sale.order'].browse(self._context.get('active_id')) 	
		if obj :
		     if obj.report_currency_id:
			return obj.report_currency_id.id
		else:
			return self.env.user.company_id.currency_id
        else:
                obj = self.env['purchase.order'].browse(self._context.get('active_id')) 
                return obj.currency_id.id 

    @api.model
    def get_match(self):
        if self._context.get('active_id') and not self._context.get('from_purchase'):
            obj = self.env['sale.order'].browse(self._context.get('active_id'))
            if obj.partner_id.credit_limit < (obj.converted_amount_total+self.previous_pending):
                return True
        return False

    name = fields.Char(string="Request Payment Term Name")
    upload_credit_profile_name = fields.Char(string="Upload Credit Profile name")
    #CH_N066 
    #upload_credit_profile = fields.Binary(string="Upload Credit Profile")  #CH_N036 make field to store file in filesystem
    upload_credit_profile = fields.One2many('customer.upload.doc','request_term_id',string="Upload Credit Profile")  #CH_N067 
    download_credit_profile = fields.Char('Downoad Credit Profile Form', default=get_url, readonly="1")
    
    payment_term_id = fields.Many2one('account.payment.term', string='Current Payment Term', default=get_payment_term)
    customer_id = fields.Many2one('res.partner', string='Customer', default=get_customer)
    customer_credit = fields.Float(string='Credit Limit', default=get_customer_credit)
    order_total = fields.Float(string="Credit Amount")
    n_remaining_amount = fields.Char('Remaining Amount', readonly="1")
    not_match = fields.Boolean(string="Not Matched", default=get_match)
    previous_pending = fields.Float(string="Other Pending",default=_get_other_pending)
    currency_id = fields.Many2one('res.currency', 'Currency',default=_get_currency)

    @api.one
    def do_request(self):
        for rec in self.upload_credit_profile:
	    if not rec.name:
            	raise UserError("Please Upload Credit Profile and name") 

        if self.order_total > 100 :
		raise UserError('Please Enter proper value for advance in percentage')
	obj = self.env['sale.order'].browse(self._context.get('active_id'))
	ids_list=[]
	required_credit=((obj.converted_amount_total*self.order_total)/(100))
        n_id=self.env['account.payment.term.request'].create({
							'name' : self[0].name,
							'quote_id' : obj.id,
                                                        'customer_id':self.customer_id.id,
							'sales_person_id' : self.env.user.id,
							'state' : 'requested',
							'requested_date' : date.today(),
							'n_percenatge':self.order_total,
							'n_sale_amount':obj.converted_amount_total,
							'currency_id':self.currency_id.id,
							'credit_required_amount':required_credit,})
	#CH_N067 >>
	for rec in self.upload_credit_profile:
		rec.write({'sale_id':obj.id,'payment_term_id':n_id.id,'customer_id':self.customer_id.id})
	#CH_N067 <<<
        obj.payment_term_requested = True
        temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_req')
        if temp_id:
            email_to = obj.team_id.user_id.email
            group_id = self.env.ref('account.group_account_manager', False)
            if group_id:
                user_ids = self.env['res.users'].sudo().search([('groups_id', 'in',group_id._ids)])
                if user_ids:
                    email_to = ''.join([user.email + ',' for user in user_ids])
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
                'model': 'sale.order',
                'view_type': 'form',
                'id': obj.id,
            }
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,obj.name)
            body_html = """<div>
             
    <p> <strong>New Payment Term Requested </strong></p><br/>
    <p>Dear Accountant,<br/>
        <b>%s </b>requested for New Payment Term :  <b> %s </b>for <b>%s </b> <br/>
    </p>
    </div>"""%(obj.user_id.name or '', self[0].name, text_link)

            body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',obj.id, context=self._context)
            temp_id.write({'body_html': body_html, 'email_to' : email_to, 'email_from' : obj.user_id.name})
            temp_id.send_mail(obj.id)
        return True
    
    @api.multi
    def do_request_po(self): 
        for record in self:
            obj = self.env['purchase.order'].browse(self._context.get('active_id'))
            if record.order_total > 100 :
		raise UserError('Please Enter proper value for advance in percentage')
            required_credit=((obj.amount_total*self.order_total)/(100))
            n_id=self.env['account.payment.term.request'].create({
							'name' : self[0].name,
							'purchase_id' : obj.id,
                                                        'customer_id':self.customer_id.id,
							'sales_person_id' : self.env.user.id,
							'state' : 'requested',
							'requested_date' : date.today(),
							'n_percenatge':self.order_total,
							'n_sale_amount':obj.amount_total,
							'currency_id':self.currency_id.id,
							'credit_required_amount':required_credit,})
            obj.payment_term_request='request'
	    temp_id = self.env.ref('gt_order_mgnt.email_template_payment_term_req_po')
	    if temp_id:
              # email_to = obj.team_id.user_id.partner_id.email
               email_to=''
               group = self.env['res.groups'].search([('name', '=', 'Adviser')])
               group_id = self.env.ref('base.group_sale_manager', False)
               val=group.users - group_id.users
               for recipient in val:
                   email_to += ","+str(recipient.login)
               group_id = self.env.ref('account.group_account_user', False)
               group = self.env['res.groups'].search([('name', '=', 'Adviser')])
               group_id = self.env.ref('base.group_sale_manager', False)
               val=group.users - group_id.users
            '''if group_id:
                user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', [group_id.id])])
                if user_ids:
                    email_to = ''.join([user.partner_id.email + ',' for user in user_ids])
                    email_to = email_to[:-1]'''
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            query = {'db': self._cr.dbname}
            fragment = {
                'model': 'purchase.order',
                'view_type': 'form',
                'id': obj.id,
            }
            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
            text_link = _("""<a href="%s">%s</a> """) % (url,obj.name)

            body_html = """<div>
    <p> <strong>New Payment Term Requested </strong></p><br/>
    <p>Dear Accountant,<br/>
        <b></b>requested for New Payment Term :  <b> %s </b>for <b>%s </b> <br/>
    </p>
    </div>"""%( self[0].name, text_link)

            body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'purchase.order',obj.id, context=self._context)
            temp_id.write({'body_html': body_html, 
             'email_to' : email_to, 'email_from' :self.env.user.login})
            temp_id.send_mail(obj.id)
        return True
