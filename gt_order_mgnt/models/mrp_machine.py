
from openerp.addons import decimal_precision as dp
from openerp import models, fields, api,_
import time
import datetime
from datetime import datetime
from openerp import models, fields, api, exceptions, _

from datetime import datetime, date, time, timedelta
from urlparse import urljoin
from urllib import urlencode
from time import gmtime, strftime
import math
from openerp.exceptions import UserError, ValidationError
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)
import sys

class MachineMaintenance(models.Model):
    _name ='mrp.work.order.maintenance'
    production_id=fields.Many2one('mrp.production','Manufacturing No.' ,readonly="1")
    workorder_id=fields.Many2one('mrp.production.workcenter.line', 'Work Order No.', readonly="1")
    machine_id=fields.Many2one('machinery',string="Machine", readonly="1")
    required_date=fields.Datetime('Required Date')
    urgent=fields.Boolean('Urgent Required')
    note=fields.Text('Remark')
    maintenance_type=fields.Selection([('regular','Regular'),('breakdown','Machine Breakdown')],
                    string='Maintenance Type', required=True)
    @api.multi
    def send_maintenancerequest(self):
        for record in self:
            main=self.env['machine.maintenance'].create({'production_id':record.production_id.id,'workorder_id':record.workorder_id.id,'requested_by':self.env.user.id,
                                      'machine_id':record.machine_id.id, 'required_date':record.required_date,
                                       'urgent':record.urgent, 'note':record.note, 
                                        'maintenance_type':record.maintenance_type,'state':'new'})
            record.workorder_id.maintenance_id=main.id
            res=dict(self.fields_get(allfields=['maintenance_type'])['maintenance_type']['selection'])[record.maintenance_type]
            if record.maintenance_type == 'breakdown':
               record.workorder_id.wk_planned_status='maintenace'
               record.workorder_id.machine_breakdown=True
               record.workorder_id.action_pause()
               record.workorder_id.signal_workflow('button_pause')
               if record.workorder_id.machine.status in ('active', 'pause'):
                  record.workorder_id.machine.status='outofservice'
            temp_id = self.env.ref('gt_order_mgnt.email_template_maintenance_department')
	    if temp_id:
	       recipient_partners=str(self.env.user.login)
	       group = self.env['res.groups'].search([('name', '=', 'User'),('category_id.name','=','Manufacturing')])
	       for recipient in group.users:
	    	   recipient_partners += ","+str(recipient.login)
	       user_obj = self.env['res.users'].browse(self.env.uid)
	       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			'model': 'machine.maintenance',
			'view_type': 'form',
			'id': main.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	       text_link = _("""<a href="%s">%s</a> """) % (url,main.name)
               body='<b>Maintenance Request  Sent:</b>'
               body +='<ul><li> Maintenance No.    : '+str(text_link) +'</li></ul>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> Work Order No.  : '+str(record.workorder_id.name) +'</li></ul>'
               body +='<ul><li> Machine   : '+str(record.machine_id.name) +'</li></ul>'
               body +='<ul><li> Sent Date   : '+str(date.today()) +'</li></ul>'
               body +='<ul><li> Maintenance Type   : '+str(res) +'</li></ul>'
               body +='<ul><li> Remark      : '+str(self.note) +'</li></ul>' 
               record.workorder_id.message_post(body=body)
               record.production_id.message_post(body=body)
	       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'machine.maintenance',main.id, context=self._context)
				
	       temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email})
	       temp_id.send_mail(main.id)
	       
class MachineMaintenance(models.Model):
    _name ='machine.maintenance'
    _inherit=['mail.thread']
    name=fields.Char('Request Number', readonly="1")
    requested_by=fields.Many2one('res.users', 'Requested By', readonly="1")
    requested_date=fields.Date('Requested Date', default=fields.Datetime.now, readonly="1")
    production_id=fields.Many2one('mrp.production','Manufacturing No.' ,readonly="1")
    workorder_id=fields.Many2one('mrp.production.workcenter.line', 'Work Order No.', readonly="1")
    note=fields.Text('Remark')
    user_ids=fields.Many2many('res.users', string='Responsible')
    schedule_date=fields.Datetime('Schedule Start Date')
    finish_date=fields.Datetime('Maintenance Finish Date')
    reason=fields.Text('Reason')
    required_date=fields.Datetime('Required Date')
    urgent=fields.Boolean('Urgent Required')
    machine_id=fields.Many2one('machinery',string="Machine", readonly="1")
    state = fields.Selection([
        ('new', 'New Request'),
        ('progress', 'In Progress'),
        ('repaired', 'Repaired'),
        ('scrap', 'Scrap'),
        ('cancel', 'Cancel'),
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange')
    maintenance_type=fields.Selection([('regular','Regular'),('breakdown','Machine Breakdown')], 
         string='Maintenance Type', readonly=True)
    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('machine.maintenance') or 'New'
        result = super(MachineMaintenance, self).create(vals)
        return result
    @api.multi
    def write (self, vals):
       for record in self:
         if vals.get('schedule_date') or vals.get('finish_date') or vals.get('reason') or vals.get('user_ids'):
           temp_id = self.env.ref('gt_order_mgnt.email_template_maintenance_department')
	   if temp_id:
	       recipient_partners=str(self.env.user.login)
               recipient_partners1=''
	       group = self.env['res.groups'].search([('name', '=', 'User'),('category_id.name','=','Manufacturing')])
	       for recipient in group.users:
	    	   recipient_partners += ","+str(recipient.login)
                   recipient_partners1 += str(recipient.login)
	       user_obj = self.env['res.users'].browse(self.env.uid)
	       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			'model': 'machine.maintenance',
			'view_type': 'form',
			'id': self.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	       text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
               body='<b>Maintenance Request  Planned:</b>'
               body +='<ul><li><b> Maintenance No.   </b> : '+str(text_link) +'</li></ul>'
               body +='<ul><li><b> Production No. </b>: '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li><b> Work Order No.  </b>: '+str(record.workorder_id.name) +'</li></ul>'
               body +='<ul><li><b> Machine   </b>: '+str(record.machine_id.name) +'</li></ul>'
               body +='<ul><li><b> Responsible Persons   </b>: '
               for user in record.user_ids:
                   body +=str(user.name) +','
               body +='</li></ul>'
               body +='<ul><li><b> Schedule Start Date  </b> : '+str(record.schedule_date) +'</li></ul>'
               body +='<ul><li><b> Maintenance Finish Date  </b> : '+str(record.finish_date) +'</li></ul>'
               body +='<ul><li><b> Requested By  </b> : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li><b> Reason     </b> : '+str(self.reason) +'</li></ul>' 
	       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'machine.maintenance',self.id, context=self._context)
	       temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email}) 
	       temp_id.send_mail(self.id)
       return super(MachineMaintenance, self).write(vals)
       
    @api.multi
    def send_request(self):
        for record in self:
            record.workorder_id.machine_breakdown=True
            record.state ='new'
            body='<b>Maintenance Request  Sent:</b>'
            body +='<ul><li> Maintenance No.    : '+str(record.name) +'</li></ul>'
            body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
            body +='<ul><li> Work Order No.  : '+str(record.workorder_id.name) +'</li></ul>'
            body +='<ul><li> Machine   : '+str(record.machine_id.name) +'</li></ul>'
            body +='<ul><li> Sent Date   : '+str(date.today()) +'</li></ul>'
            body +='<ul><li> Reason      : '+str(self.reason) +'</li></ul>' 
            record.workorder_id.message_post(body=body)
            record.production_id.message_post(body=body)
            temp_id = self.env.ref('gt_order_mgnt.email_template_maintenance_department')
	    if temp_id:
	       recipient_partners=str(self.env.user.login)
               rec=[]
	       group = self.env['res.groups'].search([('name', '=', 'User'),('category_id.name','=','Manufacturing')])
	       for recipient in group.users:
	    	   recipient_partners += ","+str(recipient.login)
                  
	       user_obj = self.env['res.users'].browse(self.env.uid)
	       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			'model': 'machine.maintenance',
			'view_type': 'form',
			'id': self.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	       text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
               body='<b>Maintenance Request  For Machine:</b>'
               body +='<ul><li><b> Maintenance No.   </b> : '+str(text_link) +'</li></ul>'
               body +='<ul><li><b> Production No. </b>: '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li><b> Work Order No.  </b>: '+str(record.workorder_id.name) +'</li></ul>'
               body +='<ul><li><b> Machine   </b>: '+str(record.machine_id.name) +'</li></ul>'
               body +='<ul><li><b> Sent Date  </b> : '+str(date.today()) +'</li></ul>'
               body +='<ul><li><b> Requested By  </b> : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li><b> Reason     </b> : '+str(self.note) +'</li></ul>' 
	       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'machine.maintenance',self.id, context=self._context)
				
	       temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email, })
	       temp_id.send_mail(self.id)
            
    @api.multi
    def request_cancel(self):
        for record in self:
            record.state ='cancel'
            record.workorder_id.machine_breakdown=False
            record.workorder_id.wk_planned_status='fully'
            body='<b>Maintenance Request Cancelled:</b>'
            body +='<ul><li> Maintenance No.    : '+str(record.name) +'</li></ul>'
            body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
            body +='<ul><li> Work Order No.  : '+str(record.workorder_id.name) +'</li></ul>'
            body +='<ul><li> Machine   : '+str(record.machine_id.name) +'</li></ul>'
            body +='<ul><li> Cancel Date   : '+str(date.today()) +'</li></ul>'
            body +='<ul><li> Reason      : '+str(self.note) +'</li></ul>' 
            record.workorder_id.message_post(body=body)
            record.production_id.message_post(body=body)
            record.message_post(body=body)

    @api.multi
    def request_progress(self):
        for record in self:
            record.state ='progress'
            temp_id = self.env.ref('gt_order_mgnt.email_template_maintenance_department')
	    if temp_id:
	       recipient_partners=str(self.env.user.login)
	       group = self.env['res.groups'].search([('name', '=', 'User'),('category_id.name','=','Manufacturing')])
	       for recipient in group.users:
	    	   recipient_partners += ","+str(recipient.login)
	       user_obj = self.env['res.users'].browse(self.env.uid)
	       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			'model': 'machine.maintenance',
			'view_type': 'form',
			'id': self.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	       text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
               body='<b> Start working on Maintenance Request:</b>'
               body +='<ul><li><b> Maintenance No.   </b> : '+str(text_link) +'</li></ul>'
               body +='<ul><li><b> Production No. </b>: '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li><b> Work Order No.  </b>: '+str(record.workorder_id.name) +'</li></ul>'
               body +='<ul><li><b> Machine   </b>: '+str(record.machine_id.name) +'</li></ul>' 
               body +='<ul><li><b> Responsible Persons   </b>: '
               for user in record.user_ids:
                   body +=str(user.name) +','
               body +='</li></ul>'
               body +='<ul><li><b> Start Date  </b> : '+str(date.today()) +'</li></ul>'
               body +='<ul><li><b> Start By  </b> : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li><b> Schedule Start Date  </b> : '+str(record.schedule_date) +'</li></ul>'
               body +='<ul><li><b> Maintenance Finish Date  </b> : '+str(record.finish_date) +'</li></ul>'
               body +='<ul><li><b> Reason     </b> : '+str(self.reason) +'</li></ul>'
               record.workorder_id.message_post(body=body)
               record.production_id.message_post(body=body) 
	       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'machine.maintenance',self.id, context=self._context)
				
	       temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email})
	       temp_id.send_mail(self.id)

    @api.multi
    def request_repaired(self):
        for record in self:
            record.state ='repaired'
            record.workorder_id.machine_breakdown=False
            record.workorder_id.wk_planned_status='fully'
            record.machine_id.status='inactive'
            temp_id = self.env.ref('gt_order_mgnt.email_template_maintenance_department')
	    if temp_id:
	       recipient_partners=str(self.env.user.login)
	       group = self.env['res.groups'].search([('name', '=', 'User'),('category_id.name','=','Manufacturing')])
	       for recipient in group.users:
	    	   recipient_partners += ","+str(recipient.login)
	       user_obj = self.env['res.users'].browse(self.env.uid)
	       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	       query = {'db': self._cr.dbname}
	       fragment = {
			'model': 'machine.maintenance',
			'view_type': 'form',
			'id': self.id,
			}
	       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	       text_link = _("""<a href="%s">%s</a> """) % (url,record.name)
               body='<b>Machine Repaired:</b>'
               body +='<ul><li><b> Maintenance No.   </b> : '+str(text_link) +'</li></ul>'
               body +='<ul><li><b> Production No. </b>: '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li><b> Work Order No.  </b>: '+str(record.workorder_id.name) +'</li></ul>'
               body +='<ul><li><b> Machine   </b>: '+str(record.machine_id.name) +'</li></ul>'
               body +='<ul><li><b> Responsible Persons   </b>: '
               for user in record.user_ids:
                   body +=str(user.name) +','
               body +='</li></ul>'
               body +='<ul><li><b> Sent Date  </b> : '+str(date.today()) +'</li></ul>'
               body +='<ul><li><b> Requested By  </b> : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li><b> Reason     </b> : '+str(self.note) +'</li></ul>' 
               record.workorder_id.message_post(body=body)
               record.production_id.message_post(body=body)
	       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body, 'machine.maintenance',self.id, context=self._context)
				
	       temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email})
	       temp_id.send_mail(self.id)

    @api.multi
    def request_scrap(self):
        for record in self:
            record.state ='scrap'
            body='<b>Maintenance Request Scraped:</b>'
            body +='<ul><li> Maintenance No.    : '+str(record.name) +'</li></ul>'
            body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
            body +='<ul><li> Work Order No.  : '+str(record.workorder_id.name) +'</li></ul>'
            body +='<ul><li> Machine   : '+str(record.machine_id.name) +'</li></ul>'
            body +='<ul><li> Finish Date   : '+str(record.finish_date) +'</li></ul>'
            body +='<ul><li> Scraped Date   : '+str(date.today()) +'</li></ul>'
            body +='<ul><li> State      : '+str(self.state) +'</li></ul>' 
            body +='<ul><li> Reason      : '+str(self.reason) +'</li></ul>' 
            record.workorder_id.message_post(body=body)
            record.production_id.message_post(body=body)

class MrpWorkcenterUnit(models.Model):
    _name = 'mrp.workcenter.unit'
    name=fields.Char('Name')
    
class MrpWorkcenterProcess(models.Model):
    _name = 'mrp.workcenter.process'
    name=fields.Char()
    process_type=fields.Selection([('raw','Raw Material'),('film','Film (Extrusion)'),('cutting','Cutting'),('ptube', 'Printing in Tube'), ('psheet', 'Printing in Sheet'),('other', 'Others'),('injection', 'Injection')], string='Type')
    machine_type=fields.Many2one('machinery.type')
    machine = fields.Many2one('machinery', string='Machine')
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    cate_id=fields.Many2one('product.category')
    unit_id=fields.Many2one('product.uom',string='Unit')
    code=fields.Char('Sequence Code')
    
class MrpWorkcenter(models.Model):
    _name = "mrp.workcenter"
    _inherit = ['mrp.workcenter','mail.thread']

    machine = fields.Many2one('machinery', string='Machine')
    machine_ids = fields.Many2many('machinery', string='Machine')
    machine_type_ids=fields.Many2many('machinery.type', string="Machine Type")
    product_uom_id=fields.Many2one('product.uom',string='Unit')
    unit_id=fields.Many2one('mrp.workcenter.unit',string='Unit')
    unit_ids=fields.Many2one('product.uom',string='Unit')
    product_ids=fields.Many2many('product.product', string='Products')
    work_ids=fields.One2many('mrp.production.workcenter.line', 'workcenter_id', string='Schedule Detail')
    #capacity_per_cycle=fields.Float(compute='capacity_time_option')
    capacity_per_cycle_time=fields.Float()
    process_id=fields.Many2one('mrp.workcenter.process',string="Process Type")
    cate_id=fields.Many2one('product.category')
    product_qty=fields.Float("product Qty")
    print_option=fields.Selection([('tube','In Tube'),('sheet','In Sheet')], string='Print Option')
    time_option=fields.Selection([('1','1x'),('2','2x'),('3','3x'),('4', '4x'),
                                        ('5', '5x')], string='Production Output', default='1') 
    
    shift_time=fields.Float("Shift Time")

    @api.multi
    @api.onchange('resource_type')
    def resource_human(self):
        for record in self:
            if record.resource_type == 'user':
               human_machine=self.env['machinery.type'].search([('is_human','=',True)])
               if human_machine:
                  lst=[]
                  for human in human_machine:
                      lst.append(human.id)
                  record.machine_type_ids=[(6,0,lst)]
            else:
                record.machine_type_ids=[]
    '''@api.multi
    @api.onchange('machine')
    def Machine_efficiency(self):
        for record in self:
            if record.machine:
               record.time_efficiency=record.machine.time_efficiency
               record.time_start=record.machine.time_start
               record.time_stop=record.machine.time_stop'''
   
  
    @api.multi
    @api.onchange('process_id')
    def processUnit(self):
        for record in self:
            if record.process_id.process_type == 'raw':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
            if record.process_id.process_type == 'film':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
            if record.process_id.process_type == 'cutting':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
            if record.process_id.process_type == 'ptube':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
            if record.process_id.process_type == 'psheet':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
            if not record.process_id.process_type and record.process_id.cate_id.cat_type == 'injection':
               record.machine_type=record.process_id.machine_type.id
               record.unit_ids=record.process_id.unit_id.id
               
