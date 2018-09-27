# -*- coding: utf-8 -*-
# copyright reserved

from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from urlparse import urljoin
from urllib import urlencode
import json

class MrpWorkSplit(models.TransientModel):
    _inherit = 'mrp.workorder.split'
    
    @api.multi
    def split_orders(self):
    	super(MrpWorkSplit,self).split_orders()
        for res in self:
     		# for Current Wo except raw material mixing
		workorder=False
		self_process_ids=self.env['mrp.production.workcenter.line'].search([('production_id','=',res.order_id.production_id.id),('workcenter_id','=',res.order_id.workcenter_id.id)])
		for self_process in self_process_ids:
			workorder=self.env['mrp.production.workcenter.line'].search([('workcenter_id.process_id.process_type','=','raw'),('next_order_id','=',self_process.id)])
			if workorder:
				break
		if res.order_id.process_type!='raw' and res.order_id.shift_base_qty:
			if res.order_id.raw_materials_id or workorder.raw_materials_id:
				import math
				shift_base_qty =raw_shift_base_qty =0
				nseconds=raw_shift_time=raw_seconds=0
				shift_per=False		# % of all rm according to MO
				total_mo_qty=0.0			# total of all wo qty with same process of MO
				total_process=self.env['mrp.production.workcenter.line'].search([('production_id','=',res.order_id.production_id.id),('workcenter_id','=',res.order_id.workcenter_id.id)])
				for line in total_process:
					total_mo_qty += line.wk_required_qty
					
				# Calculate shift Rm %	to main qty
				if not shift_per:	
					total_per = round(total_mo_qty/100,6)
					if res.order_id.shift_base_qty > res.order_id.wk_required_qty:
						shift_per = 100				
					else:
						shift_per  = round(res.order_id.shift_base_qty/total_per,6)
					shift_base_qty = round(total_mo_qty/100,6) * shift_per  # get shift qty according to total all process qty
					if workorder:
						raw_shift_base_qty = round(workorder.wk_required_qty/100,6) * shift_per  # get shift qty according to total all process qty
					
				if workorder and workorder.machine:
					raw_time_option = float(workorder.time_option) if workorder.time_option else 1
					raw_cycle=raw_time_option * float(workorder.capacity_per_cycle)
					w_seconds=(workorder.p_hour*60*60)+(workorder.p_minute*60+workorder.p_second)
					raw_shift_time = (w_seconds*raw_shift_base_qty)/raw_cycle
					raw_seconds = (w_seconds*workorder.wk_required_qty) / raw_cycle
               				
               				## to update Hours and cycle in Raw Material Mixing WO 
               				hr=(workorder.p_hour * 60 *60)+(workorder.p_minute*60 +workorder.p_second)
		       			time_cycle= (hr*0.000277778)
					capacity= workorder.capacity_per_cycle * (int(workorder.time_option) if workorder.time_option else 1)
					cycle=float(workorder.wk_required_qty/capacity)
					hour=(cycle *(time_cycle)) *(workorder.machine.time_efficiency or 1.0) +((workorder.machine.time_start or 0.0) +(workorder.machine.time_stop or 0.0))
					workorder.hour=hour
					workorder.cycle=cycle
				
				time_option = float(res.order_id.time_option) if res.order_id.time_option else 1
				cycle=time_option * float(res.order_id.capacity_per_cycle)
				w_seconds=(res.order_id.p_hour*60*60)+(res.order_id.p_minute*60+res.order_id.p_second)
				shift_time = (w_seconds*shift_base_qty)/cycle
				nseconds = (w_seconds*res.order_id.wk_required_qty) / cycle	
				
				shift_required=res.order_id.shift_required
				total_qty = res.order_id.wk_required_qty
				if workorder and not workorder.machine:
					raw_shift_time=shift_time
					raw_seconds=nseconds
					raw_shift_base_qty = shift_base_qty
					
				print "@@@@@@@>>>>>>>>>....",nseconds,shift_time,shift_base_qty,total_qty
				
				# Get Raw Material details of current process (qty ,received + requsted)
				raw_products={}
				received_product_qty = {}
				for raw in res.order_id.raw_materials_id:
					print "RRRRRRRRRRR1111111",raw.original_qty
					raw_products[raw.product_id.id] = raw_products[raw.product_id.id]+ raw.original_qty if raw_products.get(raw.product_id.id) else raw.original_qty
					
					# to get count of receive or in process of receving raw Materials
					if received_product_qty.get(raw.product_id.id):
						received_product_qty[raw.product_id.id] = received_product_qty[raw.product_id.id]+raw.receive_qty
					else:
						 received_product_qty.update({raw.product_id.id:raw.receive_qty}) 
				# Get Raw Material details of Previous process if it is Raw materila mixing Process (qty ,received + requsted)
				for raw in workorder.raw_materials_id:
					#if raw.next_order_id.id == res.order_id.id:
					raw_products[raw.product_id.id] = raw_products[raw.product_id.id]+ raw.qty if raw_products.get(raw.product_id.id) else raw.qty
					
					# to get count of receive or in process of receving raw Materials
					if received_product_qty.get(raw.product_id.id):
						received_product_qty[raw.product_id.id] = received_product_qty[raw.product_id.id]+raw.receive_qty
					else:
						 received_product_qty.update({raw.product_id.id:raw.receive_qty}) 
				request_id = self.env['mrp.raw.material.request'].search([('production_id','=',res.production_id.id)],limit=1)   # Check if Raw MAterial request for shifts is exists or not
				count=1
					
				exist_order=[]
				# start and end Time of Raw Material Mixing Process (-6 Hours)
				start_time = datetime.strptime(res.order_id.date_planned,'%Y-%m-%d %H:%M:%S')
				end_time = start_time + timedelta(seconds=shift_time)
				raw_end_time = datetime.strptime(res.order_id.date_planned,'%Y-%m-%d %H:%M:%S')-timedelta(hours=6)
				raw_start_time = end_time-timedelta(seconds=raw_shift_time)
				receive_qty = 0
				
				print "FFFFFFFFFFFF##$$$..",received_product_qty
				print "NNNNNNNNNN..",raw_products
				# calculate shifts
				next_shift_id=False
				for n in range(int(math.ceil(res.order_id.shift_required))):
					shift_name='SHIFT-'+str(count)
					shift=self.env['mrp.workorder.rm.shifts'].search([('name','=',shift_name),
										('workorder_id','=',res.order_id.id),
										('used_work_id','=',res.order_id.id)])
					
					if shift_required >1:
						total_qty -= res.order_id.shift_base_qty
						nseconds -= shift_time
						raw_seconds -= raw_shift_time
						exist_order.append(shift.id)
						for sub_p in shift.sub_product:
							rec_qty=0.0
							ext_qty=received_product_qty.get(sub_p.product.id)
							if ext_qty > sub_p.qty:
								rec_qty = ext_qty - sub_p.qty
							
							received_product_qty.update({sub_p.product.id:rec_qty})
							if shift.status in ('picking','request'):
								sub_p.required_qty=sub_p.stock_qty
								sub_p.stock_qty=0.0
								sub_p.available_qty =sub_p.qty - sub_p.stock_qty
								
						if shift.status in ('picking','request'):
							shift.status='draft'
							
					else:
						total_per = round(total_mo_qty/100,4)
						shift_per  = round(total_qty/total_per,4)
						shift_time = nseconds
						shift_base_qty =  round(total_mo_qty/100,4) * shift_per
						end_time = start_time + timedelta(seconds=int(shift_time))
						if workorder :
							raw_shift_time=raw_seconds
							raw_end_time = raw_start_time + timedelta(seconds=int(raw_shift_time))
						print "TRRRRRRRRRRRr",total_qty,shift_base_qty
						
						shift_vals={'uom':res.order_id.uom.id,
							    'stock_qty':round(res.order_id.qty/100,4)*shift_per,
							    'qty':round(res.order_id.qty/100,4)*shift_per,
							    'wo_qty':shift_base_qty,
							    'wo_uom':res.order_id.wk_required_uom.id,
							    'request_id':request_id.id,
							    'hours':shift_time/3600,
							    'date':raw_start_time-timedelta(hours=int(2)),
							    'start_time':start_time,
							    'end_time':end_time,'used_work_id':res.order_id.id}
					        if workorder:
					        	shift_vals.update({'raw_uom':workorder.uom.id,
						    		'raw_qty':round(workorder.qty/100,4)*shift_per,
						    		'raw_hours':raw_shift_time/3600,
							    	'raw_start_time':raw_start_time,
				        			 'raw_end_time':raw_end_time})
						check_state=[]
						new_product=[]  
						for raw_p in res.order_id.raw_materials_id:
							raw_vals={}
							rem_qty=0.0
							print "bbbbbbbbbbbbbbb,",raw_products.get(raw_p.product_id.id)
							print "VVVV",shift_per
							avl_qty=new_qty = round(raw_products.get(raw_p.product_id.id)/100,4)*shift_per
							print "B%%%%%%%%",received_product_qty,raw_p.product_id.id
							ext_qty = received_product_qty[raw_p.product_id.id] if received_product_qty.get(raw_p.product_id.id) else 0.0
							print "VVVVVVVVVVVnnn.",ext_qty,new_qty
							if ext_qty >= new_qty: # if inprocess qty 
			    					rem_qty = ext_qty - new_qty
			    					check_state.append(True)
			    				else:
			    					print "1111>..."
			    					rem_qty = 0
			    					avl_qty = ext_qty
			    					check_state.append(False)
	    						req_qty= new_qty-avl_qty if (new_qty-avl_qty)>0 else 0
							print "VVVVVv%%",ext_qty,new_qty
							raw_vals.update({'product':raw_p.product_id.id,
									 'qty':new_qty,'uom':raw_p.uom_id.id,
									 'required_qty':req_qty,
									 'available_qty':avl_qty})
							new_product.append((0,0,raw_vals))
							print "bbbb.......",raw_vals
							received_product_qty[raw_p.product_id.id] = rem_qty
						check_state=[]
						new_product_raw=[]	
						for raw_p in workorder.raw_materials_id:
						    if raw_p.next_order_id.id == res.order_id.id:
							raw_vals={}
							rem_qty=0.0
							avl_qty=new_qty = round(raw_products.get(raw_p.product_id.id)/100,4)*shift_per
							ext_qty = received_product_qty[raw_p.product_id.id] if received_product_qty.get(raw_p.product_id.id) else 0.0
							if ext_qty >= new_qty: # if inprocess qty 
			    					rem_qty = ext_qty - new_qty
			    					check_state.append(True)
			    				else:
			    					rem_qty = 0
			    					avl_qty = ext_qty
			    					check_state.append(False)
		    					req_qty= new_qty-avl_qty if (new_qty-avl_qty)>0 else 0
							raw_vals.update({'product':raw_p.product_id.id,
									'qty':new_qty,'uom':raw_p.uom_id.id,
									'required_qty':req_qty,
									'available_qty':avl_qty})
							print "111111111111!!!!!...",raw_vals
							new_product_raw.append((0,0,raw_vals))
							received_product_qty[raw_p.product_id.id] = rem_qty
						print "VRRR#$$#$#$#$>.>.....!!",check_state
						if all([i for i in check_state]):
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
										('workorder_id','=',res.order_id.id),
										('id','not in',exist_order),
										('used_work_id','=',res.order_id.id)])
				exist_shifts.unlink()
				

