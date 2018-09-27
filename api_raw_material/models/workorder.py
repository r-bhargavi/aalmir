# -*- coding: utf-8 -*-
# copyright reserved

from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
from datetime import datetime,date,timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
import time
import math
from urlparse import urljoin
from openerp import tools, SUPERUSER_ID
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class MrpWorkcenterPructionline(models.Model):
    _inherit = 'mrp.production.workcenter.line'

    rm_request_id=fields.Many2one('mrp.raw.material.request')
    raw_materials_id=fields.One2many('workorder.raw.material', 'order_id','Raw Material Details')
    #rm_status = fields.Selection([('send','Send Request'),('planed','Picking Planned'),('draft','Draft'),('no_rm','No Raw Material'),('done','Done')],default='draft', string='Rm Request Type') # for hide button of schedule rm 
    workorder_shifts =fields.One2many('mrp.workorder.rm.shifts','workorder_id','Working Shifts') # get shifts details
    wo_shift_raw_line =fields.Many2many('mrp.workorder.rm.shifts','work_order_raw_shift_rel',
				'workorder_id','shift_id','Working Shifts') # get shifts details of Raw Process
    wo_shift_line =fields.Many2many('mrp.workorder.rm.shifts','work_order_shift_rel',
				'workorder_id','shift_id','Working Shifts') # get shifts details of Non Raw Process
    raw_materials_time=fields.Float('Raw Material Time',help="Raw meterial available time in hours")
    #raw_materials_request_id=fields.One2many('mrp.workorder.raw.material.request','workorder_id','Raw Material Request')
    rm_picking_ids = fields.Many2many('stock.picking','wo_raw_material_picking_rel','wo_id','picking_id',
        				'Delivery No.',help="Receive Raw Material Delivery no.")
        				