class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    machine = fields.Many2one('machinery', string='Machine')
    machine_type_ids=fields.Many2many('machinery.type', string="Machine Type")
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    cycle_nbr= fields.Float('Number of Cycles', required=True, default=0,
            help="Number of iterations this work center has to do in the specified operation of the routing.")
   
    @api.multi
    @api.onchange('workcenter_id',)
    def Routename(self):
        for record in self:
            if record.workcenter_id:
               record.name =str(record.workcenter_id.name)
            
class MrpWorkorderMachinePause(models.Model):
    _name = 'mrp.order.machine.pause'
    production_id=fields.Many2one('mrp.production', string='Current Manufacturing No.')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Work Order No.')
    product_id=fields.Many2one('product.product', string='Product')
    machine = fields.Many2one('machinery', string='Current Machine')
    user_id=fields.Many2one('res.users',string='User Name' ,default=lambda self: self.env.user)
    reason=fields.Text('Remark')
    bool_check=fields.Boolean('Bool')
    document_name=fields.Char()
    document=fields.Binary('Document')
    pause_reason=fields.Selection([('shift',' Shift End'),('machine','Maintenance'), 
                                  ('plan','Plan Change'),('other','Others')], default='shift')
    date_start=fields.Datetime('Start Time', default=fields.Datetime.now)
    date_end=fields.Datetime('End Time')
    duration=fields.Float('Duration', compute='duration_cal')
    state=fields.Selection([('pause','Pause'),('resume','Pause(c)'),('play','Play'),('playc','Play(c)'),
                           ('hold','Hold'), ('holdc','Hold(c)')], string='State', default='pause') 
   
    @api.multi
    @api.depends('date_start','date_end')
    def duration_cal(self):
        for record in self:
            if record.date_start and record.date_end: 
               start = datetime.strptime(record.date_start, "%Y-%m-%d %H:%M:%S")
               end = datetime.strptime(record.date_end, "%Y-%m-%d %H:%M:%S")
               diff = end - start
               duration = float(diff.days)* 24 + (float(diff.seconds) / 3600)
               record.duration=round(duration, 2) 
 
    @api.multi
    def button_cancel(self):
        for record in self:
            record.order_id.state ='startworking'
    @api.multi
    def OrderPause(self):
        for record in self:
            if record.order_id:
               play=self.env['mrp.order.machine.pause'].search([('state','=','play'),('order_id','=',record.order_id.id)], limit=1)
               if play:
                  play.state ='playc'
                  play.date_end=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
               attachment=[]
               res=dict(self.fields_get(allfields=['pause_reason'])['pause_reason']['selection'])[record.pause_reason]
               body='<b>Work Order Pause:</b>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> Work Order No. : '+str(record.order_id.name) +'</li></ul>'
               body +='<ul><li> User Name      : '+str(record.user_id.name) +'</li></ul>'  
               body +='<ul><li> Pause Time     : '+str(datetime.now() + timedelta(hours=4)) +'</li></ul>' 
               body +='<ul><li> Pause Reason   : '+str(res) +'</li></ul>'
               body +='<ul><li> Remark         : '+str(record.reason) +'</li></ul>'
               attachment.append((record.document_name,record.document)) 
               record.order_id.message_post(body=body)
               record.production_id.message_post(body=body)
               record.bool_check =True
               record.machine.status ='pause'
               record.order_id.action_pause()
               record.order_id.signal_workflow('button_pause')

class MrpWorkorderMachineProduce(models.Model):
    _name = 'mrp.order.machine.produce'
    @api.multi
    @api.depends('order_id')
    def compute_first_wo(self):
        for record in self: 
            if record.order_id:
                print "recorf,mjk,nk",record.order_id.sequence,type(record.order_id.sequence)
                if record.order_id.sequence==1:
                   record.first_order=True
                else:
                   record.first_order=False
    
    req_product_qty=fields.Float('Required',related='batch_id.req_product_qty',store=True)

    first_order = fields.Boolean('First Order',compute='compute_first_wo')

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.order_id:
            return {'domain': {'employee_ids': [('id', 'in', self.order_id.employee_ids.ids)]}}
        
    @api.onchange('supplier_btc_no')
    def _onchange_supplier_btc_no(self):
        batches=[]
        if self.production_id:
            rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',self.production_id.id)])
            print "rm_idsrm_idsrm_ids",rm_ids
            if rm_ids:
                for each_rm in rm_ids:
                    pick_ids=self.env['stock.picking'].search([('material_request_id','=',each_rm.id),('state','=','done')])
                    print "pick_idspick_idspick_ids",pick_ids
                    if pick_ids:
                        for each in pick_ids:
                            if each.store_ids:
                                for each_store in each.store_ids:
                                    for each_batches in each_store.batches_ids:
                                        batches.append(each_batches.batch_number.id)
            return {'domain': {'supplier_btc_no': [('id', 'in', batches)]}}

    
    @api.depends('batch_id')
    def _check_txr(self):
        print "check ro--------------------------"
        for rec in self:
            if rec.batch_id.batch_tfred==True:
                print "yes matching----------------------"
                rec.check_txr=True
            print "selfkjhjstet tracjet======================================",rec.check_txr
            
    @api.depends('batch_id')
    def _check_produced_qty(self):
        print "check ro--------------------------"
        for rec in self:
            if rec.batch_id:
                print "yes matching--------------s--------"
                rec.produced_qty=rec.batch_id.convert_product_qty
            print "selfkjhjstet tracjet======================================",rec.produced_qty


    @api.model
    def _get_uom_id(self):
        return self.env["product.uom"].search([('name','=','Kg')], limit=1, order='id')[0]
    check_txr=fields.Boolean('Check Batch Transfer',compute='_check_txr') 

    product_qty=fields.Float('Product Qty')
#    produced_qty=fields.Float('Produced Qty',compute='_check_produced_qty')
    produced_qty=fields.Float('Produced Qty')
    production_id=fields.Many2one('mrp.production', string='Current Manufacturing No.')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Work Order No.')
    previous_order_id=fields.Many2one('mrp.production.workcenter.line', string='Previous Work Order No.')
    previous_order_ids=fields.Many2many('mrp.production.workcenter.line', string='Previous Work Order No.')
    product_id=fields.Many2one('product.product', string='Product')
    machine = fields.Many2one('machinery', string='Current Machine')
    bool_check=fields.Boolean('Bool')
    remark=fields.Text('Remark')
    document_name=fields.Char()
    batch_id=fields.Many2one('mrp.order.batch.number',string='Batch No.')
    previous_batch_id=fields.Many2one('mrp.order.batch.number',string='Previous Batch No.')
    previous_batch_qty=fields.Float('Previous Batch Produced Qty',related='previous_batch_id.remain_used_qty')
    previous_uom_id=fields.Many2one('product.uom',related='previous_batch_id.uom_id')
    previous_batch_ids=fields.Many2many('mrp.order.batch.number',string='Previous Batch No.')
#    document=fields.Binary('Document')
    document=fields.Many2many('ir.attachment','machine_produce_document_rel','produce_id','doc_id','Document')

    uom_id=fields.Many2one('product.uom')
    produce_date=fields.Datetime('Date', default=fields.Datetime.now)
    wastage_bool=fields.Boolean('Any Wastage')
    wastage_qty=fields.Float('Wastage Qty')
    wastage_uom=fields.Many2one('product.uom', default=_get_uom_id)
    wastage_reason=fields.Text('Reason')
    user_id=fields.Many2many('res.users', string='User Group')
    employee_ids=fields.Many2many('hr.employee', string='Operators Name')
    supplier_btc_no=fields.Many2many('mrp.order.batch.number', string='Supplier Batch Number')
    supplier_batch_no=fields.Char('Supplier Batch No.')
    produced_line_id=fields.One2many('mrp.order.machine.produce.line','produced_id',compute='checkproduced_qty',store=True)
    warning_bool=fields.Boolean('Give warning for product qty', default=False)

    @api.multi
    def confirmation(self):
      for record in self:
#        if record.check_txr==True:
#            if record.batch_id.transferred_qty!=record.produced_qty:
#              raise UserError("You are not allowed to make changes to this batch produced qty as the batch is already transferred!!")
        wast_qty=00.0
        print "recordrecordrecordrecord",record
        if record.wastage_qty:
                  if record.previous_batch_id.uom_id.id !=record.wastage_uom.id:
		     if record.previous_batch_id.uom_id.name =='Pcs':
		        wast_qty=math.ceil(record.wastage_qty * record.product_id.weight) if record.wastage_qty else 0.0
		     if record.previous_batch_id.uom_id.name =='m': 
                        qty_m=(record.order_id.wk_required_qty/record.order_id.qty)
                        wast_qty=qty_m * record.wastage_qty
                  else:
		       wast_qty=record.wastage_qty   
        produce_qty=0.0
        if record.previous_batch_id:
                  if record.previous_batch_id.uom_id.id != record.uom_id.id:
                     if record.uom_id.name =='Pcs':
		        produce_qty=math.ceil(record.produced_qty*record.product_id.weight) if record.product_qty else 0.0   
                     if record.uom_id.name =='m': 
                        qty_m=(record.order_id.qty/record.order_id.wk_required_qty)
                        produce_qty=qty_m * record.produced_qty

                  else:
                       produce_qty=record.produced_qty
                  '''if record.previous_batch_id.remain_used_qty < (produce_qty + wast_qty):
                        raise UserError(_("You can not Produced Qty(%s)(%s) because your selected Previous Batch Remaining Qty(%s)(%s).")%(round((produce_qty + wast_qty),2),(record.previous_batch_id.uom_id.name),round(record.previous_batch_id.remain_used_qty,2) ,(record.previous_batch_id.uom_id.name)))'''
      	if record.produced_qty <=0:
      		raise UserError("Enter Proper Produce Quantity")
      	elif record.wastage_qty <0:
      		raise UserError("Enter Proper Wastage Quantity")
	if record.produced_qty==0 and record.wastage_qty ==0:
		raise UserError("Please Enter Produce quantity or Wastage quantity")
        if record.produced_line_id:
                for line in record.produced_line_id:
                    product=record.production_id.product_lines.search([('product_id','=',line.product_id.id),('production_id','=',record.production_id.id)])
                    '''if round(product.receive_qty -product.consumed_qty,2)  < round(line.product_qty,2):
                       raise UserError(_("Raw Material(%s) Received Qty(%s) is not Enough ...")%((product.product_id.name),round(product.receive_qty -product.consumed_qty, 2)))'''
        context=self._context.copy()
        context.update({'confirm':True})
        print "contextcontextcontext",context
        self.bool_check =True 
        return {"type": "ir.actions.do_nothing"}    
        return {'context':context,"type": "ir.actions.do_nothing"}    
 
    @api.multi
    @api.depends('produced_qty','wastage_qty')
    def checkproduced_qty(self):
        for record in self:
            print"sdfsdfsdfsdfsdf",self._context
            wo_id=self.env['mrp.production.workcenter.line'].browse(self._context.get('default_order_id',False))
            wastage_qty=0.0
            if record.wastage_qty:
               if record.uom_id.id !=record.wastage_uom.id:
                  if record.uom_id.name =='Pcs':
                      wastage_qty=math.ceil(record.wastage_qty/record.product_id.weight) if record.wastage_qty else 0.0
                  if record.uom_id.name =='m':
                     qty_m=(wo_id.wk_required_qty/record.order_id.qty)
                     wastage_qty=qty_m * record.wastage_qty
               else:
                     wastage_qty=record.wastage_qty
                     
#            if record.product_qty:
            if record.produced_qty:
               if record.uom_id.id !=record.wastage_uom.id:
		   if record.uom_id.name =='Pcs':
		      wastage_qty=math.ceil(record.produced_qty *record.product_id.weight) if record.wastage_qty else 0.0
		   if record.uom_id.name =='m':
                             qty_m=(record.order_id.wk_required_qty/record.order_id.qty)
                             wastage_qty=qty_m * record.wastage_qty
               else:
		    wastage_qty=record.wastage_qty
#               if record.order_id.wk_required_qty < (wastage_qty + record.product_qty + record.order_id.total_product_qty +record.order_id.total_wastage_qty):
#               if record.order_id.wk_required_qty < (wastage_qty + record.produced_qty + record.order_id.total_product_qty +record.order_id.total_wastage_qty):
               if record.req_product_qty < record.produced_qty:
                  record.warning_bool=True
               else:
                  record.warning_bool=False
            print "recordrecordrecordrecord",record
            if wo_id.raw_materials_id:
                '''for raw in record.order_id.raw_materials_id:
                   qty_one=(raw.qty/record.order_id.wk_required_qty)
                   total =round(qty_one * record.product_qty,2)
                   print"UUUUUUuuuuuuuuuuu",qty_one,raw.qty,record.order_id.wk_required_qty, total,record.product_qty'''
                raw_lst=[]
                rm_append=[]
                for bom in  record.production_id.bom_id.bom_line_ids:
                    rm_append.append((bom.id))
                for bom_ln in record.production_id.bom_id.bom_packging_line:
                    rm_append.append((bom_ln.id))
                for bom in self.env['mrp.bom.line'].browse(rm_append):
                    if bom.workcenter_id.id == wo_id.workcenter_id.id:
                       for product in record.production_id.product_lines:
                           if product.product_id.id == bom.product_id.id:
                              one_qty=0.0
                              if record.uom_id.name == 'Kg':
                                 one_qty =((record.produced_qty + wastage_qty) / record.product_id.weight)
                              else:
                                 one_qty =(record.produced_qty + wastage_qty)
                              for rec in record.produced_line_id:
                              	if rec.product_id.id == bom.product_id.id:
                              		rec.receive_qty=bom.product_qty *(one_qty)
                              qty_1=round(one_qty,2)
                              bom_qty=round(bom.product_qty, 5)
                              raw_lst.append((0,0,{'product_id':bom.product_id.id,'uom_id':bom.product_uom.id,
							 'receive_qty':product.receive_qty, 
							 'consumed_qty':product.consumed_qty,
							 'remain_consumed':product.remain_consumed,
							 'product_qty':round(qty_1 * bom.product_qty,2) }))#one_qty * bom.product_qty}))
                if raw_lst:
                	record.produced_line_id=raw_lst
    
    @api.multi
    def orderProduceqty(self):
        for record in self:
            print "recordrecord",record.uom_id
            attachment=[]
            body=''
            next_order=0
#            if not record.product_qty and  record.wastage_bool:
            if not record.produced_qty and  record.wastage_bool:
               raise UserError(_("Please Fill Produce Qty ..."))
            else:
               order=self.env['mrp.production.workcenter.line'].search([('production_id','=',record.production_id.id),('sequence','>',record.order_id.sequence)], limit=1)
               if order:
                  next_order=order.id
               body='<b>Product Produced In Work Order:</b>'
