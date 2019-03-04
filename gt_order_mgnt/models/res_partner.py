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
from datetime import datetime, date, timedelta
from urllib import urlencode
from urlparse import urljoin
from openerp.exceptions import UserError, ValidationError
import json

class ResPartnerCredit(models.Model):
    _name = 'res.partner.credit'
    _order='id desc'

    sale_id=fields.Many2one('sale.order', string="SO Number")
    sale_amount=fields.Float('Total Amount',compute='due_invoice')
    credit_ask=fields.Float('Credit Requested Amount', compute='remain_saleamt')
    inv_paid=fields.Float('Amount Paid', compute='due_invoice')
    user_id=fields.Many2one('res.users', string="Approved By")
    request_date=fields.Date('Approved On')
    state=fields.Selection([('request', 'Request'),
			    ('approve','Approved'),('cancel', 'Cancel'),
			    ('reject','Reject')], readonly=True, copy=False,  track_visibility='onchange',  string='Status')
    partner_id=fields.Many2one('res.partner', string="SO Number")
    note=fields.Text('Reason')
    from_date=fields.Date('From Date')
    to_date=fields.Date('To Date')
    stop_delivery=fields.Boolean('Stop Delivery')
    deliery_note=fields.Char('Delivery Note')
    delivery_id=fields.Many2one('stock.picking','Delivery Number')

    @api.multi
    def delivery_allow(self):
        for record in self:
            if record.delivery_id:
               record.stop_delivery=False
               record.state='approve'
               record.delivery_id.write({'allow_delivery':True})
               record.partner_id.message_post(body="Delivery Request Block is Approved" +'<br></br> ' + 'Delivery No. : '+ str(record.delivery_id.name) )
               record.delivery_id.message_post(body="Delivery Request Block is Approved:" +'<br></br> ' + 'Delivery No. : '+ str(record.delivery_id.name) )
               

    @api.multi
    def write(self,vals):
	for record in self:
		body=''
		if vals.get('stop_delivery'):
			body += '<ul><li>Stop Delivery Changed : '+str(vals.get('stop_delivery'))+"</li></ul> "
		if vals.get('note'):
			body += '<ul><li>By Reason : '+str(vals.get('note'))+"</li></ul> "
		if body:
			record.partner_id.message_post(body)
	return super(ResPartnerCredit,self).write(vals)
 
    @api.multi
    def approved_stock(self):
        self.stop_delivery=False
        self.sale_id.write({'stop_delivery':False})

    @api.multi
    @api.depends('sale_id')
    def due_invoice(self):
       for record in self:
	   currency_id = record.partner_id.credit_currency_id if record.partner_id and record.partner_id.credit_currency_id else self.env.user.company_id.currency_id
           if record.sale_id:
              record.sale_amount=record.sale_id.report_currency_id.compute(record.sale_id.amount_total,currency_id)
              invoice=self.env['account.invoice'].search([('sale_id', '=',record.sale_id.id), ('state', 'in',('open', 'paid'))])
              total=0.0
              if invoice:
                 for inv in invoice:
		     if inv.state=='paid':
			total += inv.currency_id.compute(inv.amount_total,currency_id)
		     else:
		             d = json.loads(inv.payments_widget)
		             if d:
		               for payment in d['content']:
		                 total += inv.currency_id.compute((payment['amount']),currency_id)
                 record.inv_paid=total

    @api.multi
    def remain_saleamt(self):
        for record in self:
          if record.state == 'request':
            credit_currency_id=record.partner_id.credit_currency_id if record.partner_id.credit_currency_id else self.env.user.company_id.currency_id
            
            partner_id=[record.sale_id.partner_id.id]
            for prtn in self.env['res.partner'].search([('parent_id','=',record.sale_id.partner_id.id)]):
                partner_id.append(prtn.id)

            pending_invoices=uninvoice_amt=order_amt=0.0    
            
            invoice=self.env['account.invoice'].search([('state','=','open'),('sale_id', '!=', record.sale_id.id),('partner_id','in',tuple(partner_id))])
            for inv in invoice:
                   pending_invoices += inv.currency_id.compute((inv.residual_new1),credit_currency_id) 
            
            sale=self.env['sale.order'].search([('partner_id', 'in',tuple(partner_id)),('state','in',('sale','awaiting')),('id','!=',record.sale_id.id)])
            for saleamt in sale:
                   uninvoice_amt +=saleamt.n_quotation_currency_id.compute(saleamt.amount_total,saleamt.report_currency_id) #CH_N103 add convert currency
                   invoice=self.env['account.invoice'].search([('sale_id','=',saleamt.id),('state','in',('open','paid'))])
                   total_inv=0.0
                   for inv in invoice:
                   	total_inv  += inv.currency_id.compute(inv.amount_total,credit_currency_id)   #CH_N103 add convert currency
                   uninvoice_amt -=total_inv
            
            invoice1=self.env['account.invoice'].search([('sale_id', '=', record.sale_id.id),('state','in',('open','paid'))])
            print "recordrecordrecord----------------",record,record.sale_id
            order_amt = record.sale_id.n_quotation_currency_id.compute(record.sale_id.amount_total,record.sale_id.report_currency_id)
	#CH_N103 ADD currecny converter >>>
            for ln in invoice1:
            	order_amt -= ln.currency_id.compute((ln.amount_total -ln.residual),record.sale_id.report_currency_id)
            record.credit_ask = pending_invoices+uninvoice_amt+order_amt
             
    @api.multi
    def allow_rqst(self):
        for record in self:
            record.sale_id.write({'stop_delivery':record.stop_delivery, 'cr_note':record.note,
            'cr_state':'approve',})
            record.sale_id.message_post(body="<ul><li><span style='color:green'>Request for customer credit is Approved:</span></li><li> Approved By:"+str(self.env.user.name)+"</li><li> Stop Delivery:"+str(record.stop_delivery)+"</li><li> Reason:"+str(record.note)+"</li><ul>")
            record.partner_id.message_post(body="<ul><li><span style='color:green'>Request for customer credit is Approved:</span> </li><li>'Sale Order No.:"+str(record.sale_id.name)+"</li><li> Stop Delivery:"+str(record.stop_delivery)+"</li><li> Reason:"+str(record.note)+"</li><ul>")
            temp_id = self.env.ref('gt_order_mgnt.email_template_customer_credit_sale_approve')
            if temp_id:
			recipient_partners=''
			group = self.env['res.groups'].search([('name', '=', 'Adviser')])
			group_id = self.env.ref('base.group_sale_manager', False)
			val=group.users - group_id.users
			for recipient in val:
	    		    recipient_partners += str(recipient.login)+","

			user_obj = self.env['res.users'].browse(self.env.uid)
			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
			query = {'db': self._cr.dbname}
			fragment = {
			    'model': 'sale.order',
			    'view_type': 'form',
			    'id': record.sale_id.id,
			}
			url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))

			body_html = """<div>
			    <p> <strong>Request for customer credit unblock is Approved</strong></p><br/>
			    <p>Dear Sir/Madam,<br/>
				Your sale order No-:<b> %s  \n</b> Customer Name-:'%s ' </p>
			    </div>"""%(record.sale_id.name or '',record.partner_id.name or  '',)

			body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',record.sale_id.id, context=self._context)
			body_html +='<li>Sale Order Amount:'+str(record.sale_amount) +str(record.sale_id.n_quotation_currency_id.name) +'</li>'
                        body_html +='<li>credit Ask:'+str(record.credit_ask) +str(record.sale_id.n_quotation_currency_id.name)+'</li>'
			temp_id.write({'body_html': body_html, 'email_to':record.create_uid.login,
                                      'email_from': self.env.user.login})
			temp_id.send_mail(record.sale_id.id)  
            record.write({'user_id':self.env.user.id,'state':'approve','request_date':date.today()})
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def reject_rqst(self):
        for record in self:
            record.sale_id.write({'cr_state':'reject', 'cr_note':record.note})
            record.sale_id.message_post(body="<ul><li> <span style='color:red'>Request for customer credit is Rejected:</span> </li><li> Reject By:"+str(self.env.user.name)+"</li><li> Reason:"+str(record.note)+"</li><ul>")
            record.partner_id.message_post(body="<ul><li> <span style='color:red'>Request for customer credit is Rejected:</span> Sale Order No.:"+str(record.sale_id.name) +'</li><li> Reason:'+str(record.note)+"</li><ul>")
            #self.env["res.partner.credit"].search([('id','=',record.id)]).unlink()
            record.write({'user_id':self.env.user.id,'state':'reject','request_date':date.today()})
        return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def open_request(self):
        move_form = self.env.ref('gt_order_mgnt.customer_credit_form', False)
        if move_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'res.partner.credit',
                    'views': [(move_form.id, 'form')],
                    'view_id': move_form.id,
                    'target': 'new',
                    'res_id':self.id,
                }
        return True
        
