# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp


class QualityInspection(models.Model):
    _name = 'quality.inspection'
    _description = 'Qualit Check Inspection'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.one
    @api.depends('inspection_lines', 'inspection_lines.success')
    def _success(self):
        self.success = all([x.success for x in self.inspection_lines])

    name = fields.Char(string='Inspection number', required=True, select=True, 
    				readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    date = fields.Datetime(string='Date', required=True, readonly=True, copy=False, default=fields.Datetime.now,
        			states={'draft': [('readonly', False)]}, select=True)
    quality_id = fields.Many2one("quality.checking",'Quality Number',readonly=True,)
    quality_line_id = fields.Many2one("quality.checking.line",'Quality Line',readonly=True,)
    inspection_lines = fields.One2many('quality.inspection.line', 'inspection_id',string='Inspection lines',
    					 readonly=True,states={'ready': [('readonly', False)]})
    lot_lines = fields.One2many('lot.quality.line', 'inspection_id',string='Inspection lines',readonly=True)
    product = fields.Many2one("product.product",'Product Name',readonly=True,)
    qty = fields.Float(string="Quantity", readonly=True, default=1.0)
    uom_id = fields.Many2one("product.uom",related='quality_id.uom_id')
    approve_qty = fields.Float("Approve Quantity", default=0)
    auom_id = fields.Many2one("product.uom",related='quality_id.uom_id')
    reject_qty = fields.Float("Reject Quantity", default=0)
    ruom_id = fields.Many2one("product.uom",related='quality_id.uom_id')
    test = fields.Many2one('quality.test', string='Test',select=True)
    
    notes = fields.Text(string='Notes')
    state = fields.Selection([('draft', 'Draft'),('ready', 'Ready'),
    				 ('partial', 'Partial Success'),
    				 ('partial_failed', 'Partial Failed'),
				 ('success', 'Quality Success'),
				 ('failed', 'Quality Failed'),
				 ('canceled', 'Canceled')],
				string='State', readonly=True, default='draft')
    success = fields.Boolean(compute="_success", string='Success',help='This field will be marked if all tests have succeeded.',store=True)
    full_test = fields.Boolean('Full test',help='This field is used to perform Full Quantity Test from Main form')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)]},
        	default=lambda self: self.env['res.company']._company_default_get('quality.inspection'))
    user = fields.Many2one('res.users', string='Responsible',track_visibility='always', default=lambda self: self.env.user)
    uploaded_documents = fields.Many2many('ir.attachment','inspection_scrap_attachment_rel','inspection_id','id','Reject Documents')
    ntype = fields.Selection([('reject','Reject'),('accept','Approve')],string='Type')
    @api.model
    def create(self, vals):
     	vals['name'] = self.env['ir.sequence'].next_by_code('quality.inspection')
        return super(QualityInspection, self).create(vals)
 	
    @api.multi
    def write(self,vals):
    	body=''
    	for res in self:
	    	if vals.get('inspection_lines'):
	    		for line in vals.get('inspection_lines'):
	    			if len(line)==3 and type(line[2])==dict:
	    				rec=self.env['quality.test.question'].search([('id','=',line[2].get('test_line'))])
	    				if rec:
		    				line[2].update({'name':rec.name})
						line[2].update({'notes':rec.notes})
						line[2].update({'min_value':rec.min_value})
						line[2].update({'max_value':rec.max_value})
						line[2].update({'test_uom_id':rec.uom_id.id})
						line[2].update({'question_type':rec.question_type})
						if line[0]==0:
							body += '<li>New Question '+str(rec.name)+' is Added</li>'
						if line[0]==1:
							for record in self.inspection_lines:
								if record.id == line[1]:
									body += '<li>Question '+str(record.name)+' is Changed to '+str(rec.name)+'</li>'
				if line[0]==2:
					rec=self.env['quality.inspection.line'].search([('id','=',line[0])])
					body += '<li>Question '+str(rec.test_line.name)+' is removed</li>'
		if body:
			res.message_post(body= body)
	return super(QualityInspection,self).write(vals)

    @api.multi
    def action_validate(self):
        for inspection in self:
            if not inspection.test:
                raise exceptions.Warning(_("Select test to perform."))
            if not inspection.inspection_lines:
            	self.onchange_test()
        self.write({'state': 'ready','user':self.env.user.id})
        return {
        "type": "ir.actions.do_nothing",
    	}

    @api.multi
    @api.onchange('test')
    def onchange_test(self):
    	new_data=[]
    	if self.test.test_lines:
	    	for line in self.test.test_lines:
		    	data = {
			    'name': line.name,
			    'test_line': line.id,
			    'notes': line.notes,
			    'min_value': line.min_value,
			    'max_value': line.max_value,
			    'test_uom_id': line.uom_id.id,
			    'uom_id': line.uom_id.id,
			    'question_type': line.question_type,
			    'possible_ql_values': [x.id for x in line.ql_values]
			}
			if self.test.fill_correct_values:
			    if line.question_type == 'qualitative':	 # Fill with the first correct value found
				for value in line.ql_values:
				    if value.ok:
				        data['qualitative_value'] = value.id
				        break
			    else: 				# Fill with a value inside the interval
				data['quantitative_value'] = (line.min_value + line.max_value) * 0.5
			new_data.append((0, 0, data))
		self.inspection_lines.unlink()
		self.inspection_lines = new_data
        
    @api.multi
    def action_confirm(self):
        for inspection in self:
            approve_qty=reject_qty=0
            if not inspection.full_test and not inspection.approve_qty and not inspection.reject_qty:
            	raise exceptions.Warning(_("Please Enter Approve quantity or Reject Quantity"))
            if inspection.full_test :
            	f_qty=0
            	for qt in inspection.lot_lines:
            		f_qty += qt.approve_qty
            		approve_qty += qt.approve_qty
            		f_qty += qt.reject_qty
            		reject_qty += qt.reject_qty
    		if f_qty != inspection.qty:
            		raise exceptions.Warning(_("Approve Quantity + Reject Quantity is equal to Available Quantity"))
            if (inspection.approve_qty+inspection.reject_qty) > inspection.qty:
            	raise exceptions.Warning(_("Entered Quantity in Approve and Reject is Greate than Available Quantity.It should be less than or equal to available Quantity"))
	    approve_qty += inspection.approve_qty
	    reject_qty += inspection.reject_qty
            for line in inspection.inspection_lines:
                if line.question_type == 'qualitative':
                    if not line.qualitative_value:
                        raise exceptions.Warning(_("You should provide an answer for all qualitative questions."))
                else:
                    if not line.quantitative_value:
                        raise exceptions.Warning(_("You should provide quantitative value for questions."))
            
            context =self._context.copy()

            if approve_qty:	# send qunaity to batch wizard to check batch quantiy and process quantity shod be equal
            	context.update({'default_approve_qty':approve_qty,'approve':True,
            			'default_approve_uom':inspection.uom_id.id if inspection.uom_id else False})
    	    if reject_qty:
    	    	# add reject and approve values in context to remove the reject quantity field dynamicaly
    	    	context.update({'default_reject_qty':reject_qty,'default_nbool':True,'reject':True,
    	    			'default_reject_uom':inspection.uom_id.id if inspection.uom_id else False})
            domain=[('available_qty','>','0'),('production_id','=',inspection.quality_id.mrp_id.id)]
            if inspection.full_test:
            	l=[]
            	lot=[]
            	for batch in inspection.lot_lines:
            		l.append(batch.quality_line_id.lot_id.id) 
            		lot.append((0,0,{'lot_id':batch.quality_line_id.lot_id.id,'approve_qty':batch.approve_qty
            				,'reject_qty':batch.reject_qty,'uom_id':inspection.uom_id.id}))
		context.update({'default_lots_ids':lot})
            	domain.append(('lot_id','in',l))
    	    else:
    	    	domain.append(('lot_id','=',inspection.quality_line_id.lot_id.id))
            batches=self.env['mrp.order.batch.number'].search(domain)
            batch_list=[]
            for btch in batches:
            	batch_list.append((0,0,{'production_id':btch.production_id.id,'product_id':btch.product_id.id,
            				'product_qty':btch.available_qty,'lot_id':btch.lot_id.id,
            				'main_batches':btch.id,'uom_id':btch.uom_id.id}))
	    if batch_list:
	    	    context.update({'default_batches_ids':batch_list})

    	    context.update({'default_inspection':inspection.id})
            form_id= self.env.ref('quality_control.view_scrap_doc_form')
            return {
    			'name' :'Select Batch Details',
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'quality.scrap.doc',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'context': context,
            		}
        self.action_do_confirm()	
        return 
            		
    @api.multi
    def action_do_confirm(self):
        for inspection in self:
            approve_qty=0
            if not inspection.approve_qty:
            	inspection.state = 'failed'
            elif not inspection.reject_qty:
            	inspection.state = 'success'
            else:
            	inspection.state = 'partial'
            	
            if inspection.full_test:
            	for rec in inspection.lot_lines:
            		approve_qty += rec.approve_qty
            		rec.quality_line_id.quantity = 0.0
            		rec.quality_line_id.state = 'complete'
            		if rec.approve_qty:
            			state='approve'
			    	qty=rec.approve_qty
		  		self.action_create_history(inspection,rec.quality_line_id,qty,state)
  		
		  	if rec.reject_qty:
		  		state='reject'
			    	qty=rec.reject_qty
		  		self.action_create_history(inspection,rec.quality_line_id,qty,state)
    	     
            if inspection.approve_qty:
            	state='approve'
            	qty=inspection.approve_qty
  		self.action_create_history(inspection,inspection.quality_line_id,qty,state)
            	
  		if inspection.quality_line_id:
  			inspection.quality_line_id.quantity -= inspection.approve_qty
  			
            if inspection.reject_qty:
            	state='reject'
            	qty=inspection.reject_qty
            	
  		self.action_create_history(inspection,inspection.quality_line_id,qty,state)
  		if inspection.quality_line_id:
  			inspection.quality_line_id.quantity -=inspection.reject_qty
  			
	    if inspection.quality_line_id:	
  	    	if inspection.quality_line_id.quantity == 0:
			inspection.quality_line_id.state='complete'
 	    flag=False
 	    if inspection.full_test:
 	    	inspection.approve_qty = approve_qty
 	    if inspection.approve_qty:
	 	    for picking in inspection.quality_id.picking_id:
	 	    	for operation in picking.pack_operation_product_ids:
	 	    		if operation.product_qty!=inspection.approve_qty:
	 	    			flag=True
	 	    		operation.qty_done=inspection.approve_qty
	 	    inspection.quality_id.picking_id.do_new_transfer()
	 	    if flag:
	 	    	wiz_immediate_id=self.env['stock.immediate.transfer'].search([('pick_id','=',inspection.quality_id.picking_id.id)])
	 	    	if wiz_immediate_id:
	 	    		wiz_immediate_id.process()
	 	    	else:	
		    		wiz_backorder_id=self.env['stock.backorder.confirmation'].search([('pick_id','=',inspection.quality_id.picking_id.id)])
		    		wiz_backorder_id.process()
	    	    inspection.quality_id.picking_id = self.env['stock.picking'].search([('backorder_id', '=', inspection.quality_id.picking_id.id)],limit=1).id
            return True
            
    @api.multi
    def action_create_history(self,inspection,quality_id,qty,state):
    	vals={  'inspection_id':inspection.id,
    		'quality_id':inspection.quality_id.id if inspection.quality_id else False,
	  	'quality_line_id':quality_id.id if quality_id else False,
	  	'product_id':inspection.product.id if inspection.product else False,
	  	'quantity':qty ,'qty_available':qty,
	  	'state':state,'move_status':'in_mo' if state=='reject' else False,
	  	'uom_id':inspection.uom_id.id if inspection.uom_id else False,
	  	'approve_uom':inspection.uom_id.id if inspection.uom_id else False,
	  	'reject_uom':inspection.uom_id.id if inspection.uom_id else False,
	  	'approve_qty':0.0,'reject_qty':0.0}
    	create_id=self.env['quality.checking.line.history'].create(vals)
    	history_ids=self.env['quality.scrap.batches'].search([('quality_id','=',inspection.quality_id.id),('history_id','=',False),('lot_id','=',quality_id.lot_id.id)])
    	history_ids.write({'history_id':create_id.id})
    	if state=='reject' and quality_id:
  		search_id=self.env['quality.scrap.batches'].search([('inspection_id','=',inspection.id),('lot_id','=',quality_id.lot_id.id),('history_id','=',False)])
  		search_id.write({'history_id':create_id.id})
        
    @api.multi
    def action_draft(self):
    	self.quality_id.message_post('Inspection :'+str(self.name)+" Is Set to Draft")
        self.write({'state': 'draft'})
        
    @api.multi
    def action_cancel(self):
    	self.quality_id.message_post('Inspection :'+str(self.name)+" Is Cancelled")
        self.write({'state': 'canceled'})