#               body +='<ul><li> Produced Qty    : '+str(record.product_qty) +'</li></ul>'
               body +='<ul><li> Produced Qty    : '+str(record.produced_qty) +'</li></ul>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> Work Order No.  : '+str(record.order_id.name) +'</li></ul>'
               body +='<ul><li> Batch Number   : '+str(record.batch_id.name) +'</li></ul>'
               body +='<ul><li> User Name      : '+str(self.create_uid.name) +'</li></ul>' 
               body +='<ul><li> Produced Time   : '+str(datetime.now() + timedelta(hours=4)) +'</li></ul>' 
               body +='<ul><li> Remark         : '+str(self.remark) +'</li></ul>'
               if record.wastage_qty:
                  body +='<b><p style="color:red">Wastage Information:</p></b>'
                  body +='<ul><li style="color:red"> Wastage Qty  : '+str(self.wastage_qty) +'</li></ul>'
                  body +='<ul><li style="color:red"> Reason         : '+str(self.wastage_reason) +'</li></ul>'
               record.order_id.message_post(body=body)
               record.production_id.message_post(body=body)
               record.production_id.write({'state':'in_production'})
               record.bool_check =False 
               name=''
               wast_qty=produce_qty=0.0
               if record.wastage_qty:
                  if record.previous_batch_id.uom_id.id !=record.wastage_uom.id:
		     if record.previous_batch_id.uom_id.name =='Pcs':
		        wast_qty=math.ceil(record.wastage_qty/record.product_id.weight) if record.wastage_qty else 0.0
		     if record.previous_batch_id.uom_id.name =='m':
                        qty_m=(record.order_id.qty/record.order_id.wk_required_qty)
                        wast_qty=qty_m * record.wastage_qty
                  else:
		       wast_qty=record.wastage_qty               
               if record.previous_batch_id:
                  if record.previous_batch_id.uom_id.id != record.uom_id.id:
		     if record.uom_id.name =='Pcs':
#		        produce_qty=math.ceil(record.product_qty * record.product_id.weight) if record.product_qty else 0.0   
		        produce_qty=math.ceil(record.produced_qty * record.product_id.weight) if record.produced_qty else 0.0   
                     if record.uom_id.name =='m': 
                        qty_m=(record.order_id.qty/record.order_id.wk_required_qty)
#                        produce_qty=qty_m * record.product_qty          
                        produce_qty=qty_m * record.produced_qty          
		  else: 
#                    produce_qty=record.product_qty
                    produce_qty=record.produced_qty
		  print"+++++++================",produce_qty , record.wastage_qty,record.previous_batch_id.remain_used_qty
                  '''if record.previous_batch_id.remain_used_qty < (produce_qty + wast_qty):
                        print"TTTttttttttt",record.previous_batch_id.remain_used_qty, wast_qty, produce_qty
                        raise UserError(_("You can not Produced Qty(%s)(%s) because your selected Previous Batch Remaining Qty(%s)(%s).")%(round((produce_qty + wast_qty),2),(record.previous_batch_id.uom_id.name),round(record.previous_batch_id.remain_used_qty,2) ,(record.previous_batch_id.uom_id.name)))'''
		  record.previous_batch_id.used_qty +=(produce_qty + wast_qty)
		  record.previous_batch_id.remain_used_qty -=(produce_qty + wast_qty)
               for emp in record.employee_ids:
                   name +='%s %s'%(emp.name,"\n")
               supp_name=''
               if record.supplier_btc_no and record.first_order==True:
                  for supp in record.supplier_btc_no:
                     supp_name +='%s %s'%(supp.name,"\n") 
#               record.batch_id.write({'product_qty':record.batch_id.product_qty + record.product_qty,
               record.batch_id.write({
#                                    'product_qty':record.batch_id.product_qty + record.produced_qty,
                                    'product_qty':record.produced_qty,
                                      'uom_id':record.uom_id.id,'next_order_id':next_order,
                                      'reason':record.wastage_reason, 'remark':record.remark,
                                       'employee_name':name,
                                       'user_id':self.env.user.id,
                                       'produce_qty_date':record.produce_date,
#                                       'remain_used_qty':record.batch_id.remain_used_qty +(record.product_qty),
                                       'remain_used_qty':record.batch_id.remain_used_qty +(record.produced_qty),
                                       'supplier_batch_no':supp_name,
#                                      'wastage_qty':record.batch_id.wastage_qty + record.wastage_qty,
                                      'wastage_qty':record.wastage_qty,
                                      'prev_batch_id':record.previous_batch_id.id})
               if record.document:
                   record.batch_id.write({                                      
                   'document':[(4, record.document.ids)]
                    })
               if record.employee_ids:
                   record.batch_id.write({                                      
                   'employee_ids':[(4, record.employee_ids.ids)]
                    })
               record.batch_id._check_ro()
                
class MrpWorkorderMachineProduceLine(models.Model):
    _name = 'mrp.order.machine.produce.line'  
    
    produced_id=fields.Many2one('mrp.order.machine.produce')      
    product_id=fields.Many2one('product.product',string='Raw Material')
    product_qty=fields.Float('Required Qty')
    receive_qty=fields.Float('Received Qty')
    consumed_qty=fields.Float('Consumed Qty')
    remain_consumed=fields.Float('Remaining Qty')
    uom_id=fields.Many2one('product.uom', string='Unit')
           
class MrpWorkorderBatchNo(models.Model):
    _name='mrp.order.batch.number'
    
    @api.depends('batch_tfred')
    def _check_ro(self):
        print "check ro--------------------------"
        for rec in self:
            print "rec.product_qty",rec.product_qty,rec.convert_product_qty
            if rec.batch_tfred==True:
                print "yes matching----------------------"
                rec.check_ro=True
            print "selfkjhjstet tracjet======================================",rec.check_ro
            
    @api.depends('batch_tfred')
    def _check_tfred_qty(self):
        print "check ro--------------------------"
        for rec in self:
            print "rec.product_qty",rec.product_qty,rec.convert_product_qty
            if rec.batch_tfred==True:
                print "yes matching----------------------"
                rec.transferred_qty=rec.convert_product_qty
            else:
                rec.transferred_qty=0.0
            print "selfkjhjstet tracjet======================================",rec.transferred_qty

    
    @api.model
    def _get_uom_id(self):
        return self.env["product.uom"].search([('name','=','Kg')], limit=1, order='id')[0]
    employee_ids=fields.Many2many('hr.employee', string='Operators')


    check_ro=fields.Boolean('Check RO',compute='_check_ro') 
    batch_tfred=fields.Boolean('Batch Transferred') 
    transferred_qty=fields.Float('Qty Transferred',compute='_check_tfred_qty') 
    name=fields.Char('Number',copy=False) 
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.')
    order_id=fields.Many2one('mrp.production.workcenter.line', string=' Previous Work-Order No.')
    next_order_id=fields.Many2one('mrp.production.workcenter.line', string='Work-Order No.')      
    machine = fields.Many2one('machinery', string='Machine') 
    product_id=fields.Many2one('product.product',string='Product Name')
    product_qty=fields.Float('Produced Qty',digits=dp.get_precision('Product Unit of Measure'))
    req_product_qty=fields.Float('Required Qty')
    prev_batch_id=fields.Many2one('mrp.order.batch.number','Previous Batch No.')
    wastage_qty=fields.Float('Wastage Qty',)
    wastage_allow=fields.Float('Allowed Wastage', compute='allow_wastage_mo')
    allow_wastage_uom_id=fields.Many2one('product.uom', default=_get_uom_id)
    uom_id=fields.Many2one('product.uom', string='Unit')
    lot_id=fields.Many2one('stock.production.lot', string='Transfer No.',Help="Product LOT number,Shows total Quantity is comes in lot") 
    print_bool=fields.Boolean('Select', default=False)
    ntype = fields.Selection([('reject','Rejct'),('accept','Approve'),('pending','Pending')],
    				string='Type',default='pending')
    produce_bool = fields.Boolean('Produce In MO', default=False)
    user_id=fields.Many2one('res.users',string='User Name')
    employee_name=fields.Char(string='Operators Name')
    supplier_batch_no=fields.Char('Supplier Batch No.')
    remark=fields.Text('Remark')
    reason=fields.Text('Wastage Reason')
    document = fields.Many2many('ir.attachment','batches_produce_attachment_rel','batch_id','doc_id','Batch Documents')
    state = fields.Selection([('draft','Draft'),('pause','Pause'),('hold','On Hold'),('ready','Ready'),
    				('startworking', 'In Progress'),('done','Finished'),('cancel','Cancelled'),],
    				'Status', readonly=True,related='order_id.state')
    				
    used_qty=fields.Float('Used Qty')
    remain_used_qty=fields.Float('Used Qty', )
    equal_qty=fields.Boolean('hide add more button when rq qty and produced qty is equal', compute='batch_equal_qty')
    sale_line_id = fields.Many2one('sale.order.line','Sale Order Line')
    sale_id = fields.Many2one('sale.order',string='Sale Order',related='sale_line_id.order_id')
    logistic_state = fields.Selection([('draft','Draft'),('ready','Ready'),('transit_in','Transit-IN'),
    				('stored','In Store'),('reserved','Reserved'),('r_t_dispatch', 'Ready To Dispatch'),
    				('transit', 'Transit-OUT'),('dispatch','Dispatched'),('returned','Return'),
    				('done','Done'),('cancel','Cancel')],string='Logistic Status',default='draft',
    				readonly=True,copy=True)
    				
    produce_qty_date= fields.Datetime('Produced Date')
    convert_product_qty= fields.Float(help="Convert batch produce qty to MO unit",string='produced MO qty',compute="_convert_product_qty",store=True,digits=dp.get_precision('Product Unit of Measure'))
    
    @api.multi
    @api.depends('product_qty','production_id.mrp_third_qty_sheet')
    def _convert_product_qty(self):
    	for line in self:
    		if not line.next_order_id and line.production_id:
    			total_qty=0.0
			if line.production_id.product_uom.id != line.uom_id.id:
				if line.uom_id.name == 'm' and line.order_id.process_type == 'psheet' :
					total_qty=(line.production_id.product_qty/line.production_id.mrp_third_qty_sheet) * line.product_qty
				if line.uom_id.name == 'm' and line.order_id.process_type == 'ptube' :
					total_qty=(line.production_id.product_qty/line.production_id.mrp_third_qty) * line.product_qty
				if line.uom_id.name == 'Pcs':
		             		total_qty=(line.production_id.product_qty / line.production_id.mrp_sec_qty )* line.product_qty
     			else:
     				total_qty = line.product_qty
                   	line.convert_product_qty = total_qty
           	elif line.product_qty:
           		line.convert_product_qty=line.product_qty
    				
    @api.multi
    @api.depends('req_product_qty','product_qty')
    def batch_equal_qty(self):
        for record in self:
            if record.product_qty:
               if (record.product_qty + record.wastage_qty) == record.req_product_qty:
                  record.equal_qty=True
               else:
                  record.equal_qty=False
            else:
                record.equal_qty=False

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('prev') and context.get('previous_order_ids'):
           batch_ids=self.search(cr,uid,[('order_id','in',context.get('previous_order_ids')[0][2]),
                                        ('product_qty','>',0)])
           args.extend([('id','in',batch_ids)])
        if context.get('last_batch') and context.get('production'):
           order=self.pool.get('mrp.production.workcenter.line').search(cr, uid,[('production_id','=',context.get('production')), ('order_last','=',True)],context=context)
           batch_ids=self.search(cr,uid,[('order_id','in',order)])
           args.extend([('id','in',batch_ids)])
        return super(MrpWorkorderBatchNo,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
   
    @api.multi
    @api.depends('production_id')
    def allow_wastage_mo(self):
        for record in self:
            if record.production_id:
               record.wastage_allow=record.production_id.wastage_allow
    
    @api.multi
    def open_batches(self):
        for line in self:
            batches_tree = self.env.ref('gt_order_mgnt.mrp_work_order_wastage_tree_aalmir', False)
            batches_form = self.env.ref('gt_order_mgnt.mrp_work_order_wastage_form_aalmir', False)
            if batches_tree:
                return {
                    'name':'Total Work Order Batches',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'mrp.order.batch.number',
                    'views': [(batches_tree.id, 'tree'),(batches_form.id, 'form')],
                    'view_id': batches_tree.id, 
                    'target': 'current',
                    'domain':[('production_id','=',line.production_id.id),('id','!=',line.id),
                                ('wastage_qty','>',0)],
                }
        return True

    @api.multi
    def check_print(self):
        for record in self:
            record.print_bool=True
            return {'type':'ir.actions.do_nothing'}
            
    @api.multi
    def uncheck_print(self):
        for record in self:
            record.print_bool=False
            return {'type':'ir.actions.do_nothing'}
            
    @api.multi
    def print_batch_barcode(self):
        self.env.cr.execute("select mrp_production_workcenter_line_id from mrp_order_batch_number_mrp_production_workcenter_line_rel where mrp_order_batch_number_id="+str(self.id) )
    	wc_line_id=self.env.cr.fetchone()
        print "wc_line_idwc_line_idwc_line_idwc_line_id",wc_line_id
        print_type=self.env['mrp.production.workcenter.line'].browse(wc_line_id[0]).print_type
        if print_type=='normal':
            return self.env['report'].get_action(self, 'gt_order_mgnt.report_batch_number_barcode')
        elif print_type=='detailed':
            return self.env['report'].get_action(self, 'gt_order_mgnt.production_batch_number_print_wo_line')

   
    @api.one
    def save_batch(self):
         obj=self.env['mrp.order.batch.number'].search([('id','=',self._context.get('active_id'))])
         body='<b>Produced Qty Changed in Batch:  </b>'
         body +='<ul><li> Manufanufacturing No. : '+str(self.production_id.name) +'</li></ul>'
         body +='<ul><li> Batch No. : '+str(self.name) +'</li></ul>'
         body +='<ul><li> Previous Produced Qty : '+str(obj.product_qty) +'</li></ul>'
         body +='<ul><li> Current Produced Qty : '+str(self.product_qty) +'</li></ul>'
         body +='<ul><li> Changed By  : '+str(self.env.user.name) +'</li></ul>'
         body +='<ul><li> Changed Date  : '+str(date.today()) +'</li></ul>'
         wastage_qty_old=wastage_qty_new=0.0
         if obj.order_id.raw_materials_id  and obj.product_qty:
            if self.uom_id.name == 'Pcs':
               wastage_qty_new=math.ceil(self.wastage_qty/obj.order_id.product.weight) if self.wastage_qty else 0.0
               wastage_qty_old=math.ceil(obj.wastage_qty/obj.order_id.product.weight) if obj.wastage_qty else 0.0
            if self.uom_id.name =='m':
               qty_m=(obj.order_id.wk_required_qty/obj.order_id.qty)
               wastage_qty_old=qty_m * obj.wastage_qty
               wastage_qty_news=qty_m * self.wastage_qty
            if self.uom_id.name =='Kg':
	       wastage_qty_old=obj.wastage_qty
               wastage_qty_new=self.wastage_qty
           
            for raw in self.order_id.raw_materials_id:
                one_qty=raw.qty/obj.order_id.wk_required_qty
                raw.consumed_qty = raw.consumed_qty -(one_qty * (obj.product_qty + wastage_qty_old))
                raw.consumed_qty = raw.consumed_qty + (one_qty * (self.product_qty + wastage_qty_new))
                print"after raw",one_qty, raw.consumed_qty, self.product_qty + wastage_qty_new, (one_qty * (self.product_qty + wastage_qty_new))
         produced=self.env['mrp.order.machine.produce'].search([('batch_id','=',obj.id)])
         if produced:
            for produce in produced:
                produce.product_qty=self.product_qty
                produce.wastage_qty=self.wastage_qty
         produced_zero=self.env['mrp.order.machine.produce'].search([('order_id','=',obj.order_id.id),('product_qty','=',0)])
         if produced_zero:
            produced_zero.unlink()
         obj.order_id.message_post(body=body)
         self.production_id.message_post(body=body)
         obj.product_qty=self.product_qty
         obj.reason=self.reason
         obj.remark=self.remark
         obj.document=self.document
         obj.user_id=self.user_id.id
         obj.employee_name=self.employee_name
         obj.supplier_batch_no=self.supplier_batch_no
         obj.wastage_qty=self.wastage_qty
         if not self.product_qty  and not self.wastage_qty:
            obj.next_order_id=''
         else:
            obj.next_order_id=obj.next_order_id.id
         self.unlink()
         return {'type': 'ir.actions.act_window',}
    
    @api.multi
    def edit_batch(self): 
        context = self._context.copy() 
        '''context.update({'default_order_id':self.order_id.id, 'default_machine':self.machine.id,
                     'default_product_qty':(self.product_qty) ,'default_uom_id':self.uom_id.id,
                       'default_production_id':self.production_id.id,
                        'default_name':self.name, 
                        'default_employee_name':self.employee_name,'default_document':self.document,
                        'default_reason':self.reason,'default_remark':self.remark,
                        'default_supplier_batch_no':self.supplier_batch_no,
                         
                          'default_wastage_qty':self.wastage_qty,
                           'default_uom_id':self.uom_id.id})'''
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_wastage_form_aalmir', False)
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.order.batch.number',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                     'res_id':self.id
                    #'domain':[('id','=',self.id)],
                    #'context': context,
             }
             
    @api.multi
    def change_produceqty(self):