# method to calculate shift wize raw material in workorders >>START
    @api.multi
    def write(self, vals, update=True):
    	if self._context.get('mo_cal'):
		if vals.get('capacity_per_cycle') and vals.get('res.shift_time'):
		       hr=(vals.get('p_hour') * 60 *60)  +(vals.get('p_minute')*60 + vals.get('p_second'))
		       time_hr=(hr * 0.000277778)
		       in_one_hr=((vals.get('capacity_per_cycle') * float(vals.get('time_option')))/time_hr)
		       if not vals.get('shift_base_qty'):
		       		vals.update({'shift_base_qty':math.ceil(in_one_hr * res.shift_time)})
		       if not vals.get('shift_base_qty'):
		       		vals.update({'shift_required':res.hour / res.shift_time})
        result = super(MrpWorkcenterPructionline, self).write(vals, update=update)
        
        for res in self:
        	#workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('id','=',res.id)])
        	
	#Code to Update Shifts in Raw Material
		workorder=False
		self_process_ids=self.search([('production_id','=',res.production_id.id),('workcenter_id','=',res.workcenter_id.id)])
		for self_process in self_process_ids:
			workorder=self.search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',self_process.id)])
			if workorder:
				break
		change_flag=False
		if vals.get('capacity_per_cycle') or vals.get('shift_time') or vals.get('time_option'):
			change_flag=True
		if vals.get('p_hour') or vals.get('p_minute') or vals.get('p_second'):
			change_flag=True
				
		## CODE to create SHIFTS of Current Workorder
		if res.process_type!='raw' and res.shift_required and res.state=='draft' and change_flag:
			if res.raw_materials_id or workorder.raw_materials_id:
				import math
				shift_base_qty =raw_shift_base_qty =0
				nseconds=raw_shift_time=raw_seconds=0
				shift_per=False		# % of all rm according to MO
				total_mo_qty=0.0			# total of all wo qty with same process of MO
				total_process=self.env['mrp.production.workcenter.line'].search([('production_id','=',res.production_id.id),('workcenter_id','=',res.workcenter_id.id)])
				for line in total_process:
					total_mo_qty += line.wk_required_qty
					
				# Calculate shift Rm %	to main qty
				if not shift_per:	
					total_per = round(total_mo_qty/100,4)
					print "@@@@,....",total_per,res.shift_base_qty , res.wk_required_qty
					if res.shift_base_qty > res.wk_required_qty:
						shift_per = 100				
					else:
						shift_per  = round(res.shift_base_qty/total_per,4)
					shift_base_qty = round(total_mo_qty/100,4) * shift_per  # get shift qty according to total all process qty
					if workorder:
						raw_shift_base_qty = round(workorder.wk_required_qty/100,4) * shift_per  # get shift qty according to total all process qty
					
				if workorder and workorder.machine:
					raw_time_option = float(workorder.time_option) if workorder.time_option else 1
					raw_cycle=raw_time_option * float(workorder.capacity_per_cycle)
					w_seconds=(workorder.p_hour*60*60)+(workorder.p_minute*60+workorder.p_second)
					raw_shift_time = (w_seconds*raw_shift_base_qty)/raw_cycle
					raw_seconds = (w_seconds*workorder.wk_required_qty) / raw_cycle
				
				time_option = float(res.time_option) if res.time_option else 1
				cycle=time_option * float(res.capacity_per_cycle)
				w_seconds=(res.p_hour*60*60)+(res.p_minute*60+res.p_second)
				shift_time = (w_seconds*shift_base_qty)/cycle
				nseconds = (w_seconds*res.wk_required_qty) / cycle	
				
				shift_required=res.shift_required
				total_qty = res.wk_required_qty
				
				if workorder and not workorder.machine:
					raw_shift_time=shift_time
					raw_seconds=nseconds
					raw_shift_base_qty = shift_base_qty
					
				if workorder:		# update in previous Raw material Process
					workorder_vals={'machine_show':True,'wk_planned_status':res.wk_planned_status}
					workorder.with_context({'update_film':True}).write(workorder_vals)
				
				# Get Raw Material details of current process all WO(qty ,received + requsted)
				raw_products={}
				received_product_qty = {}
				all_process=self.search([('production_id','=',res.production_id.id),('workcenter_id','=',res.workcenter_id.id)])
				for all_proce in all_process:
					for proc_raw in all_proce.raw_materials_id:
						raw_products[proc_raw.product_id.id] = raw_products[proc_raw.product_id.id]+ proc_raw.qty if raw_products.get(proc_raw.product_id.id) else proc_raw.qty
					
				for raw in res.raw_materials_id:
					#raw_products[raw.product_id.id] = raw_products[raw.product_id.id]+ raw.qty if raw_products.get(raw.product_id.id) else raw.qty
					
					# to get count of receive or in process of receving raw Materials
					rm_qty = raw.requested_qty + raw.receive_qty
					if received_product_qty.get(raw.product_id.id):
						received_product_qty[raw.product_id.id] = received_product_qty[raw.product_id.id]+rm_qty
					else:
						 received_product_qty.update({raw.product_id.id:rm_qty}) 
				# Get Raw Material details of Previous process if it is Raw materila mixing Process (qty ,received + requsted)
				for raw in workorder.raw_materials_id:
					
					raw_products[raw.product_id.id] = raw_products[raw.product_id.id]+ raw.qty if raw_products.get(raw.product_id.id) else raw.qty
					if raw.next_order_id.id == res.id:	
						# to get count of receive or in process of receving raw Materials
						rm_qty = raw.requested_qty + raw.receive_qty
						if received_product_qty.get(raw.product_id.id):
							received_product_qty[raw.product_id.id] = received_product_qty[raw.product_id.id]+rm_qty
						else:
							 received_product_qty.update({raw.product_id.id:rm_qty}) 
				request_id = self.env['mrp.raw.material.request'].search([('production_id','=',res.production_id.id)],limit=1)   # Check if Raw MAterial request for shifts is exists or not
				count=1
				
				exist_order=[]
				# start and end Time of Raw Material Mixing Process (-6 Hours)
				start_time = datetime.strptime(res.date_planned,'%Y-%m-%d %H:%M:%S')
				end_time = start_time + timedelta(seconds=shift_time)
				raw_end_time = datetime.strptime(res.date_planned,'%Y-%m-%d %H:%M:%S')-timedelta(hours=6)
				raw_start_time = raw_end_time-timedelta(seconds=raw_shift_time)
				receive_qty = 0
				
				# calculate shifts
				next_shift_id=False
				for n in range(int(math.ceil(res.shift_required))):
					shift_name='SHIFT-'+str(count)
					shift=self.env['mrp.workorder.rm.shifts'].search([('name','=',shift_name),
										('workorder_id','=',res.id),
										('used_work_id','=',res.id)])
					
					shift1=self.env['mrp.workorder.rm.shifts'].search([('name','=',shift_name),
										('workorder_id','=',res.id),
										('used_work_id','=',res.id),
									('status','not in',('draft','hold'))])
					# IF to check existing shift is in process
					if shift1:	# code for existing shifts
				    		if shift_required <1:
							total_per = round(total_mo_qty/100,4)
							shift_per  = round(total_qty/total_per,6)
							shift_time = nseconds
							shift_base_qty =  round(total_mo_qty/100,4) * shift_per
							end_time = start_time + timedelta(seconds=int(shift_time))
							if workorder :
								raw_shift_time=raw_seconds
								raw_end_time = raw_start_time + timedelta(seconds=int(raw_shift_time))
				    		nvals={'qty':round(res.qty/100,4)*shift_per,
					    	       'wo_qty': shift_base_qty,'hours':shift_time/3600,
						       'start_time':start_time,'end_time':end_time,}
						   	# Update Shift with new values
						
						if workorder:
							   nvals.update({'raw_qty':round(workorder.qty/100,4)*shift_per,
							    	  'raw_hours':raw_shift_time/3600,
								  'raw_start_time':raw_start_time,
								  'raw_end_time':raw_end_time,})
						print "vvvvvvvvvvvvvvvvWWWWW.....m",nvals		  
				    		if shift_base_qty <= shift1.wo_qty: # check if current shift data is greater than new data
					    	    #receive_qty += shift1.wo_qty - shift_base_qty
					    	    check_state=[]
					    	    for sub_p in shift1.sub_product:
					    		for product in res.raw_materials_id:
							    if sub_p.product.id == product.product_id.id:
								rem_qty = 0
								req_qty = avl_qty = new_qty = round(raw_products.get(product.product_id.id)/100,4)*shift_per
								ext_qty = received_product_qty[sub_p.product.id] if received_product_qty.get(sub_p.product.id) else 0.0
								print "1111111111$$",new_qty,ext_qty
								if ext_qty > new_qty: # if inprocess qty 
				    					rem_qty = ext_qty - new_qty
				    					req_qty = 0.0
				    					check_state.append(False)
								else:
				    					rem_qty = 0
				    					req_qty = new_qty - ext_qty
				    					avl_qty = ext_qty
				    					check_state.append(True)
								print "FFFF........."		
								sub_p.write({'qty':new_qty,
									     'required_qty':req_qty,
									     'available_qty':avl_qty})
								print "PPPPPP...",new_qty,req_qty,avl_qty
					     			# update received qty in dic.
								received_product_qty[sub_p.product.id] = rem_qty 
								
					    		# if previous Wo is raw material mixing	
					    		for product in workorder.raw_materials_id:
					    		    if sub_p.product.id == product.product_id.id and product.next_order_id.id == res.id:
								rem_qty = 0
								req_qty = avl_qty = new_qty = round(raw_products.get(product.product_id.id)/100,4)*shift_per
								ext_qty = received_product_qty[sub_p.product.id] if received_product_qty.get(sub_p.product.id) else 0.0
								print "1111111112222$$...",new_qty,ext_qty
								if ext_qty >= new_qty: # if new qty is less than old qty 
				    					rem_qty = ext_qty - new_qty
				    					req_qty = 0.0
				    					check_state.append(False)
				    				else:
				    					rem_qty = 0
				    					req_qty = new_qty - ext_qty
				    					avl_qty = ext_qty
				    					check_state.append(True)
				    						
								sub_p.write({'qty':new_qty,
									     'required_qty':req_qty,
									     'available_qty':avl_qty})
					     			
					     			# update received qty in dic.
								received_product_qty[sub_p.product.id] = rem_qty 
					    		print "sssssssssssssssssssss11..",check_state
					    		if all([i for i in check_state]):
					    			nvals.update({'status':'draft'})	
					    		shift1.write(nvals)
						
				    		else:		# if current SHIFT data in less than new data
					    	    check_state=[]
					    	    for sub_p in shift1.sub_product:
						        for product in res.raw_materials_id:
							    if sub_p.product.id == product.product_id.id:
								rem_qty = 0
								req_qty = avl_qty = new_qty = round(raw_products.get(product.product_id.id)/100,4)*shift_per
								ext_qty = received_product_qty[sub_p.product.id] if received_product_qty.get(sub_p.product.id) else 0.0
								if ext_qty >= new_qty: # if new qty is less than old qty
				    					rem_qty = ext_qty - new_qty
				    					req_qty = 0.0
				    					check_state.append(False)
				    				else:
				    					rem_qty = 0
				    					req_qty = new_qty - ext_qty
				    					avl_qty = ext_qty
				    					check_state.append(True)
				    						
								sub_p.write({'qty':new_qty,
									     'required_qty':req_qty,
									     'available_qty':avl_qty})
						     	
								received_product_qty[sub_p.product.id] = rem_qty
								
						        for product in workorder.raw_materials_id:
							    if sub_p.product.id == product.product_id.id and product.next_order_id.id == res.id:
								rem_qty = 0
								req_qty = avl_qty = new_qty = round(raw_products.get(product.product_id.id)/100,4)*shift_per
								ext_qty = received_product_qty[sub_p.product.id] if received_product_qty.get(sub_p.product.id) else 0.0
								if ext_qty >= new_qty: # if new qty is less than old qty
				    					rem_qty = ext_qty - new_qty
				    					req_qty = 0.0
				    					check_state.append(False)
				    				else:
				    					rem_qty = 0
				    					req_qty = new_qty - ext_qty
				    					avl_qty = ext_qty
				    					check_state.append(True)
				    						
								sub_p.write({'qty':new_qty,
									     'required_qty':req_qty,
									     'available_qty':avl_qty})
						     	
								received_product_qty[sub_p.product.id] = rem_qty 
					    	    print "sssssssssssssssssssss22.....",check_state
					    	    if all([i for i in check_state]):
							nvals.update({'status':'draft'})			
							
					    	    shift1.write(nvals)
				    		exist_order.append(shift1.id)	
				    		total_qty -= shift_base_qty
				    		nseconds -= shift_time
				    		raw_seconds -= raw_shift_time
				    		
				    		if next_shift_id:
				    			next_shift_id.next_shift_id= shift1.id
				    		next_shift_id = shift1
					else:
					# create or update shifts which are not processed by logistics
						if shift_required >1:
							total_qty -= res.shift_base_qty
							nseconds -= shift_time
							raw_seconds -= raw_shift_time
						else:
							total_per = round(total_mo_qty/100,4)
							shift_per  = round(total_qty/total_per,6)
							shift_time = nseconds
							shift_base_qty =  round(total_mo_qty/100,4) * shift_per
							end_time = start_time + timedelta(seconds=int(shift_time))
							if workorder :
								raw_shift_time=raw_seconds
								raw_end_time = raw_start_time + timedelta(seconds=int(raw_shift_time))
							
						
						print "TRRRRRRRRRRRr",total_qty,shift_base_qty
						
						shift_vals={'uom':res.uom.id,'stock_qty':round(res.qty/100,4)*shift_per,
							    'qty':round(res.qty/100,4)*shift_per,
							    'wo_qty':shift_base_qty,
							    'wo_uom':res.wk_required_uom.id,'request_id':request_id.id,
							    'hours':shift_time/3600,
							    'date':raw_start_time-timedelta(hours=int(2)),
							    'start_time':start_time,
							    'end_time':end_time,'used_work_id':res.id}
					        if workorder:
					        	shift_vals.update({'raw_uom':workorder.uom.id,
						    		'raw_qty':round(workorder.qty/100,4)*shift_per,

						    		'raw_hours':raw_shift_time/3600,
							    	'raw_start_time':raw_start_time,
				        			 'raw_end_time':raw_end_time})
						 
						check_state=[]
						new_product=[]  
						for raw_p in res.raw_materials_id:
							raw_vals={}
							rem_qty=0.0
							req_qty=avl_qty=new_qty = round(raw_products.get(raw_p.product_id.id)/100,4)*shift_per
							
							ext_qty = received_product_qty[raw_p.product_id.id] if received_product_qty.get(raw_p.product_id.id) else 0.0
							
							if ext_qty >= new_qty: # if inprocess qty 
			    					rem_qty = ext_qty - new_qty
			    					req_qty = 0.0
			    					check_state.append(True)
			    				else:
			    					print "1111>..."
			    					rem_qty = 0
			    					req_qty = new_qty - ext_qty
			    					avl_qty = ext_qty
			    					check_state.append(False)
							
							raw_vals.update({'product':raw_p.product_id.id,
									 'qty':new_qty,'uom':raw_p.uom_id.id,
									 'required_qty':req_qty,
									 'available_qty':avl_qty})
							new_product.append((0,0,raw_vals))
							received_product_qty[raw_p.product_id.id] = rem_qty
						check_state=[]
						new_product_raw=[]	
						for raw_p in workorder.raw_materials_id:
						   	if raw_p.next_order_id.id == res.id:
								raw_vals={}
								rem_qty=0.0
								req_qty=avl_qty=new_qty = round(raw_products.get(raw_p.product_id.id)/100,4)*shift_per
								print "B%%%%%%%%//..............",received_product_qty,raw_p.product_id.id
								ext_qty = received_product_qty[raw_p.product_id.id] if received_product_qty.get(raw_p.product_id.id) else 0.0
							
								if ext_qty >= new_qty: # if inprocess qty 
				    					rem_qty = ext_qty - new_qty
				    					req_qty = 0.0
				    					check_state.append(True)
				    				else:
				    					print "1111>..."
				    					rem_qty = 0
				    					req_qty = new_qty - ext_qty
				    					avl_qty = ext_qty
				    					check_state.append(False)
								print "VVVVVv%%.....",ext_qty,req_qty,new_qty
								raw_vals.update({'product':raw_p.product_id.id,
										'qty':new_qty,'uom':raw_p.uom_id.id,
										'required_qty':req_qty,
										'available_qty':avl_qty})
								new_product_raw.append((0,0,raw_vals))
								received_product_qty[raw_p.product_id.id] = rem_qty
						print "VRRR#$$#$#$#$>.>.............!!",check_state
						if check_state and all([i for i in check_state]):
							shift_vals.update({'status':'received'})
						
						if new_product:		
							shift_vals.update({'wo_shift_product':new_product})
						if workorder and new_product_raw:
							shift_vals.update({'wo_raw_shift_product':new_product_raw})
						
						if shift:
							print "WWWWWWWWWWWWWW",shift_vals
							shift.sub_product.unlink()
							shift.wo_shift_product.unlink()
							shift.wo_raw_shift_product.unlink()
							shift.write(shift_vals)
							for line1 in shift.wo_shift_product:
								line1.shift_id = shift.id
							for line2 in shift.wo_raw_shift_product:
								line2.shift_id = shift.id
							exist_order.append(shift.id)
							if next_shift_id:
				    				next_shift_id.next_shift_id= shift.id
				    			next_shift_id = shift
						else:
							if not shift_vals.get('status'):
								shift_vals.update({'status':'draft'})
							shift_vals.update({'product':res.product.id,'name':shift_name,
								'workorder_id':res.id})
							new_id=self.env['mrp.workorder.rm.shifts'].create(shift_vals)
							for line1 in new_id.wo_shift_product:
								line1.shift_id = new_id.id
							for line1 in new_id.wo_raw_shift_product:
								line1.shift_id = new_id.id 
							if workorder:
								workorder.wo_shift_raw_line=[(4,new_id.id)]
								
							res.wo_shift_line = [(4,new_id.id)]	
							exist_order.append(new_id.id)
							if next_shift_id:
				    				next_shift_id.next_shift_id= new_id.id
							next_shift_id=new_id
							print "CCCCCCCCCC",shift_vals
							
					shift_required -= 1
					count +=1
					start_time = end_time
					end_time = start_time + timedelta(seconds=int(shift_time))
					raw_start_time = raw_end_time
					raw_end_time = raw_start_time + timedelta(seconds=int(raw_shift_time))
					print "..VVVTT&&&..",nseconds,start_time,end_time,shift_time,raw_shift_time
				
				exist_shifts=self.env['mrp.workorder.rm.shifts'].search([
										('workorder_id','=',res.id),
										('id','not in',exist_order),
										('used_work_id','=',res.id)])
				exist_shifts.unlink()
		if res.process_type=='raw' and change_flag:
			nseconds=0
			shift_per=False		# % of all rm according to MO
			total_mo_qty=res.wk_required_qty	# total of all wo qty with same process of MO
			
			if res.machine:
				shift_base_qty = round(res.wk_required_qty/100,4) * shift_per
				time_option = float(res.time_option) if res.time_option else 1
				cycle=time_option * float(res.capacity_per_cycle)
				w_seconds=(res.p_hour*60*60)+(res.p_minute*60+res.p_second)
				
				for pro in res.wo_shift_raw_line:
					shift_time = (w_seconds*pro.raw_qty)/cycle
					end_time = datetime.strptime(pro.start_time,'%Y-%m-%d %H:%M:%S') - timedelta(hours=6) 
					pro.raw_end_time = end_time
					pro.raw_start_time = end_time - timedelta(seconds=shift_time)
					pro.raw_hours=(shift_time/3600)
					
					
        return result

    @api.multi
    def shift_rm_wizard(self):
    	form_view = self.env.ref('api_raw_material.raw_material_shift_wizard', False)
    	context=self._context.copy()
	raw_id=[]
	for rec in self:
		for line in rec.raw_materials_id:
			 raw_id.append((0,0,{'product_id':line.product_id.id,'uom':line.uom_id.id,'qty':line.qty,
			 		    'request_qty':line.requested_qty,'received_qty':line.receive_qty}))
	context.update({'default_raw_id':raw_id,'default_order_id':self.id})
	if form_view:
		return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'workorder.raw.material.shift',
		    'views': [(form_view.id, 'form')],
		    'view_id': form_view.id,
		    'target': 'new',
		    'context':context
		}
    	

