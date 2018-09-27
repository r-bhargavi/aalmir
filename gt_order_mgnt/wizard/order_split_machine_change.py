# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
from openerp import tools
from datetime import datetime, date, timedelta
import math
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import json

class MrpWorkSplit(models.TransientModel):
    _name = 'mrp.workorder.split'
    
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Current Order No.') 
    production_id=fields.Many2one('mrp.production', string='Manufacturing No.') 
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    machine_type_ids=fields.Many2many('machinery.type', string="Machine Type", related='workcenter_id.machine_type_ids')
    machine = fields.Many2one('machinery', string='Machine')  
    date_planned=fields.Datetime('Schedule Date', default=fields.Datetime.now)
    date_planned_end=fields.Datetime('End Date', readonly=True)
    product=fields.Many2one('product.product', string='Product Name')
    uom=fields.Many2one('product.uom', string='Unit')
    qty=fields.Float('qty')
    split_qty=fields.Float('Split qty')
    split_uom=fields.Many2one('product.uom', string='Unit')
    hide_rm=fields.Boolean('Hide Rm Related field')
    #capacity_per_cycle=fields.Float('Capacity Per Cycle')
    #p_hour=fields.Integer('Hour')
    #p_minute=fields.Integer('Minute')
    #p_second=fields.Integer('Second')
    #wk_capacity_type=fields.Selection([('product','Product'),('custom','Custom'),('next','Process')] ,
    #                   string='Capacity Type', default='product')
    #total_cycle=fields.Float('Total Cycle')
    #total_hour=fields.Float('Total Hour')
    #remaining_qty=fields.Float('Move to Next Splitted Work Order Qty', compute='rmqty')
    #remaining_uom=fields.Many2one('product.uom', string='Unit',compute='rmqty')
    
    remain_qty=fields.Float('Current Remain qty', compute='_get_remain_qty')
    change_reason=fields.Text('Reason')
    machine_capacity_type=fields.Selection([('product','Product Base'),('machine','Machine Base')],string='Capacity Calculation Type', related='machine.capacity_type')
    capacity_type=fields.Many2one('machinery.capacity.type', string='Applicable Capacity')
    split_line_ids=fields.One2many('mrp.workorder.split.line','split_id', string='Split Lines')
    
    #requested_qty=fields.Float('Requested Qty')
    #requested_uom=fields.Many2one('product.uom', string='Unit')
    #remain_requested_qty=fields.Float('Requested Remain',compute='_get_remain_qty')
    #remain_requested_uom=fields.Many2one('product.uom', string='Unit')
    received_qty=fields.Float('Received Qty')
    received_uom=fields.Many2one('product.uom', string='Unit')
    remain_received_qty=fields.Float('Received Remain',compute='_get_remain_qty')
    remain_received_uom=fields.Many2one('product.uom', string='Unit')
    check_bool=fields.Boolean(compute='check_bool_val', )
  
    @api.multi
    @api.depends('remain_received_qty','remain_qty') 
    def check_bool_val(self):
        for record in self:
            if record.received_qty:
               if record.remain_received_qty < record.remain_qty:
                  record.check_bool=True
               else:
                  record.check_bool=False
            else:
                if record.remain_received_qty < 0:
                   record.check_bool=True
            if record.remain_received_qty:
               if record.remain_received_qty > record.remain_qty:
                  record.check_bool=True
            
    @api.constrains('qty',)
    def _check_qty(self):
        for record in self:
            pass
            '''if record.split_line_ids:
               sm=sum(line.qty for line in record.split_line_ids)
               if record.qty <= sm:
                  raise ValidationError("In split Case Split qty is always less than Required Qty ") '''

    @api.multi
    @api.depends('split_line_ids.qty') 
    def _get_remain_qty(self):
       for record in self:
           qty=received=0
           for line in record.split_line_ids:
               qty=sum(line.qty for line in record.split_line_ids)
               received=sum(line.received for line in record.split_line_ids)
           if qty:
              record.remain_qty=record.qty-qty
           else:
              record.remain_qty=record.qty
           
           if received:
              record.remain_received_qty=record.received_qty-received
           else:
              record.remain_received_qty=record.received_qty
              

    @api.multi
    @api.onchange('split_qty')
    def enddate(self):
        for record in self:
            if record.qty:
               if record.order_id.machine:
                  hr=(record.order_id.p_hour * 60 *60)  +(record.order_id.p_minute*60 + record.order_id.p_second)
                  time_cycle=hr * 0.000277778
                  cycle=float((record.split_qty + record.order_id.total_product_qty)/record.order_id.capacity_per_cycle)
                  hour=(cycle *(time_cycle)) *(record.order_id.machine.time_efficiency or 1.0)# +((record.order_id.machine.time_start or 0.0) +(record.order_id.machine.time_stop or 0.0))
                  record.date_planned_end=datetime.strptime(record.order_id.date_planned, '%Y-%m-%d %H:%M:%S')+ timedelta(hours=hour)
               
    @api.multi
    @api.depends('qty', 'split_qty')
    def rmqty(self):
        for record in self:
            if record.qty:
               record.remaining_qty=record.qty - record.split_qty      
               record.remaining_uom=record.split_uom.id
    @api.multi
    @api.onchange('split_qty')
    def _splitqty(self):
        if self.split_qty:
           if self.split_qty > self.qty and not self.machine:
              raise UserError(_("Split Qty is Greater than Required Qty"))
    
    @api.multi
    def Changemachine(self):
        for record in self:
            if record.machine:
               lst=[]
               for bom in record.production_id.bom_id.bom_line_ids:
                   pcs_qty=((record.order_id.wk_required_qty - record.split_qty)/record.order_id.product.weight)
                   if bom.product_id.product_material_type.string == 'raw':
                      lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                       'qty':(pcs_qty * bom.product_qty)}))
               split_id=self.env['mrp.production.workcenter.line'].create({'production_id':record.production_id.id,
                             'workcenter_id':record.workcenter_id.id, 'sequence':record.order_id.sequence,
                             'product':record.product,'raw_materials_id':lst,
                             'order_last':True if record.order_id.order_last else False,
                              'batch_unit':record.order_id.batch_unit,'req_uom_id':record.order_id.req_uom_id.id,
                              'each_batch_qty':record.order_id.each_batch_qty, 
                              'req_product_qty':math.ceil((record.order_id.wk_required_qty - record.split_qty)/record.order_id.each_batch_qty),
                              'wk_required_qty':(record.order_id.wk_required_qty - record.split_qty),
                             'wk_required_uom':record.split_uom.id,'time_option':record.order_id.time_option,
                             'machine':record.machine.id,'capacity_type':record.capacity_type.id,
                             'machine_show':True,'date_planned':record.date_planned,
                             'shift_time':record.machine.shift_time,
                             'information_types':'default',
                             'user_ids':[(6, 0, [x.id for x in record.order_id.user_ids])],
                             'parent_id':record.order_id.id })
               split_hr=(split_id.p_hour * 60 *60)  +(split_id.p_minute*60 + split_id.p_second)
               split_time_cycle=split_hr * 0.000277778
               split_cycle=float(split_id.wk_required_qty/(split_id.capacity_per_cycle * int(split_id.time_option if split_id.time_option else 1.0 )))
               split_hour=(split_cycle *(split_time_cycle)) *(split_id.time_efficiency or 1.0) +((record.machine.time_start or 0.0) +(record.machine.time_stop or 0.0))
               split_id.hour=split_hour
               split_id.cycle=split_cycle
               record.order_id.wk_required_qty =record.split_qty
   
               if record.order_id.machine:
                  hr=(record.order_id.p_hour * 60 *60)  +(record.order_id.p_minute*60 + record.order_id.p_second)
                  time_cycle=hr * 0.000277778
                  cycle=float(record.order_id.wk_required_qty/(record.order_id.capacity_per_cycle * int(record.order_id.time_option if record.order_id.time_option else 1.0 )))
                  hour=(cycle *(time_cycle)) *(record.order_id.time_efficiency or 1.0) +((record.order_id.machine.time_start or 0.0) +(record.order_id.machine.time_stop or 0.0))
                  record.order_id.hour=hour
                  record.order_id.cycle=cycle
	          record.order_id.machine.status = 'inactive'
	          record.order_id.machine.running_workorder_id=''
		  record.order_id.machine.running_production_id=''
                  record.order_id.action_done()
                  record.order_id.signal_workflow('button_done')
               if record.order_id.raw_materials_id:
                  '''lst=[]
                  for line in record.order_id.raw_materials_id:
                      print"===============",record.order_id.wk_required_qty,line.qty,(record.order_id.wk_required_qty+ split_id.wk_required_qty)
                      print"PPPPp",line.product_id.name, line.qty
                      one_pcs=(line.qty/(record.order_id.wk_required_qty+ split_id.wk_required_qty))
                      print"jjjjjjjjjjjjjj",one_pcs, one_pcs * split_id.wk_required_qty,split_id.wk_required_qty
                      lst.append((0,0,{'product_id':line.product_id.id, 'uom_id':line.uom_id.id,
                         'qty':(one_pcs * split_id.wk_required_qty), 'receive_qty':line.remain_consumed}))
                      line.qty -=one_pcs * split_id.wk_required_qty
                      print"LLLLLLLLLLLLLLLLLL",line.qty
                  print"========lllllllll=========",lst'''
                  record.order_id.raw_materials_id.unlink()
                  rm_list=[]
                  for bom in record.production_id.bom_id.bom_line_ids:
                      rm_qty=((record.split_qty)/record.order_id.product.weight)
                      if bom.product_id.product_material_type.string == 'raw':
                         rm_list.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                         'qty':(rm_qty * bom.product_qty)}))
                  record.split_id.raw_materials_id=lst
          
               '''body='<b>Split Work Order For Change Multi Machine:</b>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> Previous Work Order No. : '+str(record.order_id.name) +'</li></ul>'
               body +='<ul><li> Next Work Order No. : '+str(split_id.name) +'</li></ul>'
               body +='<ul><li> Previous QTy : '+str(record.qty) +' '+str(record.uom.name)+'</li></ul>'
               body +='<ul><li> Split Qty : '+str(record.split_qty) +' '+str(record.split_uom.name)+'</li></ul>'
               body +='<ul><li> Split Date : '+str(date.today()) +'</li></ul>'
               body +='<ul><li> Split By : '+str(self.env.user.name) +'</li></ul>'
               record.order_id.message_post(body=body) 
               split_id.message_post(body=body)'''
               
    @api.multi
    def split_orders(self):
        for record in self:
            if record.split_line_ids:
               body='<b>Split Work Order based on Work order Required Qty:</b>'
               body +='<ul><li> Production No. : '+str(record.production_id.name) +'</li></ul>'
               body +='<ul><li> current Work Order No. : '+str(record.order_id.name) +'</li></ul>'
               body +='<ul><li> Previous Qty : '+str(record.order_id.wk_required_qty) +' '+str(record.order_id.wk_required_uom.name)+'</li></ul>'
               body +='<ul><li> Produced Qty : '+str(record.order_id.total_product_qty) +' '+str(record.order_id.total_uom_id.name)+'</li></ul>'
               body +='<ul><li> Splitted Date : '+str(date.today()) +'</li></ul>'
               body +='<ul><li> Splitted By : '+str(self.env.user.name) +'</li></ul>'
               body +="<table class='table' style='width:80%; height: 50%;font-family:arial; text-align:left;'><tr><th>Split Orders No. </th><th> qty</th></tr>"
               wk_required_qty=0.0
               raw_products={}
               all_process_id = self.env['mrp.production.workcenter.line'].search([('workcenter_id','=',record.workcenter_id.id),('production_id','=',record.order_id.production_id.id)])
               for process in all_process_id:
			wk_required_qty += process.wk_required_qty
		       	for raw in process.raw_materials_id:
				raw_products[raw.product_id.id] = raw_products[raw.product_id.id]+raw.qty if raw_products.get(raw.product_id.id) else raw.qty
	
               per= round(wk_required_qty/100,6)		# % to Total of same Process Wo qty
               per_qty = round(record.order_id.total_product_qty + record.remain_qty)/per 
               			
               for raw in record.order_id.raw_materials_id:
			r_per = round(raw_products.get(raw.product_id.id)/100,6)
			raw.qty = round(per_qty*r_per,6)
	       raw_p={}
	       
	       count= len([i.id for i in record.order_id.split_work_ids]) if record.order_id.split_work_ids else 1 
	       
               for line in record.split_line_ids:
               	   if not line.qty:
               	   	raise UserError("Please Fill qty in Split LIne")
               	   rm_list_raw=[]	
                   workorder=False
                   self_process_ids=self.env['mrp.production.workcenter.line'].search([('production_id','=',record.production_id.id),('workcenter_id','=',record.workcenter_id.id)])
                   for self_process in self_process_ids:
                   	workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',self_process.id)])
                   	if workorder:
				break
		   #workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',record.order_id.id)])
		   
		   if len(record.order_id.name.split('SP'))>1:
		        num =''
	   		parent=record.order_id.name.split('SP')[1]
		   	c=parent.count('-')
		   	for ch in parent:
				if ch=='-':
					c-=1
				else:
					num+=ch
				if c==0:
					break
			split_str = '-SP'+str(num)+('-'+str(count) if count else '')
		   else:
		   	split_str = '-SP'+str(count)
		   	
                   split_id=self.env['mrp.production.workcenter.line'].with_context({'new_split':split_str}).create({'production_id':record.production_id.id,
                             'workcenter_id':record.workcenter_id.id, 
                             'sequence':int(record.order_id.sequence), 
                             'user_ids':[(6, 0, [x.id for x in record.order_id.user_ids])],
                             'product':record.order_id.product,
                             'order_last':True if record.order_id.order_last else False,
                             'wk_required_qty':(line.qty),
                             'wk_required_uom':line.uom_id.id,
                             'parent_id':record.order_id.id,
                             'req_product_qty':math.ceil(line.qty / record.order_id.each_batch_qty) if record.order_id.each_batch_qty else 0.0,
                             'batch_unit':record.order_id.batch_unit,
                             'each_batch_qty':record.order_id.each_batch_qty,
                             'req_uom_id':record.order_id.req_uom_id.id,
                             'next_order_id':record.order_id.next_order_id.id})
                             
                   line.order_id=split_id.id   
                   count +=1  
                   raws=self.env['workorder.raw.material'].search([('next_order_id','=',record.order_id.id), ('order_id','!=',record.order_id.id)])
                 
                   if raws:
                          for raw in raws:
                              one_qty=(raw.qty/record.qty)
                              rm_list_raw.append((0,0,{'product_id':raw.product_id.id, 'uom_id':raw.uom_id.id,
	                                   'qty':(one_qty * line.qty),
                                           'production_id':record.production_id.id,
                                           'original_qty':raw.original_qty,
                                           'next_order_id':split_id.id ,
	                                   'receive_qty':(one_qty * line.received)}))
                              raw.receive_qty -=(one_qty * line.received)
                              raw.requested = 0.0
			      raw_p[raw.product_id.id] =raw_p[raw.product_id.id]+(one_qty * line.qty) if raw_p.get(raw.product_id.id) else (one_qty * line.qty)
                          workorder.raw_materials_id=rm_list_raw 
                   body +="<tr><td>%s</td><td>%s %s</td></tr>"%(str(split_id.name), str(line.qty), str(line.uom_id.name))
                   per_qty = round(line.qty/per,6)
                   if record.order_id.raw_materials_id:
                      	rm_list=[]
                      	split_id.raw_materials_id.unlink()
			# in the below Rm qty is deducted before at line no. 221 
	              	for raw in record.order_id.raw_materials_id:
	              		raw.requested_qty =0.0
                                one_qty=(raw.qty/record.qty)
	              		r_per = round(raw_products.get(raw.product_id.id)/100,6)
	                 	new_qty= round(per_qty*r_per,6)
	                 	rec_qty = 0.0

	                 	if raw.receive_qty > raw.qty:
					if new_qty < (raw.receive_qty - raw.qty):
						rec_qty = new_qty
						raw.receive_qty -= new_qty
					else:
						rec_qty = raw.receive_qty - raw.qty
						raw.receive_qty = raw.qty
							
	      	   		rm_list.append((0,0,{'product_id':raw.product_id.id, 'uom_id':raw.uom_id.id,
	                         		     'qty':new_qty,'production_id':record.production_id.id,
	                         		     'original_qty':raw.original_qty,'receive_qty':rec_qty,
	                         		     'next_order_id':split_id.id}))
	              	split_id.raw_materials_id=rm_list
	           cancel_picking_id=[]
                   for picking in record.order_id.rm_picking_ids:
                   	if picking.state not in ('done','cancel'):
                   		picking.action_cancel()
           		if picking.next_prev_picking_id:
           			if picking.next_prev_picking_id.state not in ('done','cancel'):
           				picking.next_prev_picking_id.action_cancel()
           		
                   if record.order_id.machine:
			hr=(record.order_id.p_hour * 60 *60)  +(record.order_id.p_minute*60 + record.order_id.p_second)
			time_cycle=hr * 0.000277778
             		cycle = float(record.remain_qty/(record.order_id.capacity_per_cycle * int(record.order_id.time_option if record.order_id.time_option else 1.0 )))
                     	hour = (cycle *(time_cycle)) *(record.order_id.time_efficiency or 1.0) +((record.order_id.machine.time_start or 0.0) +(record.order_id.machine.time_stop or 0.0))
                     	record.order_id.hour=hour
                     	record.order_id.cycle=cycle

                   if record.order_id.product_sepcification_ids:
                      spec_list=[]
                      for spec in record.order_id.product_sepcification_ids:
                           spec_list.append((0,0,{'attribute':spec.attribute.id,
                                 'value':spec.value,'unit':spec.unit.id}))
                      split_id.product_sepcification_ids=spec_list
	       raws=self.env['workorder.raw.material'].search([('next_order_id','=',record.order_id.id), ('order_id','!=',record.order_id.id)])
               for raw in raws:
			raw.qty -= raw_p[raw.product_id.id]
			raw.requested_qty = 0.0
			
               body +="</table>"
               record.order_id.message_post(body=body)
               record.order_id.wk_required_qty = (record.order_id.total_product_qty + record.remain_qty) # set remaining qty to existing WO
               if record.order_id.each_batch_qty:
                      if record.order_id.batch_ids:
                         total=req_qty=0.0
                         for batch in record.order_id.batch_ids:
                             if batch.product_qty != 0:
                                req_qty +=batch.req_product_qty
                                total +=1
                             else:
                                 batch.unlink() 
                         record.order_id.req_product_qty=math.ceil((record.order_id.wk_required_qty -req_qty)/record.order_id.each_batch_qty)
                         rec=record.order_id.issue_batchnumber() if math.ceil((record.order_id.wk_required_qty -req_qty)/record.order_id.each_batch_qty) >0 else None
                         record.order_id.req_product_qty +=total
                   
class MrpWorkSplit(models.TransientModel):
    _name = 'mrp.workorder.split.line'
    
    @api.model
    def get_qty(self):
        return self._context.get('wk_qty')
 
    @api.model
    def get_req_qty(self):
        return self._context.get('req_qty')

    @api.model
    def get_rec_qty(self):
        if self._context.get('received_qty') < self._context.get('wk_qty'):
            return 0.0
        else:
            return self._context.get('rec_qty')
    @api.model
    def get_uom(self):
        return self._context.get('uom')
        
    qty=fields.Float('Qty', default=get_qty, required=True)
    requested=fields.Float('Requested Qty',default=get_req_qty,)
    received=fields.Float('Received Qty',default=get_rec_qty,)
    uom_id=fields.Many2one('product.uom', string="Unit", default=get_uom)
    split_id=fields.Many2one('mrp.workorder.split')
    order_id=fields.Many2one('mrp.production.workcenter.line', string='Order No.')
    
    