#        if self.batch_tfred==True:
#              raise UserError("You are not allowed to make changes to this batch as the batch is already transferred!!")
        order=''
        workorder=self.env['mrp.production.workcenter.line']
        batchnumber=self.env['mrp.order.batch.number']
        order_lst=[]
        if self.order_id.parent_id:
           order=workorder.search([('production_id','=',self.production_id.id),('next_order_id','=',self.order_id.parent_id.id)], limit=1)
        else:

	    order=workorder.search([('production_id','=',self.production_id.id),('next_order_id','=',self.order_id.id)])
        if order:
           batch=''
           for orde in order:
		   if orde.split_work_ids:
		      for split_order in orde.split_work_ids:
		          order_lst.append((split_order.id))
		      order_lst.append((orde.id))
		   else:
		      order_lst.append((orde.id))
           batch=batchnumber.search([('production_id','=',self.production_id.id),('order_id','in',order_lst),('product_qty','!=',0)], limit=1)
           '''if not batch:
              raise UserError("Produced Previous Work order Batches Before Issued this Batch.")'''
	context = self._context.copy()
        ids_cus = [] 
        if self.order_id.batch_no_ids_prev:
           for batch in self.order_id.batch_no_ids_prev:
               ids_cus.append(batch.order_id.id)
        else:
           if self.order_id.parent_id:
              for batch in self.order_id.parent_id.batch_no_ids_prev:
                  ids_cus.append(batch.order_id.id)
           else:
              ids_cus = [] 
        print "ids- cus----------------------",ids_cus
        batches=[]
        print "self.employee_idsself.employee_ids",self,self.order_id.employee_ids
        if self.production_id:
            rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',self.production_id.id)])
            print "rm_idsrm_idsrm_ids",rm_ids
            if rm_ids:
                for each_rm in rm_ids:
                    pick_ids=self.env['stock.picking'].search([('material_request_id','=',each_rm.id),('state','=','done')])
                    print "pick_idspick_idspick_ids",pick_ids
                    if pick_ids:
                        for each in pick_ids:
                            if each.store_ids:
                                for each_store in each.store_ids:
                                    for each_batches in each_store.batches_ids:
                                        batches.append(each_batches.batch_number.id)
        if self.order_id.employee_ids:
            context.update({
            'default_employee_ids':[(6,0,[self.order_id.employee_ids[0].id])],
            })
        if batches:
            context.update({'default_supplier_btc_no':[(6,0,[batches[0]])],})
        machine_produce_id=self.env['mrp.order.machine.produce'].search([('batch_id','=',self.id),('order_id','=',self.order_id.id)])
        print "self.order_idself.order_idself.order_id",self.order_id
	context.update({
                        'default_order_id':self.order_id.id, 
                        'default_machine':self.machine.id,
                         'default_previous_order_id':self.order_id.batch_no_ids_prev[0].order_id.id if self.order_id.batch_no_ids_prev else '',
                       'default_batch_id':self.id,
                       'default_remark':self.remark,
                       'default_wastage_reason':self.reason,
                       'default_supplier_batch_no':self.supplier_batch_no,
#                       'default_produced_qty':self.product_qty,
                       'default_produced_qty':self.req_product_qty,
                     'default_product_qty':(self.req_product_qty - self.product_qty) if self.req_product_qty > self.product_qty else 0.0,'default_uom_id':self.uom_id.id if self.uom_id else self.order_id.wk_required_uom.id,'default_user_id':self.order_id.user_ids.ids,
                      'default_previous_order_ids':[(6,0,ids_cus)],
                        'supplier_batch':True if self.order_id.process_type == 'raw' else False,
                        'raw_material':True if self.order_id.raw_materials_id else False,
                       'default_product_id':self.product_id.id, 'default_production_id':self.production_id.id})
        if self.document:
            context.update({
            'default_document':[(6,0,self.document.ids)],
            })
	raw_lst=[]
        for res in self:
		if res.order_id.raw_materials_id:
		        
		        rm_append=[]
		        for bom in  res.production_id.bom_id.bom_line_ids:
		            rm_append.append((bom.id))
		        for bom_ln in res.production_id.bom_id.bom_packging_line:
		            rm_append.append((bom_ln.id))
		        for bom in self.env['mrp.bom.line'].browse(rm_append):
		            if bom.workcenter_id.id == res.order_id.workcenter_id.id:
		               for product in res.production_id.product_lines:
		                   if product.product_id.id == bom.product_id.id:
		                      one_qty=0.0
		                      if res.uom_id.name == 'Kg':
		                         print"###########",res.product_qty ,res.product_id.weight
		                         one_qty =((res.product_qty) / res.product_id.weight)
		                      else:
		                         one_qty =res.product_qty
		                      print"44444444444",one_qty, bom.product_qty *(one_qty)
		              	      raw_lst.append((0,0,{'product_id':bom.product_id.id,'uom_id':bom.product_uom.id,
			                    		'receive_qty':product.receive_qty, 
			                    		'consumed_qty':product.consumed_qty,
			                   		'remain_consumed':product.remain_consumed,
				                    	'product_qty':bom.product_qty *(one_qty)}))
	context.update({'produced_line_id':raw_lst})	                                       
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_machine_produce_form', False)
        res_id=False
        if machine_produce_id:
            res_id=machine_produce_id[0].id
        print "context before opening pop up---------------",context
        if mo_form:
                return {
                    'name':'Produced Qty in Batch',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.order.machine.produce',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'res_id': res_id,
                    'target': 'new',
                    'context': context,
             }
             
class MrpProductionroutingProcess(models.Model):
    _name='mrp.rounting.process'
    machine = fields.Many2one('machinery', string='Machine') 
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    routing_id=fields.Many2one('mrp.routing', string="routing")
    production_id=fields.Many2one('mrp.production',string="Production")
    product_id=fields.Many2one('product.product')
    capacity_per_cycle=fields.Float('Capacity Per Cycle')
    time_cycle=fields.Float('Time Cycle')
    sequence=fields.Integer('Sequence') 
    hour=fields.Integer('Hour')
    minute=fields.Integer('Minute')
    second=fields.Integer('Second')
    time_option=fields.Selection([('1','1x'),('2','2x'),('3','3x'),
                               ('4', '4x'),('5', '5x')], string='Production Output')
                               
class MrpWorkcenterPructionlineScheduleLine(models.Model):
    _name = 'mrp.production.workcenter.line.schedule.line'
    line_schedule_id=fields.Many2one('mrp.production.workcenter.line.schedule') 
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.')
    line_schedule_id_date=fields.Many2one('mrp.production.workcenter.line.schedule')   
    name=fields.Char('Name')
    state= fields.Selection([('draft','Draft'),('cancel','Cancelled'),('pause','Pending'),('startworking', 'In Progress'),('done','Finished')],'Status')
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.') 
    workcenter_id=fields.Many2one('mrp.workcenter', string="Process")
    machine = fields.Many2one('machinery', string='Machine') 
    date_planned=fields.Datetime('Schedule Date')
    date_planned_end=fields.Datetime('Schedule Date')
    product=fields.Many2one('product.product', string='Product Name')
    uom=fields.Many2one('product.uom', string='Unit')
    qty=fields.Float('qty')
    hour=fields.Float('Hour')
    cycle=fields.Float('Cycle')
    
class MrpWorkcenterPructionlineSchedule(models.Model):
    _name = 'mrp.production.workcenter.line.schedule'  
    name=fields.Char('Name')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.') 
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.') 
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    machine_type_ids=fields.Many2many('machinery.type', string="Machine Type")
    work_id=fields.One2many('mrp.production.workcenter.line','schedule_id', string='Work order', order='id desc')
    machine = fields.Many2one('machinery', string='Machine')  
    product=fields.Many2one('product.product', string='Product Name')
    uom=fields.Many2one('product.uom', string='Unit')
    qty=fields.Float('qty')
    date_planned=fields.Datetime('Schedule Date')
    date_planned_end=fields.Datetime('End Date')
    time_efficiency=fields.Float('Efficiency Factor')
    hour=fields.Float('Hour')
    cycle=fields.Float('Cycle')
    state= fields.Selection([('draft','Draft'),('cancel','Cancelled'),('pause','Pending'),('startworking', 'In Progress'),('done','Finished'),('ready','Ready')],'Status')
    work_ids=fields.One2many('mrp.production.workcenter.line.schedule.line','line_schedule_id', string='Work order', order='id desc')
    machine_schedule_ids=fields.One2many('mrp.production.workcenter.line.schedule.line','line_schedule_id_date', string='Work order', order='id desc')
               
    
class MrpWorkorderShiftRequest(models.Model):
    _name = 'mrp.work.order.shiftrequest'
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.') 
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.') 
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    wk_required_qty = fields.Float('Required Quantity')
    wk_required_uom = fields.Many2one('product.uom')
    sequence=fields.Integer('Sequence')
    remain_qty=fields.Float('Remaining Qty', compute='rmainqty')
    shift_request=fields.Selection([('current','Max Output'),('next','Link to Parent'),('custom','Custom')], default='current', string='Shift Request')
    next_order_id=fields.Many2one('mrp.production.workcenter.line', string='Parent Order')
    request_line_ids=fields.One2many('mrp.work.order.shiftrequest.line' ,'shift_request_id') 
    shift_check=fields.Boolean('Shift Not create', default=False)

    @api.multi
    @api.onchange('next_order_id') 
    def shiftcheck(self):
        for record in self:
            if record.next_order_id:
               if not record.next_order_id.split_work_ids:
                  record.shift_check=True
               else:
                  record.shift_check=False
    @api.multi
    @api.depends('request_line_ids.qty') 
    def rmainqty(self):
       for record in self:
           sm=0
           for line in record.request_line_ids:
               sm=sum(line.qty for line in record.request_line_ids)
           if sm:
              record.remain_qty=record.wk_required_qty-sm
           else:
              record.remain_qty=record.wk_required_qty  
    '''@api.multi
    def create_jobcard(self):
        for record in self:
            workorder=self.env['mrp.production.workcenter.line']
            shift_hr=(record.order_id.hour -((record.order_id.machine.time_start or 0.0) +(record.order_id.machine.time_stop or 0.0)))
            count=int(math.ceil(shift_hr/record.order_id.shift_time))
            count -=1
            if record.shift_request == 'current':
               req_qty=0.0
               req_hr=0.0
               req=(record.order_id.shift_required -1) 
               rm_hr=shift_hr
               for x in range(0, count):
                   if req > 1:
                      req_qty=(record.order_id.shift_base_qty)
                      req_hr=record.order_id.shift_time
                   else:
                       req_qty=record.order_id.shift_base_qty * req
                       req_hr=(rm_hr - record.order_id.shift_time)
                   if record.order_id.shift_child_order_id:
                      child_id=workorder.create({'production_id':record.production_id.id,
                            'machine':record.order_id.shift_child_order_id.machine.id,
                            'sequence':record.order_id.shift_child_order_id.sequence,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.shift_child_order_id.user_ids])],
                            'workcenter_id':record.order_id.shift_child_order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.shift_child_order_id.machine_capacity_type, 
                            'capacity_type':record.order_id.shift_child_order_id.capacity_type.id,
                            'hour':req_hr,'date_planned':record.order_id.date_planned, 
                            'cycle':(req_qty/ record.order_id.capacity_per_cycle),
                            'capacity_per_cycle':record.order_id.capacity_per_cycle, 'p_hour':record.order_id.p_hour,
                            'p_minute':record.order_id.p_minute, 'p_second':record.order_id.p_second,
                            'parent_id':record.order_id.shift_child_order_id.id,'wk_required_qty':req_qty,
                            'workorder_type':'child',
                            'shift_time':record.order_id.shift_time, 'time_option':record.order_id.time_option})
                   
                   split_id=workorder.create({'production_id':record.production_id.id,
                            'machine':record.order_id.machine.id,
                            'sequence':record.order_id.sequence,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.user_ids])],
                            'workcenter_id':record.order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.machine_capacity_type, 
                            'capacity_type':record.order_id.capacity_type.id,
                            'hour':req_hr,'date_planned':record.order_id.date_planned, 
                            'cycle':(req_qty/ record.order_id.capacity_per_cycle),
                            'capacity_per_cycle':record.order_id.capacity_per_cycle, 'p_hour':record.order_id.p_hour,
                            'p_minute':record.order_id.p_minute, 'p_second':record.order_id.p_second,
                            'parent_id':record.order_id.id,'wk_required_qty':req_qty,
                            'workorder_type':'child',
                            'shift_time':record.order_id.shift_time, 'time_option':record.order_id.time_option})
                   req -=1
                   rm_hr -=record.order_id.shift_time
               record.order_id.workorder_type='both'
               record.order_id.hour=record.order_id.shift_time
               cycle=(record.order_id.capacity_per_cycle/record.order_id.wk_required_qty)
               record.order_id.cycle=cycle
            if record.shift_request == 'custom':
               for line in record.request_line_ids:
                   if record.order_id.shift_child_order_id:
                      child_id=workorder.create({'production_id':record.production_id.id,
                            'machine':record.order_id.shift_child_order_id.machine.id,
                            'sequence':record.order_id.shift_child_order_id.sequence,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.shift_child_order_id.user_ids])],
                            'workcenter_id':record.order_id.shift_child_order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.shift_child_order_id.machine_capacity_type, 
                            'capacity_type':record.order_id.shift_child_order_id.capacity_type.id,
                            'hour':line.hour,'date_planned':line.date_planned, 
                            'cycle':(line.qty/ record.order_id.capacity_per_cycle),
                            'capacity_per_cycle':record.order_id.capacity_per_cycle, 'p_hour':record.order_id.p_hour,
                            'p_minute':record.order_id.p_minute, 'p_second':record.order_id.p_second,
                            'parent_id':record.order_id.shift_child_order_id.id,'wk_required_qty':line.qty,
                            'workorder_type':'child',
                            'shift_time':record.order_id.shift_time, 'time_option':record.order_id.time_option})
                   split_id=workorder.create({'production_id':record.production_id.id,
                            'machine':record.order_id.machine.id,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.user_ids])],
                            'sequence':record.order_id.sequence,
                            'workcenter_id':record.order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.machine_capacity_type, 
                            'capacity_type':record.order_id.capacity_type.id,
                            'hour':line.hour,'date_planned':line.date_planned, 
                            'cycle':(line.qty/ record.order_id.capacity_per_cycle),
                            'capacity_per_cycle':record.order_id.capacity_per_cycle, 'p_hour':record.order_id.p_hour,
                            'p_minute':record.order_id.p_minute, 'p_second':record.order_id.p_second,
                            'parent_id':record.order_id.id,'wk_required_qty':line.qty,
                            'workorder_type':'child',
                            'shift_time':record.order_id.shift_time, 'time_option':record.order_id.time_option}) 
            if record.shift_request == 'next':
               if record.next_order_id.split_work_ids:
                  for line in record.next_order_id.split_work_ids:
                      if record.order_id.shift_child_order_id:
                         #if record.next_order_id.process_type == 'cutting' and record.order_id.process_type == 'ptube:
                         child_split=workorder.create({'production_id':line.production_id.id,
                            'machine':record.order_id.shift_child_order_id.machine.id,
                            'sequence':record.order_id.shift_child_order_id.sequence,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.shift_child_order_id.user_ids])],
                            'workcenter_id':record.order_id.shift_child_order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.shift_child_order_id.machine_capacity_type, 
                            'capacity_type':line.capacity_type.id,
                            'hour':line.hour,'date_planned':line.date_planned, 
                            'cycle':line.cycle,
                            'capacity_per_cycle':line.capacity_per_cycle, 'p_hour':line.p_hour,
                            'p_minute':line.p_minute, 'p_second':line.p_second,
                            'parent_id':record.order_id.shift_child_order_id.id,
                            'wk_required_qty':line.wk_required_qty,
                            'workorder_type':'child',
                            'shift_time':line.shift_time, 'time_option':line.time_option})
                           
                      split_id=workorder.create({'production_id':line.production_id.id,
                            'machine':record.order_id.machine.id,
                            'user_ids':[(6, 0, [x.id for x in record.order_id.user_ids])],
                            'sequence':record.order_id.sequence,
                            'workcenter_id':record.order_id.workcenter_id.id,
                            'machine_capacity_type':record.order_id.machine_capacity_type, 
                            'capacity_type':line.capacity_type.id,
                            'hour':line.hour,'date_planned':line.date_planned, 
                            'cycle':line.cycle,
                            'capacity_per_cycle':line.capacity_per_cycle, 'p_hour':line.p_hour,
                            'p_minute':line.p_minute, 'p_second':line.p_second,
                            'parent_id':record.order_id.id,'wk_required_qty':line.wk_required_qty,
                            'workorder_type':'child',
                            'shift_time':line.shift_time, 'time_option':line.time_option}) 
                     
               else:    
                   record.order_id.shift_order_id=record.next_order_id.id
                   record.next_order_id.shift_child_order_id=record.order_id.id  '''    
                           
