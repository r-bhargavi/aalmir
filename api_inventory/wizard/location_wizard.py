# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api,_
import math
from datetime import datetime
from datetime import datetime, date, time, timedelta
from openerp.exceptions import UserError
import sys
import logging
_logger = logging.getLogger(__name__)
import os

class StockStoreLocationWizard(models.TransientModel):
    """This wizard is used to preset the free store location for a given
    lots and batches.  """
    
    _name = 'stock.store.location.wizard'

    wizard_line = fields.One2many('stock.store.location.wizard.line','wizard_id','Master Batches')
    wizard_product_line = fields.One2many('stock.store.product.wizard.line','wizard_id','Product')
    picking = fields.Many2one('stock.picking', string='Picking')
    
    back_order_id = fields.Many2one('stock.backorder.confirmation', string='Picking')
    immediate_tra = fields.Many2one('stock.immediate.transfer', string='Picking')
    backorder = fields.Boolean('',default=False)
    reverse_reason=fields.Selection([('reject', 'Goods Rejected'), ('notdelivered', 'Not Delivered')], string="Reverse  Reason")
    
    locations = fields.Many2one('n.warehouse.placed.product','Bin-Location',help="Product is moved to this Location after Process")
    #for warehouse 2 warehouse Tarnsfer
    store_dest_id = fields.Many2one('n.warehouse.placed.product','Bin-Location',help="Tarnsfer Product to this Location after Process")
    status = fields.Selection([('invt_loss','Inventory'),('manu','Manufacturing'),('Purchase','purchase'),
    				('dispatch','Dispatch'),('int_production','Production')],string="Status",
    		help='''Inventory : Quantity comes from Inventory Loss (add in stock) \n
    			Manufacturing : Quantity Comes from Manufacturing (add in stock)\n
    			Purchase : Quantity Comes for Purcahse (add in stock)\n
    			Dispatch : Quantity is Dispatching (removing from stock)\n ''')
    			
    no_of_batch = fields.Float('No of Batches', compute='total_batches')
    per_batch_qty = fields.Float('Each Batch Qty')
    hide_button = fields.Boolean('Hide create Batch Button')
    
    dispatch_doc = fields.Many2many('ir.attachment','dispatch_attachment_wizard_rel','dic_id','wiz_id','Attachment')
    #dispatch_doc_name = fields.Char(string='Doc Name')
    note = fields.Text(string='Remark')
    show_label = fields.Boolean('Hide' , compute="_get_label_data")# show move alert for remaining product on dispatch
    move_loc = fields.Selection([('out','Transit-OUT(Current)'),('in','Transit-IN')],string="Location",help="shows where to move undispatched quantity from picked quantity",default="in")
        
    @api.multi
    @api.depends('per_batch_qty')
    def total_batches(self):
        for record in self:
            if record.per_batch_qty:
               qty=sum(line.product_qty if line.product_qty else line.qty_done for line in record.picking.pack_operation_product_ids)
               record.no_of_batch=math.ceil(qty/record.per_batch_qty)

    @api.multi
    def unlink(self):
    	print "------------stock.store.location.wizard.....location_wizard.py in api_inventory",self,self._context
    	for res in self:
	    	if res.status=='dispatch':
		        return True
	return super(StockStoreLocationWizard,self).unlink()
    
    @api.onchange('wizard_line')
    def wizard_line_onchange(self):
    	for rec in self:
    		product_data={}
    		for res in rec.wizard_line:
    			if product_data.get(res.product_id.id):
    				product_data[res.product_id.id] += res.done_qty
			else:
				product_data[res.product_id.id] = res.done_qty
				
    		for line in rec.wizard_product_line:
    			if product_data.get(line.product_id.id):
				line.qty = product_data.get(line.product_id.id)

    @api.multi
    @api.depends('wizard_line','wizard_line.master_batches')
    def _get_label_data(self):
            for rec in self:
            	location_view = self.env['stock.location.view'].search([('location_type','=','transit_out'),
            							('location_id','=',rec.picking.location_id.id)])
		location_dest = self.env['n.warehouse.placed.product'].search([
								('n_location_view','=',location_view.id)])
		
            	master_batches = self.env['mrp.order.batch.number'].search([('picking_id','=',rec.picking.id),
            							('store_id','=',location_dest.id)])
		master_qty = sum([ btch.convert_product_qty for btch in master_batches])
		operation_qty= 0
		for line in rec.wizard_line:
			for master in line.master_batches:
				operation_qty += master.total_quantity
				
            	if operation_qty != master_qty:
            		rec.show_label=True
    		else:
    			rec.show_label=False
    
    @api.multi
    def production_process(self):
    	'''This fuunction is used to Transfer production batches to Warehouse INput location '''
    	self.ensure_one()
    	if not self.wizard_product_line:
    		raise UserError("There is No Record to Process Please add Product Records")

	product_qty={}
    	for rec in self:
		for line in self.wizard_product_line:
			if not line.batch_ids:
    				raise UserError("Please add Batches to process.!")
			qty=0
			for batches in line.batch_ids:
				if batches.product_qty <= 0.0:
					batches.unlink()
					continue
				qty += batches.product_qty
			product_qty.update({line.product_id.id:qty})
			line.pack_id.qty_done = qty
			line.pack_id.pack_qty = len(line.batch_ids)
	self.picking.with_context({'production_batches':True}).do_new_transfer()
	# if product_qty = qty_done then wizards are not open it that case default method call(do_transfer)
	# check if backorder wizards are create
	if self.picking.state == 'draft' or all([x.qty_done == 0.0 for x in self.picking.pack_operation_ids]):
		wiz_id = self.env['stock.immediate.transfer'].search([('pick_id','=',self.picking.id)],order='id desc',limit=1)
		if wiz_id:
			wiz_id.process()
	else:
		wiz_id = self.env['stock.backorder.confirmation'].search([('pick_id','=',self.picking.id)],order='id desc',limit=1)
    		if wiz_id:
	    		wiz_id._process()
	product_req_id=self.env['n.manufacturing.request'].search([('name','=',self.picking.origin)])
	backorder_id=self.env['stock.picking'].search([('backorder_id','=',self.picking.id)])
	if not backorder_id:
		 product_req_id.n_state='done'
		 
	for rec in self:
		history_batches=[]
		for line in self.wizard_product_line:
			pack_operation=False
			if backorder_id:
				pack_operation=self.env['stock.pack.operation'].search([
									('picking_id','=',backorder_id.id),
							 		('product_id','=',line.product_id.id)])
			lot_obj=self.env['stock.production.lot']
			lot_id=lot_obj.create({'product_id':line.product_id.id,
						'total_qty':product_qty.get(line.product_id.id),
						'product_uom_id':line.qty_unit.id,})
						
			for batches in line.batch_ids:
				batches.write({'logistic_state':'ready','picking_id':False,'lot_id':lot_id.id,
						'user_id':self.env.user.id,'batch_history':[(0,0,
						{'operation':'production','description':'Tarnsfer to Logistics'})]})
				history_batches.append(batches.id)
			#Tarsfer remaining batches to New Transfer (Produces batches)	
			for btch in line.pack_id.produce_batches:
				if btch.id not in line.batch_ids._ids and pack_operation:
					btch.pack_id = pack_operation.id
			#Tarsfer remaining batches to New Transfer (In-Production batches)	
			if line.pack_id.inprocess_batches and pack_operation:
					line.pack_id.inprocess_batches.write({'pack_id':pack_operation.id})
			# Update Transfer Batches in Production request
                        for each_prod_req in product_req_id:
                            each_prod_req.batches_ids = [(4,b.id) for b in line.batch_ids]
	return True
    		
    @api.multi
    def generate_child_batches(self):
    	''' This method is call when quanity is comes from inventory loss/Purchase '''
    	self.ensure_one()
    	if not self.wizard_product_line:
    		if all(x.product_id.type !='product' for x in self.picking.pack_operation_product_ids):
    			pass
		else:
			raise UserError("There is No Record to Process Please contact to administrator")

	for  rec in self:
		batch_obj=self.env['mrp.order.batch.number']
		lot_obj=self.env['stock.production.lot']
		for  line in rec.wizard_product_line:
			if line.product_id.type !='product':
				continue
			product_qty = line.qty_done 
			batches=[]
			first_str,num_str='',0
			lot_id=lot_obj.create({'product_id':line.product_id.id,'total_qty':product_qty,
					'product_uom_id':line.qty_unit.id,})
			if line.batch_number:
				first_str = line.batch_number[:-4]
				num_str = line.batch_number[-4:]
				if num_str.isdigit():
					num_str=int(num_str)
				else:
					raise UserError('Your Batch number is invalid, please Enter only number in last four Places')
			while product_qty >0:
				n_qty = line.pack_id.packaging_id.qty if product_qty > line.pack_id.packaging_id.qty else product_qty 
				product_qty -= line.pack_id.packaging_id.qty
				batct=''
           			if not line.batch_number:
           				code = self.env['ir.sequence'].next_by_code('mrp.order.batch.number') or 'New'
	           			batct = str('INVT')+'-'+str(code)[3:]
	           		else:
	           			batct =str(first_str)+str(num_str).zfill(4)	
				ids=batch_obj.create({'product_id':line.product_id.id,'lot_id':lot_id.id,
				 	'approve_qty':n_qty,'product_qty':n_qty,
				 	'uom_id':line.qty_unit.id,
					'qty_unit_id':line.qty_unit.id,
					'produce_qty_date':datetime.now(),
					'name':'{}'.format(batct),
					'request_state':'done','logistic_state':'ready',
					'company_id':line.pack_id.picking_id.company_id.id})
				batches.append(ids.id)
				if num_str:
					num_str+=1
			line.pack_id.batch_number=[(6,0,batches)]
    
    # call default backorder method after generating child Batches
    	if self.back_order_id:
		self.back_order_id._process(self.backorder)
    # call default Transfer method after generating child Batches	    
    	elif self.immediate_tra:
		# If still in draft => confirm and assign
		if self.picking.state == 'draft':
		    self.picking.action_confirm()
		    if self.picking.state != 'assigned':
		        self.picking.action_assign()
		        if self.picking.state != 'assigned':
		            raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
		for pack in self.picking.pack_operation_ids:
		    if pack.product_qty > 0:
		        pack.write({'qty_done': pack.product_qty})
		    else:
		        pack.unlink()
		self.picking.do_transfer()
	else:
		#code for get extra receive quantity from purchase/inventory loss
		if (self.picking.location_id.usage in ('inventory','production') or self.picking.picking_type_code =='incoming'):
			for operation in self.picking.pack_operation_product_ids:
				operation.product_qty=operation.qty_done
		 	self.picking.do_transfer()
			
    # click button in Master batch wizard when Picking is in Move to location
    @api.multi	
    def generate_master_batch(self):
    	'''Function used to move Quantity from Input to STOCK(Transit-IN) Location.
    		and Generate Master Batches'''
    	self.ensure_one()
    	if not self.wizard_line:
    		raise UserError("There is No Record to Process Please contact to administrator")
	
	batches_id=[]
	batches_product={}	#Get Batches Quantity of each Product
	for line in self.wizard_line:
		if line.batch_ids==[]:
   			raise UserError("Please add Batches in Master-Batch {}",format(line.master_batch))	
   		if len(line.batch_ids) != len(set(line.batch_ids)):
			raise UserError("In Master Batch '{}' some Child Batches are dupllicate",format(line.master_batch))
		if set(batches_id)&(set(line.batch_ids._ids)):
			btch_list=list(set(batches_id)&(set(line.batch_ids._ids)))
			mtch_ids=self.env['mrp.order.batch.number'].search([('id','in',btch_list)])
			mtch_str=",".join([ m.name for m in mtch_ids])
			raise UserError("{} Batches are in multiple Master-Batches".format(mtch_str))
		batches_id.extend(line.batch_ids._ids)
		batches_product[line.product_id.id] = batches_product[line.product_id.id] + line.done_qty if batches_product.get(line.product_id.id) else  line.done_qty
		
	operation_product={}	#Get Operation Quantity of each Product
	for operation in self.picking.pack_operation_product_ids:
		qty = operation.qty_done if operation.qty_done else operation.product_qty
   		operation_product[operation.product_id.id] = operation_product[operation.product_id.id] + qty if operation_product.get(operation.product_id.id) else  qty
    	
    	# check opearation quantity and batches quantity
	for d in operation_product:
		product_id = self.env['product.product'].search([('id','=',d)]).name
		if not batches_product.get(d,False):
			raise UserError("Product '{}' Not in Found batches Batches".format(product_id))

		if operation_product[d] != batches_product[d]:
			raise UserError("Product '{}' selected batches Quantity  {} is not equal to opeartion Quantity  {} ".format(product_id,batches_product[d],operation_product[d]))

    	for rec in self.wizard_line:
            if not rec.product_id:
                    raise UserError("Please Select product")
            if not rec.master_batch:
                    raise UserError("Please Select master Batches")
            bin_id=self.env['n.warehouse.placed.product'].search([('id','=',rec.stock_location.id)])
            if not bin_id:
                    raise UserError("Bin-Location not found")
            elif bin_id.state =='full':
                    raise UserError("Bin-Location '{}' is fully accoupied".format(bin_id.name))

            if  bin_id.product_type == 'single' and bin_id.product_id.id:
                    if bin_id.product_id.id != rec.product_id.id:
                            raise UserError("Selected '{}' Bin in only for single product, You can't store different product in this Locaiton".format(bin_id.name))
				
		# need to write the code for different packaging of same product
            n_type='out'
            operation_name='Transfer Quantity from store'
            body1="<ul>New Quantity Added in Store</ul>"
            body ="<li>Store Quantity is Transfered To {}</li>".format(bin_id.name)
            operation='transfer'

            add_qty = packages = pkg_capicity=0.0
            add_unit = Packaging_type = pkg_capicity_unit=False
            for btch in rec.master_batch:
                    print "master_batchmaster_batchmaster_batch",btch
                    btch.store_id=bin_id.id
                    add_unit = btch.uom_id
                    packages += len(btch.batch_id)
                    Packaging_type = btch.packaging
                    for child in btch.batch_id:
                            add_qty += child.convert_product_qty
                            child.write({'store_id':bin_id.id,
                            'batch_history':[(0,0,{'operation':'logistics',
                                    'description':'Transfer from Bin-{} To Bin-{}'.format(rec.stock_location.name,bin_id.name)})]})

            secondary_pkg = self.env['product.packaging'].search([('pkgtype','=','secondary'),
                                            ('product_tmpl_id','=',rec.product_id.product_tmpl_id.id),
                                            ('unit_id','=',Packaging_type.uom_id.id)],limit=1)

            if  rec.stock_location.product_type == 'multi':
                    store_product=self.env['store.multi.product.data'].search([
                                    ('product_id','=',rec.product_id.id),
                                    ('store_id','=',rec.stock_location.id),
                                    ('Packaging_type','=',Packaging_type.id)])
                    if not store_product :
                            raise UserError("Product Not found in '{}', Contact administrator".format(rec.stock_location.name))

                    elif len(store_product)>1:
                            raise UserError("Multiple Product({}) entry with same packaging found which is not allowed in bin {}, Contact administrator".format(rec.product_id.name,rec.stock_location.name))
                    if (store_product.total_quantity - add_qty)<0 :
                                raise UserError("Trasnfer Quantity is greater than present batch quantity, Contact administrator")
			## validation code in single product		
            if  bin_id.product_type == 'single':
                if bin_id.state=='full':
                        raise UserError("Selected Bin-Location in FULLY Occoupied")
                elif bin_id.state in ('no_use','maintenance',):
                        raise UserError("Selected Bin-Location is Not available for storage")
                elif bin_id.state in ('partial','empty',):
                        secondary_pkg_qty = secondary_pkg.qty if secondary_pkg else 1
                        pkg_capicity =  (Packaging_type.qty * secondary_pkg_qty)*bin_id.max_qty
                        if add_qty > pkg_capicity :
                                raise UserError("According to your packaging capacity you can store maximun {} {} quantity \n but Your Selected Quantity is {} {}".format(pkg_capicity,Packaging_type.unit_id.name,add_qty,Packaging_type.unit_id.name))
					
            pkg_capicity_unit = Packaging_type.uom_id if secondary_pkg else Packaging_type.unit_id
		# update CURRENT Bin-Location(single product)		
            if  rec.stock_location.product_type == 'single':
                    rec.stock_location.total_quantity -= add_qty
                    if rec.stock_location.total_quantity <= 0.0 :
                            rec.stock_location.write({'state':'empty','product_id':False,
                                    'total_quantity':0.0,'total_qty_unit':False,'qty_unit':False,
                                    'pkg_capicity':0.0,'pkg_capicity_unit':False,'packages':0.0,
                                    'pkg_unit':False,'Packaging_type':False})
                            body+="<li> Location makes empty </li>"
                    else:
                            new_qty = rec.stock_location.total_quantity - add_qty 
                            new_pkg = rec.stock_location.packages-packages
                            rec.stock_location.write({'state':'partial','total_quantity':new_qty,
                                                      'packages':new_pkg})

                            body+="<li>Quantity Transfered  : "+str(add_qty)+" </li>"
                            body+="<li>Packets Transfered  : "+str(packages)+()+" </li>"

    # update CURRENT Bin-Location(Multi product)
            elif  rec.stock_location.product_type == 'multi':
                    store_product=self.env['store.multi.product.data'].search([
                                    ('product_id','=',rec.product_id.id),
                                    ('store_id','=',rec.stock_location.id),
                                    ('Packaging_type','=',Packaging_type.id)])

                    if store_product.total_quantity <= add_qty:
                            store_product.unlink()
                    else:
                            new_qty = store_product.total_quantity - add_qty 
                            new_pkg = store_product.packages-packages
                            store_product.write({'total_quantity':new_qty,'packages':new_pkg})
                            rec.stock_location.state='partial'

                    if rec.stock_location.multi_product_ids==[]:
                            rec.stock_location.state='empty'

		# Transfer Quantity in NEW location(Sigle product location)
            if  bin_id.product_type == 'single':
                    pkg_qty = secondary_pkg.qty if secondary_pkg else Packaging_type.qty
                    pkg_capicity =  pkg_qty * bin_id.max_qty
                    if not bin_id.product_id:
                            bin_id.product_id = rec.product_id.id
                            bin_id.total_qty_unit = add_unit.id
                            body1+="<li>Product added  : "+str(rec.product_id.name)+" </li>"

                            bin_id.pkg_unit = pkg_capicity_unit
                            bin_id.Packaging_type = Packaging_type
                            body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"

                            bin_id.pkg_capicity = pkg_capicity
                            bin_id.pkg_capicity_unit = pkg_capicity_unit
                            body1+="<li>Packaging Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"

                    else:
                            body1+="<li>Product '{}' Update </li>".format(str(rec.product_id.name))
						
                    bin_id.total_quantity += add_qty
                    body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"

                    bin_id.packages += packages if secondary_pkg else pkg_qty
                    body1+="<li>Packets Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"

                    if bin_id.pkg_capicity == bin_id.packages :
                            bin_id.state = 'full'
                    else:
                            bin_id.state = 'partial'
					
		# Transfer Quantity in NEW location(Multi product location)	
            elif  bin_id.product_type == 'multi':
                    store_product=self.env['store.multi.product.data'].search([
                                    ('product_id','=',rec.product_id.id),
                                    ('store_id','=',bin_id.id),
                                    ('Packaging_type','=',Packaging_type.id)])

                    if not store_product:
                            add_vals={'product_id':rec.product_id.id}
                            body1 +="<li>Product add : "+str(rec.product_id.name)+" </li>"

                            add_vals.update({'total_quantity':add_qty})
                            add_vals.update({'total_qty_unit':add_unit.id})
                            body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"

                            add_vals.update({'pkg_capicity':pkg_capicity})
                            add_vals.update({'pkg_capicity_unit':pkg_capicity_unit.id})
                            body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"

                            add_vals.update({'pkg_unit':pkg_capicity_unit})
                            add_vals.update({'Packaging_type':Packaging_type.id})
                            body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
                            bin_id.multi_product_ids=[(0,0,add_vals)]

                    elif store_product:
                            body1 +="<li>Product update qty : "+str(rec.product_id.name)+" </li>"
                            store_product.total_quantity += add_qty
                            body1+="<li>Quantity Added : "+str(add_qty)+" "+str(add_unit.name)+" </li>"
                            store_product.pkg_capicity += packages
                            body1+="<li>Packag Capicity : "+str(packages)+" "+str(pkg_capicity_unit.name)+" </li>"
                            body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
                            store_product.packages += packages
					
				#if rec.add_qty == rec.qty:
				#	bin_id.state = 'full'
				#else:
                    bin_id.state = 'partial'

            self.env['location.history'].create({
                            'stock_location':bin_id.id,
                            'product_id':rec.product_id.id,
                            'operation_name':'Receive Quantity from Store Transfer',
                            'operation':'transfer',
                            'qty':self.add_qty,
                            'n_type':'in'})

            self.env['location.history'].create({
                            'stock_location':rec.stock_location.id,
                            'product_id':rec.product_id.id,
                            'operation_name':'Transfer to Other Bin {}'.format(bin_id.name),
                            'operation':'transfer',
                            'qty':self.add_qty,
                            'n_type':'out'})
					
            if body1:
                    bin_id.message_post(body1)
            if body:
                    rec.stock_location.message_post(body)

        rec.master_batches= False
        order_form = self.env.ref('api_inventory.bin_location_trasnfer_form_view', False)
        name='Transfer Quantity In Store To Store'
        context=self._context.copy()
        remove_list=('default_loc_bin_id','default_product_id','default_t_qty_unit','default_dest_bin_id',
                                    'trsf_id','bin_id','default_master_batches')
        context={ key:context[key] for key in context if key not in remove_list}
        self.update_html_view(order_form,rec.location_id)
        context.update({'default_stock_location':rec.stock_location.id,
                        'default_location_id':rec.stock_location.n_location.id,
                        'default_operation_type':'transfer',
                        'default_product_id':rec.product_id.id,})
        if rec.stock_location.product_type=='multi':
                context.update({'multi_product_operation':True})
        else:
                context.update({'product_id':rec.stock_location.product_id.id})
        return {
                    'name':name,
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'location.stock.operation',
                    'views': [(order_form.id, 'form')],
                    'view_id': order_form.id,
                    'target': 'current',
                    'nodestroy' : False,
                    'context':context,
                    'flags': {'form': {'options': {'mode': 'edit'}}},
                 }