class WorkOrderRawMaterial(models.Model):
   _name='workorder.raw.material'
   
   order_id=fields.Many2one('mrp.production.workcenter.line', 'Work Order No.')
   production_id=fields.Many2one('mrp.production', 'Production No.')
   rm_request_id=fields.Many2one('mrp.raw.material.request')
   product_id=fields.Many2one('product.product', string='Raw Material')
   qty=fields.Float('Required Qty')
   original_qty=fields.Float('Quantity')
   uom_id=fields.Many2one('product.uom', string="Unit")
   requested_qty=fields.Float('Requested Qty',help='Raw Material requsted Quantity Proceed by Logistics')
   receive_qty=fields.Float('Received Qty',help='Raw Material received Quantity') 
   consumed_qty=fields.Float('Consumed Qty', compute='raw_comsumed')
   remain_consumed=fields.Float('Remaining to Consumed Qty', compute='_getrawqty')
   remain_received=fields.Float('Remaining to Received Qty', compute='_getrawqty')
   report_qty=fields.Float('Job Card Qty')
   next_order_id=fields.Many2one('mrp.production.workcenter.line', 'WorkOrder No.')

   @api.multi
   @api.depends('consumed_qty', 'receive_qty','requested_qty')
   def _getrawqty(self):
       for record in self:
           if record.receive_qty and record.requested_qty:
              record.remain_received=round(record.requested_qty - record.receive_qty, 2)
           else:
              record.remain_received=0.0
           if record.consumed_qty and record.receive_qty:
              
              record.remain_consumed=round(record.receive_qty - record.consumed_qty, 2)
           else:
              record.remain_consume=0.0
   @api.multi
   @api.depends('order_id.total_product_qty', 'order_id.total_wastage_qty', 'order_id')
   def raw_comsumed(self):
       for record in self:
           if record.order_id.raw_materials_id :
              wastage_qty=total=0.0
              if record.order_id.total_uom_id.id !=record.order_id.wastage_uom_id.id:
		 if record.order_id.total_uom_id.name =='Pcs':
		      wastage_qty=(record.order_id.total_wastage_qty/record.order_id.product.weight) if record.order_id.total_wastage_qty else 0.0
		 if record.order_id.total_uom_id.name =='m':
                             qty_m=(record.order_id.wk_required_qty/record.order_id.qty)
                             wastage_qty=qty_m * record.order_id.total_wastage_qty
              else:
		  wastage_qty= record.order_id.total_wastage_qty
              for raw in record.order_id.raw_materials_id:
                  one_qty=raw.qty/record.order_id.wk_required_qty if record.order_id.wk_required_qty else 0
                  total=one_qty * (record.order_id.total_product_qty + wastage_qty)
                  #print"+=================TTTTTttt",total,one_qty, record.order_id.total_product_qty ,wastage_qty
                  raw.consumed_qty=total
           else:
                record.consumed_qty=0.0
   