class MrpWorkorderShiftRequestLine(models.Model):
    _name = 'mrp.work.order.shiftrequest.line'
    @api.model
    def get_qty(self):
        return self._context.get('mo_rqty')
    @api.model
    def get_currentorder(self):
        return self._context.get('order_id')
    '''@api.model
    def get_nextorder(self):
        return self._context.get('next_order_id') '''
    @api.model
    def get_uom(self):
        return self._context.get('uom') 
    qty=fields.Float('Qty', default=get_qty)
    uom = fields.Many2one('product.uom' ,default=get_uom)
    hour=fields.Float('Hour')
    date_planned=fields.Datetime('Schedule Date')
    date_planned_end=fields.Datetime('End Date', compute='enddate')
    shift_request_id=fields.Many2one('mrp.work.order.shiftrequest')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.', default=get_currentorder)

    @api.multi
    @api.onchange('qty')
    def hourcalculation(self):
        for record in self:
            if record.qty:
               hr=(record.order_id.p_hour * 60 *60)  +(record.order_id.p_minute*60 + record.order_id.p_second)
               time_cycle=hr * 0.000277778
               cycle=float(record.qty/(record.order_id.capacity_per_cycle * int(record.order_id.time_option if record.order_id.time_option else 1.0 )))
               hour=(cycle *(time_cycle)) *(record.order_id.time_efficiency or 1.0) +((record.order_id.machine.time_start or 0.0) +(record.order_id.machine.time_stop or 0.0))
               record.hour=hour
    @api.multi
    @api.depends('date_planned','hour')
    def enddate(self):
        for record in self:
            if record.date_planned and record.hour:
               record.date_planned_end=datetime.strptime(record.date_planned, '%Y-%m-%d %H:%M:%S')+ timedelta(hours=record.hour) 
               
class MrpWorkorderJobcard(models.Model):
    _name = 'mrp.work.order.jobcard'
    name=fields.Char('Name')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.') 
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.') 
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    date_planned=fields.Datetime('Schedule Date')
    date_planned_end=fields.Datetime('End Date')
    product=fields.Many2one('product.product', string='Product Name')
    uom=fields.Many2one('product.uom', string='Unit')
    qty=fields.Float('qty')
    hour=fields.Float('Working Hour')

    @api.model
    def create(self, vals):
        if  vals.get('order_id'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.work.order.jobcard') or 'New'
        result = super(MrpWorkorderJobcard, self).create(vals)
        return result
        

class MrpWorkcenterPructionline(models.Model):
    _inherit = 'mrp.production.workcenter.line'
  
    @api.model
    def create(self, vals):
        if self._context.get('mo_cal'):
           order=self.env['mrp.production.workcenter.line'].search([('id','=',self._context.get('prev_workorder_id'))])
           if order:
              machine=self.env['machinery'].search([('id','=',vals.get('machine'))])
              order.machine=vals.get('machine')
              wk_vals={'date_planned':vals.get('date_planned'),
              		'machine_show':vals.get('machine_show'),'capacity_type':vals.get('capacity_type'),
              		'capacity_per_cycle':vals.get('capacity_per_cycle'),
              		'time_option':vals.get('time_option'),'p_hour':vals.get('p_hour'),
              		'p_minute':vals.get('p_minute'),'p_second':vals.get('p_second'),
              		'shift_time':vals.get('shift_time') ,'hour':vals.get('hour'),
              		'cycle':vals.get('cycle'),'wk_planned_status':'fully','self_id':order.id,
              		'user_ids':vals.get('user_ids'),'employee_ids':vals.get('employee_ids'),
                        'information_types':vals.get('information_types'),
                         'm_schedule_ids':vals.get('m_schedule_ids')}

              order.write(wk_vals) 

              body='<b>Work Order Details with Machine:</b>'
              body +='<ul><li> Machine : '+str(order.machine.name) +'</li></ul>'
              body +='<ul><li> Scheduled Date. : '+str(order.date_planned) +'</li></ul>'
              body +='<ul><li> End Date    : '+str(order.date_planned_end) +'</li></ul>' 
              body +='<ul><li> Time          : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
              body +='<ul><li> Scheduled By    : '+str(self.env.user.name)+'</li></ul>' 
              order.message_post(body=body)
              ctx=order._context.copy()
              ctx.update({'mo_cal':False,})
              return order
        if vals.get('name'):
            if vals.get('production_id'):
               code=self.env['mrp.workcenter'].search([('id','=',vals.get('workcenter_id'))])
               pr=self.env['mrp.production'].browse(vals.get('production_id'))
               name=pr.name[:7]
               vals['name'] =name +'-'+str(code.process_id.code)+str(vals.get('sequence'))
            
        else:
            if vals.get('production_id'):
               code=self.env['mrp.workcenter'].search([('id','=',vals.get('workcenter_id'))])
               pr=self.env['mrp.production'].browse(vals.get('production_id'))
               name=pr.name[:7]
               split=self._context.get('new_split') if self._context.get('new_split') else ''
               vals['name'] =name+split+'-'+str(code.process_id.code)+str(vals.get('sequence'))
        if not vals.get('machine'):
        	vals.update({'hour':0.0})
        result = super(MrpWorkcenterPructionline, self).create(vals)
        return result

    @api.multi
    def write(self, vals, update=True):
    	error_string=''
    	try:
    	    for res in self:
		if vals.get('date_planned'):
			new_date=datetime.strptime(vals.get('date_planned'),'%Y-%m-%d %H:%M:%S')
			if datetime.strptime(res.production_id.date_planned,'%Y-%m-%d %H:%M:%S') > new_date:
				error_string="You can not Schedule Workorder in less than Manufacturing order time."
				raise
				
		date_planned = vals.get('date_planned') if vals.get('date_planned') else res.date_planned
		if vals.get('date_planned') or vals.get('hour') or vals.get('machine'):
			if date_planned:
				hour=vals.get('hour') if vals.get('hour') else res.hour
				date_planned_end=datetime.strftime(datetime.strptime(date_planned,'%Y-%m-%d %H:%M:%S')+timedelta(hours=hour),'%Y-%m-%d %H:%M:%S')
				machine = vals.get('machine') if  vals.get('machine') else res.machine.id
			
				if machine:
					machine_ids=self.search([('machine','=',machine),('id','!=',res.id),('date_planned','<=',date_planned_end),('state','not in',('cancel','done'))])
					machine_string=''
					falg=False
					for m_ids in machine_ids:
						if m_ids.date_planned >= date_planned: 
							error_string="You Schedule Start Time {} and End Time {} of Current Workorder {} is conflecting with other Workorders No. {} {} To {}".format(date_planned,date_planned_end,res.name,m_ids.name,m_ids.date_planned,m_ids.date_planned_end)
							raise
						elif m_ids.date_planned_end > date_planned :
							error_string = "You Schedule Start Time {} and End Time {} of Current Workorder {} is conflecting with other Workorders No. {} {} To {}".format(date_planned,date_planned_end,res.name,m_ids.name,m_ids.date_planned,m_ids.date_planned_end)
							raise
		
		if date_planned:
			#check previous order planned time
			process=self.search([('production_id','=',res.production_id.id),('process_id','=',res.process_id.id)])
			prev_ids =self.search([('next_order_id','in',[p_id.id for p_id in process]),('date_planned','!=',False)],order='date_planned asc',limit=1)
			if prev_ids:
				if prev_ids.date_planned and prev_ids.date_planned>date_planned:
					error_string="You can not Schedule Workorder in less than Previous Process Workorder {} Time {}".format(prev_ids.name,prev_ids.date_planned)
					raise
					
			#check Next order planned time	
			curr_process_ids=self.search([('production_id','=',res.production_id.id),('process_id','=',res.process_id.id),('date_planned','!=',False),('id','!=',res.id)],order='date_planned asc',limit=1)
			if curr_process_ids:
				if curr_process_ids.date_planned < date_planned:
					date_planned=curr_process_ids.date_planned
					
			next_id = vals.get('next_order_id') if vals.get('next_order_id') else res.next_order_id.id if res.next_order_id else False
			if next_id:
				next=self.search([('id','=',next_id)])
				next_process=self.search([('production_id','=',res.production_id.id),('process_id','=',next.process_id.id),('date_planned','!=',False)],order='date_planned asc',limit=1)
				if next_process:
					if next_process.date_planned and next_process.date_planned<date_planned:
						error_string="You can not Schedule Workorder in Greater than Next Process Workorder {} Time {}".format(next_process.name,next_process.date_planned)
						raise
						
			#Check process by Sequence Code
			if res.sequence and not vals.get('sequence') and vals.get('date_planned') :
				date_planned = vals.get('date_planned')
				#for Previous process Time on Sequence
				prev_ids=False
				sequence = int(res.sequence)
				while True:
					print "ggg111"
					sequence -=1
					prev_ids=self.search([('production_id','=',res.production_id.id),('sequence','=',sequence),('date_planned','!=',False),('id','!=',res.id)],order='date_planned asc',limit=1)
					if prev_ids or sequence <=0:
						break
						
				if prev_ids:
					if prev_ids.date_planned and prev_ids.date_planned>date_planned:
						error_string="You can not Schedule Workorder in less than Previous Sequence Workorder {} Time {}".format(prev_ids.name,prev_ids.date_planned)
						raise
						
				#check Next order planned time on Sequence
				sequence = int(res.sequence)
				next_id=False
				max_seq=self.search([('production_id','=',res.production_id.id),('sequence','!=',False)],order='sequence Desc',limit=1)
				print "gggggggggggggggg",max_seq,sequence
				while True:
					print "ggg"
					sequence +=1
					next_id=self.search([('production_id','=',res.production_id.id),('sequence','=',sequence),('date_planned','!=',False),('id','!=',res.id)],order='date_planned asc',limit=1)
					if next_id or sequence >=int(max_seq.sequence):
						break
					
				if next_id:
					if next_id.date_planned and next_id.date_planned<date_planned:
						error_string="You can not Schedule Workorder in Greater than Next Sequence Workorder {} Time {}".format(next_id.name,next_id.date_planned)
						raise
						
			else:
				error_string="Workorder {} does not have any Sequence, Set Sequence for   scheduling".format(res.id)
    	    if vals.get('date_planned'):
        	new_date=datetime.strptime(vals.get('date_planned'),'%Y-%m-%d %H:%M:%S')
#        	if datetime.now() > new_date:
#        		error_string="You can not Schedule Workorder in less than current time."
#        		raise
        
    	    if  vals.get('capacity_type') and vals.get('machine'): 
    	    	m_type=self.env['machinery.capacity.type'].search([('id','=',vals.get('capacity_type'))])
    	    	vals.update({'capacity_per_cycle':m_type.capacity_per_cycle,'p_hour':m_type.hour,
    	    		     'p_minute':m_type.minute,'p_second':m_type.second,
    	    		     'time_option':m_type.time_option})
    	    return super(MrpWorkcenterPructionline, self).write(vals, update=update)
    	except Exception as err:
    		if error_string:
    			raise UserError(error_string)
		else:
	    		exc_type, exc_obj, exc_tb = sys.exc_info()
		    	_logger.error("API-EXCEPTION..Exception in Workorder data updation.. {} {}".format(err,exc_tb.tb_lineno))
		    	raise UserError("API-EXCEPTION..Exception in Workorder data updation..{} {}".format(err,exc_tb.tb_lineno))

    @api.v7    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        
        if context.get('order'):
            if context.get('order') and context.get('order_id') and context.get('production'):
               args=[]
	       order_ids=self.search(cr,uid,[('id','!=', context.get('order_id')),('sequence','>', context.get('sequence')),('production_id','=', context.get('production')),('workorder_type','!=','child')])
                         
               args.extend([('id','in',order_ids)])
            if context.get('order') and not context.get('order_id') and context.get('production'):
               args=[]
	       order_ids=self.search(cr,uid,[('production_id','=', context.get('production'))])
               args.extend([('id','in',order_ids)])
        return super(MrpWorkcenterPructionline,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
    @api.multi
    @api.depends('extra_batch')
    def extra_batch_compute(self):
        for record in self:
            if record.extra_batch and record.req_product_qty:
                if record.extra_batch>=record.req_product_qty-len(record.batch_ids):
                        record.warning_mess = True

    @api.multi
    @api.onchange('machine', 'capacity_type')
    def wk_machinee(self):
        print"________________________MMMMMMMMMMM",
        for record in self:
            if record.machine:
               record.user_ids=record.machine.machine_user_ids
               record.employee_ids=record.machine.employee_ids
            else:
               record.user_ids=[]
               record.employee_ids=[]
            if record.machine and record.process_id.process_type != 'raw':
               record.shift_time=record.machine.shift_time
               if record.machine_capacity_type == 'product':
                  process=self.env['product.template.process'].search([('workcenter_id','=',record.workcenter_id.id),('product_id','=',record.product.product_tmpl_id.id)], limit=1)
                  if process:
                     record.time_efficiency=record.machine.time_efficiency
                     record.time_option=process.time_option
                     record.capacity_per_cycle=process.capacity_per_cycle_option
                     record.p_hour=process.hour
                     record.p_minute=process.minute
                     record.p_second =process.second
                     record.information_types='default'
                  else:
                     record.not_ok=True
               else:
                  record.information_types='default'
                  record.not_ok=False
                  if record.capacity_type:
                     record.time_option=record.capacity_type.time_option
                     record.capacity_per_cycle= record.capacity_type.capacity_per_cycle
                     record.p_hour=record.capacity_type.hour
                     record.p_minute=record.capacity_type.minute
                     record.p_second =record.capacity_type.second
              
               order=self.env['mrp.production.workcenter.line'].search([('machine','=',record.machine.id),('state','in',('draft','startworking','pause','ready')), ('name','!=', record.name)])
               lst=[]
               
               if record.capacity_per_cycle:
                  hr=(record.p_hour * 60 *60)  +(record.p_minute*60 + record.p_second)
                  time_cycle=hr * 0.000277778
                  cycle=float(record.wk_required_qty/(record.capacity_per_cycle * int(record.time_option if record.time_option else 1.0 )))
                  hour=(cycle *(time_cycle)) *(record.time_efficiency or 1.0) +((record.machine.time_start or 0.0) +(record.machine.time_stop or 0.0))
                  record.hour=hour
                  record.cycle=cycle
               for rec in order:
                   lst.append((0,0,{'name':rec.name, 'state':rec.state, 'date_planned':rec.date_planned,
                            'production_id':rec.production_id.id,'product':rec.product.id,'qty':rec.qty,
                            'uom':rec.uom.id,'workcenter_id':rec.workcenter_id.id,'cycle':rec.cycle,
                            'hour':rec.hour,'machine':rec.machine.id,'date_planned_end':rec.date_planned_end}))
               record.m_schedule_ids=lst
            if record.machine and record.process_id.process_type == 'raw':
                if record.machine_capacity_type == 'product':
                  process=self.env['product.template.process'].search([('workcenter_id','=',record.workcenter_id.id),('product_id','=',record.product.product_tmpl_id.id)], limit=1)
                  if process:
                     record.each_batch_qty=process.capacity_per_cycle_option
                else:
                  if record.capacity_type:
                     record.each_batch_qty= record.capacity_type.capacity_per_cycle
                  else:
                     record.each_batch_qty=record.capacity_per_cycle
                record.req_uom_id=record.wk_required_uom.id
 
    @api.multi
    def schedule_date_workorder(self):
        
	order_form = self.env.ref('gt_order_mgnt.manufacturing_date_history_form_view', False)
	context = self._context.copy()
	context.update({'default_wo_schedule_planned':self.date_planned, 'default_work_order_id':self.id,
                       'default_wo_schedule_planned_end':self.date_planned_end})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.complete.date',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,}    

    @api.multi
    def issue_batchnumber(self):
        for record in self:
            if not record.req_product_qty:
               raise UserError(_("Please Fill the Required Batch No. for Batch Numbers Issue....."))
            else:
               name=record.name[8:11]
               pr_no=record.production_id.name[:7]
               b_list=[]
               body='<b>New Batch Numbers Issue In Work Order:</b>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> Work Order No. : '+str(record.name) +'</li></ul>'
               body +='<ul><li> Issued By   : '+str(self.env.user.name) +'</li></ul>' 
               body +='<ul><li> Issued Time : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
               body +='<ul><li> Batch Numbers: '
               req=batch_qty=0.0
               if not record.batch_ids:
                  req=record.wk_required_qty 
               else:
                    for batch in record.batch_ids:
                        if batch.product_qty != 0:
                           batch_qty +=batch.req_product_qty
                    req=(record.wk_required_qty -batch_qty)
               wastage_qty=0.0
               if record.production_id.bom_id.bom_wastage_ids:
                  for bom_wastage in record.production_id.bom_id.bom_wastage_ids:
                      if bom_wastage.workcenter_id.id == record.workcenter_id.id:
                         wastage_qty=(record.wk_required_qty *((record.product.weight)*bom_wastage.value ) /100)
               for x in range(0, record.req_product_qty if record.req_product_qty < 10 else 10 ): 
                   qty=0.0
                   if req >  record.each_batch_qty:
                      qty= record.each_batch_qty
                   else:
                      qty=req
                   code = self.env['ir.sequence'].next_by_code('mrp.order.batch.number') or 'New'
                   final_code= str(pr_no)+'-'+str(code)#str(pr_no)+str(name)+str(code)
                   batch=self.env['mrp.order.batch.number'].create({'name':final_code,'product_id':record.product.id,
                                       'production_id':record.production_id.id,
                                       'sale_line_id':record.production_id.sale_line.id if record.production_id.sale_line else False,
                                       'order_id':record.id,'uom_id':record.wk_required_uom.id,
                                       'machine':record.machine.id,'wastage_allow':wastage_qty,
                                       'req_product_qty':qty})
                   req -=record.each_batch_qty
                   b_list.append(batch.id)
                   body +=str(batch.name)+' '
               body +='</li></ul>' 
               record.batch_ids=b_list
               record.issue_bool=True
               #record.write({'batch_ids':[(6,0, b_list)],'issue_bool':True})
               record.message_post(body=body)
               record.production_id.message_post(body=body)
   
    @api.multi
    def split_order(self):
        context = self._context.copy() 
        flag=False
        self_process_ids=self.env['mrp.production.workcenter.line'].search([('production_id','=',self.production_id.id),('workcenter_id','=',self.workcenter_id.id)])
        rq_qty=0.0
	for self_process in self_process_ids:
		workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',self_process.id)])
                if workorder:
                   per=round(self.wk_required_qty /100, 6)
                   for raw in workorder.raw_materials_id.search([('next_order_id','=',self.id)],limit=1):
                        print"llllllllllll",raw.qty,raw.receive_qty
                        one_qty=self.wk_required_qty /round(raw.qty,2)
                        one_per=round(raw.receive_qty/per, 6)
                        rq_qty =round(one_qty * raw.receive_qty,2)
                       	'''if raw.next_order_id.id == self.id:
                       		one_qty=self.wk_required_qty /round(raw.qty,2)
                                one_per=round(raw.receive_qty/per, 6)
                                print"YYyyyy",(raw.qty/self.wk_required_qty),round(raw.receive_qty/(raw.qty/self.wk_required_qty),2)
                                print"TTTTTTTTTTTtttt",self.wk_required_qty,raw.qty,one_qty,raw.receive_qty, one_per ,one_per*raw.receive_qty
                       	        rq_qty =round(one_qty * raw.receive_qty,2)'''
                   print"yyyyyyyyyyyyy",rq_qty 
                   flag=True
        context.update({'default_order_id':self.id, 
                        'default_product':self.product.id,'default_uom':self.wk_required_uom.id,
                        'default_qty':(self.wk_required_qty-self.total_product_qty) if self.total_product_qty else self.wk_required_qty,
                        'default_received_qty':(rq_qty-self.total_product_qty) if self.total_product_qty else rq_qty,
                        'default_received_uom':self.wk_required_uom.id,
                        'default_remain_received_uom':self.wk_required_uom.id,
                        'default_hide_rm':flag,
                        'default_split_uom':self.wk_required_uom.id,
                        'default_split_qty':self.total_product_qty if self._context.get('change') else 0.0,
                        'default_wk_capacity_type':self.wk_capacity_type,
                        'default_capacity_per_cycle':self.capacity_per_cycle,
                        'default_p_hour':self.p_hour,'default_p_minute':self.p_minute,
                        'default_p_second':self.p_second,
                        'default_production_id':self.production_id.id, 
                        'default_workcenter_id':self.workcenter_id.id})
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_split_form', False)
        if mo_form:
                return {
                    'name':'Work Order Split Form',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.workorder.split',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
             }
             
    @api.multi
    def action_pause_order(self):
        context = self._context.copy()
        context.update({'default_order_id':self.id, 'default_machine':self.machine.id,
                        'default_production_id':self.production_id.id})
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_pause_form', False)
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.order.machine.pause',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
             }

    @api.multi
    def action_resume(self):
        res=super(MrpWorkcenterPructionline,self).action_resume()
        pause=self.env['mrp.order.machine.pause'].search([('state','=','pause'),('order_id','=',self.id)],limit=1)
        if pause:
           pause.date_end=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
           pause.state='resume'
        self.machine.status='active'
        play_his=self.env['mrp.order.machine.pause'].create({'production_id':self.production_id.id,
                                    'order_id':self.id, 'product_id':self.product.id,
                                    'machine':self.machine.id, 'state':'play'})
        if not self.machine.running_workorder_id:
           self.machine.running_workorder_id=self.id
        if not self.machine.running_production_id:
           self.machine.running_production_id=self.production_id.id
        body='<b>Work Order Restart:</b>'
        body +='<ul><li> Work Order No. : '+str(self.name) +'</li></ul>'
        body +='<ul><li> Restart By    : '+str(self.env.user.name) +'</li></ul>' 
        body +='<ul><li> Time          : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
        self.message_post(body=body)
        self.production_id.message_post(body=body)
        return res

    @api.multi
    def change_machine(self):
	context = self._context.copy()
	context.update({'default_production_id':self.production_id.id, 'default_order_id':self.id,
                        'default_machine':self.machine.id ,'default_workcenter_id':self.workcenter_id.id})
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_machine_change_form', False)
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.order.machine.change',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
             }
             