#	   batches_data=[]
#    	   if line.batch_ids:
#    	   	body=''
#    	   	total_qty = sum([res.convert_product_qty if res.convert_product_qty else res.product_qty for res in line.batch_ids ])
#                #                                added by bhargavi
#
#                matser_batch_id.total_quantity=total_qty
#                matser_batch_id.uom_id=res.uom_id.id
#                #                                added by bhargavi
#
#    	   	for res in line.batch_ids:
#    	   		qty=res.convert_product_qty if res.convert_product_qty else res.product_qty
#    	   		batches_data.append((0,0,{'product_id':line.product_id.id,'store_id':self.locations.id,
#   				'quantity':qty,'unit_id':line.qty_unit.id,'batch_number':res.id,
#   				'lot_number':res.lot_id.id}))
#			res.write({'logistic_state':'transit_in',
#				   'master_id':matser_batch_id.id,'store_id':self.locations.id,'picking_id':self.picking.id,
#				   'batch_history':[(0,0,{'operation':'logistics',
#				   	'description':'Received by Logistics({}) using Master-Batch {}'.format(self.picking.name,matser_batch_id.name)})]})
#		print "......................",self.locations,self.locations.product_type
#
#		if self.locations.product_type=='multi':
#                        print "self.locations,,,,,,,,,,,",self.locations
#			loc_id=self.locations
#			exist_pro = self.env['store.multi.product.data'].search([('product_id','=',line.product_id.id),
#							('Packaging_type','=',line.packaging.id),
#							('store_id','=',loc_id.id)])
#			if exist_pro:
#				exist_pro.packages += len(line.batch_ids._ids)
#				exist_pro.total_quantity += total_qty
#				body+="<li>Packages added : "+str(len(line.batch_ids._ids))+" </li>"
#				body+="<li>Quantity added : "+str(total_qty)+" </li>"
#			else:	
#				add_vals={'product_id':line.product_id.id}
#				body+="<li>New Product add : "+str(line.product_id.name)+" </li>"
#				if not line.sec_packaging:
#					capacity=line.packaging.qty*loc_id.max_qty
#					add_vals.update({'pkg_capicity':capacity})
#					add_vals.update({'pkg_capicity_unit':line.packaging.unit_id.id})
#					body+="<li>Packaging Capicity : "+str(capacity)+" "+str(line.packaging.unit_id.name)+" </li>"
#					add_vals.update({'packages':len(line.batch_ids._ids)})
#					add_vals.update({'pkg_unit':line.packaging.uom_id.id})
#					
#				elif line.packaging and line.sec_packaging:
#					capacity=line.sec_packaging.qty*loc_id.max_qty
#					add_vals.update({'pkg_capicity':capacity})
#					add_vals.update({'pkg_capicity_unit':line.sec_packaging.unit_id.id})
#					body+="<li>Packag Capicity : "+str(capacity)+" "+str(line.sec_packaging.unit_id.name)+" </li>"
#					add_vals.update({'packages':len(line.batch_ids._ids)})
#					add_vals.update({'pkg_unit':line.sec_packaging.unit_id.id})
#				body+="<li>No of Packages : "+str(len(line.batch_ids._ids))+" "+str(line.sec_packaging.unit_id.name)+" </li>"
#				add_vals.update({'total_quantity':total_qty})
#				add_vals.update({'total_qty_unit':line.packaging.unit_id.id})
#				body+="<li>Quantity Added : "+str(total_qty)+" "+str(line.packaging.unit_id.name)+" </li>"
#				add_vals.update({'Packaging_type':line.packaging.id})
#				body+="<li>Packaging : "+str(line.packaging.name)+" </li>"
#				loc_id.multi_product_ids=[(0,0,add_vals)]
#			loc_id.state='partial'
#		else:
#			raise UserError("Transfer error in generate master batch...")
#			
#		self.locations.message_post(body)
#		operation_dsc = 'From Inventory Loss'
#		if mo_number:
#			operation_dsc = 'From Manufacturing {}'.format(mo_number)
#		elif po_number:
#			operation_dsc = 'From Purchasing {}'.format(po_number)
#
#		self.env['location.history'].create({'stock_location':self.locations.id,
#							'product_id':line.product_id.id,
#							'qty':total_qty,'n_type':'in',
#							'operation_name':operation_dsc,
#							'operation':'mo' if mo_number else 'po' if po_number else 'stk',
#							})
#							
#		# create history in stock Picking
#		store_data=self.env['picking.lot.store.location'].create({'picking_id':self.picking.id,
#    							'master_id':matser_batch_id.id,'quantity':line.done_qty,
#    							'unit_id':line.qty_unit.id,'store_id':self.locations.id,
#    							'product_id':line.product_id.id,
#    							'batches_ids':batches_data})
#    							
    # call default backorder methods
    	if self.back_order_id:
		self.back_order_id._process(self.backorder)
		picking_obj=self.env['stock.picking']
    		if self.backorder:
    			pre_order_id= picking_obj.search([('name','=',self.picking.origin)])
    			backorder_id= picking_obj.search([('backorder_id','=',self.picking.id)])
    			if pre_order_id:
    				result1=[]
    				for move in pre_order_id.move_lines:
    					for back in backorder_id.move_lines:
    						if move.product_id.id ==back.product_id.id:
    							result1.append((0, 0, {'product_id': move.product_id.id,
    								 'quantity': back.product_qty, 'move_id': move.id}))
                		vals={'product_return_moves':result1,'location_id': pre_order_id.location_id.id}
                		return_id = self.env['stock.return.picking'].with_context({
                							'new_active_id':pre_order_id.id}).create(vals)
				return_data=return_id.create_returns()
				pick_id=picking_obj.search([('id','=',return_data.get('res_id'))])
				pick_id.name = pick_id.name.replace('/INT/','/RE-INT/')
				self.picking.message_post('Return for Rejected quantity <b>{}</b>'.format(pick_id.name))
				pick_id.message_post('Return form Order <b>{}</b>'.format(self.picking.name))
					    
	# call default Transfer methods	    
    	elif self.immediate_tra:
		# If still in draft => confirm and assign
		if self.picking.state == 'draft':
		    self.picking.action_confirm()
		    if self.picking.state != 'assigned':
		        self.picking.action_assign()
		        if self.picking.state != 'assigned':
		            raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
		for pack in self.picking.pack_operation_ids:
		    if pack.product_qty > 0:
		        pack.write({'qty_done': pack.product_qty})
		    else:
		        pack.unlink()
		self.picking.do_transfer()

    # On Clicking dispatch process in Wizard of delivery order
    @api.multi
    def dispatch_process(self):
    	'''Use in Dispatch Delivery Order for batches selection from wizard.'''
    	try:
		for rec in self:
    	# MO	
			if rec.wizard_line==[] or not rec.wizard_line:
				raise ValueError("There is not record to process")
			product_ids=[]
			for line in rec.wizard_line:
				if line.done_qty <= 0:
					raise ValueError("Currently there is no quantity picked for product '{}', Please Pick some quantity then click on Dispatch \n Or \n If You dont want to dispatch this product then remove product from line it will transfer to backorder after dispatch of this order".format(line.product_id.name))	
				line.pack_id.qty_done=line.done_qty
				product_ids.append(line.product_id.id)
				
			for op in rec.picking.pack_operation_product_ids:
				if op.product_id.id not in product_ids:
					op.qty_done=0.0	
					
			if not rec.dispatch_doc or not rec.note:
				if rec.picking.sale_id:
					raise ValueError("Please Upload Dispatch Documents or add Remarks.")
				
			store_history=[]
                        if rec.picking.material_request_id:
                            if rec.picking.material_request_id.production_id.state not in ('in_production','done','cancel'):
                                rec.picking.material_request_id.production_id.write({'state':'ready'})
