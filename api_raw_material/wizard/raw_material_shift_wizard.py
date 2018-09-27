# -*- coding: utf-8 -*-
# copyright reserved

from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from urlparse import urljoin
from urllib import urlencode
import json

class rawMaterialshiftWizard(models.TransientModel):
    _name = "workorder.raw.material.shift"
    
    shift_id = fields.Many2many("mrp.workorder.rm.shifts",'shift_wizard_raw_rel','shift_id','wizard_id',"Shifts")
    raw_id = fields.One2many("raw.material.detail.line",'line_id',"Raw Material Details")
    line_id = fields.One2many("workorder.raw.material.shift.line",'line_id',"Product Line")
    date=fields.Datetime('Date',help='Date & Time send to logistics for delivery of raw material')
    order_id = fields.Many2one("mrp.production.workcenter.line","Workorder")
    
   
    def create_rm_request(self):
	for record in self:
		for raw in record.raw_id:
                        for shift in res.shift_id:
                             shift.request_bool=True
			qty=raw.request_qty+ raw.received_qty
			for line in record.line_id:
				if line.product_id.id == raw.product_id.id:
					qty += line.qty
					
			if qty > raw.qty:
				raise UserError(_("Your Selected Raw Material Quantity for Product {} is Greater Than MO required Raw Material".format(raw.product_id.name)))
		
		shift_vals={'uom':workorder.uom.id,'qty':round(workorder.qty/100,4)*shift_per,
							    'wo_qty':shift_base_qty,
							    'wo_uom':workorder.wk_required_uom.id,
							    'request_id':request_id.id,
							    'hours':shift_time/3600,
							    'date':start_time-timedelta(hours=int(2)),
							    'start_time':start_time,
							    'end_time':end_time,'used_work_id':res.id}
	        product_dic=[]
		for rec in record.line_id:
			product_dic.append({'product':rec.product_id.id,'uom':rec.uom.id,'qty':rec.qty})
		self.env['mrp.workorder.raw.material.request'].create(shift_vals)
					
		body='<b>Send Raw Material Request :  </b>'
		body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
		body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
		body +="<table class='table' style='width:50%; height: 50%;font-family:arial; text-align:left;'><tr><th>Transered Order Name </th><th> Required Date</th></tr>"                  
		   
		#body +="<tr><td>%s</td><td>%s</td></tr>"%(str(picking.name), str(picking.request_sch_date_mo)) 
		body +="</table>"
		record.order_id.message_post(body=body)

	return True

    
    @api.onchange('shift_id')
    def shiftonchange(self):
        lst=[]
        date=False
	if self.shift_id:
		product={}
		for line in self.shift_id:
			if not date:
				date =  datetime.strptime(line.date,'%Y-%m-%d %H:%M:%S')
			if line.date:
				ndate = datetime.strptime(line.date,'%Y-%m-%d %H:%M:%S')
				date = ndate if date > ndate else date
			print "nnnnnnnnnnn",sub_product	
			for sub in line.sub_product:
				print "1111111111",sub
				if product.get(sub.product.id):
					val=product.get(sub.product.id)
					x=val[0]+sub.qty
					product[sub.product.id] = [x,val[1]]
				else:
					product[sub.product.id] = [sub.qty,sub.uom.id]
		print "PPPPPPppp...",product
    		for i,key in enumerate(product):
    			lst.append((0,0,{'product_id':key,'qty':product.get(key)[0],'uom':product.get(key)[1]}))
		print "lst...........",lst
	self.line_id=lst if lst else [(6,0,[])]
	self.date=date
		
class rawMaterialshiftWizardLine(models.TransientModel):
    _name = "workorder.raw.material.shift.line"
    
    line_id = fields.Many2one("workorder.raw.material.shift","Line")
    product_id = fields.Many2one("product.product", "Product")
    uom=fields.Many2one('product.uom', string="Unit") 
    qty=fields.Float('Quantity')   		

class rawMaterialsDetailsWizard(models.TransientModel):
    _name = "raw.material.detail.line"
    
    line_id = fields.Many2one("workorder.raw.material.shift","Line")
    product_id = fields.Many2one("product.product", "Product")
    uom=fields.Many2one('product.uom', string="Unit") 
    qty=fields.Float('Quantity') 
    request_qty=fields.Float('Request Quantity')
    received_qty=fields.Float('Received Quantity')  		
    
    
    		
