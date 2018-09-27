# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api, exceptions, _
import math

class QualityChecking(models.Model):
    _name = 'quality.checking'
    _description = "Quality Check for all MO and PO"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "id desc"
    
    @api.one
    def _get_qty(self):
    	for rec in self:
	    	qty=approved=reject=0
	    	for line in rec.quality_line:
			qty += line.quantity
		for line1 in rec.history_line_approve:
			approved += line.quantity
		for line2 in rec.history_line_reject:
			reject += line2.quantity
		rec.quantity = qty
		rec.approved_qty =approved
		rec.reject_qty = reject
    
    @api.one
    @api.depends('quantity','mo_state','quality_line','history_line_reject','history_line_reject.move_status',
    		'quality_line.history_line_approve','quality_line.history_line_reject','quality_line.state')
    def _get_state(self):
    	for rec in self:
		if rec.quantity>0.0:
			qty=0.0
			state='available'
			for line1 in rec.history_line_approve:
				qty += line1.quantity
			if qty >= rec.quantity:
				state='complete'
			for line2 in rec.history_line_reject:
				if line2.move_status in ('in_mo','in_po'):
					state='waiting'
			rec.state=state

		elif rec.mo_state == 'in_production':
			rec.state='waiting'
		elif rec.mo_state == 'done':
			flag=True
			for line in rec.history_line_reject:
				if line.move_status in ('in_mo','in_po'):
					flag=False
					rec.state='waiting' 
			if flag:
				rec.state='complete' 
    		
    name = fields.Char('Name', required=True, readonly=True)
    quality_line=fields.One2many('quality.checking.line','quality_id','Quality Line') 
    history_line_approve = fields.One2many('quality.checking.line.history','quality_id','Quality Line History', domain=[('state','=','approve')])
    history_line_reject = fields.One2many('quality.checking.line.history','quality_id','Quality Line History', domain=[('state','=','reject')]) 
    source = fields.Char('Source', required=True, readonly=True)
    picking_id = fields.Many2one("stock.picking",'QC Operation',readonly=True)
    mrp_id = fields.Many2one("mrp.production",'MO Number',readonly=True)
    purchase_id = fields.Many2one("purchase.order",'PO Number',readonly=True)
    
    product_id = fields.Many2one("product.product", string='Product')
    uom_id = fields.Many2one("product.uom",'Unit',readonly=True)
    quantity = fields.Float(string="Quantity Available", compute="_get_qty")
    approved_qty = fields.Float(string="Approved Qty",compute="_get_qty")
    reject_qty = fields.Float(string="Reject Qty",compute="_get_qty")
    state = fields.Selection([('draft', 'Draft'),
				 ('waiting', 'Waiting Quantity'),
				 ('available', 'Available'),
				 ('complete', 'Complete'),
				 ('canceled', 'Canceled')],
				string='State',compute="_get_state",store=True)
				
    mo_state = fields.Selection([('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'),
                ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('done', 'Done')],
            string='MO Status', readonly=True,related="mrp_id.state")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
        	default=lambda self: self.env['res.company']._company_default_get('quality.checking'))
    user = fields.Many2one('res.users', string='Responsible',track_visibility='always', default=lambda self: self.env.user)
    operation_type = fields.Selection([('New', 'Product for Deliver'), ('raw', 'Raw Material')], readonly=True,string="Type")
     
    @api.model
    def create(self,vals):
    	name=self.env['ir.sequence'].next_by_code('quality.checking')
    	vals.update({'name':name})
    	return super(QualityChecking,self).create(vals)
    
    @api.multi
    def quality_test(self):
    	context=self._context.copy()
    	qty= context.get('qty') if context.get('qty') else self.quantity
    	form_id = self.env.ref('quality_control.quality_inspection_form_view')
    	if not context.get('qty'):
    	    full_test= self.env['quality.inspection'].search([('quality_id','=',self.id),('state','in',('draft','ready')),('full_test','=',True)],limit=1)
    	    if full_test:
    	    	return {
		'name' :'Perform Test',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'form',
		'res_model': 'quality.inspection',
		'views': [(form_id.id, 'form')],
		'view_id': form_id.id,
		'target': 'new',
		'res_id':full_test.id,
		'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
	    }
    	    search_id= self.env['quality.inspection'].search([('quality_id','=',self.id),('state','in',('draft','ready'))])
    	    if search_id:
    		raise exceptions.Warning(_("Already inspection is running on this Request Please complete That."))
    	if not qty:
    		raise exceptions.Warning(_("No Quantity Available To Perform Quality Test"))
    	full = False if context.get('default_quality_line_id') else True
    	context.update({'default_name':'New','default_product':self.product_id.id,
    			'default_qty':qty,'default_quality_id':self.id,'default_full_test':full})
    	
    	return {
		'name' :'Perform New Test',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'form',
		'res_model': 'quality.inspection',
		'views': [(form_id.id, 'form')],
		'view_id': form_id.id,
		'target': 'new',
		'context':context,
		'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
	    }
	    
    @api.multi
    def open_test_performed(self):
    	tree_id = self.env.ref('quality_control.quality_inspection_tree_view')
    	form_id = self.env.ref('quality_control.quality_inspection_form_view')
    	if self._context.get('quality_line_id'):
    		domain=[('quality_line_id','=',self._context.get('quality_line_id'))]
	else:
		domain=[('quality_id','=',self.id)]
    	return {
		'name' :'Open Inspections',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'tree',
		'res_model': 'quality.inspection',
		'views': [(tree_id.id,'tree'),(form_id.id, 'form')],
		'view_id': tree_id.id,
		'target': 'new',
		'domain':domain,
	    }
    	
    	