#    @api.multi       
#    def action_done(self):
#        """ Sets state to done, writes finish date and calculates delay.
#        @return: True
        #"""
#        for rec in self:
#            delay = 0.0
#            date_now = time.strftime('%Y-%m-%d %H:%M:%S')
#
#            date_start = datetime.strptime(rec.date_start,'%Y-%m-%d %H:%M:%S')
#            date_finished = datetime.strptime(date_now,'%Y-%m-%d %H:%M:%S')
#            delay += (date_finished-date_start).days * 24
#            delay += (date_finished-date_start).seconds / float(60*60)
#
#            rec.write({'state':'done', 'date_finished': date_now,'delay':delay}, context=context)
##        self.modify_production_order_state(cr,uid,ids,'done')
#        return True
    @api.multi
    def action_start_working(self):
        res=super(MrpWorkcenterPructionline,self).action_start_working()
        for rec in self:
            if rec.production_id.state not in ('ready','in_production'):
                raise UserError(_('Cannot Start Work Order as MO is not in Ready to produce!!'))
            rec.production_id.state='in_production'
            if rec.production_id.request_line:
                rec.production_id.request_line.n_state='manufacture'
            rec.production_id.state='in_production'
        return res
             
    '''@api.multi
    def action_start_working(self):
        for record in self:
            workorder=self.env['mrp.production.workcenter.line']
            for product in record.raw_materials_id:
                   for line in record.production_id.product_lines:
                   	if product.product_id.id == line.product_id.id:
           			if not line.receive_qty:
           				raise UserError(_("Raw Materials Qty not Received in Mrp Raw Material Location.."))
                   		if line.consumed_qty >= line.receive_qty: 
                         		raise UserError(_("Received raw-materials quantity is used in Production, need more raw material quantity for start this workorder"))
            if record.hold_order == 'hold':
               raise UserError("Manufacturing Order Hold by Production Department.Before Start work order please confirmed to Production Department.")

            order=''
            if record.parent_id :
                order=workorder.search([('production_id','=',record.production_id.id),('next_order_id','=',record.parent_id.id)])
            else:
                order=workorder.search([('production_id','=',record.production_id.id),('next_order_id','=',record.id)])
            for wk_order in order:
                if wk_order.state in ('startworking','pause','cancel','done'):
                   break;
                else:
                   raise UserError(_("Previous Work Order not started.Please First Start Previous Work Order."))
            if record.machine:
               m_order=workorder.search([('state','in',('startworking',)),('machine','=',self.machine.id),('id','!=',record.id)], limit=1)
               if m_order:
                  raise UserError(_("Machine Busy In Work Order(%s) of Manufacturing Order No(%s)..")%(m_order.name,m_order.production_id.name))
               else:
                  play_his=self.env['mrp.order.machine.pause'].create({'production_id':record.production_id.id,
                                    'order_id':record.id, 'product_id':record.product.id,
                                    'machine':record.machine.id, 'state':'play'})
                  record.machine.status = 'active'
                  record.machine.running_workorder_id=record.id
                  record.machine.running_production_id=record.production_id.id
            body='<b>Work Order start:</b>'
            body +='<ul><li> Production No. : '+str(self.production_id.name) +'</li></ul>'
            body +='<ul><li> Work Order No. : '+str(self.name) +'</li></ul>'
            body +='<ul><li> Restart By    : '+str(self.env.user.name) +'</li></ul>' 
            body +='<ul><li> Time          : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
            self.message_post(body=body)
            self.production_id.message_post(body=body)
            if record.process_id.process_type =='raw':
            	record.production_id.state='in_production'
            res=super(MrpWorkcenterPructionline,self).action_start_working()
            return res'''

    @api.multi
    def action_done(self):
        if self.hold_order == 'hold':
               raise UserError("Manufacturing Order Hold by Production Department.Before Finished please confirmed to Production Department.")
        if self.machine.status == 'active':
           self.machine.status = 'inactive'
           self.machine.running_workorder_id=''
           self.machine.running_production_id=''
        body='<b>Work Order Finished:</b>'
        body +='<ul><li> Production No. : '+str(self.production_id.name) +'</li></ul>'
        body +='<ul><li> Work Order No. : '+str(self.name) +'</li></ul>'
        body +='<ul><li> Finished By    : '+str(self.env.user.name) +'</li></ul>' 
        body +='<ul><li> Time          : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
        self.message_post(body=body)
        self.production_id.message_post(body=body)
        res=super(MrpWorkcenterPructionline,self).action_done()
        return res

    @api.multi
    def machine_maintenance(self):
        order_form = self.env.ref('gt_order_mgnt.work_order_maintenance_form', False)
        context = self._context.copy()
        context.update({'default_production_id':self.production_id.id, 'default_workorder_id':self.id,
                        'default_machine_id':self.machine.id })
        return {
                    'name':'MRP work Order Maintenance Request',
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'mrp.work.order.maintenance',
		    'views': [(order_form.id, 'form')],
		    'view_id': order_form.id,
                   # 'res_id':main.id,
		    'target': 'new',
		    'context':context
           }
    
    @api.multi
    @api.depends('date_planned', 'hour')
    def endtime(self):
        for record in self:
            DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
            if record.date_planned:
               record.date_planned_end=datetime.strptime(record.date_planned, DATETIME_FORMAT) + timedelta(hours=record.hour)
               
    @api.multi
    def print_order(self):
        return self.env['report'].get_action(self, 'gt_order_mgnt.report_mrp_workorder')
        
    @api.multi
    def print_form(self):
        for record in self:
            if record.raw_materials_id:
               batch_qty=0.0
               for batch in record.batch_ids:
                   if batch.print_bool and batch.product_qty == 0:
                      batch_qty +=batch.req_product_qty
               for raw in record.raw_materials_id:
                    if raw.report_qty:
                       raw.report_qty=0.0
                       one_qty=(raw.qty/record.wk_required_qty)
                       raw.report_qty= one_qty *  batch_qty
                    else:
                       one_qty=(raw.qty/record.wk_required_qty)
                       raw.report_qty=round(one_qty * batch_qty , 2)   
        return self.env['report'].get_action(self, 'gt_order_mgnt.report_mrp_workorder_form')
        
    @api.multi
    def print_batch_barcode(self):
        if self.print_type=='normal':
            for line in self.batch_ids:
                res=self.env['report'].get_action(self, 'gt_order_mgnt.report_workorder_batch_number_barcode')
        elif self.print_type=='detailed':
            for line in self.batch_ids:
                res= self.env['report'].get_action(self, 'gt_order_mgnt.production_batch_details_print_wo')
        return res
    @api.multi
    def select_all(self):
        for record in self:
            if record.batch_ids:
               for rec in record.batch_ids:
                   if rec.print_bool==True:
                      rec.print_bool=False
                   else:
                       rec.print_bool=True
    @api.multi
    def print_batch_data(self):
        form_id = self.env.ref('gt_order_mgnt.print_batches_data_form_view')
        return {
                'name' :'Print Batches Data',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'print.batches.data',
                'views': [(form_id.id, 'form')],
                'view_id': form_id.id,
                'target': 'new',
#                'res_id':rec.picking_id.id,
            }
    @api.multi
    def issue_bulk_batch(self):
        form_id = self.env.ref('gt_order_mgnt.bulk_issue_batches_form_view')
        return {
                'name' :'Issue Bulk Batches',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'issue.bulk.batches',
                'views': [(form_id.id, 'form')],
                'view_id': form_id.id,
                'target': 'new',
            }
  
    @api.multi
    @api.depends('workcenter_id')
    def requiredunit(self):
        for record in self:
            if record.workcenter_id:  
               record.req_uom_id=record.workcenter_id.product_uom_id.id
    
    @api.multi
    @api.depends('batch_ids')
    def total_producedqty(self):
        for record in self: 
            if record.batch_ids:
               record.total_product_qty=sum(line.product_qty for line in record.batch_ids)
               record.total_uom_id=record.batch_ids[0].uom_id.id
    @api.multi
    @api.depends('req_product_qty')
    def compute_req_qty(self):
        for record in self: 
            if record.req_product_qty:
               record.req_product_qty_comp=record.req_product_qty
    
    @api.multi
    @api.depends('sequence')
    def compute_first_wo(self):
        for record in self: 
            if record.sequence==1:
               record.first_order=True
            else:
               record.first_order=False
    
    
    date_planned_end=fields.Datetime(compute='endtime')
    user_ids=fields.Many2many('res.users', string='Assign To')
    total_product_qty=fields.Float('Total Produced Qty', compute='total_producedqty')
    total_uom_id=fields.Many2one('product.uom', string='Required Product Unit',compute='total_producedqty')
    uom = fields.Many2one('product.uom', 'UoM',related='production_id.product_uom',store=True)


    duration=fields.Float('Duration')
    m_change=fields.Boolean('Machine Change', deafult=False)
    warning_mess=fields.Boolean('Warning', compute='extra_batch_compute')
    working_machine = fields.Many2one('machinery', string='Change Machine', )
    
    maintenance_id=fields.Many2one('machine.maintenance', string='Maintenance Request No.')
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    machine = fields.Many2one('machinery', string='Machine')   #shoud be repalce with machine_id
    machine_id= fields.Many2one('product.template','Machine Name') # new added for Machine
    
    process_id=fields.Many2one('mrp.workcenter.process',string="Process Type",related='workcenter_id.process_id' )
    time_option=fields.Selection([('1','1x'),('2','2x'),('3','3x'),
                               ('4', '4x'),('5', '5x')], string='Production Output', default='1')
    remark=fields.Text('Remark')
    req_product_qty = fields.Integer('Required Batch Qty')
    req_product_qty_comp = fields.Integer('Required Batch Qty',compute='compute_req_qty')
    each_batch_qty = fields.Integer('Each Batch Qty')
    print_type=fields.Selection([('normal','Normal'),('detailed','Detailed')], default='normal', string='Print Type')    
    req_uom_id=fields.Many2one('product.uom')
    batch_ids=fields.Many2many('mrp.order.batch.number',string='Batch No.') 
    batch_no_ids_prev=fields.One2many('mrp.order.batch.number', 'next_order_id',string='Batch Details')
    produce_ids=fields.One2many('mrp.order.machine.produce','order_id',string='Batch No.')
    extra_batch=fields.Integer('Extra Batch')
    issue_bool=fields.Boolean(Default=False)
    extra_bool=fields.Boolean(Default=False)
    machine_breakdown=fields.Boolean('Machine BreakDown', default=False)
    maintenace_count=fields.Integer("Work Orders Count", compute='count_maintenace')
    schedule_id=fields.Many2one('mrp.production.workcenter.line.schedule')
    total_wastage_qty=fields.Float('Total Wastage Qty', compute='total_wastageqty')
    wastage_uom_id=fields.Many2one('product.uom', compute='total_wastageqty') 
    batch_unit=fields.Char('Batch Unit')
    new_end_date=fields.Datetime('End Date')
    next_order_id=fields.Many2one('mrp.production.workcenter.line', string='Next Work Order')
    shift_order_id=fields.Many2one('mrp.production.workcenter.line', string='Parent Shift No.')
    shift_child_order_id=fields.Many2one('mrp.production.workcenter.line', string='Child Shift No.')
    time_efficiency=fields.Float('Efficiency Factor', default=1.0, related='machine.time_efficiency')
    machine_type_ids=fields.Many2many('machinery.type', string="Machine Type", related='workcenter_id.machine_type_ids')
    capacity_per_cycle=fields.Float('Capacity Per Cycle',)
    p_hour=fields.Integer('Hour',help="Please Enter Value less than 60")
    p_minute=fields.Integer('Minute',help="Please Enter Value less than 60")
    p_second=fields.Integer('Second',help="Please Enter Value less than 60")
    wk_capacity_type=fields.Selection([('product','Product'),('custom','Custom'),('next','Process')] ,
                       string='Capacity Type', default='product')
    m_schedule_ids=fields.One2many('mrp.production.workcenter.line.schedule','order_id',string='Schedule Details')
    shift_time=fields.Float("Shift Time")
    capacity_unit=fields.Many2one('product.uom', related='workcenter_id.product_uom_id', string='Unit')
    jobcard_ids=fields.One2many('mrp.work.order.jobcard','order_id',string='Job Card Details')
    mo_date_planned=fields.Datetime('Manufactuirng Schedule Date' ,compute='Mo_date')
    mo_date_completed=fields.Datetime('Manufacturing EC Date',compute='Mo_date')
    mo_date_request=fields.Datetime('Required By Date',compute='Mo_date') 

    mrp_sec_qty = fields.Float('Secondary Quantity',related='production_id.mrp_sec_qty')
    mrp_sec_uom = fields.Many2one('product.uom', 'Secondary Unit',related='production_id.mrp_sec_uom')
    mrp_third_qty = fields.Float('Third Quantity', related='production_id.mrp_third_qty')
    mrp_third_uom = fields.Many2one('product.uom', 'Third Unit', related='production_id.mrp_third_uom')
    mrp_third_qty_sheet = fields.Float('Third Quantity', related='production_id.mrp_third_qty_sheet')
    mrp_third_uom_sheet= fields.Many2one('product.uom', 'Third Unit',related='production_id.mrp_third_uom_sheet') 
  
    parent_id=fields.Many2one('mrp.production.workcenter.line', string='Parent Work Order No.')
    split_work_ids=fields.One2many('mrp.production.workcenter.line','parent_id', string='Split Work Orders')
    process_type=fields.Selection([('raw','Raw Material'),('film','Film (Extrusion)'),('cutting','Cutting'),
              ('ptube', 'Printing in Tube'), ('psheet', 'Printing in Sheet'),('other', 'Others'),
               ('injection', 'Injection')], related='process_id.process_type', string='Type')
    shift_required=fields.Float('Shift Required', compute='cal_shift', digits_compute=dp.get_precision('Product Unit of Measure'))
    shift_produced=fields.Float('Shift Completed',compute='cal_shift', digits_compute=dp.get_precision('Product Unit of Measure'))  
    wk_required_qty = fields.Float('Required Quantity')
    wk_required_uom = fields.Many2one('product.uom')
    n_packaging = fields.Many2one('product.packaging' ,string="Package Type")
    wk_rm_qty=fields.Float('Remaining Qty', compute='Rmqty')
    capacity_per_cycle_kg=fields.Float('Capacity Per Cycle KG', compute='Capacity_kg')
   # capacity_per_cycle_change=fields.Float('Capacity Per Cycle Change', compute='capacitychange')
    capacity_per_cycle_kg_current=fields.Float('Capacity Per Cycle Current KG')
    machine_capacity_type=fields.Selection([('product','Product Base'),('machine','Machine Base')],string='Capacity Calculation Type', related='machine.capacity_type')
    capacity_type=fields.Many2one('machinery.capacity.type', string='Machine Type')
    not_ok=fields.Boolean()
    shift_base_qty=fields.Float('Each Shift Base qty', compute='shiftqty')
    shift_base_uom = fields.Many2one('product.uom', related='wk_required_uom')
    workorder_type=fields.Selection([('master','Master'),('child','Child'),('both','Master&Child')],default='master', string='Work Order Type')
    information_types=fields.Selection([('default','Default'),('custom','Custom')], string='Type')
    
    machine_show=fields.Boolean(default=False)
    hold_order=fields.Selection([('active','Active'),('hold','Hold')],default='active', string='Order Status')
    order_last=fields.Boolean('Last Order', default=False)
    first_order=fields.Boolean('First Work Order', default=False,compute='compute_first_wo',store=True)
    partner_id=fields.Many2one('res.partner', 'Customer Name', related='production_id.partner_id')
    wk_planned_status=fields.Selection([('unplanned','Unplanned'),('partial','Partial planned'),
                                     ('fully','Fully Planned'),('maintenace','Machine Maintenance'),
                                    ('hold','Hold')], default='unplanned', string='planned Status')

    index_seq = fields.Integer(compute='_compute_index')
    
    pause_ids=fields.One2many('mrp.order.machine.pause','order_id')

    #rm_delivery_id=fields.Many2one('stock.picking', string='Transfer Order No.')   
    #next_work_orders=fields.One2many('mrp.production.workcenter.line','next_order_id', string='Next Work Orders')
    self_id=fields.Many2one('mrp.production.workcenter.line')
    product_sepcification_ids=fields.One2many('workorder.product.discription','order_id',string='Product Specification')
    state = fields.Selection([('draft','Draft'),('pause','Pause'),('hold','On Hold'),('ready','Ready'),
    				('startworking', 'In Progress'),('done','Finished'),('cancel','Cancelled'),],
    				'Status', readonly=True, copy=False,
         help="* When a work order is created it is set in 'Draft' status.\n" \
         	"* When the user set Lock the work order it will be set in 'Ready' status.\n" \
               "* When user sets work order in start mode that time it will be set in 'In Progress' status.\n" \
               "* When work order is in running mode, during that time if user wants to stop or to make changes in order then can set in 'Pending' status.\n" \
               "* When the user hold the work order it will be set in 'On Hold' status.\n" \
               "* When the user cancels the work order it will be set in 'Canceled' status.\n" \
               "* When order is completely processed that time it is set in 'Finished' status.")
    hold_state = fields.Selection([('draft','Draft'),('cancel','Cancelled'),
    				('pause','Pause'),('hold','On Hold'),
    				('startworking', 'In Progress'),('done','Finished')],
    				'Previous status', readonly=True,help="this field is used for maintaining previous status before hold")
    employee_ids=fields.Many2many('hr.employee', string='Operators')
    cutting_pac_qty=fields.Char(compute='cutting_pack')
    production_state=fields.Selection(
            [('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'),('requestrm', 'Raw Materials Requested'),('rmr', 'Raw Materials Rejected'), ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('done', 'Done')],
            string='Production Status',related='production_id.state',store=True, readonly=True)
  
    @api.multi
    @api.depends('req_uom_id')
    def cutting_pack(self):
        for order in self:
            if order.req_uom_id.name == 'Kg':
               pack_qty=round(((order.production_id.n_packaging.qty) / order.product.weight), 2) if order.production_id.n_packaging else 0.0  
               order.cutting_pac_qty=str(pack_qty)+str('Pcs')
               print"+==============",str(pack_qty)
            else:
               pack_qty=round(((order.production_id.n_packaging.qty) * order.product.weight), 2)  if order.production_id.n_packaging else 0.0
               order.cutting_pac_qty=str(pack_qty)+str('Kg')
               print"+==ffffffffffff=====",str(pack_qty), order.production_id.n_packaging.qty

    @api.multi
    @api.onchange('information_types')
    def informationtypes(self):
        for record in self:
            if record.information_types == 'custom':
               pass #record.capacity_type=''  
            else:
               if record.machine_capacity_type == 'product':
                  process=self.env['product.template.process'].search([('workcenter_id','=',record.workcenter_id.id),('product_id','=',record.product.product_tmpl_id.id)], limit=1)
                  if process:
                     record.time_efficiency=record.machine.time_efficiency
                     record.time_option=process.time_option
                     record.capacity_per_cycle=process.capacity_per_cycle_option
                     record.p_hour=process.hour
                     record.p_minute=process.minute
                     record.p_second =process.second
 
    @api.multi
    @api.depends('batch_ids')
    def total_wastageqty(self):
        for record in self: 
            if record.batch_ids:
               record.total_wastage_qty=sum(line.wastage_qty for line in record.batch_ids)
               record.wastage_uom_id=record.batch_ids[0].allow_wastage_uom_id.id

    @api.one
    @api.depends('sequence')
    def _compute_index(self):
        if self.sequence:
           self.index_seq=self.sequence
       
    @api.multi
    @api.depends('wk_required_qty','total_product_qty')
    def Rmqty(self):
      for record in self:
          record.wk_rm_qty =record.wk_required_qty
          if record.wk_required_qty and record.total_product_qty:
             record.wk_rm_qty =record.wk_required_qty - record.total_product_qty
    
    @api.multi
    @api.depends('capacity_per_cycle','shift_time','p_hour','p_minute','p_second', 'time_option')
    def shiftqty(self):
        for record in self:
            if record.capacity_per_cycle and record.shift_time:
               hr=(record.p_hour * 60 *60)  +(record.p_minute*60 + record.p_second)
	       time_hr=(hr * 0.000277778)
               in_one_hr=((record.capacity_per_cycle * float(record.time_option or 1))/time_hr if time_hr else 1)
               record.shift_base_qty=round(in_one_hr * record.shift_time,2)

    @api.multi
    @api.depends('capacity_per_cycle')
    def Capacity_kg(self):
        for record in self:
            if record.capacity_per_cycle:
               cap=0.0
               ln=wd=lt=rt=tp=bm=0.0
               for des in record.product.discription_line:
                       if des.attribute.name == 'Length':
                          ln =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Width':
                          wd =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Left gusset':
                          lt =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Right gusset':
                          rt =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Top Fold':
                          tp =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Bottom gusset':
                          bm =float(des.value)
               if record.capacity_unit.name =='m' and record.process_type == 'ptube':
                  pcs=(record.capacity_per_cycle * 100) /(ln+tp+bm)
                  cap=pcs * record.product.weight
               if record.capacity_unit.name =='m' and record.process_type == 'psheet':
                  pcs=(record.capacity_per_cycle * 100) /(wd+lt+rt)  
                  cap=pcs * record.product.weight
               if record.capacity_unit.name =='Pcs':
                  cap=(record.capacity_per_cycle * record.product.weight)
               if record.capacity_unit.name =='Kg':
                  cap=(record.capacity_per_cycle)
               record.capacity_per_cycle_kg=cap

    @api.multi
    @api.onchange('capacity_per_cycle', 'p_hour','p_minute','p_second', 'time_option','machine.time_efficiency', 'shift_time')
    def cycle_info(self): 
        for record in self:
		    
            if record.capacity_per_cycle:
               hr=(record.p_hour * 60 *60)  +(record.p_minute*60 + record.p_second)
               time_cycle= (hr*0.000277778)
               capacity= record.capacity_per_cycle * (int(record.time_option) if record.time_option else 1)
               cycle=float(record.wk_required_qty/capacity)
               hour=(cycle *(time_cycle)) *(record.machine.time_efficiency or 1.0) +((record.machine.time_start or 0.0) +(record.machine.time_stop or 0.0))
               record.hour=hour
               record.cycle=cycle
            if record.capacity_per_cycle and record.process_id.process_type == 'raw':
               record.each_batch_qty=record.capacity_per_cycle
               record.req_uom_id=record.wk_required_uom.id
                  
    @api.multi
    @api.depends('capacity_per_cycle','p_hour','p_minute','p_second','time_option','machine.time_efficiency', 'shift_time')
    def cal_shift(self):
        for record in self:
              if record.capacity_per_cycle and record.shift_time:#and record.process_id.process_type != 'raw' :
                    shift_time=record.shift_time * 3600
		    hr=(record.p_hour * 60 *60)  +(record.p_minute*60 + record.p_second)
		    time_cycle=record.cycle * (hr * 0.000277778)
		    
		    time_option = int(record.time_option) if record.time_option else 1
		    capacity= record.wk_required_qty / (int(record.capacity_per_cycle) * int(time_option) )
		    hours = (capacity * hr)/3600
		    record.shift_required= hours / record.shift_time
                    if record.shift_required:
		       record.shift_produced=record.total_product_qty/(record.wk_required_qty/record.shift_required)  if  record.total_product_qty else 0.0
                    else:
                       record.shift_produced=0.0
                    
      
    @api.multi
    def open_calendar(self):
        context = self._context.copy()
        context.update({'default_production_id':self.production_id.id,'default_workcenter_id':self.workcenter_id.id,
                      'default_process_id':self.process_id.id, 'default_capacity_per_cycle':self.capacity_per_cycle,
                      'default_p_hour':self.p_hour,'default_p_minute':self.p_minute, 'default_p_second':self.p_second,
                      'default_name':self.name, 'default_wk_capacity_type':'custom','default_machine_show':True,
                        'default_product':self.product.id, 'default_qty':self.qty,
                        'default_user_ids':self.user_ids.ids,'default_time_option':self.time_option,
                        'mo_cal':True , 'prev_workorder_id':self.id ,'default_order_id':self.id,
                        'default_wk_required_qty':self.wk_required_qty,'default_machine':self.machine.id,
                        'default_capacity_type':self.capacity_type.id,
                        'default_wk_required_uom':self.wk_required_uom.id})
        for line in self:
            order_cal_tree = self.env.ref('stock_merge_picking.view_mrp_machine_calendar_inherite', False)
            order_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
            if order_cal_tree:
                
                return {
                    'name':'Check Machine Schedule',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'calendar,',
                    'res_model': 'mrp.production.workcenter.line',
                    'views': [(order_cal_tree.id, 'calendar'),(order_form.id, 'form')],
                    'view_id': order_cal_tree.id, 
                    'target': 'current',
                    'domain':[('workcenter_id','=',line.workcenter_id.id)],
                    'context':context
                }
        return True

    @api.multi
    def change_state(self):
        for res in self:
        	if self._context.get('ready'):