class MrpWordkorderShifts(models.Model):

	_name="mrp.workorder.rm.shifts"
	
	name = fields.Char('Name')
	request_id=fields.Many2one('mrp.raw.material.request',string='Raw Material')
	workorder_id = fields.Many2one('mrp.production.workcenter.line','Workorder No.')
	production_id = fields.Many2one('mrp.production','Manufacturing No.',related='workorder_id.production_id')
	product = fields.Many2one('product.product', string='Product Name')
	sub_product = fields.One2many('mrp.workorder.rm.shifts.line','shift_id',string='Product Details')
	wo_shift_product = fields.Many2many('mrp.workorder.rm.shifts.line','wo_shift_product_rel',
					'shift_id','pro_id',string='Product Details')
	wo_raw_shift_product = fields.Many2many('mrp.workorder.rm.shifts.line','wo_shift_raw_product_rel',
					'shift_id','pro_id',string='Product Details')
	#receive_sub_product = fields.One2many('mrp.workorder.rm.shifts.line','receive_shift_id',string='Receive Product Details')
	
	# fields for raw material process shifts
	raw_qty = fields.Float('Qty',help="Manufacture Order Quantity per Shift")
    	raw_uom = fields.Many2one('product.uom', string='Unit')
    	raw_hours = fields.Float('Hours')
    	
    	# fields for non raw material process shifts
    	qty = fields.Float('Qty',help="Manufacture Order Quantity per Shift")
    	uom = fields.Many2one('product.uom', string='Unit')
    	stock_qty = fields.Float('Qty',help="Manufacture Order Quantity per Shift for Inventory to send Raw Material")
    	wo_qty = fields.Float('Workorder qty',help="Workorder Quantity per Shift")
    	wo_uom = fields.Many2one('product.uom', string='Unit')
    	date = fields.Datetime('Schedule Date')		# date for logistics
    	
	hours = fields.Float('Hours')
	start_time = fields.Datetime('Start Time')
	end_time = fields.Datetime('End Time')
	raw_start_time = fields.Datetime('Start Time')
	raw_end_time = fields.Datetime('End Time')
	
	status=fields.Selection([('draft','Draft'),('request','Raw Material Request'),
				 ('picking','Delivery In Progress'),('hold','Hold'),('delivered','Delivered'),
				 ('received','Received'),('start','Start'),
				 ('end','End'),('cancel','Cancel')])
	date_history = fields.One2many('mrp.workorder.rm.shifts.date.history','shift_id',string='Re-schedule History')
	used_work_id = fields.Many2one('mrp.production.workcenter.line','Used in WO',help='Raw Material Shift USed for workorder')
	state = fields.Selection([('draft','Requested'),('approve','Approved'),('partialy','Partialy Send'),
   			   ('send','Send'),('reject','Rejeted'),('cancel','Cancelled')],related='request_id.state')
   	received_qty = fields.Float('Received RM',help='Raw Material is received in previous SHift,This fields shows only when you changes in number of shifts more than one')
   	rec_qty_uom = fields.Many2one('product.uom', string='Unit')
   	
   	wo_state = fields.Selection([('draft','Draft'),('pause','Pause'),('hold','On Hold'),('ready','Ready'),
    				('startworking', 'In Progress'),('done','Finished'),('cancel','Cancelled'),],
    				'Status', readonly=True, copy=False,related='workorder_id.state')
        picking_ids = fields.Many2many('stock.picking','raw_material_send_picking_rel','rm_id','picking_id',
        				'Delivery No.',help="Send Raw Material To Manufacturing Department")
        rec_picking_id = fields.Many2many('stock.picking','raw_material_receive_picking_rel','rm_id','picking_id',
        				'Delivery No.',help="Receive Raw Material Delivery no.")
	next_shift_id = fields.Many2one('mrp.workorder.rm.shifts','Next Shift',help='Next Shift id')
        
        shift_wo_raw_line =fields.Many2many('mrp.production.workcenter.line','work_order_raw_shift_rel',
				'shift_id','workorder_id','Working Shifts') # get shifts details of Raw Process
    	shift_wo_line =fields.Many2many('mrp.production.workcenter.line','work_order_shift_rel',
				'shift_id','workorder_id','Working Shifts') # get shifts details of Non Raw Process
	request_bool=fields.Boolean('filter in shifts in rm reqiest')
				
	@api.multi
	def create_picking(self):
		for record in self:
		   #if  record.work_order_ids:
		   	record.status='picking'
			if record.production_id.product_id.categ_id.cat_type == 'film':
		       		location_1='send_film_rm_picking'
		       		location_2='receive_film_rm_picking'
			elif record.production_id.product_id.categ_id.cat_type == 'injection':
				location_1='send_injection_rm_picking'
		       		location_2='receive_injection_rm_picking'
			else:
		       	  	raise UserError("Product Internal Type is not proper")
		       	  
			data_obj = self.env['ir.model.data']
			raw_picking_location1 = data_obj.get_object_reference('api_raw_material', location_1)[1]
			picking_type1=self.env['stock.picking.type'].search([('id','=',raw_picking_location1)],limit=1)

			body='<b>Created Transfered Orders for Scheduled Work Orders  :  </b>'
			body +='<ul><li> Manufanufacturing No. : '+str(record.production_id.name) +'</li></ul>'
			body +='<ul><li> Product Name : '+str(record.product.name) +'</li></ul>'
			body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
			body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
			body +="<table class='table' style='width:50%; height: 50%;font-family:arial; text-align:left;'><tr><th>Transered Order Name </th><th> Required Date</th></tr>"                  
			
			# Create procurement group>>
			procurement_id=self.env['procurement.group'].create({'name':record.production_id.name,
							      'move_type':'direct'})
			lst=[]
			picking=picking1=False
			for line in record.sub_product:
				if line.qty < (line.stock_qty+line.available_qty):
					raise UserError("requested Raw material quantity is not proper")
				move_ids = self.env['stock.move'].create({ 'date':record.date,
						  'product_id':line.product.id,'product_uom_qty':line.stock_qty,
						  'product_uom':line.uom.id, 'picking_type_id':picking_type1.id,  
						  'location_dest_id':picking_type1.default_location_dest_id.id,
						  'location_id':record.request_id.source_location.id, 
						  'name':record.request_id.name,'group_id':procurement_id.id})
				move_ids.with_context({'rm_route':True,'product_id':record.request_id.product_id.id}).action_confirm()
				picking=move_ids.picking_id
			if picking:
				picking.material_request_id=record.request_id.id
				picking.origin=record.request_id.name
				picking.ntransfer_type ='rm_virtual'
				for move in picking.move_lines:
					if move.move_dest_id and move.move_dest_id.picking_id:
						picking1 = move.move_dest_id.picking_id
						break 
			if picking1:
				picking1.material_request_id=record.request_id.id
				picking1.production_id=record.request_id.production_id.id
				picking1.origin=record.request_id.name
				picking1.ntransfer_type ='rm_production'
				picking1.next_prev_picking_id=[(4,picking.id)]	
			else:
				raise UserError("Routes are not set for Raw Material products, Please go to setting and set Injection or Film")		
			for rm in record.sub_product:
			    rm.available_qty += rm.stock_qty
		   	    if record.shift_wo_line:
				for wo_rm in record.shift_wo_line.raw_materials_id:
					if wo_rm.product_id.id==rm.product.id:
						wo_rm.requested_qty += rm.stock_qty
						
			for rm in record.sub_product:
			    if record.shift_wo_line:
				for wo_rm in record.shift_wo_raw_line.raw_materials_id:
					if wo_rm.product_id.id==rm.product.id:
						if wo_rm.next_order_id.id == record.shift_wo_line.id:
							wo_rm.requested_qty += rm.stock_qty
			
			record.request_id.picking_ids = [(4,picking.id)]		# in Send part of SHIFT
			record.picking_ids=[(4,picking.id)]				# in RM
			record.rec_picking_id=[(4,picking1.id)]				# in receive part of SHIFT
			
			if record.shift_wo_raw_line:		# add picking in raw materil process WO
				record.shift_wo_raw_line.rm_picking_ids = [(4,picking1.id)]
			if record.shift_wo_line:		# add picking in non raw materil process WO
				record.shift_wo_line.rm_picking_ids = [(4,picking1.id)]
			record.workorder_id.production_id.delivery_ids= [(4,picking1.id)]		# MO
			body +="<tr><td>%s</td><td>%s</td></tr>"%(str(picking.name), str(picking.request_sch_date_mo)) 
			body +="</table>"
			record.request_id.message_post(body=body)
			record.production_id.message_post(body=body)
		return True
		
	@api.multi
	def allow_picking(self):
		for res in self:
			if res.request_id.state in ('reject','cancel'):
				raise UserError("Raw Material Request For Manufacturing Order is Canceld By Logistics.")
				
			flag=False
			for rec in res.sub_product:  # Check if requset qty is ZERO but button is visible 
				if not rec.required_qty:
					res.status='received'
					flag=True
			if flag:			# if request qty is zero the break the loop
				break
				
			shift_id=self.search([('next_shift_id','=',res.id)])
			if shift_id.status =='draft':
				raise UserError("First send the request for {}".format(shift_id.name))
			rec_shift_id=self.search([('status','=','request'),('workorder_id','=',res.workorder_id.id)])

			if len(rec_shift_id)>=2:
				raise UserError("You can not send request for more than two shifts at same time")
				
			location=False
			if res.production_id.product_id.categ_id.cat_type == 'film':
		       		location='receive_film_rm_picking'
			elif res.production_id.product_id.categ_id.cat_type == 'injection':
		       		location='receive_injection_rm_picking'
			else:
		       	  	raise UserError("Product Internal Type is not proper")
		       	  
			data_obj = self.env['ir.model.data']
			raw_picking_type = data_obj.get_object_reference('api_raw_material', location)[1]
			if not res.production_id.raw_request:
				res.production_id.RM_Request_Mo()
				
			pickings=self.env['stock.picking'].search([('material_request_id','=',res.request_id.id),
							('picking_type_id','=',raw_picking_type),('state','!=','cancel')])
			product_data={}
			print "mmmmmmm...",pickings
			for pick in pickings:
				if pick.move_lines:
					for move in pick.move_lines:
						product_data[move.product_id.id] = product_data[move.product_id.id]+move.product_uom_qty if product_data.get(move.product_id.id) else move.product_uom_qty
				else:
					for operation in pick.pack_operation_product_ids:
						product_data[operation.product_id.id] = product_data[operation.product_id.id]+operation.qty_done if product_data.get(operation.product_id.id) else operation.qty_done
							
			shifts=self.env['mrp.workorder.rm.shifts'].search([('workorder_id','=',res.workorder_id.id),
									('status','in',('request','hold')),])
			print "Shifts..............",shifts,product_data
			for sh in shifts:
				for sub in res.sub_product:
					product_data[sub.product.id] = product_data[sub.product.id]+sub.required_qty if product_data.get(sub.product.id) else sub.required_qty
			
			for line in res.sub_product:
				product_data[line.product.id] = product_data[line.product.id]+line.required_qty if product_data.get(line.product.id) else line.required_qty
			for mo in res.workorder_id.production_id.product_lines:
				if product_data.get(mo.product_id.id):
					if int(mo.product_qty)<int(product_data.get(mo.product_id.id)):
						raise UserError("Raw Material Request quantity For product {} is out of rquired quantity ".format(mo.product_id.name))
			raw_date=False
			for shift in res.workorder_id.wo_shift_line:
				if raw_date and shift.date :
					if raw_date > datetime.strptime(shift.date,'%Y-%m-%d %H:%M:%S'):
						raw_date = datetime.strptime(shift.date,'%Y-%m-%d %H:%M:%S')
				elif shift.date:
					raw_date=datetime.strptime(shift.date,'%Y-%m-%d %H:%M:%S')
					
			for rm_request in res.production_id.material_request_id:
				if rm_request.request_type !='extra':
					rm_request.request_date = raw_date
					res.request_id = rm_request.id
					
			for rm in res.sub_product:
				rm.stock_qty = rm.required_qty 
				rm.required_qty = 0.0
			res.status='request'
		return True
		
	@api.multi
	def cancel_picking(self):
		for res in self:
			for rec in res.sub_product:  
				rec.required_qty = rec.qty-rec.available_qty
				rec.stock_qty=0.0
			res.status='draft'

	@api.multi
	def change_date(self):
		for res in self:
			form_view = self.env.ref('api_raw_material.reschedule_shift_form_view', False)
			context=self._context.copy()
			context.update({'default_shift_id':res.id,'default_start_time':res.start_time,
					'default_end_time':res.end_time})
			if form_view:
				return {
				    'type': 'ir.actions.act_window',
				    'view_type': 'form',
				    'view_mode': 'form',
				    'res_model': 'mrp.workorder.rm.shifts.date.history',
				    'views': [(form_view.id, 'form')],
				    'view_id': form_view.id,
				    'target': 'new',
				    'context':context
				}	

