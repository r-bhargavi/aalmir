# -*- coding: utf-8 -*-
from openerp import models, fields, api,_
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare, float_round
from openerp.exceptions import UserError
from urlparse import urljoin
from urllib import urlencode

class ProcessInstruction(models.Model):
    _name = 'process.instruction'

    name = fields.Char(string='Name')
    sale_id = fields.Many2one('sale.order','Sale Order')
    sale_line = fields.Many2one('sale.order.line','Sale Order Line')
    product_id = fields.Many2one('product.product','Product')
    all_messages_line = fields.One2many('process.instruction.line','process_id','Process Line')
    messages_line = fields.One2many('process.instruction.line','process_msg_id','Process Line')
    messages_receive = fields.One2many('process.instruction.line','process_rec_id','Process Line')
    messages_send = fields.One2many('process.instruction.line','process_send_id','Process Line')
    message = fields.Text(string="Message")
    send_user_id = fields.Many2many('res.users','n_user_process_rel','process_id','user_id','Send user')
    sale_state = fields.Selection([('draft', 'Quotation'),
					('sent', 'Quotation Sent'),
					('awaiting', 'Awaiting'),
					('sale', 'Sale Order'),
					('done', 'Done'),
					('cancel', 'Cancelled'),
					], string='Status', readonly=True, copy=False, index=True,related='sale_id.state')

    #n_model = fields.Selection([('sale_order', 'Sale'),
#					('production_request', 'Production Request'),
#					('mrp', 'Manufacturing'),
#					('purchase', 'Purchase Order'),
#					('delivery', 'Delivery'),
#					('quality', 'Quality')
#					], string='model')

    @api.multi
    def send(self):
	if not self.message:
		raise UserError('Please Enter Message to send')
	if not self.send_user_id:
		raise UserError('Please select user to send Message')
	user=[]
	for rec in self.send_user_id:
		user.append(rec.id)
	vals={'message':self.message,'send_user_id':[(6,0,user)],'product_id':self.product_id.id if self.product_id else False,'sale_id':self.sale_id.id,
		'sale_line':self.sale_line.id,'state':'send','process_id':self.id,'process_msg_id':self.id,'process_send_id':self.id,'sent_message':True,
		'message_type':'outgoing'}
	send_ids=self.env['process.instruction.line'].create(vals)
	self.message=''
	self.send_user_id=False
	temp_id = self.env.ref('stock_merge_picking.email_template_sale_instruction')
    	if temp_id:
    		for rec in self.send_user_id:
			user_obj = self.env['res.users'].browse(self.env.uid)
			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
			query = {'db': self._cr.dbname}
			fragment = {
			    'model': 'process.instruction',
			    'view_type': 'form',
			    'id': self.id,
			}
			url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))

			body_html = """<div> 
			<p> <strong>New Instruction</strong></p><br/>
			<p>Dear %s,<br/>
			    One New Instruction '%s' from <b>%s </b> for  Product:%s <br/>
			</p>
			</div>"""%(rec.user_id.name, str(rec.message), user_obj.name, str(rec.product_id.name))

			body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'process.instruction',self.id, context=self._context)
			temp_id.write({'body_html': body_html, 'email_to':str(rec.user_id.login),'email_from': user_obj.partner_id.email})
			temp_id.send_mail(self.id)

	return {"type": "ir.actions.do_nothing",}

    @api.multi
    #@api.onchange('product_id','sale_line')
    def _get_sale_line(self):
	update_ids=[]
	receive_ids=[]
	send_ids=[]
	if self.product_id:
		res = {'domain': {'process_line': [('product_id', '=', self.product_id.id)],'process_line_receive': [('product_id', '=', self.product_id.id),('create_uid','!=',self.env.user.id)],'process_line_send': [('product_id', '=', self.product_id.id),('create_uid','=',self.env.user.id)]}}
	if self.sale_line:
		res = {'domain': {'process_line': [('sale_id', '=', self.sale_id.id)],'process_line_receive': [('sale_id', '=', self.sale_id.id)],'process_line_send': [('sale_id', '=', self.sale_id.id)]}}
	return res #{'value': {'process_line': update_ids,'process_line_receive':receive_ids,'process_line_send':send_ids}}
	
class ProcessInstructionLine(models.Model):
    _name = 'process.instruction.line'

    @api.multi
    #@api.depends('set_message_type')
    def _get_msg_type(self):
	for rec in self:
		if rec.create_uid.id == self.env.user.id:
			rec.message_type='outgoing'
		else:
			rec.message_type='incomming'