#                    need to uncomment while gng live for bom
#                        if res.production_id.state not in ('ready','in_production'):
#                            raise UserError(_('Cannot Lock Work Order as MO is not in Ready to produce or Production state!!'))

#                        if not res.machine:
#		          raise UserError(_('Please Select Machine Before Lock Work order..'))
		        if not res.req_product_qty and not res.each_batch_qty:
		           raise UserError(_("Please Fill the Required Batch No. and Each Batch Qty..."))
                        if not res.batch_ids:
                           res.issue_batchnumber()
        		res.state='ready'
		elif self._context.get('draft'):
        		res.state='draft'
		if res.process_id == 'raw':
			date_dic={}
			ndate_dic={}
			for line in res.workorder_shifts:
				if not date_dic.get(line.workorder_id.id):
					date_dic.update({line.workorder_id.id:line.workorder_id.date_planned})
			for rec in res.workorder_shifts:
				date=date_dic.get(line.workorder_id.id)
				if date:
					
					time=6+rec.shift_time
					date=datetime.strptime(date,'%Y-%m-%d %H:%M:%S')-timedelta(hours=time)
					rec.start_time = date
					ndate_dic.update({line.workorder_id.id:rec.start_time})
					
                body='<b>Work Order Locked:</b>'
                body +='<ul><li> Work Order No.: '+str(res.name) +'</li></ul>' 
                body +='<ul><li> Locked By    : '+str(self.env.user.name) +'</li></ul>' 
                body +='<ul><li> Locked Time  : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
                res.message_post(body=body)
                res.production_id.message_post(body=body)

        return True
         
    @api.multi
    @api.depends('production_id')
    def Mo_date(self):
        for record in self:
            if record.production_id:
               record.mo_date_planned=record.production_id.date_planned
               record.mo_date_completed=record.production_id.n_request_date  
               record.mo_date_request=record.production_id.n_client_date
    @api.multi
    @api.onchange('each_batch_qty')
    def batch_detail(self):
        for record in self:
            if record.each_batch_qty:
               qty=0.0
               if record.process_type == 'cutting':
                  if record.req_uom_id.name == 'Kg':
                     qty=record.qty
                  else:
                     qty=record.wk_required_qty 
                     print "qtyqtyqty",qty
               else:
                   qty=record.wk_required_qty 
               record.req_product_qty= math.ceil(qty /record.each_batch_qty)
               record.req_uom_id=record.wk_required_uom.id
          
    @api.multi
    def count_maintenace(self):
        for record in self:
            main=self.env['machine.maintenance'].search([('workorder_id','=',record.id)])
            record.maintenace_count=len(main)
    @api.multi
    def open_maintenace(self):
        for line in self:
            maintenace_tree = self.env.ref('gt_order_mgnt.machines_maintenance_tree', False)
            maintenace_form = self.env.ref('gt_order_mgnt.machines_maintenance_form', False)
            if maintenace_tree:
                return {
                    'name':'Work Orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'machine.maintenance',
                    'views': [(maintenace_tree.id, 'tree'),(maintenace_form.id, 'form')],
                    'view_id': maintenace_tree.id,
                    'target': 'current',
                    'domain':[('workorder_id','=',self.id)],
                }
        return True
        
    @api.multi
    def open_workorder(self):
        for line in self:
            order_tree = self.env.ref('mrp_operations.mrp_production_workcenter_tree_view_inherit', False)
            order_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