class QualityCheckingLine(models.Model):
    _name = 'quality.checking.line'
    _description = "when every time MO produce some quantity it added to quality check"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name="lot_id"
    _order = "id desc"
    
    @api.one
    def _get_quantity(self):
    	for rec in self:
	    	approved=reject=0
	    	for line in rec.history_line_approve:
			approved += line.quantity
		for line1 in rec.history_line_reject:
			reject += line1.quantity
		rec.approved_qty =approved
		rec.reject_qty = reject

    name = fields.Char('Name',readonly=True)
    quality_id = fields.Many2one("quality.checking",readonly=True)
    product_id = fields.Many2one("product.product",readonly=True, string='Product')
    quantity = fields.Float(string="Available Qty", default=1.0,readonly=True)
    uom_id = fields.Many2one("product.uom",'Unit',readonly=True)
    approved_qty = fields.Float(string="Approve Qty",compute='_get_quantity')
    approve_uom_id = fields.Many2one("product.uom",'Unit',related='lot_id.product_uom_id',readonly=True)
    reject_qty = fields.Float(string="Reject Qty", compute='_get_quantity')
    reject_uom_id = fields.Many2one("product.uom",'Unit',related='lot_id.product_uom_id', readonly=True)
    state = fields.Selection([('draft', 'Draft'),('available', 'Available'),('partial', 'Partial Approved'),
				 ('complete', 'Complete'),('approve', 'Approved'),('reject', 'Rejected'),
				 ('canceled', 'Canceled')],
				string='State', readonly=True, default='draft')
    n_type = fields.Selection([('new', 'New Production'),('repaired', 'Repaired')], string='Quantity From', readonly=True, default='new')
    lot_id = fields.Many2one('stock.production.lot', 'Transfer Number',readonly=True)			
    mo_state = fields.Selection(
            [('draft', 'New'), ('cancel', 'Cancelled'), ('confirmed', 'Awaiting Raw Materials'),
                ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('done', 'Done')],
            string='MO Status', readonly=True, default='draft')
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
        	default=lambda self: self.env['res.company']._company_default_get('quality.checking'))
    history_line_approve=fields.One2many('quality.checking.line.history','quality_line_id','Quality Line History',domain=[('state','=','approve')])
    history_line_reject=fields.One2many('quality.checking.line.history','quality_line_id','Quality Line History',domain=[('state','=','reject')])   
    scrap_reason = fields.Selection([('reject','Quality not Good'),('min','Quantity is Less' )], string="Scrap Reason")
    batch_ids=fields.One2many('mrp.order.batch.number', 'quality_line_id', string='Batch Details')
    sample_id=fields.Many2one('product.sample.check', string='QC samplaing %', related='product_id.sample_id')
    mrp_id = fields.Many2one("mrp.production",'MO Number',readonly=True)
    check_batch_no=fields.Integer('Min. batches to check ',compute='check_batchs') 
    comment=fields.Text('Remark')
    document_ids=fields.Many2many('ir.attachment', 'reject_rel','reject_rel2','id',string='Documents')
    check_type = fields.Selection([('approve','Approve All'),('reject','Reject All')],"Inspect",)
    rejected_batches_line = fields.One2many('quality.scrap.batches','line_id','Scrap Batches Line')

    @api.onchange('check_type')
    def _get_inspect(self):
    	for rec in self:
	    	for line in rec.batch_ids:
			if rec.check_type == 'approve':
				line.check_type='approve'
			elif rec.check_type == 'reject':
				line.check_type='reject'
			else:
				line.check_type=False
			
				
    @api.multi
    def check_batchs(self):
        for record in self:
            if record.lot_id and record.batch_ids:
               lot_per=math.ceil((record.lot_id.total_qty * record.sample_id.name)/100)
               print"_----------------",lot_per
               count=0.0
               res=lot_per
               for line in record.batch_ids:
                   if line.product_qty > lot_per:
                      print"-------------",line.product_qty
                      count=1
                      break;
                   else:
                      if res>0:
                         print"RRRRRRRRRRRRRRRRR",res
                         count +=1
                         res -=line.product_qty
               
               record.check_batch_no=count#math.ceil(sum(line.product_qty for line in record.batch_ids)/lot_per)
         
    @api.multi
    def quality_test(self):	# perform new test
    	search_id= self.env['quality.inspection'].search([('quality_line_id','=',self.id),('state','in',('draft','ready'))])
    	if search_id:
    		raise exceptions.Warning(_("Already inspection is running on this Request Please complete That."))
	search_main_id= self.env['quality.inspection'].search([('quality_id','=',self.quality_id.id),('state','in',('draft','ready')),('quality_line_id','=',False)])
    	if search_main_id:
    		raise exceptions.Warning(_("Already inspection is running on this Request Please complete That."))
    	return self.with_context(qty=self.quantity,default_quality_line_id=self.id).quality_id.quality_test()  # use Parent Method

    @api.multi
    def open_test_performed(self):	#show all test
    	return self.with_context(quality_line_id=self.id).quality_id.open_test_performed()
    	
    @api.multi
    def line_quality_process(self):
    	for rec in self:
    		count=check=reject=0
    		for line in rec.batch_ids:
    			if line.check_bool :
    				check +=1
    				if line.reject_resion:
    					reject+=1
			count +=1
		if (check/count)*100 < float(rec.sample_id.name):
			raise exceptions.Warning(_("Please inspect {} batchs \n You Inspect only {} batches".format(rec.sample_id.name,(check/count)*100)))
		
		if (reject/count)*100 >= float(rec.sample_id.name):
			form_id = self.env.ref('quality_control.view_quality_reject_form')
			return {
				'name' :'Reject form',
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'quality.reject.qty',
				'views': [(form_id.id, 'form')],
				'view_id': form_id.id,
				'target': 'new',
			    }
		else:
			rec.state='approve'
			for line in rec.batch_ids:
	    			if line.check_bool :
	    				if line.reject_resion:
	    					line.reject_qty = line.product_qty
					
    @api.multi
    def line_approve_reject(self):
    	error_str=''
    	try:
		for res in self:
			context=self._context.copy()
			name='Approve/Reject form'
			form_id = self.env.ref('quality_control.view_quality_approve_reject_form')
			count=check= 0
	    		for line in res.batch_ids:
	    			if line.check_type in ('approve','reject'):
	    				check +=1
				count +=1
			if (float(check)/float(count))*100 < float(res.sample_id.name):
				error_str="Please inspect {}% batches \n You Inspect only {}% batches ".format(res.sample_id.name,(check/count)*100)
				raise
	
			line_batches,line_batches1=[],[]
			for line in res.batch_ids:
    				if line.check_type !='reject':
    					line_batches.append((0,0,{'check_bool':True,'batches':str(line.name)}))
				if line.check_type =='reject':
    					line_batches1.append((0,0,{'check_bool':True,'batches':str(line.name)}))
			context.update({'default_approve_line_one2many':line_batches,
					'default_line_one2many':line_batches1})
			if form_id:	
				return {
					'name' :name,
					'type': 'ir.actions.act_window',
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'quality.reject.qty',
					'views': [(form_id.id,'form')],
					'view_id': form_id.id,
					'target': 'new',
					'context':context,
				    }	
    	except Exception as err:
    		if error_str:
    			raise exceptions.Warning(_(error_str))
		else:
			raise exceptions.Warning(_(err))
	return True

    @api.multi
    def line_reverse(self):
    	for res in self:
    		pass
	    		
	    		
class QualityRejectReason(models.Model):
    _name = 'quality.reject.reason'
    
    name=fields.Char('Reject Reason')