#            to link backorder of rm request to mo prodiction
			# call method in module directory(stock_picking.py)
			if rec.dispatch_doc:
				rec.picking.dispatch_doc=rec.dispatch_doc
				
			if rec.note:
				rec.picking.message_post(body='<b>Remark from Dispatch State</b> <ul>\n'+str(rec.note))
			_logger.info("Dispatch process Start....")
			for line in rec.wizard_line:
				if rec.picking.picking_type_code=='outgoing':
					line.master_batches.write({'store_id':False,'logistic_state':'dispatch',
							'location_id':False,'picking_id':False})
				elif rec.picking.picking_type_code=='internal':
                                        if 'MO' in rec.picking.origin if rec.picking.origin else '':
                                            if rec.picking.material_request_id:
                                                if rec.picking.material_request_id.production_id.state!='in_production':
                                                    rec.picking.material_request_id.production_id.write({'state':'ready'})
					if rec.picking.location_dest_id.actual_location and rec.picking.location_id.actual_location:
						new_company_id = rec.picking.location_dest_id.company_id.id
						line.master_batches.write({'store_id':rec.store_dest_id.id,
							'logistic_state':'transit_in',
							'location_id':rec.picking.location_dest_id.id,
							'company_id':new_company_id,
							'picking_id':False})
					elif rec.picking.location_id.actual_location and rec.picking.location_dest_id.usage == 'production':
						line.master_batches.write({'store_id':False,
							'logistic_state':'done',
							'location_id':rec.picking.location_dest_id.id,
							'picking_id':False})
					else:
						raise m1
				else:
					raise m2
				for master in line.master_batches:	#master Batches
					st_qty=pkg=0.0
					batch_history=[]
					unit_btch=False
					for btch in master.batch_id:
						if rec.locations.id==btch.store_id.id:
							st_qty += btch.convert_product_qty
							if rec.picking.picking_type_code=='outgoing':
								btch.write({'store_id':False,
									'logistic_state':'dispatch',
									'sale_line_id':False,
									'sale_id':False,'picking_id':False,
									'batch_history':[(0,0,
						{'operation':'dispatch','description':'Dispatch from stock in Delivery Order {}'.format(rec.picking.name)})]})
							elif rec.picking.picking_type_code=='internal':
								if rec.picking.location_dest_id.actual_location and rec.picking.location_id.actual_location:
									new_company_id = rec.picking.location_dest_id.company_id.id
									btch.write({'store_id':rec.store_dest_id.id,
									'sale_line_id':False,
									'logistic_state':'transit_in',
									'sale_id':False,'picking_id':False,
									'company_id':new_company_id,
									'batch_history':[(0,0,
						{'operation':'logistics','description':'Warehouse Transfer from {} To {}'.format(rec.picking.location_id.complete_name,rec.picking.location_dest_id.complete_name)})]})
								elif rec.picking.location_id.actual_location and rec.picking.location_dest_id.usage == 'production':
									btch.write({'store_id':False,
										'sale_line_id':False,
										'logistic_state':'done',
										'sale_id':False,'picking_id':False,
									'batch_history':[(0,0,
						{'operation':'logistics','description':'Internal Transfer from {} To {}'.format(rec.picking.location_id.complete_name,rec.picking.location_dest_id.complete_name)})]})
								else:
									raise e1
							else:
								raise e2
								
							unit_btch=btch.qty_unit_id.id if btch.qty_unit_id else btch.uom_id.id if btch.uom_id else None,
							batch_history.append((0,0,{
								'picking_id':rec.picking.id,
								'store_id':rec.locations.id,
								'product_id':line.product_id.id if btch.product_id else None,
								'quantity':btch.convert_product_qty,
								'unit_id':unit_btch,
								'lot_number':btch.lot_id.id if btch.lot_id else  None,
								'batch_number':btch.id,}))
							pkg +=1
							
					n_qty=st_qty
					if batch_history:
						store_history.append((0,0,{'batches_ids':batch_history,
							'product_id':line.product_id.id,
							'picking_id':rec.picking.id,
							'store_id':rec.locations.id,
							'master_id':master.id,
							'quantity':n_qty,'unit_id':unit_btch}))
							
					if rec.locations.product_type=='multi':
						for pro in rec.locations.multi_product_ids:
							if  pro.product_id.id==line.product_id.id:
								n_qty=pro.total_quantity
								pro.total_quantity -= st_qty
								pro.packages -= int(pkg)
								st_qty -=  n_qty
								if pro.total_quantity <=0:
									pro.unlink()
								if st_qty <=0:
									break
						rec.locations.state = 'partial'

					self.env['location.history'].create({
							'stock_location':rec.locations.id,
							'product_id':line.product_id.id,
							'qty':n_qty,'n_type':'out',
							'n_do_number':rec.picking.id,
							'operation':'do',
							'operation_name':'Dispatched Product from transit Location',
							})
				#use in Warehouse2Warehouse Tarnsfer			
				if rec.picking.picking_type_code=='internal':
					if rec.picking.location_dest_id.actual_location and rec.picking.location_id.actual_location:
						exit_pro=self.env['store.multi.product.data'].search([
									('store_id','=',rec.store_dest_id.id),
									('product_id','=',line.product_id.id),
									('Packaging_type','=',line.packaging.id),])
						packages = sum([ len(master.batch_id) for q in line.master_batches])
						if exit_pro:
							exit_pro.total_quantity += line.done_qty
							exit_pro.packages += packages
						else:
							add_vals={'product_id':line.product_id}
							body ="<li>Product add : "+str(line.product_id.name)+" </li>"
							add_vals.update({'total_quantity':line.done_qty})
							add_vals.update({'total_qty_unit':line.to_do_unit.id})
							body+="<li>Quantity Added : "+str(line.done_qty)+" "+str(line.to_do_unit.name)+" </li>"
							add_vals.update({'packages':packages})
							add_vals.update({'pkg_unit':line.packaging.uom_id.id})
							add_vals.update({'Packaging_type':line.packaging.id})
							body+="<li>Packaging : "+str(line.packaging.name)+" </li>"
							rec.store_dest_id.multi_product_ids=[(0,0,add_vals)]
							rec.store_dest_id.message_post(body)
							
						self.env['location.history'].create({
								'stock_location':rec.store_dest_id.id,
								'product_id':line.product_id.id,
								'operation_name':'comes From Warehouse tarnsfer',
								'operation':'transfer',
								'qty':line.done_qty,
								'n_type':'in'})
		# Write History of master batches in Delivery
			if store_history:
				rec.picking.store_ids=store_history
				
		# to upadate remaining undispatched picked quantity of product 
			if rec.move_loc == 'in':
			    	location_view = self.env['stock.location.view'].search([
			    						('location_type','=','transit_in'),
			    						('location_id','=',rec.picking.location_id.id)])
				location_dest = self.env['n.warehouse.placed.product'].search([
									('n_location_view','=',location_view.id)])
			    	master_extra_batches=self.env['stock.store.master.batch'].search([
			    						('picking_id','=',rec.picking.id)])
			    	backorder = self.env['stock.picking'].search([('backorder_id','=',rec.picking.id),
							('state','not in' ,('done','cancel','dispatch','delivered'))])
			    	if backorder:
			    		backorder.note=False
				for mst in master_extra_batches:
					mst.store_id=location_dest.id
					mst.logistic_state='reserved'
					mst.picking_id = False #backorder.id if backorder else False