#            line.production_id.write({'state':'in_production'})
            if order_form:
                return {
                    'name':'Work Orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form,',
                    'res_model': 'mrp.production.workcenter.line',
                    'views': [(order_form.id, 'form'),(order_tree.id, 'tree')],
                    'view_id': order_form.id,
                    'res_id':line.id,
                    'target': 'current',
                    'domain':[('production_id','=',line.production_id.id)],
                   # 'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
                }
        return True
    @api.multi
    def extra_batchnumber(self):
        for record in self:
            if not record.extra_batch:
               raise UserError(_("Please Fill the Extra Batch No. for Batch Numbers Issue....."))
            else:
               name=record.name[8:11]
               pr_no=record.production_id.name[:7]
               b_list=[]
               '''next_order=0
               order=self.env['mrp.production.workcenter.line'].search([('production_id','=',record.production_id.id),('sequence','>',record.sequence)], limit=1)
               if order:
                  next_order=order.id'''
               body='<b>Extra Batch Numbers Create In Work Order:  </b>'
               body +='<ul><li> Work Order No. : '+str(record.name) +'</li></ul>'
               body +='<ul><li> Total Previous Batch  : '+str(record.req_product_qty) +'</li></ul>'
               body +='<ul><li> New Batch  : '+str(record.extra_batch) +'</li></ul>'
               body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
               body +='<ul><li> New Batch Numbers  : '
               wastage_qty=0.0
               if record.production_id.bom_id.bom_wastage_ids:
                  for bom_wastage in record.production_id.bom_id.bom_wastage_ids:
                      if bom_wastage.workcenter_id.id == record.workcenter_id.id:
                         wastage_qty=(record.wk_required_qty *((record.product.weight)*bom_wastage.value ) /100)
               for x in range(0, record.extra_batch):  
                   code = self.env['ir.sequence'].next_by_code('mrp.order.batch.number') or 'New'
                   final_code= str(pr_no)+'-'+str(code)#str(pr_no)+str(name)+str(code)
                   batch=self.env['mrp.order.batch.number'].create({'name':final_code,'product_id':record.product.id,
                                       'production_id':record.production_id.id, 'uom_id':record.req_uom_id.id,
                                        'req_product_qty':record.each_batch_qty, 'order_id':record.id,
                                        'machine':record.machine.id, 'wastage_allow':wastage_qty})
              
                   body += str(batch.name) +' '
               body +='</li></ul>'
               record.message_post(body=body)
               record.production_id.message_post(body=body)
               bt=self.env['mrp.order.batch.number'].search([('order_id', '=',record.id)])
               for btn in bt:
                   b_list.append(btn.id)
               record.batch_ids=[(6, 0,b_list)]
               record.extra_bool=True

class Machinery(models.Model):
    _name = "machinery"
    _description = "Holds records of Machines"

    def _def_company(self):
        return self.env.user.company_id.id
    
    name = fields.Char('Machine Name', required=True)
    company = fields.Many2one('res.company', 'Company', required=True,
                              default=_def_company)
    capacity_per_cycle=fields.Float('Capacity Per Cycle')
    hour=fields.Integer('Hour')
    minute=fields.Integer('Minute')
    second=fields.Integer('Second')
    time_cycle=fields.Float('Time Cycle')
    time_efficiency=fields.Float('Efficiency Factor')
    time_start=fields.Float('Loading Time(in hour)')
    time_stop=fields.Float('Unloading Time(in hour)')
    machine_type_ids=fields.Many2many('machinery.type' ,string="Machine Type")
    maintenance_ids=fields.One2many('machine.maintenance','machine_id',string='Maintenance Details')
    weight=fields.Float('Weight')
    note=fields.Text('Description')
    serial_no=fields.Char('Serial No.')
    assets_no=fields.Char('Assets No.')
    product_uom_id=fields.Many2one('product.uom',string='Unit')
    assetacc = fields.Many2one('account.account', string='Asset Account')
    depracc = fields.Many2one('account.account', string='Depreciation Account')
    year = fields.Char('Year')
    model = fields.Char('Model')
    product = fields.Many2many(
        comodel_name='product.product', string='Associated product',
        help="This product will contain information about the machine such as"
        " the manufacturer.")
    manufacturer = fields.Char('Manufacturer', help="Manufacturer is related to the associated product defined for the machine.")
    serial_char = fields.Char('Product Serial #')
    serial = fields.Many2one('stock.production.lot', string='Product Serial #',
                             )
    ##model_type = fields.Many2one('machine.model', 'Type')
    status = fields.Selection([('active', 'Active'), ('inactive', 'InActive'), ('pause', 'Pause'),
                               ('outofservice', 'Maintenance')],
                              'Status', required=True, default='inactive')
    ownership = fields.Selection([('own', 'Own'), ('lease', 'Lease'),
                                  ('rental', 'Rental')],
                                 'Ownership', default='own', required=True)
    bcyl = fields.Float('Base Cycles', digits=(16, 3),
                        help="Last recorded cycles")
    bdate = fields.Date('Record Date',
                        help="Date on which the cycles is recorded")
    purch_date = fields.Date('Purchase Date',
                             help="Machine's date of purchase")
    purch_cost = fields.Float('Purchase Value', digits=(16, 2))
    purch_partner = fields.Many2one('res.partner', 'Purchased From', domain=[('supplier','=',True)])
    purch_inv = fields.Many2one('account.invoice', string='Purchase Invoice')
    purch_cycles = fields.Integer('Cycles at Purchase')
    actcycles = fields.Integer('Actual Cycles')
    deprecperc = fields.Float('Depreciation in %', digits=(10, 2))
    deprecperiod = fields.Selection([('monthly', 'Monthly'),
                                     ('quarterly', 'Quarterly'),
                                     ('halfyearly', 'Half Yearly'),
                                     ('annual', 'Yearly')], 'Depr. period',
                                    default='annual', required=True)
    primarymeter = fields.Selection([('calendar', 'Calendar'),
                                     ('cycles', 'Cycles'),
                                     ('hourmeter', 'Hour Meter')],
                                    'Primary Meter', default='cycles',
                                    required=True)
    warrexp = fields.Date('Date', help="Expiry date for warranty of product")
    warrexpcy = fields.Integer('(or) cycles',
                               help="Expiry cycles for warranty of product")
    location = fields.Many2one('stock.location', 'Stk Location',
                               help="This association is necessary if you want"
                               " to make repair orders with the machine")
    enrolldate = fields.Date('Enrollment date', required=True,
                             default=lambda
                             self: fields.Date.context_today(self))
    ambit = fields.Selection([('local', 'Local'), ('national', 'National'),
                              ('international', 'International')],
                             'Ambit', default='local')
    work_ids=fields.One2many('mrp.production.workcenter.line', 'machine', string='Schedule Detail')
    card = fields.Char('Card')
    cardexp = fields.Date('Card Expiration')
    frame = fields.Char('Frame Number')
    phone = fields.Char('Phone number')
    mac = fields.Char('MAC Address')
    insurance = fields.Char('Insurance Name')
    policy = fields.Char('Machine policy')
    #users = fields.One2many('machinery.users', 'machine', 'Machine Users')
    power = fields.Char('Power (Kw)')
    product_categ = fields.Many2one('product.category', 'Internal category',
                                    related='product.categ_id')
    salvage_value = fields.Float('Salvage Value',
                                 digits=dp.get_precision('Product Price'))
    conflict_count=fields.Integer('Total Conflict', compute='total_conflict')
    shift_time=fields.Float("Shift Time")
    capacity_type=fields.Selection([('product','Product Base'),('machine','Machine Base')],string='Capacity Calculation Type')
    capacity_ids=fields.One2many('machinery.capacity.type','machine')
    running_workorder_id=fields.Many2one('mrp.production.workcenter.line', string='Running Work order No.')
    running_production_id=fields.Many2one('mrp.production', string='Running MO No.')
    shft_rq=fields.Float(compute='shift_calculation')
    shft_pr=fields.Float(compute='shift_calculation')
    machine_user_ids = fields.Many2many('res.users')
    employee_ids=fields.Many2many('hr.employee', string='Operators Name')

    @api.multi
    @api.onchange('machine_user_ids')
    def operators_list(self):
        for record in self:
            if record.machine_user_ids:
               lst=[]
               for user in record.machine_user_ids:
                   for operator in user.employee_ids:
                       lst.append((operator.id))
               record.employee_ids=lst
            else:
               record.employee_ids=[]
    @api.multi
    @api.depends('running_workorder_id.shift_required','running_workorder_id.shift_produced')
    def shift_calculation(self):
        for record in self:
            if record.running_workorder_id.shift_required:
               record.shft_rq=round(record.running_workorder_id.shift_required, 2)
            else:
               record.shft_rq=0.0
            if record.running_workorder_id.shift_produced:
               record.shft_pr=round(record.running_workorder_id.shift_produced, 2)
            else:
               record.shft_pr=0.0
    @api.multi
    def total_conflict(self):
      for record in self: 
        lst=[]
        work_order=self.env['mrp.production.workcenter.line']
        for order in work_order.search([('machine','=',record.id),('state','in',('draft','startworking','pause'))]): 
            for schedule in work_order.search([('machine','=',record.id),('state','in',('draft','startworking','pause'))]): 
                if order.date_planned > schedule.date_planned and order.date_planned < schedule.date_planned_end:
                   lst.append(schedule.id)
        val=work_order.search([('id','in',lst)])
        record.conflict_count=len(val)
      

    @api.multi
    def action_currentorder(self):
    	domain=[]
	wo_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
        if wo_form:
            return {
		'name':"Running Work order",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'from',
                'res_model': 'mrp.production.workcenter.line',
		'views': [(wo_form.id, 'form')],
                'view_id': wo_form.id,
                'target': 'new',
                'res_id':self.running_workorder_id.id,
		'domain':[('id','=',self.running_workorder_id.id)],
            }
    @api.multi
    def action_currentMo(self):
    	domain=[]
	mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        if mo_form:
            return {
		'name':"Running Manufaturing order",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'from',
                'res_model': 'mrp.production',
		'views': [(mo_form.id, 'form')],
                'view_id': mo_form.id,
                'target': 'new',
                'res_id':self.running_production_id.id,
		'domain':[('id','=',self.running_production_id.id)],
            }
    @api.multi
    def action_planning_workorders(self):
    	domain=[]
        name="Work Orders Planned By:" + '-'+str(self.name)
	mo_tree = self.env.ref('stock_merge_picking.view_mrp_order_calendar_inherite', False)
	mo_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
        if mo_tree:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'calendar',
                'res_model': 'mrp.production.workcenter.line',
		'views': [(mo_tree.id, 'calendar'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':[('machine','=',self.id)],
            }
    @api.multi
    def action_conflict_workorders(self):
        #term_qry="select id,machine,date_planned from mrp_production_workcenter_line where date_planned in (select date_planned from mrp_production_workcenter_line where machine ="+str(self.id)+" GROUP BY machine, date_planned HAVING count(*) >1) and machine ="+str(self.id)
        lst=[]    
	#self.env.cr.execute(term_qry)
	#schedule_date=([i[0] for i in self.env.cr.fetchall()])
        work_order=self.env['mrp.production.workcenter.line']
        domain=[('machine','=',self.id),('id','in',lst)]
        for order in work_order.search([('machine','=',self.id),('state','in',('draft','startworking','pause'))]):  
            for schedule in work_order.search([('machine','=',self.id),('state','in',('draft','startworking','pause'))]): 
                if order.date_planned > schedule.date_planned and order.date_planned < schedule.date_planned_end:
                   lst.append(order.id)
                   lst.append(schedule.id)
            #domain.append(('|'))
            #domain.append(('id','=',schedule.id))
            #workorder=self.env['mrp.production.workcenter.line'].search([('date_planned','=',schedule)])
            #print"==========+++++++++++",workorder
            #for wk_order in workorder:
        
        name="Work Orders Planned By:" + '-'+str(self.name)
	mo_tree = self.env.ref('stock_merge_picking.view_mrp_order_calendar_inherite', False)
	mo_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
        
        if mo_tree:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'calendar',
                'res_model': 'mrp.production.workcenter.line',
		'views': [(mo_tree.id, 'calendar'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context.get('order_machine'):
            if context.get('machine_type_ids') and context.get('machine_type_ids')[0] and context.get('machine_type_ids')[0][2]:
                args=[]
		product_ids=self.search(cr,uid,[('machine_type_ids','in',context.get('machine_type_ids')[0][2])])
                args.extend([('id','in',product_ids)])
        
        return super(Machinery,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
        
class MachineryCapacityType(models.Model):
    _name = "machinery.capacity.type"
    name=fields.Char('Name')
    capacity_per_cycle=fields.Float('Capacity Per Cycle')
    hour=fields.Integer('Hour')
    minute=fields.Integer('Minute')
    second=fields.Integer('Second')
    time_option=fields.Selection([('1','1x'),('2','2x'),('3','3x'),
                               ('4', '4x'),('5', '5x')], string='Production Output',default='1'
                                   )
    machine=fields.Many2one('machinery')
     
class MachineryType(models.Model):
    _name = "machinery.type"
    name=fields.Char('Name')
    is_human=fields.Boolean('Is Human')
    
class WorkorderProductDiscription(models.Model):
    _name = "workorder.product.discription"
	
    order_id = fields.Many2one('mrp.production.workcenter.line', 'Work Order Name')
    attribute = fields.Many2one('n.product.discription.value', 'Attributes')
    value=fields.Char('Product Discription')
    unit = fields.Many2one('product.uom', 'Unit')
    
