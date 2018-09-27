# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api, exceptions, _

# file is not in use
class QualityScrapDoc(models.TransientModel):
    """This wizard is used to get document of rejected quantity and note.
    """
    _name = 'quality.scrap.doc'

    test = fields.Many2one(comodel_name='quality.test', string='Test')
    batches_ids = fields.One2many('quality.batches.line', 'wizard_id',string='Production batches')
    lots_ids = fields.One2many('wizard.lot.line', 'wizard_id',string='Lot Lines')
    note = fields.Text(string='Note')
    nbool = fields.Boolean(string='Note')
    uploaded_documents = fields.Many2many('ir.attachment','wizard_attachment_rel','wizard','id','Reject Documents')
    approve_qty = fields.Float(string='Approve Qty')
    approve_uom = fields.Many2one('product.uom','Unit')
    reject_qty = fields.Float(string='Reject Qty')
    reject_uom = fields.Many2one('product.uom','Unit')
    inspection = fields.Many2one('quality.inspection', string='Test')
    check_bool =fields.Boolean('Check All')
    
    @api.onchange('check_bool')
    def onchange_type(self):
    	for rec in self:
    		for line in rec.batches_ids:
    			if rec.check_bool:
    				if rec.approve_qty:
    					line.approve_quantity = line.product_qty
				if rec.reject_qty:
					line.reject_quantity = line.product_qty
			else:
				if rec.approve_qty:
    					line.approve_quantity = 0
				if rec.reject_qty:
					line.reject_quantity = 0	
    			line.check_bool=rec.check_bool
    			
    @api.multi
    def action_upload_document(self):
    	self.ensure_one()
    	#inspection = self.env['quality.inspection'].browse(self.env.context['active_id'])
    	
	if self.lots_ids:		# for all quantity Inspetion 
		lot_approve_qty=lot_reject_qty=0
		for lot in self.lots_ids:
			approve_qty=reject_qty=0
			for batch in self.batches_ids:
			    if batch.check_bool:
				if lot.lot_id.id == batch.lot_id.id:
					if batch.approve_quantity < 0 or batch.reject_quantity <0:
						raise exceptions.Warning(_("Please Enter Proper Value in batch "+str(lot.name)+", You Enter A Negative Value"))
					if batch.approve_quantity > 0 and batch.approve_quantity > batch.product_qty:
						raise exceptions.Warning(_("Please Enter Proper Value in batch "+str(lot.name)+", Approve Quantity is Less than available Quantity"))
					if batch.reject_quantity > 0 and batch.reject_quantity > batch.product_qty:
						raise exceptions.Warning(_("Please Enter Proper Value in batch "+str(lot.name)+", Reject Quantity is Less than available Quantity"))	
					lot_approve_qty += batch.approve_quantity  # for all quantity
					approve_qty += batch.approve_quantity	# for single lot
					lot_reject_qty += batch.reject_quantity
					reject_qty += batch.reject_quantity
			if approve_qty != lot.approve_qty:
				raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of "+str(lot.approve_qty)+" but you select bacthes of Quantity "+str(approve_qty)+" To Approve "+str(lot.lot_id.name)))
			if reject_qty != lot.reject_qty:
				raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of "+str(lot.reject_qty)+" but you select bacthes of Quantity "+str(reject_qty)+" To Reject "+str(lot.lot_id.name)))
		if lot_approve_qty != self.approve_qty:
			raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of  "+str(self.approve_qty)+" but you select bacthes of Quantity "+str(lot_approve_qty)+" To Approve "))
		if lot_reject_qty != self.reject_qty:
			raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of  "+str(self.reject_qty)+" but you select bacthes of Quantity "+str(lot_reject_qty)+" To Reject "))
			
	else:		# For Perticular Lot Inspection
		approve_qty=reject_qty=0
		for batch in self.batches_ids:
		   if batch.check_bool:
			approve_qty += batch.approve_quantity	
			reject_qty += batch.reject_quantity
		if approve_qty != self.approve_qty:
			raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of  "+str(self.approve_qty)+" but you select bacthes of Quantity "+str(approve_qty)+" To Approve "))
		if reject_qty != self.reject_qty:
			raise exceptions.Warning(_("Please Select Proper Quantity Batches, You have to Get total of  "+str(self.reject_qty)+" but you select bacthes of Quantity "+str(reject_qty)+" To Reject "))
			
	if self.nbool:
    		if not self.uploaded_documents:
    			raise exceptions.Warning(_("Please Upload at least one Document of Quality Check Failed"))
        	self.inspection.uploaded_documents = self.uploaded_documents
        	self.inspection.notes = self.note
        			
	for nline in self.batches_ids:
		if nline.reject_quantity:
			self.env['quality.scrap.batches'].create({'lot_id':nline.lot_id.id,
					'inspection_id':self.inspection.id,'ntype':'reject',
					'main_batches':nline.main_batches.id,'quantity':nline.reject_quantity,
					'avail_quantity':nline.reject_quantity,'uom_id':nline.uom_id.id})
		if nline.approve_quantity:
			self.env['quality.scrap.batches'].create({'lot_id':nline.lot_id.id,
					'inspection_id':self.inspection.id,'ntype':'approve',
					'main_batches':nline.main_batches.id,'quantity':nline.approve_quantity,
					'avail_quantity':nline.reject_quantity,'uom_id':nline.uom_id.id})
		nline.main_batches.approve_qty += nline.approve_quantity
		nline.main_batches.reject_qty += nline.reject_quantity
		nline.main_batches.qty_unit_id = nline.uom_id.id
        self.inspection.action_do_confirm()

class QualitybatchesLine(models.TransientModel):
    """This table is used to select approved and reject batches in wizard.
    """
    _name = 'quality.batches.line'

    wizard_id = fields.Many2one('quality.scrap.doc',string='Production batches')
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.')
    product_id=fields.Many2one('product.product',string='Product Name')
    product_qty=fields.Float('Product Qty')
    lot_id=fields.Many2one('stock.production.lot', string='Production Lot No.') 
    uom_id=fields.Many2one('product.uom', string='Unit')
    main_batches=fields.Many2one('mrp.order.batch.number', string='Batch No.')
    approve_quantity =fields.Float('Approve Quantity')
    reject_quantity =fields.Float('Reject Quantity')
    check_bool =fields.Boolean('Check')

class wizardLotLine(models.TransientModel):
    _name = 'wizard.lot.line'
    _description = "Used to get Lots from inspection"
    
    wizard_id = fields.Many2one('quality.scrap.doc',string='Production batches')
    lot_id = fields.Many2one('stock.production.lot','Lot Number',readonly=True)
    approve_qty = fields.Float("Approve Qty",readonly=True)
    reject_qty = fields.Float("Reject Qty",readonly=True)
    uom_id=fields.Many2one('product.uom', string='Unit',readonly=True)
   