#                                        commented by bhargavi
#					for btch in mst.batch_id:
#						btch.store_id=location_dest.id
#						btch.picking_id = backorder.id if backorder else False
#						btch.logistic_state = 'reserved' if backorder else 'transit_in'
					multi_store_obj=self.env['store.multi.product.data']
					# Transit IN multi product data id
					transit_in = multi_store_obj.search([('store_id','=',location_dest.id),
									('product_id','=',mst.product_id.id),
									('Packaging_type','=',mst.packaging.id)]) 
					# Transit out multi product data id
					transit_out = multi_store_obj.search([('store_id','=',rec.locations.id),
									('product_id','=',mst.product_id.id),
									('Packaging_type','=',mst.packaging.id)])
					
					self.env['location.history'].create({'stock_location':location_dest.id,
								'product_id':mst.product_id.id,
								'operation_name':'comes after Dispatch remaining',
								'operation':'transfer',
								'qty':mst.total_quantity,
								'n_type':'in'})
								
					if not transit_in:
						add_vals={'product_id':mst.product_id}
						body ="<li>Product add : "+str(mst.product_id.name)+" </li>"
						add_vals.update({'total_quantity':mst.total_quantity})
						add_vals.update({'total_qty_unit':mst.uom_id.id})
						body+="<li>Quantity Added : "+str(mst.total_quantity)+" "+str(mst.uom_id.name)+" </li>"
						add_vals.update({'packages':len(mst.batch_id)})
						add_vals.update({'pkg_unit':mst.packaging.uom_id.id})
						add_vals.update({'Packaging_type':mst.packaging.id})
						body+="<li>Packaging : "+str(mst.packaging.name)+" </li>"
						location_dest.multi_product_ids=[(0,0,add_vals)]
						location_dest.message_post(body)
					else:
						transit_in.total_quantity += mst.total_quantity
						body='Quantity update after dispatch'
						body+='<li>{} {} </li>'.format(mst.product_id.name,mst.total_quantity)
						location_dest.message_post(body)
					if transit_out.total_quantity <= mst.total_quantity:
						transit_out.unlink()
					else:
						transit_out.total_quantity -= mst.total_quantity
			# To release batches reserved against currnet delivery order but not delivered or not picked
			unpick_batches=self.env['mrp.order.batch.number'].search([
	    						('picking_id','=',rec.picking.id),
	    						('store_id','!=',False),
							('store_id.location_type','=','store')])
			if unpick_batches:
				unpick_batches.write({'picking_id':False,
					'sale_line_id': False,
					'logistic_state':'stored' ,
					'batch_history':[(0,0,{'operation':'logistics',
							'description':'UnReserve from {} after Dispatching Other Batch'.format(rec.picking.name)})]})

			unpick_tr_batche=self.env['mrp.order.batch.number'].search([
	    						('picking_id','=',rec.picking.id),
	    						('store_id','!=',False)])
				
			if unpick_tr_batche:
				unpick_tr_batche.write({'picking_id':False,
					'sale_line_id': False,
					'logistic_state':'transit_in',
					'batch_history':[(0,0,{'operation':'logistics',
							'description':'UnReserve from {} after Dispatching Other Batch'.format(rec.picking.name)})]})
			_logger.info("End Dispatch process \n Start Stock removal Process....")
			
			if rec.picking.picking_type_code=='outgoing':
				rec.picking.action_first_validation_data()
			elif rec.picking.picking_type_code=='internal':
				if rec.picking.location_id.actual_location and  (rec.picking.location_dest_id.actual_location or rec.picking.location_dest_id.usage == 'production'):
					rec.picking.do_transfer()
					if rec.picking.location_dest_id.actual_location and rec.picking.location_id.actual_location:
						new_company_id = rec.picking.location_dest_id.company_id.id
						if rec.picking.location_id.company_id.id != new_company_id:
							_logger.info("Change Company of STOCK")
							for moves in rec.picking.move_lines_related:
								for quants in moves.quant_ids:
									quants.company_id=new_company_id
			_logger.info("End Stock removal Process....")					
    	except Exception as err:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		_logger.error("API-EXCEPTION.. in wizard Dispatching of product {} {}".format(err,exc_tb.tb_lineno))
		raise UserError("API-EXCEPTION..in wizard Dispatching of product \n{}".format(err))	
    	return True
        