class ResPartner(models.Model):
    _inherit = 'res.partner' 

    @api.multi
    def totalpayment_val(self):
        partner_id=[self.id]
        for prtn in self.env['res.partner'].search([('parent_id','=',self.id)]):
            partner_id.append(prtn.id)
	po_tree = self.env.ref('account.view_account_payment_tree', False)
	po_form = self.env.ref('account.view_account_payment_form', False)
        if po_form:
            return {
		'name':"Total Payment List",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'account.payment',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':[('partner_id', 'in',tuple(partner_id))],
            }
            
    @api.multi
    def customer_name(self):
       for record in self:
           res=self.env['res.partner'].search([('id','=', record.id)]) 
           record.partner_id=res.id
           
    @api.multi
    def check_account_group(self):
       for record in self:
           group = self.env['res.groups'].search([('name', '=', 'Accountant')])
           for recipient in group.users:
           	if self.env.user.login == recipient.login:
           		record.account_user_bool=True
           		break
    @api.multi
    def total_sale_amt(self):
        for record in self:
	    credit_currency_id=record.credit_currency_id if record.credit_currency_id else self.env.user.company_id.currency_id
            sale=self.env['sale.order'].search([('partner_id','=', record.id),('state','=', 'sale')])
	    inv_pending=pending_amount=0
            total=0.0
            partner_id=[record.id]
            for prtn in self.env['res.partner'].search([('parent_id','=',record.id)]):
		partner_id.append(prtn.id)
            invoice_open=self.env['account.invoice'].search([('state','=','open'),('partner_id','in',tuple(partner_id))])
            invoice_count=self.env['account.invoice'].search([('state','in', ('open','paid')),('partner_id','in',tuple(partner_id))])
            if invoice_open:
               for inv in invoice_open:
                   total += inv.residual_new1
                   inv_pending +=1
               record.total_invoice_pending=inv.currency_id.compute((total),credit_currency_id)
               record.invoice_pending= inv_pending 
            record.run_sale=len(sale)
            if sale or invoice_count:
               sale_total=total_val=total_pay_amt1=0.0
               delay_inv=delay_inv_paid= 0.0
               for order in sale:
		   invoice=self.env['account.invoice'].search([('sale_id','=', order.id)])
		   from_currency=order.report_currency_id if order.report_currency_id else order.n_quotation_currency_id
                   sale_total += from_currency.compute(order.amount_total,credit_currency_id)  if order.state == 'sale' else 0.0                 
                   for inv1 in order.invoice_ids:
                        if inv1.state in ('open', 'paid'):
                           d = json.loads(inv1.payments_widget)
                           if d:
                              for payment in d['content']:
                                  total_pay_amt1 += inv1.currency_id.compute((payment['amount']),credit_currency_id)
               total_pay_amt=0.0
               for inv_val in invoice_count:
                    if inv_val.state in ('open', 'paid'):
                       d = json.loads(inv_val.payments_widget)
                       if d:
                          for payment in d['content']:
                              total_pay_amt += inv_val.currency_id.compute((payment['amount']),credit_currency_id)
                          record.total_pay=total_pay_amt  
                    if inv_val.date_invoice and inv_val.payment_date_inv:
                       if inv_val.state in ('open', 'paid')  and inv_val.date_invoice > inv_val.payment_date_inv:
                          delay_inv +=len(inv_val)
                          d = json.loads(inv_val.payments_widget)
                          if d:
                             for payment in d['content']:
                                 delay_inv_paid  += inv_val.currency_id.compute((payment['amount']),credit_currency_id)
                       if inv_val.state == 'open':
                          total_val += inv_val.currency_id.compute((inv_val.amount_total - inv_val.residual),credit_currency_id)

               record.total_sale_amount= sale_total 
               record.delay_invoice=delay_inv
               record.delay_inv_paid_amt=delay_inv_paid
               record.total_sale_pending_amount= sale_total - total_pay_amt1

    credit_limit = fields.Float(string="Credit Limit")
    #time_limit_value = fields.Integer(string="Time Limit")
    #time_limit_type = fields.Selection([
    #                                    ('day','Days'),
    #                                    ('week', 'weeks'),
    #                                    ('month', 'Months')], string="Time Limit")

    city_id = fields.Many2one('res.partner.city', string="City")
    n_doc_upload = fields.One2many('customer.upload.doc','customer_id') #CH_N065
    counter_customer=fields.Boolean('Counter Customer')# add boolean field for counter customer 
    from_date=fields.Date('From Date')
    to_date=fields.Date('To Date')
    new_credit_limit=fields.Float('New Credit Allowed')
    doc_name=fields.Char('Document Name')		#CH_N104  for document name
    new_upload=fields.Binary('Upload',attachment=True)
    new_note=fields.Text('Note')
    invoice_pending=fields.Integer('Pending Payments',compute=total_sale_amt)
    total_invoice_pending=fields.Float('Total Invoice Pending',compute=total_sale_amt)
    total_sale_pending_amount=fields.Float("Order Pending Amount",compute=total_sale_amt)
    delay_invoice=fields.Integer('Delay Payments',compute=total_sale_amt)
    delay_inv_paid_amt=fields.Float('Delay Paid Amount',compute=total_sale_amt) 
    run_sale=fields.Integer('Running Orders', compute=total_sale_amt)
    total_sale_amount=fields.Float('Running Order Amount', compute=total_sale_amt)
    total_pay=fields.Float('Total Payments',compute=total_sale_amt)    
    cr_state=fields.Selection([('request', 'Request'),('no_request','No Request'),('reject','Reject')], string='Status', default='no_request')
    crdit_ids=fields.One2many('res.partner.credit','partner_id', domain=[('state','=','request')])
    sale_ids =fields.One2many('sale.order','partner_id', compute='saleorder')
    invoice_val_ids =fields.One2many('account.invoice','partner_id', compute='invoicevalue')
    delivery_ids=fields.One2many('stock.picking','partner_id')
    partner_id=fields.Many2one('res.partner',compute=customer_name)