#CH_N112 add code to show only current user created records..
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
	    if args[0]:
		if args[0][2] and  type(args[0][2]) is list:
	            pr_id=self.env['process.instruction'].search([('id','in',args[0][2])])
		    args.append(('product_id','in',(pr_id.product_id.id,False)))
	    
		    if args[0][0] == 'process_rec_id':
			args.append(('create_uid','!=',self.env.user.id))
	    
		    if args[0][0] == 'process_send_id':
			args.append(('create_uid','=',self.env.user.id))

		    if args[0][0] == 'process_id':
			args.remove(('product_id','in',(pr_id.product_id.id,False)))
			args.append(('create_uid','=',self.env.user.id))
	    return super(ProcessInstructionLine, self).search(args=args,
                                          offset=offset,
                                          limit=limit,
                                          order=order,
                                          count=count)

    name = fields.Char(string='Name')
    message = fields.Text(string="Message")
    product_id = fields.Many2one('product.product','Product')
    state = fields.Selection([('draft','Draft'),('send','Send'),('seen','Seen')],'Status',Defaut='draft')
    send_user_id = fields.Many2many('res.users','n_user_process_line_rel','line_id','user_id','Send To')
    message_type = fields.Selection([('incomming','Incomming'),('outgoing','Outgoing')],'Type',compute=_get_msg_type)

    read_user_id = fields.Many2many('res.users','msg_user_read_rel','line_id','user_id','Read By')
    receive_state = fields.Selection([('draft','Draft'),('send','Send'),('seen','Seen')],'Status',Defaut='draft')
    main_id = fields.Many2one('process.instruction.line','Main Msg')

    process_id = fields.Many2one('process.instruction','All Messages')
    process_msg_id = fields.Many2one('process.instruction','Messages')
    process_rec_id = fields.Many2one('process.instruction','Received Messages')
    process_send_id = fields.Many2one('process.instruction','Send Messages')

    sale_id = fields.Many2one('sale.order','Sale Name')
    sale_line = fields.Many2one('sale.order.line','Sale Order Line')
    production_id = fields.Many2one('n.manufacturing.request','Production Request')
    manu_id = fields.Many2one('mrp.production','Manufacture')
    purchase_id = fields.Many2one('purchase.order','Purchase')
    #user_id = fields.Many2one('res.users', string='Salesperson',default=lambda self: self.env.user)
    
    sent_message = fields.Boolean(string="Display",default=False)

class SaleOrder(models.Model):
	_inherit='sale.order'
	
	@api.multi
	def _get_msg_count(self):
	    for line in self:
		count=0
		new_id=self.env['process.instruction'].search([('sale_id','=',line.id)])
		if new_id:
			for rec in new_id.all_messages_line:
				if self.env.user.id != rec.create_uid.id:
					rec_user=[]
					for n_usr in rec.send_user_id:
						rec_user.append(n_usr.id)
					if self.env.user.id in rec_user:
						li_user=[]
						for m_usr in rec.read_user_id:
							print "inside---"
							li_user.append(m_usr.id) 
						if self.env.user.id not in li_user:
							count +=1
		line.new_msg_count=count

	new_msg_count= fields.Integer(string="Count",compute="_get_msg_count")

	@api.multi
	def send_instruction(self):
		new_id=self.env['process.instruction'].search([('sale_id','=',self.id)])
		if not new_id:
			new_id=self.env['process.instruction'].create({'sale_id':self.id})
		else:
			for rec in new_id.all_messages_line:
				if rec.create_uid.id != self.env.user.id and new_id.product_id.id==rec.product_id.id :
					rec.read_user_id=[(4,self.env.user.id)]
		if self.state in ('draft','sent','awaiting'):
			sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view_draft', False)
		elif self.state in ('sale','done'):
			sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'process.instruction',
		    'views': [(sale_form.id, 'form')],
		    'view_id': sale_form.id,
		    'target':'new',
		    'res_id':new_id[0].id,
		}

class ProductProduct(models.Model):
	_inherit='product.product'
	
	def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
		if context.get('process_sale_id'):
			args=[]
			product_qry="select product_id from sale_order_line where order_id={}".format(context.get('process_sale_id'))
			cr.execute(product_qry)
			product_ids=[i[0] for i in cr.fetchall()]
			args.extend([('id','in',product_ids)])		
		return super(ProductProduct,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

class ManufactureRequest(models.Model):
	_inherit='n.manufacturing.request'
	
	@api.multi
	def _get_msg_count(self):
	    for line in self:
		count=0
		new_id=self.env['process.instruction'].search([('sale_id','=',line.n_sale_line.id)])
		if new_id:
			for rec in new_id.all_messages_line:
				if self.env.user.id != rec.create_uid.id:
					rec_user=[]
					for n_usr in rec.send_user_id:
						rec_user.append(n_usr.id)
					if self.env.user.id in rec_user:
						li_user=[]
						for m_usr in rec.read_user_id:
							li_user.append(m_usr.id) 
						if self.env.user.id not in li_user:
							count +=1
		line.new_msg_count=count

	new_msg_count= fields.Integer(string="Count",compute="_get_msg_count")

	@api.multi
	def send_instruction(self):
                context=self._context.copy()
                request_id=self.env['n.manufacturing.request'].search([('id','=',self._context.get('new_id'))])
		new_id=self.env['process.instruction'].search([('sale_id','=',self.n_sale_line.id)], limit=1)
		if not new_id:
			new_id=self.env['process.instruction'].create({'sale_id':self.n_sale_line.id})
		else:
			for rec in new_id.all_messages_line:
				if rec.create_uid.id != self.env.user.id and new_id.product_id.id==rec.product_id.id:
					rec.read_user_id=[(4,self.env.user.id)]
		sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view', False)
                context.update({'default_product_id':request_id.n_product_id.id})
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'process.instruction',
		    'views': [(sale_form.id, 'form')],
		    'view_id': sale_form.id,
		    'target':'new',
		    'res_id':new_id[0].id,
                    'context':context
		}