class StockStoreLocationWizardLine(models.TransientModel):
    """This is a temporary table to get and store the Lot in store location 
       1) use to select batches and transfer from produciton to input location."""
    
    _name = 'stock.store.location.wizard.line'
    stock_location = fields.Many2one('n.warehouse.placed.product','Stock Location')

    select_store = fields.Boolean('Check')
    wizard_id = fields.Many2one('stock.store.location.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product')
    
    master_batch = fields.Char('Master Batch')
    max_qty = fields.Float('Max Batches',help="Maxinum quantity of batches in Master Batch")
    packaging = fields.Many2one('product.packaging' ,string="Packaging",copy=True,help="Primary packaging")
    sec_packaging = fields.Many2one('product.packaging' ,string="Packaging",help="Secondary packaging")
    
    master_batches = fields.Many2many('stock.store.master.batch','master_batch_dispatch_wizard',
    				'master_id','wizard_id','Master Batch')
    lot_ids = fields.Many2many('stock.production.lot','lot_store_inventory_wizard','lot_id','wizard_id','Transfer No')
    batch_ids = fields.Many2many('mrp.order.batch.number','batch_store_inventory_wizard','batch_id',
    				'wizard_id','Reserved Batches')
    
    locations_ids = fields.Many2many('n.warehouse.placed.product','warehouse_store_inventory_wizard_rel',
    				     'wiz_id','loc_id','Bin-Locations')
    batch_qty = fields.Float('Batch Quantity',help="Total number of batches in Master Batch")
    to_do_qty = fields.Float('TO Do',help="Scheduled Dispatch Quantity, But at time of dispatch you can reduce the quantity by selecting less batches")
    pick_qty = fields.Float('Total Picked Quantity')
    done_qty = fields.Float('Done Quantity',compute='_get_batch_qty',help="Quantity is Dispatched and update in operation after process")
    qty_unit = fields.Many2one('product.uom','Unit',compute='_get_batch_qty')
    
    to_do_unit = fields.Many2one('product.uom','Unit')
    pack_id = fields.Many2one('stock.pack.operation','operation')
    