class MrpWordkorderShiftsLine(models.Model):

	_name="mrp.workorder.rm.shifts.line"
	
	shift_id = fields.Many2one('mrp.workorder.rm.shifts','Shift No.')
	#receive_shift_id = fields.Many2one('mrp.workorder.rm.shifts','Shift No.')
	#workorder_id = fields.Many2one('mrp.production.workcenter.line','Workorder No.')
	product = fields.Many2one('product.product', string='Product Name')
	uom = fields.Many2one('product.uom', string='Unit')
	#rm_request_id = fields.Many2one('mrp.workorder.raw.material.request','RM request')
    	qty = fields.Float('Total qty',default=0.0)
    	required_qty = fields.Float('Required qty',default=0.0)
    	available_qty = fields.Float('In-Process qty',default=0.0)
    	stock_qty = fields.Float('Qty to Send',default=0.0)
    	#pro_filter = fields.Selection([('raw','Raw'),('not_raw','Non Raw')])

class MrpWordkorderShiftsTimeHistory(models.Model):

	_name="mrp.workorder.rm.shifts.date.history"
	
	shift_id = fields.Many2one('mrp.workorder.rm.shifts','Shift No.')
	start_time = fields.Datetime('Start Time')
	new_start_time = fields.Datetime('New Date')
	end_time = fields.Datetime('End Time')
	date = fields.Datetime('Previous Time')
    	
    	@api.multi
    	def Process(self):
    		for res in self:
    		     if res.shift_id:
    			
    			second=res.shift_id.hours*3600
    			ntime=datetime.strptime(res.new_start_time,'%Y-%m-%d %H:%M:%S')+timedelta(seconds=second)
    			res.shift_id.start_time=res.new_start_time
			res.shift_id.end_time=ntime
			
			rawseconds=0
			rawtime=False
			workorder=False
			self_process_ids=self.env['mrp.production.workcenter.line'].search([
						('production_id','=',res.shift_id.workorder_id.production_id.id),
						('workcenter_id','=',res.shift_id.workorder_id.workcenter_id.id)])
			for self_process in self_process_ids:
				workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',self_process.id)])
				if workorder:
					break
			if workorder:
				rawseconds=workorder.hour*3600
				rawtime=datetime.strptime(res.new_start_time,'%Y-%m-%d %H:%M:%S')-timedelta(hours=6)
				res.shift_id.raw_end_time=rawtime
				res.shift_id.raw_start_time=rawtime-timedelta(seconds=rawseconds)
					
			if res.shift_id.status in ('draft','request'):
				rtime=datetime.strptime(res.new_start_time,'%Y-%m-%d %H:%M:%S')-timedelta(hours=2)
    				res.shift_id.date=rtime
			
			next_shift_id=res.shift_id.next_shift_id if res.shift_id else False
			while next_shift_id:
				next_shift_id.start_time=ntime
				ntime = ntime + timedelta(seconds=second)
				next_shift_id.end_time=ntime
				print "EEEEEEEEee",next_shift_id.start_time,next_shift_id.end_time
				if workorder:
					print "11111111",rawtime,rawseconds
					next_shift_id.raw_start_time=rawtime
					rawtime = rawtime + timedelta(seconds=rawseconds)
					next_shift_id.raw_end_time=rawtime
				next_shift_id = next_shift_id.next_shift_id
    		     
		return True
			