class MrpProduction(models.Model):
	_inherit='mrp.production'
	
	@api.multi
	def _get_msg_count(self):
	    for line in self:
		count=0
		new_id=self.env['process.instruction'].search([('sale_id','=',line.sale_id.id)])
		if new_id:
			for rec in new_id.all_messages_line:
				if self.env.user.id != rec.create_uid.id:
					rec_user=[]
					for n_usr in rec.send_user_id:
						rec_user.append(n_usr.id)
					if self.env.user.id in rec_user:
						li_user=[]
						for m_usr in rec.read_user_id:
							li_user.append(m_usr.id) 
						if self.env.user.id not in li_user:
							count +=1
		line.new_msg_count=count

	new_msg_count= fields.Integer(string="Count",compute="_get_msg_count")

	@api.multi
	def send_instruction(self):
		new_id=self.env['process.instruction'].search([('sale_id','=',self.sale_id.id)])
		if not new_id:
			new_id=self.env['process.instruction'].create({'sale_id':self.sale_id.id})
		else:
			for rec in new_id.all_messages_line:
				if rec.create_uid.id != self.env.user.id and new_id.product_id.id==rec.product_id.id:
					rec.read_user_id=[(4,self.env.user.id)]
		sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'process.instruction',
		    'views': [(sale_form.id, 'form')],
		    'view_id': sale_form.id,
		    'target':'new',
		    'res_id':new_id[0].id,
		}
    
class PurchaseOrder(models.Model):
	_inherit='purchase.order'
	
	@api.multi
	def _get_msg_count(self):
	    for line in self:
		count=0
		new_id=self.env['process.instruction'].search([('sale_id','=',line.sale_id.id)])
		if new_id:
			for rec in new_id.all_messages_line:
				if self.env.user.id != rec.create_uid.id:
					rec_user=[]
					for n_usr in rec.send_user_id:
						rec_user.append(n_usr.id)
					if self.env.user.id in rec_user:
						li_user=[]
						for m_usr in rec.read_user_id:
							li_user.append(m_usr.id) 
						if self.env.user.id not in li_user:
							count +=1
		line.new_msg_count=count

	new_msg_count= fields.Integer(string="Count",compute="_get_msg_count")

	@api.multi
	def send_instruction(self):
		new_id=self.env['process.instruction'].search([('sale_id','=',self.sale_id.id)])
		if not new_id:
			new_id=self.env['process.instruction'].create({'sale_id':self.sale_id.id})
		else:
			for rec in new_id.all_messages_line:
				if rec.create_uid.id != self.env.user.id and new_id.product_id.id==rec.product_id.id:
					rec.read_user_id=[(4,self.env.user.id)]
		sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'process.instruction',
		    'views': [(sale_form.id, 'form')],
		    'view_id': sale_form.id,
		    'target':'new',
		    'res_id':new_id[0].id,
		}

class Stockpicking(models.Model):
	_inherit='stock.picking'
	
	@api.multi
	def _get_msg_count(self):
	    for line in self:
		count=0
		new_id=self.env['process.instruction'].search([('sale_id','=',line.sale_id.id)])
		if new_id:
			for rec in new_id.all_messages_line:
				if self.env.user.id != rec.create_uid.id:
					rec_user=[]
					for n_usr in rec.send_user_id:
						rec_user.append(n_usr.id)
					if self.env.user.id in rec_user:
						li_user=[]
						for m_usr in rec.read_user_id:
							li_user.append(m_usr.id) 
						if self.env.user.id not in li_user:
							count +=1
		line.new_msg_count=count

	new_msg_count= fields.Integer(string="Count",compute="_get_msg_count")

	@api.multi
	def send_instruction(self):
		new_id=self.env['process.instruction'].search([('sale_id','=',self.sale_id.id)])
		#new_id.n_model = 'quality' if self.picking_type_id.code=='internal' else 'delivery'
		if not new_id:
			new_id=self.env['process.instruction'].create({'sale_id':self.sale_id.id})
		else:
			for rec in new_id.all_messages_line:
				if rec.create_uid.id != self.env.user.id and new_id.product_id.id==rec.product_id.id:
					rec.read_user_id=[(4,self.env.user.id)]
		sale_form = self.env.ref('stock_merge_picking.sale_instruction_form_view', False)
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'process.instruction',
		    'views': [(sale_form.id, 'form')],
		    'view_id': sale_form.id,
		    'target':'new',
		    'res_id':new_id[0].id,
		}

class productProduct(models.Model):
    _inherit = 'product.product'

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('instruction_sale_id'):
                args=[]
                product_qry="select product_id from sale_order_line where pricelist_type is not NULL and order_id={}".format(context.get('instruction_sale_id'))
                cr.execute(product_qry)
                product_ids=[i[0] for i in cr.fetchall()]
                args.extend([('id','in',product_ids)])
        return super(productProduct,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

