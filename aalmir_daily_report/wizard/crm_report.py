from datetime import datetime, timedelta
#import datetime
from openerp import tools
from openerp import models, fields, api, exceptions, _
from openerp.exceptions import ValidationError
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class CrmSummaryReport(models.Model):
    _name='crm.lead.summary'
    _description='CRM LEAD SUMMARY'
    today_create=fields.Char(' New ColdCalling Entries')
    today_contact=fields.Char('Clients Contacted in CC')
    today_interval_change=fields.Char('Interval Days Change')
    today_date_exceed=fields.Char('Date Exceed')
    user_id=fields.Many2one('res.users', string="Sales Person")
    from_date=fields.Datetime('Date')
    to_date=fields.Datetime('Date')
    today_sale=fields.Char('Total Sales Order Created')
    today_quatation=fields.Char(' Total Quotations Created')
    is_summary=fields.Boolean('Is Summary')
    today_Qualified=fields.Char('Qualified From CC')
    today_disqualified=fields.Char('DisQualified From CC')
    today_opportunity=fields.Char('New opportunities Created')
    day_target_allot=fields.Char('Daily Call Target')
    monthly_target_allot=fields.Char(' Monthly Sale Target')
    total_mails=fields.Char('Mailed')
    total_notifications=fields.Char('Notifications')
    total_calls=fields.Char('Called')
    quotation_total=fields.Float('Quotations Created Amount in AED')
    sale_total=fields.Float('Sales Order Created  Amount in AED')
    target_achieve=fields.Char('Target Achieved')
    mass_mail=fields.Char('Sent Mass Mail')
    total_lost_lead=fields.Char('Total Lost')

    @api.multi
    def views_crm_lead_create(self):
       for record in self:
           lead=self.env['crm.lead']
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('create_date','>=',n_date), ('stage_2','in', ['contacted','not_contacted','qualified','disqualified']),('create_date','<=',n_date1)]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'crm.lead',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
    @api.multi
    def views_crm_lead_contact(self):
       for record in self:
           lead=self.env['crm.lead']
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('last_contacted','>=',n_date),('last_contacted','<=',n_date1),('stage_2','in', ['contacted','not_contacted','qualified','disqualified'])]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'crm.lead',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
    #### add opportunity
    @api.multi
    def get_opportunity(self):
        for record in self:
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('type','=','opportunity'),('stage_id.name','!=','Merge'),('lead_create_date','>=',n_date),('lead_create_date','<=',n_date1)]
        return {
            'name': 'Opportunity',
            'view_mode': 'tree',
            'res_model': 'crm.lead',
            'view_id': self.env.ref('crm.crm_case_tree_view_oppor').id,
            'type': 'ir.actions.act_window',
            'target' : 'new',
            'domain': domain,
           # 'context' : {'active_id' : self.id, 'active_ids' : [self.id], 'active_model': 'crm.lead', 'from_cold_calling' : True}
        }
    ###### Add lost lead

    @api.multi
    def get_lost_lead(self):
        for record in self:
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('stage_id.name', '=', 'Lost'),('user_id','=', record.user_id.id),('create_date','>=',n_date),('create_date','<=',n_date1)]
           print"DOmain",domain
        return {
            'name': 'Lost Lead',
            'view_mode': 'tree',
            'res_model': 'crm.lead',
            'view_id': self.env.ref('crm.crm_case_tree_view_oppor').id,
            'type': 'ir.actions.act_window',
            'target' : 'new',
            'domain': domain,
        }
    @api.multi      
    def views_crm_lead_qualified(self):
       for record in self:
           lead=self.env['crm.lead']
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('qualified_date','>=',n_date),('qualified_date','<=',n_date1),('coldcalling_bool','=', True)]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'crm.lead',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
    
    @api.multi
    def views_crm_lead_disqualified(self):
       for record in self:
           lead=self.env['crm.lead']
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('disqualified_date','>=',n_date),('disqualified_date','<=',n_date1)]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'crm.lead',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
    @api.multi
    def views_crm_lead_quotation(self):
       for record in self:
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('create_date','>=',n_date),('create_date','<=',n_date1), ('state','in', ['draft', 'sent'])]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'sale.order',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
    @api.multi
    def views_crm_lead_sale(self):
       for record in self:
           n_date=datetime.strftime(datetime.strptime(record.from_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 00:00:00')           
	   n_date1=datetime.strftime(datetime.strptime(record.to_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d 23:59:59')
           domain=[('user_id','=', record.user_id.id),('date_order','>=',n_date),('date_order','<=',n_date1), ('state','in', ['sale', 'done'])]
       return {
         'type': 'ir.actions.act_window',
         'name': _('Lead'),
         'res_model': 'sale.order',
         'view_type': 'form',
         'view_mode': 'tree,form',
         'target': 'current',
         'domain': domain,
               }
class wizard_crm_lead(models.TransientModel):
    _name = 'wizard.crm.lead'
    _description = 'List crm  daily base Report'
    duration = fields.Selection([('today', 'Today'),
				('yesterday', 'Yesterday'),
				('month', 'One Month'),
				('custom', 'Custom'),], string='Duration' )
    today_date=fields.Date('Today Date')
    yesterday_date=fields.Date('Yesterday Date')
    date_from =fields.Date('From')
    date_to = fields.Date('To' )
    user_id=fields.Many2one('res.users')
    all_record=fields.Boolean('All Records')
    
    @api.v7
    def open_sale_person_report(self, cr, uid, ids, context=None):
        lead= self.pool.get('crm.lead')
        sale =self.pool.get('sale.order')
        call_history=self.pool.get('crm.coldcalling.history')
        summary=self.pool.get('crm.lead.summary')
        domain=""
        if context is None:
            context = {}
        view_type = 'form,tree'
        for lead_line in self.browse(cr, uid, ids, context=context):
	    sub_ids=self.pool.get('res.users')
	    sub_search=[]
	    if lead_line.user_id:
	    	sub_search=[lead_line.user_id.id]
	    else:
                sub_search=sub_ids.search(cr, uid ,[('id','>','0'),('sale_team_id','!=','NULL')])
                
	    n_date= datetime.strftime(datetime.today().date(),'%Y-%m-%d 00:00:00')
	    n_date1=datetime.strftime(datetime.today().date(),'%Y-%m-%d 23:59:59')            
            ### Todays    Create Coldcalling
            if lead_line.duration == 'today':
		n_date=n_date1=lead_line.today_date
	    if lead_line.duration == 'yesterday':
		n_date=n_date1=lead_line.yesterday_date
	    if lead_line.duration == 'month':
		n_date=lead_line.date_from
		n_date1=lead_line.date_to
	    if lead_line.duration == 'custom':
		n_date=lead_line.date_from
		n_date1=lead_line.date_to
		
	    summary_tbl=summary.search(cr, uid, [('create_uid','=',uid)], context=context) 
	    if summary_tbl:     
	    	summary.unlink(cr,uid,summary_tbl) 
	    	
	    for rec in sub_ids.browse(cr, uid,sub_search):
		    #### total Lost Lead 
		    lost_lead=lead.search(cr, uid, [('stage_id.name', '=', 'Lost'),('user_id','=', rec.id),('create_date','>=',n_date),('create_date','<=',n_date1)], context=context)
		    lost_lead_len=len(lost_lead)
		    ### Data Exceed
		    
		    create_today=lead.search(cr, uid, [('user_id','=',rec.id),
                    ('stage_2','in', ['contacted','not_contacted','qualified','disqualified']),('create_date','>=',n_date),('create_date','<=',n_date1)], context=context)
		    #### for mail notification call 
		    mail=note=call=date_exceed_total=0
		    for lead_value in lead.browse(cr, uid,create_today):
		        if int(lead_value.number_of_days) >= int(lead_value.contact_interval):
		           date_exceed_total = date_exceed_total +1
		        for history in lead_value.coldcalling_ids:
		              call=len(lead_value.coldcalling_ids)
		              if history.send_mail == True:
		                 mail=mail +1
		              if history.set_reminder == True:
		                 note=note + 1
		    total_create=len(create_today)
		    quotation=sale.search(cr, uid, [('user_id','=',rec.id),('create_date','>=',n_date),('create_date','<=',n_date1), ('state','in', ['draft', 'sent'])], context=context)
		    total_quotation=len(quotation)
		    
		    ## total Quotation order amount
		    total_amount=0
		    for Quotation_order in sale.browse(cr, uid,quotation):
		        total_amount =total_amount + Quotation_order.n_base_currency_amount
		    order=sale.search(cr, uid, [('user_id','=',rec.id),('date_order','>=',n_date),('date_order','<=',n_date1), ('state','in', ['sale', 'done'])], context=context)
		    total_sale=len(order)
		    ## total sale order amount
		    saletotal_amount=0
		    for sale_order in sale.browse(cr, uid,order):
		        saletotal_amount =saletotal_amount+ sale_order.n_base_currency_amount
		    interval=lead.search(cr, uid, [('user_id','=',rec.id),('cont_bool','=',True),('interval_date','>=',n_date),('interval_date','<=',n_date1)], context=context)
		    total_interval=len(interval)
		    ### Todays Contact List
		    today_contact=lead.search(cr, uid, [('user_id','=',rec.id),('last_contacted','>=',n_date),('last_contacted','<=',n_date1),
                     ('stage_2','in', ['contacted','not_contacted','qualified','disqualified'])], context=context)
		    today_contact_len=len(today_contact)
		    ### total Mamm mail 
		    mass=0
		    for today_con in lead.browse(cr, uid,today_contact):
		        history_val=call_history.search(cr, uid, [('is_mass_mail', '=',True), ('res_id', '=',today_con.id)])
		        if history_val:
		           mass = mass +1
		    ### Todays qualified Coldcalling
		    qualified=lead.search(cr, uid, [('user_id','=',rec.id),('qualified_date','>=',n_date),
                     ('qualified_date','<=',n_date1), ('coldcalling_bool','=', True)], context=context)
		    qualified_len=len(qualified) 
		    ### Todays DisQualified Coldcalling
		    disqualified=lead.search(cr, uid, [('user_id','=',rec.id),('disqualified_date','>=',n_date),('disqualified_date','<=',n_date1)], context=context)
		    disqualified_len=len(disqualified)
		    ### total Opportunity
		    oppotunity=lead.search(cr, uid, [('user_id','=',rec.id),('type','=','opportunity'),('lead_create_date','>=',n_date),('lead_create_date','<=',n_date1)], context=context)
		    oppotunity_len=len(oppotunity)
		    if  create_today or quotation or order or interval or  qualified or disqualified or oppotunity or today_contact or lost_lead or today_contact:
		           ids1=summary.create(cr, uid, {'today_create':total_create,'is_summary':True,
		           				'today_contact':today_contact_len,'user_id':rec.id, 
		           				'from_date':n_date, 'to_date':n_date1, 
	           			      'today_Qualified':qualified_len,'today_quatation':total_quotation, 
	           			      'today_sale':total_sale,'today_interval_change':total_interval,
		                              'today_disqualified':disqualified_len, 'today_opportunity':oppotunity_len,
		                          'day_target_allot':rec.salesperson_target,'target_achieve':today_contact_len,
		                          'total_mails':mail,'total_notifications':note,
		         		  'total_calls':call,'mass_mail':mass,'quotation_total':total_amount,
	                             	  'sale_total':saletotal_amount,'today_date_exceed':date_exceed_total,
		                          'monthly_target_allot':rec.monthly_target ,'total_lost_lead':lost_lead_len})
		              
            ### search in crm lead summary table 
            if lead_line.all_record:
               ids=summary.search(cr, uid, [('create_uid','=',uid)], context=context)
	    else :
		ids=summary.search(cr, uid, [('create_uid','=',uid),('user_id','=', lead_line.user_id.id)], context=context)

            if len(ids) >1 or len(ids) >= 1 or len(ids) <= 1:
                view_type = 'tree,form'
                domain = "[('id','in',["+','.join(map(str, ids))+"])]"
            elif len(ids)==1:
                domain = "[('id','in',["+','.join(map(str, ids))+"])]"
            else:
                domain = "[('id','in',["+','.join(map(str, ids))+"])]"
            value = {
			'domain': domain or False,
			'name': _('Open Sales Person Report'),
			'view_type': 'form',
			'view_mode': view_type,
			'res_model': 'crm.lead.summary',
			'view_id': False,
			'type': 'ir.actions.act_window'
    		   }
            if len(ids) == 1:
                value['res_id'] = ids[0]
            return value
            
    @api.multi
    @api.onchange('duration')
    def duration_select(self):
       for record in self:
           if record.duration == 'today':
              record.today_date=datetime.now()
           if record.duration == 'yesterday':
              record.yesterday_date=datetime.now() - timedelta(1)
           if record.duration == 'month':
              record.date_from=datetime.now() - timedelta(30)
              record.date_to=datetime.now()

            
