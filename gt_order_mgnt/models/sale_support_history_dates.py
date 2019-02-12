from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from openerp import tools, SUPERUSER_ID

from urlparse import urljoin
from urllib import urlencode

#CH_N043 add table to store manufacture date
class MrpCompleteDate(models.Model):
	_name = "mrp.complete.date"
	_order = "id desc"

	n_line_id = fields.Many2one('sale.order.line','sale order')
	n_prevoiusdate = fields.Date(string='Prevoius Date')
	n_prevoiusdate1 = fields.Date(string='Prevoius Date')		#CH_N050 for reference
	n_nextdate = fields.Datetime(string='Next Date')
	n_status  = state = fields.Selection([('draft','Draft'),('request','Pending'),('done','Approved'),('reject','Reject')],'Status',default='draft')
	n_user_id = fields.Many2one('res.users','Aproved By')
	n_reason  = fields.Text("Note")
	n_mo =fields.Many2one('mrp.production','Manufacture Order')
	n_po =fields.Many2one('purchase.order','Purchase Order')
        n_name = fields.Text("Name")
        mo_schedule_date=fields.Datetime(string='Work Orders Schedule Date')
        wo_schedule_planned=fields.Datetime(string='Schedule Date')
        wo_schedule_planned_end=fields.Datetime(string='End Date')
        work_order_id=fields.Many2one('mrp.production.workcenter.line','Work Order No.')
        time_adjust=fields.Float('Time Adjust')
    
        @api.multi
        @api.onchange('wo_schedule_planned', 'time_adjust')
        def end_date_change(self):
            for record in self:
                if record.wo_schedule_planned and record.work_order_id and record.time_adjust: 
                   DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
                   record.wo_schedule_planned_end=datetime.strptime(record.wo_schedule_planned, DATETIME_FORMAT) + timedelta(hours=(record.work_order_id.hour +record.time_adjust) )
	@api.model
	def create(self,vals):
		if str(vals.get('n_nextdate')) < str(date.today()):
			raise UserError(_('New Date can not be less than current date')) 
		return super(MrpCompleteDate,self).create(vals)

	@api.multi
	def save(self):
		self.n_status = 'request'
		if self.n_mo:
			self.n_name= self.n_mo.name
			self.env['mrp.production'].sudo().browse(self.n_mo.id).write({'n_request_bool':True,'n_request_date':self.n_nextdate,'n_request_date_bool1':True,'n_request_date_bool':False})
			self.env['mrp.production'].sudo().browse(self.n_mo.id).message_post(body='New Change Date -: '+str(self.n_nextdate if self.n_nextdate else self.mo_schedule_date)
 +"\n By Reason:"+' '+str(self.n_reason)) 
                if self.mo_schedule_date:
                   self.n_mo.date_planned=self.mo_schedule_date
                   if self.n_mo.state !='new' and self.n_mo.workcenter_lines:
                   	for mo_line in self.n_mo.workcenter_lines[0]:
                       		mo_line.date_planned=self.mo_schedule_date
                if self.work_order_id:
                   DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
                   self.work_order_id.date_planned=self.wo_schedule_planned
                   self.work_order_id.hour =self.work_order_id.hour + self.time_adjust
                   body='<b>Scheduled Date Changed:</b>'
		   body +='<ul><li> Scheduled Start Date : '+str(datetime.strptime(self.wo_schedule_planned, DATETIME_FORMAT) + timedelta(hours=4)) +'</li></ul>'
		   body +='<ul><li> Scheduled End Date : '+str(datetime.strptime(self.wo_schedule_planned_end, DATETIME_FORMAT) + timedelta(hours=4)) +'</li></ul>'
                   body +='<ul><li> Time Adjust : '+str(self.time_adjust)+'</li></ul>'
		   body +='<ul><li> Changed By    : '+str(self.env.user.name) +'</li></ul>' 
		   body +='<ul><li> Date          : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
		   self.work_order_id.message_post(body=body)
	  #CH_N050 >>>
		if self.n_po:
			self.n_name= self.n_po.name
			self.env['purchase.order'].sudo().browse(self.n_po.id).write({'n_request_date':self.wo_schedule_planned,
                          'n_request_date_bool1':True,'n_request_date_bool':False})
			po_id=self.env['stock.picking'].search([('origin','=',self.n_po.name)],limit=1)
			if po_id:
				po_id.min_date=self.n_nextdate
	  #CH_N051>>>>>
		recipient_partners = str(self.n_line_id.order_id.user_id.login)
		if self.n_line_id:
			temp_id=''
			if self.n_po:
				temp_id = self.env.ref('gt_order_mgnt.template_change_date_purchase')
				if self.n_po.production_ids:
					self.n_po.production_ids.n_purchase_date=self.n_nextdate
					self.n_po.production_ids.n_po=self.n_po.id
					self.n_po.production_ids.n_purchase_bool=True  ##write for approvaL of new date
                                        body='<span style="color:red;font-size:14px;">Purchase Order  '+str(self.n_po.name)+' Date Change -:</span>\n<li> Old Date:' +str(self.n_prevoiusdate1 and self.n_prevoiusdate1 or '') + '\tNew Date:'+str(self.n_nextdate) +' </li> <li>\nReason:' + str(self.n_reason)+'</li>'
                                        self.n_po.production_ids.message_post(body)
                                        
					group=[]
					if self.n_po.production_ids.request_line.n_category.cat_type=='film':
						group = self.env['res.groups'].search([('name', '=', 'group_film_product')])
					if self.n_po.production_ids.request_line.n_category.cat_type=='injection':
						group = self.env['res.groups'].search([('name', '=', 'group_injection_product')])
					for recipient in group.users:
		    				recipient_partners += ","+str(recipient.login)
				else:
					search_id=self.env['sale.order.line.status'].search([('n_string','=','date_request')],limit=1) ## add status
					if search_id:
						self.n_line_id.n_status_rel=[(4,search_id.id)]
					group = self.env['res.groups'].search([('name', '=', 'Sales Support Email')])
					for recipient in group.users:
		    				recipient_partners += ","+str(recipient.login)
					self.n_line_id.new_date_bool=True  ##write for approvaL of new date
				#self.n_po.message_post(body='<span style="color:red;font-size:14px;">Purchase Order Change Date Request-:</span>\n '+ 'New Date:'+str(self.n_nextdate))

			elif self.n_mo:
				temp_id = self.env.ref('gt_order_mgnt.template_change_date_mrp')
				search_id=self.env['sale.order.line.status'].search([('n_string','=','date_request')],limit=1)
				if search_id:
						self.n_line_id.n_status_rel=[(4,search_id.id)]
				self.n_line_id.new_date_bool=True  ##write for approvaL of new date
			
			if temp_id:
                            recipient_partners=[]
                            user_obj = self.env['res.users'].browse(self.env.uid)
                            group = self.env['res.groups'].search([('name', '=', 'Sales Support Email')])
                            for recipient in group.users:
                                if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                                     recipient_partners.append(recipient.login)
                            recipient_partners.append(self.n_line_id.order_id.user_id.login)
                            recipient_partners = ",".join(recipient_partners)
                            print "recipient_partnersrecipient_partners",recipient_partners
			    model_id= self.n_mo.id if self.n_mo else self.n_po.id
			    model_name = 'mrp.production' if self.n_mo else 'purchase.order'
			    name_str = 'Purchase Date Re-Scheduled' if self.n_po else 'Manufacture Date Re-Scheduled'
			    base_url = self.env['ir.config_parameter'].get_param('web.base.url')
			    query = {'db': self._cr.dbname}
			    fragment = {
				'model': model_name,
				'view_type': 'form',
				'id': model_id,
			    }
                            n_date=datetime.strftime(datetime.strptime(self.n_nextdate,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d')           
			    url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                            if not self.n_prevoiusdate1:
                                subject="API-ERP Manufacturing Alert : %s production is scheduled"%str(self.env[model_name].browse(model_id).product_id.name)
                                body_html = """<div> 
                                <p>Dear Sir/Madam,<br/>
				<p> <strong> This is to inform you that new manufacuring order is scheduled as per below details.</strong></p><br/>
					<p>Sale order No-: <b>%s</b> </p>
					<p>Manufacturing Ref-: <b>%s</b> </p>
		    			<p>Product:<b>%s</b>
		    			<p>Quantity:<b>%s %s</b>
                                        <p>Requested completion date: <b>%s</b> </p>
                                        <p>New production completion date: <b>%s</b> </p>
                                        <p>Production starting date: <b>%s</b> </p>
                                        <p>By:<b> %s</b> </p>
		    			<p>Remarks:<b>%s</b> </p>
				</p>
				</div>"""%(str(self.n_line_id.order_id.name) or '',str(self.env[model_name].browse(model_id).name) or '',str(self.n_line_id.product_id.name) or ''+str(self.n_line_id.product_id.default_code) or '',str(self.env[model_name].browse(model_id).product_qty) or '',str(self.env[model_name].browse(model_id).product_uom.name) or '',str(self.env[model_name].browse(model_id).n_client_date) or '',n_date,str(self.env[model_name].browse(model_id).date_planned) or '' ,self.env.user.name or '',self.n_reason or '')
                            else:
                                subject="API-ERP Manufacturing Alert : %s production completion date changed"%str(self.env[model_name].browse(model_id).product_id.name)
                                body_html = """<div> 
                                <p>Dear Sir/Madam,<br/>
				<p> <strong> Manufacturing completion Date for below sale order is changed by production.</strong></p><br/>
					<p>Sale order No-: <b>%s</b> </p>
					<p>Manufacturing Ref-: <b>%s</b> </p>
		    			<p>Product:<b>%s</b>
		    			<p>Quantity:<b>%s %s</b>
                                        <p>Requested completion date: <b>%s</b> </p>
                                        <p>Previous completion date:<b> %s</b> </p>
                                        <p>New production completion date: <b>%s</b> </p>
                                        <p>Production starting date: <b>%s</b> </p>
                                        <p>By:<b> %s</b> </p>
		    			<p>Remarks:<b>%s</b> </p>
				</p>
				</div>"""%(str(self.n_line_id.order_id.name) or '',str(self.env[model_name].browse(model_id).name) or '',str(self.n_line_id.product_id.name) or ''+str(self.n_line_id.product_id.default_code) or '',str(self.env[model_name].browse(model_id).product_qty) or '',str(self.env[model_name].browse(model_id).product_uom.name) or '',str(self.env[model_name].browse(model_id).n_client_date) or '',self.n_prevoiusdate1 or 'No Previous Date',n_date,str(self.env[model_name].browse(model_id).date_planned) or '' ,self.env.user.name or '',self.n_reason or '')
                           
                            print "body_htmlbody_htmlbody_html",model_name,model_id

			    body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, model_name,model_id, context=self._context)
			    temp_id.write({'subject':subject,'body_html': body_html, 'email_to' : recipient_partners, 'email_from': self.env.user.login})
			    temp_id.send_mail(model_id)
		return {'type':'ir.actions.act_window_close'}

#CH_N043

#CH_N057 >>add model to get mrp quantity change
class change_production_qty(models.Model):
    _inherit = 'change.production.qty'

    n_reason =fields.Text("Note") 

    @api.multi
    def change_prod_qty(self):
	for rec in self:
		record_id = self._context and self._context.get('active_id',False)
		self.env['mrp.production'].sudo().browse(record_id).write({'product_qty':rec.product_qty})
		self.env['mrp.production'].sudo().browse(record_id).message_post(body='	   Quantity Update -: '+str(rec.product_qty)+"\n	   -: "+rec.n_reason)
	return {'type':'ir.actions.act_window_close'}
#CH_N057<<<s

#CH_N045 add table to store delivery date
class MrpDeliveryDate(models.Model):
	_name = "mrp.delivery.date"
	_order = "id desc"

	@api.multi
	#@api.depends('n_manu_date')
	def _get_dispatch_date(self):
		for rec in self:
			if rec.n_dispatch_date_d:
				rec.n_dispatch_date= rec.n_dispatch_date_d
				n_days=rec.n_transit_time
				rec.n_schdule_date = datetime.strptime(rec.n_dispatch_date_d,'%Y-%m-%d')+timedelta(days=int(n_days))
			elif rec.n_manu_date:
				n_new_date = datetime.strptime(rec.n_manu_date,'%Y-%m-%d')+timedelta(days=1)
				rec.n_dispatch_date = n_new_date
				n_days=rec.n_transit_time+1
				rec.n_schdule_date = datetime.strptime(rec.n_manu_date,'%Y-%m-%d')+timedelta(days=int(n_days))
			else:
				if rec.n_line_id:
					n_date=rec.n_line_id.n_client_date if rec.n_line_id.n_client_date else str(date.today())
					rec.n_dispatch_date=datetime.strptime(n_date,'%Y-%m-%d')-timedelta(days=int(rec.n_line_id.n_transit_time))
					rec.n_schdule_date =rec.n_line_id.n_client_date

	n_line_id1 = fields.Many2one('sale.order.line','sale order')	#CH_N047 to store one one record
	n_line_id = fields.Many2one('sale.order.line','sale order')	#CH_N047 make relation fields
	n_manu_date = fields.Date(string="Manufacture Complete Date",related='n_line_id.n_manu_date')
    	n_transit_time = fields.Integer(string="Transit Time",related='n_line_id1.n_transit_time')
    	n_dispatch_date = fields.Date(string="Dispatch Date",compute='_get_dispatch_date')
	n_dispatch_date_d = fields.Date(string="Dispatch Date")
	n_schdule_date = fields.Date(string="Client receving Date",compute='_get_dispatch_date')
    	n_delivery_date = fields.Date(string="Client Received On")
	n_type  = state = fields.Selection([('partial','Partial Delivery'),('full','Full delivery')],'Type',default='full')
	n_status  = state = fields.Selection([('draft','System Calculated'),('waiting','Waiting for Validate'),('r_t_dispatch','Ready To Dispatch'),('dispatch','Dispatched'),('delivered','Delivered')],'Status',default='draft')
	n_reason  = fields.Text("Note") #CH_N054 add field to store
	#history_id = fields.Many2one('delivery_date_history','Delivery Date History')
	n_picking_id =fields.Many2one('stock.picking','Delivery Order')
	n_scheduled_id = fields.One2many('schedule.delivery.date.history','delivery_id','Schedule Delivery Date History')
#CH_N045

	@api.model
	def create(self,vals):
		print "nnnnnnnnnnnnnnnnnnnn++++++++++++++++++++++++++++++++++++++++++++++++",vals,self._context
		return super(MrpDeliveryDate,self).create(vals)
		
#CH_N055 add table to store delivery date change history
class ScheduleDeliveryDateHtory(models.Model):
	_name = "schedule.delivery.date.history"
	_order = "id desc"

	n_line_id = fields.Many2one('sale.order.line','sale order')
	n_prevoiusdate = fields.Datetime(string='Prevoius Date')
	n_prevoiusdate1 = fields.Datetime(string='Prevoius Date')		#CH_N055 for reference
	n_nextdate = fields.Datetime(string='Next Schedule Date')
	n_status  = fields.Selection([('scheduled','Scheduled'),('validate','Validate'),('schedule_dispatch','Scheduled Dispatch'),('dispatch','Dispatch')],'Status')
	state = fields.Selection([('draft','Draft'),('done','Done')],'State',default='draft')
	n_user_id = fields.Many2one('res.users','Aproved By')
	n_reason  = fields.Text("Reason for Date Change")
	n_picking_id =fields.Many2one('stock.picking','Delivery Order')
	delivery_id = fields.Many2one('mrp.delivery.date','Delivery Date History')

	@api.model
	def create(self,vals):
		if vals.get('n_nextdate') and str(vals.get('n_nextdate')) < str(date.today()-timedelta(days=5)):
			raise UserError(_('Please Enter Proper Date..'))
		if vals.get('n_status') == 'schedule_dispatch':
			picking_id=self.env['stock.picking'].search([('id','=',vals.get('n_picking_id'))])
			if picking_id.min_date > vals.get('n_nextdate'):
				raise UserError(_('You are not allow to Dispatch less than Schedule date.'))
		return super(ScheduleDeliveryDateHtory,self).create(vals)

	@api.multi
	def save(self):
		status='waiting'
		if self.n_status == 'scheduled':
			self.n_picking_id.min_date=self.n_nextdate
			if self.n_picking_id.dispatch_date < self.n_nextdate:
				self.n_picking_id.dispatch_date = False 
		if self.n_status == 'schedule_dispatch':
			self.n_picking_id.dispatch_date=self.n_nextdate
			status='r_t_dispatch'
		if self.n_status == 'dispatch':
			status='dispatch'

		self.state ='done'
		for rec in self.n_picking_id:
		    if rec.pack_operation_product_ids:
			for line in rec.pack_operation_product_ids:
				if line.n_sale_order_line:
					n_type='partial'
					qty= line.qty_done if line.qty_done else line.product_qty  
					for n_line in line.n_sale_order_line.res_ids:
						if n_line.n_status in ('delivered','r_t_dispatch'):
							qty += n_line.res_qty 
					if line.n_sale_order_line.product_uom_qty <= qty:
						n_type='full'
					
					serch_ids=self.env['mrp.delivery.date'].search([('n_picking_id','=',self.n_picking_id.id)
										,('n_line_id1','=',line.n_sale_order_line.id)])
					if not serch_ids:
						m_ids=self.env['mrp.delivery.date'].create({'n_dispatch_date_d':self.n_nextdate,
										'n_status':status,
										'n_picking_id':self.n_picking_id.id,'n_type':n_type,
										'n_line_id1':line.n_sale_order_line.id})
						self.delivery_id=m_ids.id
					if serch_ids:
						serch_ids.write({'n_dispatch_date_d':self.n_nextdate})
						self.delivery_id=serch_ids[0].id
					line.n_sale_order_line._get_schedule_date()
		    else:
			for line in rec.move_lines:
				if line.n_sale_line_id:
					n_type='partial'
					qty=line.product_qty
					for n_line in line.n_sale_line_id.res_ids:
						if n_line.n_status in ('delivered','r_t_dispatch'):
							qty += n_line.res_qty 
					if line.n_sale_line_id.product_uom_qty <= qty:
						n_type='full'
					serch_ids=self.env['mrp.delivery.date'].search([('n_picking_id','=',self.n_picking_id.id)
										,('n_line_id1','=',line.n_sale_line_id.id)])
					if not serch_ids:
						m_ids1=self.env['mrp.delivery.date'].create({'n_dispatch_date_d':self.n_nextdate,
										'n_status':status,
										'n_picking_id':self.n_picking_id.id,'n_type':n_type,
										'n_line_id1':line.n_sale_line_id.id})
						self.delivery_id=m_ids1.id
					if serch_ids:
						serch_ids.write({'n_dispatch_date_d':self.n_nextdate})
						self.delivery_id=serch_ids[0].id
					line.n_sale_line_id._get_schedule_date()

		#on saving it will create entry in delivery date history table
                temp_id = self.env.ref('gt_order_mgnt.email_template_for_delivery_date_changed')
                if temp_id:
		       user_obj = self.env['res.users'].browse(self.env.uid)
		       recipient_partners=[]
		       if str(self.n_picking_id.sale_id.user_id.login) != str(user_obj.partner_id.email):
				recipient_partners=[str(self.n_picking_id.sale_id.user_id.login)]
		       group = self.env['res.groups'].search([('name', '=', 'Sales Support Email')])
		       for recipient in group.users:
			   if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
		    	   	recipient_partners.append(recipient.login)

		       recipient_partners = ",".join(recipient_partners)
		       
		       body ='<ul><li><b> Delivery No.   </b> : '+str(self.n_picking_id.name) +'</li></ul>'
		       body +='<ul><li><b> Sale Order No. </b>: '+str(self.n_picking_id.sale_id.name) +'</li></ul>'
		       body +='<ul><li><b> Changed By  </b> : '+str(self.env.user.name) +'</li></ul>'
                       if self.n_prevoiusdate1:
                          body +='<ul><li><b> Old Scheduled Date</b> : {}'.format(str(self.n_prevoiusdate1))+'</li></ul>'
                       body +='<ul><li><b> New Scheduled Date    </b> : '+str(self.n_nextdate) +'</li></ul>'
                       body +='<ul><li><b> Reason     </b> : '+str(self.n_reason) +'</li></ul>'  
		       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'stock.picking',self.n_picking_id.id, context=self._context)
		       if recipient_partners:
		       		temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email})
                       		if user_obj.partner_id.id != self.n_picking_id.sale_id.user_id.id:
		          		temp_id.send_mail(self.n_picking_id.id)
                       		else:
                          		self.n_picking_id.message_post(body=body)

		return {'type':'ir.actions.act_window_close'}

#CH_N055