#    @api.onchange('stock_location')
#    def stock_location_onchange(self):
#    	if self.stock_location:
#            for each in self.wizard_id.wizard_line:
#                if each.id!=self.id:
#                    if each.stock_location.id==self.stock_location.id:
#                        self.stock_location=False
#                        return {'warning': {'title': "Invalid", 'message': "Cannot Take Same Rack Location to place Product!!"}}

    @api.multi
    @api.onchange('batch_ids','master_batches')
    def _get_batch_qty(self):
    	for res in self:
                print "xdfdgdfgdfgdfg",res,len(res.batch_ids),res.max_qty
    		if len(res.batch_ids) > res.max_qty:
    			raise UserError("Your Master Batches Quantity Is Full, You can Not add more batches")
    		qty=0.0
    		unit=False
    		# for incomming in moce to location wizard
		for line in res.batch_ids:
			qty += line.convert_product_qty 
		 	unit=line.qty_unit_id.id
		 	
		# for outgoing in Dispatch wizard	
	 	if not res.batch_ids and res.master_batches:
	 		for line in res.master_batches:
	 			qty += line.total_quantity 
		 		unit = line.uom_id.id
		res.done_qty = qty
		res.qty_unit = unit
    		res.batch_qty = len(res.batch_ids)
    		
    @api.onchange('lot_ids')
    def lot_onchange(self):
    	for res in self:
    		ids=res.lot_ids._ids
    		if res.wizard_id.status=='invt_loss':
    			search_id = self.env['mrp.order.batch.number'].search([('lot_id','in',ids),
							('product_id','=',res.product_id.id)],limit=res.max_qty)
    			if search_id :
    				res.batch_ids = [(4,i) for i in search_id._ids]
			if not res.lot_ids:
				res.batch_ids = []
				
		if res.wizard_id.status=='dispatch':
			search_id = self.env['stock.store.master.batch'].search([('lot_id','in',ids),
							('product_id','=',res.product_id.id),
							('picking_id','=',res.wizard_id.picking.id)])
    			if search_id :
    				res.master_batches = [(4,i) for i in search_id._ids]
			if not res.lot_ids:
				res.master_batches = []
  