class QcInspectionLine(models.Model):
    _name = 'quality.inspection.line'
    _description = "Quality control inspection line"

    @api.one
    @api.depends('question_type', 'uom_id', 'test_uom_id', 'max_value', 'min_value', 'quantitative_value', 'qualitative_value', 'possible_ql_values')
    def quality_test_check(self):
        if self.question_type == 'qualitative':
            self.success = self.qualitative_value.ok
        else:
            if self.uom_id.id == self.test_uom_id.id:
                n_value = self.quantitative_value
            else:
                n_value = self.env['product.uom']._compute_qty(self.uom_id.id, self.quantitative_value,
self.test_uom_id.id)
            self.success = self.max_value >= n_value >= self.min_value

    @api.one
    @api.depends('possible_ql_values', 'min_value', 'max_value', 'test_uom_id','question_type')
    def get_valid_values(self):
        if self.question_type == 'qualitative':
            self.valid_values = ", ".join([x.name for x in self.possible_ql_values if x.ok])
        else:
            self.valid_values = "%s-%s" % (self.min_value, self.max_value)
            if self.env.ref("product.group_uom") in self.env.user.groups_id:
                self.valid_values += " %s" % self.test_uom_id.name

    inspection_id = fields.Many2one('quality.inspection', string='Inspection', ondelete='cascade')
    name = fields.Char(string="Question", readonly=True)
    product = fields.Many2one("product.product", related="inspection_id.product",store=True)
    test_line = fields.Many2one('quality.test.question', string='Test question', readonly=True)
    possible_ql_values = fields.Many2many('quality.test.question.value', string='Answers')
    quantitative_value = fields.Float('Quantitative value', digits=dp.get_precision('Quality Control'),
        				help="Value of the result for a quantitative question.")
    qualitative_value = fields.Many2one('quality.test.question.value', string='Qualitative value',
        	help="Value of the result for a qualitative question.",domain="[('id', 'in', possible_ql_values[0][2])]")
    notes = fields.Text(string='Notes')
    min_value = fields.Float(string='Min', digits=dp.get_precision('Quality Control'),
        		readonly=True, help="Minimum valid value for a quantitative question.")
    max_value = fields.Float(string='Max', digits=dp.get_precision('Quality Control'),
        readonly=True, help="Maximum valid value for a quantitative question.")
    test_uom_id = fields.Many2one('product.uom', string='Test UoM', readonly=True,
        help="UoM for minimum and maximum values for a quantitative ""question.")
    test_uom_category = fields.Many2one("product.uom.categ", related="test_uom_id.category_id", store=True)
    uom_id = fields.Many2one('product.uom', string='UoM',domain="[('category_id', '=', test_uom_category)]",
        help="UoM of the inspection value for a quantitative question.")
    question_type = fields.Selection([('qualitative', 'Qualitative'),('quantitative', 'Quantitative')],string='Question type', readonly=True)
    valid_values = fields.Char(string="Valid values", store=True,compute="get_valid_values")
    success = fields.Boolean(compute="quality_test_check", string="Success?", store=True)

    @api.onchange('test_line')
    def name_onchange(self):
    	for rec in self:
    		rec.name=rec.test_line.name
		rec.notes=rec.test_line.notes
		rec.min_value=rec.test_line.min_value
		rec.max_value=rec.test_line.max_value
		rec.test_uom_id=rec.test_line.uom_id.id
		rec.uom_id=rec.test_line.uom_id.id
		rec.question_type=rec.test_line.question_type
		rec.possible_ql_values=[x.id for x in rec.test_line.ql_values]
		
		if rec.inspection_id.test.fill_correct_values:
			if rec.test_line.question_type == 'qualitative':	 # Fill with the first correct value found
				for value in rec.test_line.ql_values:
				    if value.ok:
					rec.qualitative_value= value.id
					break
			else: 				# Fill with a value inside the interval
				rec.quantitative_value= (rec.test_line.min_value + rec.test_line.max_value) * 0.5
    		
    
class LotQualityLine(models.Model):
    _name = 'lot.quality.line'
    _description = "select lot Data when perform Test for all Quantity from Quality check main View "
    
    inspection_id = fields.Many2one('quality.inspection', string='Inspection', ondelete='cascade',readonly=True)
    quality_id = fields.Many2one('quality.checking', related="inspection_id.quality_id", string='Inspection',readonly=True)
    quality_line_id = fields.Many2one('quality.checking.line','Lot Number',domain="[('quality_id','=',quality_id),('state','=','available')]")
    approve_qty = fields.Float("Approve Qty", default=0)
    reject_qty = fields.Float("Reject Qty", default=0)
    
    
