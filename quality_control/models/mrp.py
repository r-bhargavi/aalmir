# -*- coding: utf-8 -*-
# copyright reserved

from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp 
from datetime import datetime, date, time, timedelta

class MrpProduction(models.Model):
    _inherit='mrp.production'
   
    @api.model
    def default_get(self,fields):
        rec = super(MrpProduction,self).default_get(fields)
        if rec.get('product_id'):
		product_id=self.env['product.product'].search([('id','=',rec.get('product_id'))])
		if product_id:
			if product_id.product_tmpl_id.check_quality:
				dest_id=self.env['stock.location'].search([('quality_ck_loc','=',True)],order='id asc',limit=1)
				if dest_id:
					rec.update({'location_dest_id' : dest_id.id})
	return rec

    @api.v7
    def product_id_change(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Finds UoM of changed product.
        		@param product_id: Id of changed product.
       			@return: Dictionary of values."""
       			
        result = super(MrpProduction,self).product_id_change(cr, uid, ids, product_id, product_qty, context)
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
	if product:
		if product.product_tmpl_id.check_quality:
			dest_id=self.pool.get('stock.location').search(cr,uid,[('quality_ck_loc','=',True)],order='id asc' ,limit=1)
			if dest_id:
				result['value'].update({'location_dest_id':dest_id[0]})
		else:
			dest_id=self.pool.get('stock.location').search(cr,uid,[('pre_ck','=',True)],order='id asc' ,limit=1)
			if dest_id:
				result['value'].update({'location_dest_id':dest_id[0]})
	return result
        	
    @api.multi
    def action_produce(self, production_qty, production_mode, wiz=False):
    	production_id = self._context.get('active_id') if self._context.get('active_id') else self.id
    	lot_id = self._context.get('lot_id') if self._context.get('lot_id') else False
    	picking_id=user=False
    	for move in self.move_created_ids:
    		picking_id=move.move_dest_id.picking_id.id

    	for rec in self:
    	    responsible=self.env['res.groups'].sudo().search([('category_id.name', '=', 'Quality control')],limit=1)
            b_lst=[]
    	    for recipient in responsible.users:
    	    	user=recipient.id
    	    
    	    if rec.sale_line:
		if rec.location_dest_id.quality_ck_loc:	# if destination location is quality check 
			search_id=self.env['sale.order.line.status'].search([('n_string','=','quality_check')],limit=1) ## add status
			if search_id:
			    self.env['sale.order.line'].sudo().browse(rec.sale_line.id).write({'n_status_rel':[(4,search_id.id)]})
			    
            if rec.product_id.product_tmpl_id.check_quality and wiz:
	    	    if wiz.batch_ids:
           		for batch in wiz.batch_ids:
		               b_lst.append((4,batch.id))
                    # Check if record is already exist or not
               	    search_id=self.env['quality.checking'].search([('source','=',rec.name)])
	    	    if not search_id:
	    	    	self.env['stock.picking'].sudo().browse(picking_id).write({'packaging':rec.n_packaging.id})
	    		vals={'source':rec.name,'product_id':rec.product_id.id,'mrp_id':rec.id,'picking_id':picking_id,
	    			'quality_line':[(0,0,{'name':rec.name,'quantity':production_qty,'mo_state':rec.state,
	    				'product_id':rec.product_id.id,'uom_id':rec.product_uom.id,'lot_id':lot_id,
					'state':'available','n_type':'new','batch_ids':b_lst, 'mrp_id':production_id
		                        })],'uom_id':rec.product_uom.id,'user':user}
	    		self.env['quality.checking'].create(vals)
		    else:
		    	# check if Lot number is already exist or not
		    	search_line_id=self.env['quality.checking.line'].search([('lot_id','=',lot_id)],limit=1)
		    	if not search_line_id:
		    		vals={'quality_line':[(0,0,{'name':rec.name,'quantity':production_qty,'mo_state':rec.state,
		    		'product_id':rec.product_id.id,'uom_id':rec.product_uom.id,'lot_id':lot_id,'state':'available',
		    			'n_type':'new','batch_ids':b_lst, 'mrp_id':production_id})]}
	    			if production_qty:
			    		search_id.write(vals)
			    		
	    		else:
	    			# if Exist then update state and quantity
	    			search_line_id.quantity += production_qty
	    			search_line_id.state = 'available'
	    			
    	return super(MrpProduction, self).action_produce(production_qty, production_mode, wiz)
    	
class mrp_product_produce(osv.osv_memory):
    _inherit = "mrp.product.produce"
   
    @api.v7
    def do_produce(self, cr, uid, ids, context=None):
    	data = self.browse(cr, uid, ids[0], context=context)
        context.update({'lot_id':data.lot_id.id})
        return super(mrp_product_produce,self).do_produce(cr, uid, ids, context=context)

class QualityCheckingHistory(models.Model):
    _name = 'quality.checking.line.history'
    _description = "store history of every quality checking in ERP"
    _rec_name='mrp_id'

    quality_id = fields.Many2one("quality.checking",readonly=True)
    quality_line_id = fields.Many2one("quality.checking.line",readonly=True)
    inspection_id = fields.Many2one('quality.inspection', string='Inspection')
    product_id = fields.Many2one("product.product",readonly=True, string='Product')
    quantity = fields.Float(string="Quantity", default=1.0,readonly=True)
    qty_available = fields.Float(string="Quantity Available", default=1.0,readonly=True)
    uom_id = fields.Many2one("product.uom","Unit",readonly=True)
    state = fields.Selection([('approve', 'Approve'),('reject', 'Reject')], string='State', readonly=True)
    nstate = fields.Selection([('draft', 'Draft'),('done', 'Done')], string='State',default='draft', readonly=True)
    move_status = fields.Selection([('in_mo', 'Return To MO'),('move_scrap', 'Move To scrap'),('partial','Partial Move'),('move_quality', 'Move To Quality'),('in_po','Return to PO'),('done','Done')], string='Status', readonly=True)
    mrp_id = fields.Many2one("mrp.production",'MO Number',related='quality_id.mrp_id',store=True,readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Transfer No.',related='quality_line_id.lot_id',store=True,readonly=True, )
    approve_qty = fields.Float("Send To Quality", default=0)
    approve_uom = fields.Many2one("product.uom","Unit",readonly=True)
    reject_qty = fields.Float("Send To Scrap", default=0)
    reject_uom = fields.Many2one("product.uom","Unit",readonly=True)
    history_line = fields.One2many('quality.checking.line.history.line','history_id','History Line') 
    rejected_batches_line = fields.One2many('quality.scrap.batches','history_id','Scrap Batches Line',domain=[('state','=','draft')])
    document_ids = fields.Many2many('ir.attachment', 'quality_reject_doc_rel','history_id','qualilty_id',
    			string = 'Documents')
    
    @api.multi
    def open_inspection(self):
    	form_id = self.env.ref('quality_control.quality_inspection_form_view')
    	return {
		'name' :'Perform New Test',
		'type': 'ir.actions.act_window',
		'view_type': 'form',
		'view_mode': 'form',
		'res_model': 'quality.inspection',
		'views': [(form_id.id, 'form')],
		'view_id': form_id.id,
		'res_id':self.inspection_id.id,
		'target': 'new',
	    }
    
    @api.multi
    def action_validate(self):
    	for rec in self:
    		approve_qty=reject_qty=0.0
    		for line in rec.rejected_batches_line:
    		   if line.state=='draft':
    		   	if line.approve_quantity or line.reject_quantity:
    				if (line.approve_quantity+line.reject_quantity) != line.avail_quantity :
    					raise exceptions.Warning(_("(Send to Quality + Send TO Scrap) shoud be equal to Quantity Available, In batch {}".format(line.main_batches.name)))
	    		if line.approve_quantity <0.0 or line.reject_quantity<0.0:
	    			raise exceptions.Warning(_("Please Enter proper Quantity In Batch {}".format(line.main_batches.name)))
			if (line.approve_quantity+line.reject_quantity) <= line.avail_quantity:				
				if line.approve_quantity:
					rec.history_line=[(0,0,{'product_id':rec.product_id.id,
							'quantity':line.approve_quantity,'status':'move_quality',
							'unit_id':rec.approve_uom.id,'quality_batch_id':line.id,
							'main_batches':line.main_batches.id})]
					rec.quality_id.quality_line=[(0,0,{'name':rec.mrp_id.name,'state':'available',
								'product_id':rec.product_id.id,'lot_id':rec.lot_id.id,
								'quantity':line.approve_quantity,'n_type':'repaired',
						    		'uom_id':rec.uom_id.id,'quality_batch_id':line.id,
						    		'main_batches':line.main_batches.id,
						    		'batch_ids':[(4,line.main_batches.id)]})]
			    		line.main_batches.product_qty = line.approve_quantity
			    		line.main_batches.reject_resion=[]
		    			rec.qty_available -= line.approve_quantity
		    			line.avail_quantity -= line.approve_quantity
		    			approve_qty += line.approve_quantity
		    			line.main_batches.reject_qty -= line.approve_quantity
				if line.reject_quantity:
					rec.history_line=[(0,0,{'product_id':rec.product_id.id,'status':'move_scrap',
								'quantity':line.reject_quantity,
								'main_batches':line.main_batches.id,
								'unit_id':rec.reject_uom.id})]
					rec.qty_available -= line.reject_quantity
					line.avail_quantity -= line.reject_quantity
					reject_qty += line.reject_quantity
					line.main_batches.reject_qty -= line.reject_quantity
					line.main_batches.scrapt_qty += line.reject_quantity
					
			if line.avail_quantity ==0.0 and line.state=='draft':
				line.state='done'
				approve_qty1=reject_qty1=0
				for res in line.history_line:
					approve_qty1 += res.quantity if res.status == 'move_quality' else 0
					reject_qty1  += res.quantity if res.status == 'move_scrap' else 0
				line.approve_quantity = approve_qty1 
				line.reject_quantity = reject_qty1
			else:
				line.approve_quantity = line.reject_quantity = 0
			line.state='done'				
		if approve_qty == rec.quantity:
	    		rec.move_status='move_quality'
    		elif reject_qty == rec.quantity:
	    		rec.move_status='move_scrap'
    		else:
    			 rec.move_status = 'partial'
		if rec.qty_available==0:
			rec.nstate='done'
			
		approve_qty=reject_qty=0
		for res in rec.history_line:
			approve_qty += res.quantity if res.status == 'move_quality' else 0
			reject_qty  += res.quantity if res.status == 'move_scrap' else 0
		rec.approve_qty=approve_qty
		rec.reject_qty=reject_qty	
    	return True
    	
class QualityCheckingHistoryLine(models.Model):
    _name = 'quality.checking.line.history.line'
    _description = "store history of every record in rejection from MO Scrap"

    history_id = fields.Many2one("quality.checking.line.history",readonly=True)
    product_id = fields.Many2one("product.product",readonly=True)
    unit_id = fields.Many2one("product.uom",readonly=True)
    quantity = fields.Float(string="Quantity Available", default=1.0,readonly=True)
    status = fields.Selection([('move_scrap', 'Move To scrap'),('move_quality', 'Move To Quality')], string='Status', readonly=True)
    main_batches=fields.Many2one('mrp.order.batch.number', string='Batch No.')
    quality_batch_id = fields.Many2one('quality.scrap.batches', string='History Batch No.')
    quantity = fields.Float(string="Quantity Available", default=1.0,readonly=True)

class QualityScrapbatches(models.Model):
    """This table is used to select approved and reject batches in Manufacturing Scrap."""
    _name = 'quality.scrap.batches'

    history_id = fields.Many2one('quality.checking.line.history',string='Scrap')
    line_id = fields.Many2one('quality.checking.line',string='Scrap')
    quality_id=fields.Many2one('quality.checking', string='Quality No.')
    inspection_id=fields.Many2one('quality.inspection','Inspection No')
    state = fields.Selection([('draft', 'Draft'),('done', 'Done')], string='State',default='draft', readonly=True)
    history_line=fields.One2many('quality.checking.line.history.line','quality_batch_id','History Line') 
    
    lot_id=fields.Many2one('stock.production.lot', string='Transfer No.') 
    main_batches=fields.Many2one('mrp.order.batch.number', string='Batch No.')
    quantity=fields.Float('Quanitity')
    avail_quantity=fields.Float('Quantity')
    uom_id=fields.Many2one('product.uom', string='Unit')
    
    approve_quantity =fields.Float('Send to Quality')
    reject_quantity =fields.Float('Send TO Scrap')
    ntype = fields.Selection([('reject','Reject'),('approve','Approved')],string='Type')
    reject_resion=fields.Many2many('quality.reject.reason','quality_batch_reject_resion_rel','quality_id',
        			   'resion_id',string='Reject Reason',help="Rejected resign from quality checking.")
    
    