#CH_N103
    crdit_ids_history=fields.One2many('res.partner.credit','partner_id',domain=[('state','!=','request')]) #CH_N103 add field to show history
    credit_currency_id=fields.Many2one('res.currency','Credit Currency')
    
#CH_N132 inherite field to make may to many relation   
    property_payment_term_id = fields.Many2many('account.payment.term','n_partner_payment_rel','id','partner_id',
        string ='Customer Payment Term',
        help="This payment term will be used instead of the default one for sale orders and customer invoices", oldname="property_payment_term")
    
    property_supplier_payment_term_id = fields.Many2many('account.payment.term','supplier_partner_payment_rel','id','supplier_id',
        string ='Supplier Payment Term',
        help="This payment term will be used instead of the default one for sale orders and customer invoices")
        
    account_user_bool = fields.Boolean('Account user bool',compute='check_account_group')
    supplier_type=fields.Many2many('res.partner.supplier.type', String='Supplier Type')
    
    @api.multi
    def get_string_data(self):
       for record in self:
           record.invoices_pending = str(record.invoice_pending)+"("+str(record.total_invoice_pending)+")" if record.invoice_pending else ''
	   record.delay_payment_done = str(record.delay_invoice)+"("+str(record.delay_inv_paid_amt)+")" if record.delay_invoice else ''
	   record.active_order = str(record.run_sale)+"("+str(record.total_sale_amount)+")" if record.run_sale else ''

    invoices_pending = fields.Char(string="Invoices Pending",compute=get_string_data)
    delay_payment_done = fields.Char(string="Delayed payment Done",compute=get_string_data)
    active_order = fields.Char(string="Active Sale Order",compute=get_string_data)

    @api.multi
    @api.depends('sale_order_ids')
    def saleorder(self): 
        for record in self:
            if record.sale_order_ids:
               sale=record.sale_order_ids.search([('state','=','sale'), ('partner_id', '=', record.id)])
               if sale:
                  record.sale_ids=sale
    @api.multi
    @api.depends('invoice_ids')
    def invoicevalue(self): 
        for record in self:
            if record.invoice_ids:
               invoice=record.invoice_ids.search([('state','!=','cancel'),('partner_id', '=', record.id)])
               if invoice:
                  record.invoice_val_ids=invoice

    @api.multi
    def write(self, vals):
	for rec in self: 
	       	body=''
	       	attachment=[]
	       	if vals.get('new_credit_limit'):
		   vals.update({'credit_limit':vals.get('new_credit_limit')})
		   if rec.credit_limit:
			body +="<ul><li> <span style='color:green'>Credit Limit Changes : </span> From "+str(rec.credit_limit)+" To "+str(vals.get('new_credit_limit'))+"</li></ul> "
		   else:
                   	body +="<ul><li> <span style='color:green'>Credit Limit Add : </span>"+str(vals.get('new_credit_limit'))+"</li></ul> "
	       	if vals.get('credit_currency_id'):
		    currency_id=self.env['res.currency'].search([('id','=',vals.get('credit_currency_id'))])
		    if rec.credit_currency_id:
			body +="<ul><li> Currency Changed :"+str(rec.credit_currency_id.name)+" >> "+str(currency_id.name)+"</li></ul> "
		    else:
		    	body +="<ul><li> Currency Add: "+str(currency_id.name)+"</li></ul>"
	
	       	if vals.get('from_date'):
		    if not vals.get('to_date') and vals.get('from_date') > rec.to_date:
			raise UserError('Please select from date less than to date')
		    if rec.from_date:
		       body +="<ul><li> From Date Changed :"+str(rec.from_date)+" >> "+str(vals.get('from_date'))+"</li></ul>"
		    else:
		    	body +="<ul><li> From Date Added : "+str(vals.get('from_date'))+"</li></ul>"

	       	if vals.get('to_date'):
		    if not vals.get('from_date') and vals.get('to_date') < rec.from_date:
			raise UserError('Please select From date less than To date')
		    if rec.to_date:
			body +="<ul><li> To Date Changed :"+str(rec.to_date)+" >> "+str(vals.get('to_date'))+"</li></ul> "
		    else:
		    	body +="<ul><li> To Date Added : "+str(vals.get('to_date'))+"</li></ul>"
		if vals.get('new_note'):
			body +="<ul><li> Note :"+str(vals.get('new_note'))+"</li></ul>"
		if vals.get('doc_name'):
			attachment=[(vals.get('doc_name'),vals.get('new_upload'))]
			body +="<ul><li>Uploaded Document</li></ul>"
		if vals.get('doc_name')==False:
			body +="<ul><li>Document Removed -: "+str(rec.doc_name)+"</li></ul>"
		if vals.get('property_payment_term_id') :
			new_term = []
			if type(vals.get('property_payment_term_id')[0]) ==list:
				new_term = vals.get('property_payment_term_id')[0][2]
			elif type(vals.get('property_payment_term_id')[0])==tuple:
				new_term.append(vals.get('property_payment_term_id')[0][1])
			exit_term = []
			for line in rec.property_payment_term_id:
				exit_term.append(line.id)
			n_ids=list(set(new_term).difference(exit_term))
			if n_ids:
				body +="<ul style='color:green'> Payment Term Added"
				for line1 in n_ids:
				   body +='<li>'+str(self.env['account.payment.term'].sudo().browse(line1).name)+'</li>'
				body +="</ul>"
			ex_ids=list(set(exit_term).difference(new_term))
			if ex_ids:
				body +="<ul style='color:red'> Payment Term removed"
				for line2 in ex_ids:
				   body +='<li>'+str(self.env['account.payment.term'].sudo().browse(line2).name)+'</li>'
				body +="</ul>"
 	       	if body:       
	       		rec.message_post(body,attachments=attachment)
        return super(ResPartner, self).write(vals)
        
    @api.multi
    def open_creditprofile(self):
	po_form = self.env.ref('gt_order_mgnt.customer_credit_form_ac', False)
        if po_form:
            return {
		'name':"Total Payment List",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'res.partner',
		'views': [(po_form.id, 'form')],
                'view_id': po_form.id,
                'target': 'current',
		'res_id':self.id,
            }

class ResPartnerCity(models.Model):
    _name = 'res.partner.city'
    
    name = fields.Char(string="Name")
    transit_time = fields.Integer(string="Transit time(days)")
    state_id = fields.Many2one('res.country.state', string="State")
    
class ResPartnerSupplierType(models.Model):
    _name = 'res.partner.supplier.type'
    name = fields.Char(string="Name")
    
class HrEmployee(models.Model):
    _inherit='hr.employee'
    
    operator=fields.Boolean('Operator?')
    operator_type = fields.Selection([('injection','Injection'),('film','Film'),('both','Both')],
    				string='Operator Type')

    
#    for solving the operator name issue in work order issue wizard

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if self._context.get('employee'):
            if self._context.get('user_ids'):
               lst=[]
               users=self.env['res.users'].search([('id','in',self._context.get('user_ids')[0][2])])
               for rec in users:
               		lst.append(rec.employee_ids._ids)
               args.extend([('id','in',rec.employee_ids._ids)])
        return super(HrEmployee,self).name_search(name, args, operator=operator, limit=limit)
        
        