class StockStoreproductWizardLine(models.TransientModel):
    """This is a temporary table to store product information.."""
    _name = 'stock.store.product.wizard.line'

    wizard_id = fields.Many2one('stock.store.location.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product')
    qty_done = fields.Float('Operation Qty')
    qty = fields.Float('Total Batches Quantity',compute='_get_batch_qty' ,store=True)
    qty_unit = fields.Many2one('product.uom','Unit')
    batch_number = fields.Char('Batch Number')
    max_batches = fields.Float('Maximum Batches')
    btch_unit = fields.Many2one('product.uom','Type')
    pack_id = fields.Many2one('stock.pack.operation','operation')
    batch_ids = fields.Many2many('mrp.order.batch.number','batch_store_production_wizard','batch_id',
    				'wizard_line_id','Batches')
    # for production to INput Location Transfer
    batch_count = fields.Float('Total Batches Quantity',compute='_get_batch_count')
    batch_qty = fields.Float('Total Batches Quantity',compute='_get_batch_count')
    	
    @api.depends('batch_ids')
    def _get_batch_count(self):
	for rec in self:
		if rec.batch_ids:
			rec.batch_count = len(rec.batch_ids)
			rec.batch_qty = sum([q.product_qty for q in rec.batch_ids])
		
    @api.depends('wizard_id.wizard_line')
    def _get_batch_qty(self):
	for rec in self:
		qty =0
		for res in rec.wizard_id.wizard_line:
			if rec.product_id.id == res.product_id.id:
				qty += res.done_qty
		rec.qty = qty

