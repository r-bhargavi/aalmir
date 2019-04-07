# -*- coding: utf-8 -*-
# copyright reserved

from datetime import date, datetime,timedelta
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
from urlparse import urljoin
from urllib import urlencode
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
import math
from openerp.exceptions import UserError
import sys
_logger = logging.getLogger(__name__)

class ReserveHistory(models.Model):
    _inherit = 'reserve.history'
     
    #rm_line_id = fields.Many2one('mrp.raw.material.request.line', 'Material Line')
        	
class MrpRawmaterial(models.Model):
   _name='mrp.raw.material.request'
   _inherit = ['mail.thread']
   _order='id desc'
   
   
   rm_reject_reason = fields.Char(string='RM Reject Reason',track_visibility='always' ,copy=False)
   name=fields.Char('Name')
   production_id=fields.Many2one('mrp.production', string='Production No.')
   request_line_ids=fields.One2many('mrp.raw.material.request.line','material_request_id',string='Request Line')
   state=fields.Selection([('draft','Requested'),('approve','Approved'),('partialy','Partialy Send'),
   			   ('send','Send'),('reject','Rejeted'),('cancel','Cancelled')], 
   			   string='Status', default='draft')
   			   
   wastage_qty=fields.Float('Wastage Qty')
   request_date=fields.Datetime('Requested Date')
   partner_id=fields.Many2one(related='production_id.partner_id',store=True)
   expected_compl_date=fields.Datetime('Expected Completion Date')
   wastage_allow=fields.Float('Wastage Allowed')
   required_qty=fields.Float('Required Qty')
   allow_wastage_uom_id=fields.Many2one('product.uom')
   wastage_uom_id=fields.Many2one('product.uom')
   required_uom_id=fields.Many2one('product.uom')
   product_id=fields.Many2one('product.product', string='Product')
   note=fields.Text('Remark')
   note_mgnr=fields.Text('Manager Remark')
   document=fields.Binary('Document') 
   request_type=fields.Selection([('normal','Normal Request'),('extra','Extra Request')], string='Request Type')
   reason=fields.Selection([('wastage','Wastage'),('extra production','Extra Production')], string='Reason')
   
   delivery_id=fields.Many2one('stock.picking','Delivery No.')
   picking_ids = fields.Many2many('stock.picking','raw_material_request_send_picking_rel','rm_id','picking_id',
        				'Delivery No.',help="Send Raw Material To Manufacturing Department")

   work_order_ids=fields.One2many('mrp.production.workcenter.line','rm_request_id',string='Work Orders')
   work_rm_ids=fields.One2many('workorder.raw.material','rm_request_id',string='Work Orders')
   #schedule_raw_bool=fields.Boolean('Hide Schedule Raw button', default=False)
   source_location=fields.Many2one('stock.location')
   shift_request_line=fields.One2many('mrp.workorder.rm.shifts','request_id',string='Delivery Numbers')
   mo_cancel =fields.Boolean('MO Cancel')

   @api.model
   def create(self, vals):
       if not vals.get('name'):
          vals['name'] = self.env['ir.sequence'].next_by_code('mrp.raw.material.request') or 'New'
       result = super(MrpRawmaterial, self).create(vals)
       return result
       
   @api.multi
   def cancel_state(self):
       self.state ='cancel'

   @api.multi
   @api.onchange('source_location')
   def on_change_source(self):
   	#to get available qty from stock>>>
   	try:
   		for line in self:
			if line.source_location:
				for res in line.request_line_ids:
					qty=0
					quants=self.env['stock.quant'].search([('product_id','=',res.product_id.id),('location_id','=',line.source_location.id)])
					for q in quants:
						qty +=q.qty
					res.available_qty = qty - res.product_id.qty_reserved if (qty - res.product_id.qty_reserved )>0 else 0
	except Exception as err:
   		raise UserError("Exception in Source Location selection in raw Material Request -: {} ".format(err))
       
   @api.multi
   def approve_state(self):
   	error_print =''
   	try:
	       for rec in self:
#                   for both extra and normal reqest type of mrp production order internal pikcing shud get created
		   if rec.request_type in ('extra','normal'):
		   	location_1=False
			if rec.production_id.product_id.categ_id.cat_type == 'film':
				location_1='send_film_rm_picking'
			elif rec.production_id.product_id.categ_id.cat_type == 'injection':
				location_1='send_injection_rm_picking'
			else:
				error_print = "Product Internal Type is not proper"
	  			raise
	  			
			data_obj = self.env['ir.model.data']
			raw_picking_location1 = data_obj.get_object_reference('api_raw_material', location_1)[1]
			picking_type1=self.env['stock.picking.type'].search([('id','=',raw_picking_location1)],limit=1)
                        print "picking_type1picking_type1",picking_type1
			procurement_id=self.env['procurement.group'].create({'name':rec.production_id.name,
								      'move_type':'direct'})
			lst=[]
			picking=picking1=False
                        if any(line.pick_qty == 0.0 for line in rec.request_line_ids):
                            raise UserError(_("You cannot pick 0 qty for raw materials!!!"))
			for line in rec.request_line_ids:
				move_ids = self.env['stock.move'].create({ 'date':rec.request_date,'origin':rec.name,
						  'product_id':line.product_id.id,'product_uom_qty':line.pick_qty,
						  'product_uom':line.uom_id.id, 'picking_type_id':picking_type1.id,  
						  'location_dest_id':picking_type1.default_location_dest_id.id,
						  'location_id':rec.source_location.id, 
						  'name':rec.name,'group_id':procurement_id.id})
				move_ids.with_context({'rm_route':True,'product_id':rec.product_id.id}).action_confirm()
				picking=move_ids.picking_id
			if picking:
				picking.material_request_id=rec.id
				picking.min_date=rec.request_date
				picking.expected_comple_date=rec.expected_compl_date
                                picking.origin=rec.production_id.name
				picking.ntransfer_type ='rm_virtual'
				rec.picking_ids = [(4,picking.id)]
				for move in picking.move_lines:
					if move.move_dest_id and move.move_dest_id.picking_id:
						picking1 = move.move_dest_id.picking_id
						break 
				rec.delivery_id=picking.id
                                rec.production_id.delivery_ids= [(4,picking.id)]		# MO	

			if picking1:
				picking1.material_request_id=rec.id
                                picking1.min_date=rec.request_date
				picking.expected_comple_date=rec.expected_compl_date

				picking1.production_id=rec.production_id.id
				picking1.origin=rec.name
				picking1.next_prev_picking_id=[(4,picking.id)]
				picking1.ntransfer_type ='rm_production'
				rec.production_id.delivery_ids= [(4,picking1.id)]		# MO	
#			else:
#				error_print = "Routes are not set for Raw Material products, Please go to setting and set Injection or Film"		
#				raise 
				
		   rec.state ='approve'
		   for line in rec.request_line_ids:
		   	line.reserve_status='approve'
		   	
#		   if rec.request_type in ('extra','normal'):
#			   temp_id = self.env.ref('api_raw_material.email_template_extra_raw_material_approve')
#			   if temp_id:
#			       user_obj = self.env['res.users'].browse(self.env.uid)
#			       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
#			       query = {'db': self._cr.dbname}
#			       fragment = {
#				    'model': 'mrp.production',
#				     'view_type': 'form',
#				     'id': rec.production_id.id,
#				      }
#			       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
#			       text_link = _("""<a href="%s">%s</a> """) % (url,rec.production_id.name)
#			       body_html = """<div> 
#				<p> <strong>Raw Material Request Approved</strong><br/><br/>
#				 <b>Dear: %s,</b><br/>
#				 <b>Production Number :</b>%s ,<br/>
#				  <b>Customer Name :</b>%s ,<br/>
#				  <b>Product Name :</b>%s ,<br/>
#				  <b>Allowed Wastage :</b>%s %s,<br/>
#				  <b>  Wastage Qty : %s %s</b><br/>
#				  <b>  Required Qty : %s %s</b><br/>
#				  <b>  Reason : </b>%s<br/>
#				  <b>  Production Remark : </b>%s<br/>
#				  <b>  Manager Remark : </b>%s
#				</p>
#				</div>#"""%(rec.production_id.user_id.name, text_link or '',rec.production_id.partner_id.name, 
#				    rec.product_id.name, rec.wastage_allow,
#				   rec.allow_wastage_uom_id.name,
#				  rec.wastage_qty, rec.wastage_uom_id.name, rec.required_qty, 
#				 rec.required_uom_id.name,rec.reason, rec.note, rec.note_mgnr)
#			       body_html +="<table class='table' style='width:50%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th> qty</th></tr>"                  
#			       for line in rec.request_line_ids:
#				   body_html +="<tr><td>%s</td><td>%s %s</td></tr>"%(str(line.product_id.name), str(line.qty), str(line.uom_id.name)) 
#			       body_html +="</table>"
#			       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.raw.material.request',rec.id, context=self._context)
#			       n_emails=str(rec.production_id.user_id.login)
#			       temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': str(rec.production_id.user_id.login)})
#			       temp_id.send_mail(rec.id)
   	except Exception as err:
   		raise UserError("Exception in Approval of raw Material Request -: {} ".format(error_print if error_print else err))
        return True
    
   @api.multi
   def reject_rm_request(self):
       cofirm_form = self.env.ref('api_account.pay_cancel_wizard_view_form', False)
       if cofirm_form:
            return {
                        'name':'RM Reject Wizard',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'cancel.pay.reason.wizard',
                        'views': [(cofirm_form.id, 'form')],
                        'view_id': cofirm_form.id,
                        'target': 'new'
                    }
        
           
   @api.multi
   def reject_state(self):
	error_print =''
   	try:
	       for rec in self:
	       	   rec.state ='reject'
		   for line in rec.request_line_ids:
		   	line.reserve_status='reject'
                   rec.production_id.write({'state':'rmr'})
		   
		   if rec.request_type=='extra':	
			if not rec.note_mgnr:
				error_print="Pleas fill the Manager Remark...."
				raise 

#			temp_id = self.env.ref('api_raw_material.email_template_extra_raw_material_reject')
#			if temp_id:
#			       user_obj = self.env['res.users'].browse(self.env.uid)
#			       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
#			       query = {'db': self._cr.dbname}
#			       fragment = {
#				    'model': 'mrp.production',
#				     'view_type': 'form',
#				     'id': rec.production_id.id,
#				      }
#			       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
#			       text_link = _("""<a href="%s">%s</a> """) % (url,rec.production_id.name)
#			       body_html = """<div> 
#				<p> <strong>Extra Raw Material Request Rejected</strong><br/><br/>
#				 <b>Dear: %s,</b><br/>
#				 <b>Production Number :</b>%s ,<br/>
#				 <b>Customer Name :</b>%s ,<br/>
#				  <b>Product Name :</b>%s ,<br/>
#				  <b>Allowed Wastage :</b>%s %s,<br/>
#				  <b>  Wastage Qty : %s %s</b><br/>
#				  <b>  Required Qty : %s %s</b><br/>
#				  <b>  Reason : </b>%s<br/>
#				  <b>  Production Remark : </b>%s<br/>
#				  <b>  Manager Remark : </b>%s
#				</p>
#				</div>#"""%(rec.production_id.user_id.name, text_link or '',rec.production_id.partner_id.name,
#				    rec.product_id.name, rec.wastage_allow,
#				   rec.allow_wastage_uom_id.name,
#				  rec.wastage_qty, rec.wastage_uom_id.name, rec.required_qty, 
#				 rec.required_uom_id.name,rec.reason, rec.note, rec.note_mgnr)
#			       body_html +="<table class='table' style='width:50%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th> qty</th></tr>"                  
#			       for line in rec.request_line_ids:
#				   body_html +="<tr><td>%s</td><td>%s %s</td></tr>"%(str(line.product_id.name), str(line.qty), str(line.uom_id.name)) 
#			       body_html +="</table>"
#			       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.raw.material.request',rec.id, context=self._context)
#			       n_emails=str(rec.production_id.user_id.login)
#                               
#			       temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': str(rec.production_id.user_id.login)})
#			       temp_id.send_mail(rec.id)
   	except Exception as err:
   		raise UserError("{} ".format(error_print if error_print else err))
       
   	return True
       
class MrpRawmaterialLine(models.Model):
	_name='mrp.raw.material.request.line'
        

        @api.depends('pick_qty','qty')
        def _compute_extra_qty(self):
            for rec in self:
                rec.extra_qty=rec.pick_qty-rec.qty
                print "selfkjhjstet tracjet======================================",rec.extra_qty

	@api.multi
	def get_available_qty(self):
		#to get available qty from stock>>>
		for line in self:
			if line.material_request_id.source_location:
				qty=0
				quants=self.env['stock.quant'].search([('product_id','=',line.product_id.id),('location_id','=',line.material_request_id.source_location.id)])
				for q in quants:
					qty +=q.qty
				line.available_qty = qty - line.product_id.qty_reserved
			else:
				line.available_qty = line.product_id.qty_available - line.product_id.qty_reserved

	material_request_id=fields.Many2one('mrp.raw.material.request', 'Request No.')
	product_id=fields.Many2one('product.product', string='Product')
	qty=fields.Float('Required Qty',digits_compute=dp.get_precision('Stock qty'))
	extra_qty=fields.Float('Extra Qty',digits_compute=dp.get_precision('Stock qty'),compute='_compute_extra_qty')
	pick_qty=fields.Float('Pick Qty',digits_compute=dp.get_precision('Stock qty'))
	uom_id=fields.Many2one('product.uom', string="Unit")
        shift_qty=fields.Float('Shift Qty')

	rm_type=fields.Selection([('stock','Stock'),('mo','MO'),('po','PO')], default='stock')
	pro_request_id=fields.Many2one('n.manufacturing.request', string='Production No.')
	production_id=fields.Many2one('mrp.production', string='Manufacturing No.')
	requisition_id=fields.Many2one('purchase.requisition',string='PRQ No.')
	pr_id=fields.Many2one('n.manufacturing.request',string='PR No.',related='production_id.request_line',store=True)
	po_request_id=fields.Many2one('stock.purchase.request',string='Purchase Request No.')
	required_date=fields.Datetime('Required Date')
	expected_compl_date=fields.Datetime('Expected Completion Date')
	total_available_qty = fields.Float('Total Stock',digits_compute=dp.get_precision('Stock qty'),related='product_id.qty_available')
	available_qty = fields.Float('Available Qty',digits_compute=dp.get_precision('Stock qty'),compute='get_available_qty')

	#pending_qty = fields.Float('Pending Qty',digits_compute=dp.get_precision('Stock qty'))
	#reserve_qty = fields.Float('Reserve Qty',digits_compute=dp.get_precision('Stock qty'))
	#res_ids = fields.One2many('reserve.history', 'rm_line_id', 'Reserve History')
   	#reserve_status = fields.Selection([('draft','Draft'),('approve','Approve'),('reject','reject'),
   	#				('cancel','Cancel'),('reserve','Reserve'),('send','Send')],default='draft')
   	
	# reserve quantity of raw material for send to manufacture
	'''@api.multi
	def reserve_do(self):
		form_id = self.env.ref('api_raw_material.raw_material_reserve_wizard', False)
		if form_id:
		    qty=round(self.qty-self.reserve_qty,2) if (self.qty-self.reserve_qty)>0 else 0
		    return {
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'raw.material.reserve.release',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'context': {'default_line_id': self.id,'default_product_id':self.product_id.id,
				'default_avl_qty':self.available_qty,'default_total_qty_reserve':qty,
				'default_avl_uom':self.uom_id.id,'default_uom_id2':self.uom_id.id,
				'default_reserve_uom':self.uom_id.id,'default_reserve_qty':qty},
		    }
		    
	# release quantity of reserve raw material 
	@api.multi
	def release_do(self):
		form_id = self.env.ref('api_raw_material.raw_material_release_wizard', False)
		if form_id:
		    return {
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'raw.material.reserve.release',
			'views': [(form_id.id, 'form')],
			'view_id': form_id.id,
			'target': 'new',
			'context': {'default_line_id': self.id,'default_product_id':self.product_id.id,
				'default_res_qty':self.reserve_qty,'default_reserve_uom':self.uom_id.id,
				'default_release_uom':self.uom_id.id,'default_release_qty':self.reserve_qty},
		    }

	# release quantity of reserve raw material 
	@api.multi
	def open_history(self):
		tree_id = self.env.ref('api_raw_material.raw_material_reserve_history_tree', False)
		if tree_id:
		    return {
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'tree',
			'res_model': 'reserve.history',
			'views': [(tree_id.id, 'tree')],
			'view_id': tree_id.id,
			'target': 'new',
			'domain':[('rm_line_id','=',self.id)],
		    }'''

	@api.multi
	def back_schedule(self):
	   error_string=''
	   try:
		for record in self:
		   if record.pro_request_id:
   			if record.pro_request_id.state=='draft':
				body ='<b>Production Request Cancelled By Logistic Department:  </b>'
				body +='<ul><li> Production No.:'+str(record.pro_request_id.name)+'</li></ul>'
				body +='<ul><li> Product Name : '+str(record.product_id.name) +'</li></ul>' 
				body +='<ul><li> Product Qty : '+str(record.qty) +'</li></ul>'
				body +='<ul><li> Cancelled By  : '+str(self.env.user.name) +'</li></ul>'
				body +='<ul><li> Cancelled Date  : '+str(date.today()) +'</li></ul>'
				#record.pro_request_id.message_post(body=body)
				record.message_post(body=body)
				record.pro_request_id=False
				record.rm_type='stock'
			elif record.pro_request_id.state !='draft':
				error_string="Production request in Process you can not cancel it."
				raise
		   if record.po_request_id:
		      purchase_request=self.env['stock.purchase.request.line'].search([('purchase_request_id','=',record.po_request_id.id),('qty','=',record.qty), ('requisition_id','=',False)], limit=1)
		      if purchase_request: 
			 body ='<b>Purchase Request Line Deleted By Logistic Department:  </b>'
			 body +='<ul><li> Purchase Request No. : '+str(purchase_request.name) +'</li></ul>'
			 body +='<ul><li> Product Name : '+str(record.product_id.name) +'</li></ul>' 
			 body +='<ul><li> Product Qty : '+str(record.qty) +'</li></ul>'
			 body +='<ul><li> Cancelled By  : '+str(self.env.user.name) +'</li></ul>'
			 body +='<ul><li> Cancelled Date  : '+str(date.today()) +'</li></ul>'
			 record.material_request_id.message_post(body=body)
			 record.po_request_id.message_post(body=body)
			 record.po_request_id=False
			 record.rm_type='stock'
			 purchase_request.unlink()

	   except Exception as err:
	   	if error_string:
	   		raise UserError(UserError)
   		else:
	    		exc_type, exc_obj, exc_tb = sys.exc_info()
		    	_logger.error("API-EXCEPTION..Exception in Cancel Production request {} {}".format(err,exc_tb.tb_lineno))
		    	raise UserError("API-EXCEPTION..Exception in Cancel Production request {} {}".format(err,exc_tb.tb_lineno))
		    	
	@api.multi
	def schedule_mo(self):
		for record in self:
			if record.product_id and record.rm_type == 'mo':
				pr=self.env['n.manufacturing.request'].create({'n_state':'draft',
							'n_product_id':record.product_id.id,
							'n_delivery_date':record.required_date,
							'n_unit':record.uom_id.id,
							'n_order_qty':math.ceil(record.qty),
							'n_category':record.product_id.categ_id.id,
							#'n_client_date':record.required_date,
							'request_type':'raw',
							'n_default_code':record.product_id.default_code})
				record.pro_request_id=pr.id		  
				body ='<b>Production Request sent for Raw Material:  </b>'
				body +='<ul><li> Production No. : '+str(pr.name) +'</li></ul>'
				body +='<ul><li> Product Name : '+str(record.product_id.name) +'</li></ul>' 
				body +='<ul><li> Product Qty : '+str(record.qty) +'</li></ul>'
				body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
				body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
				#pr.message_post(body=body)
				record.material_request_id.message_post(body=body)

			if record.product_id and record.rm_type == 'po':
				rq_data=self.env['stock.purchase.request']
				if record.product_id:
					record.rm_type='po'
					reqst_search=rq_data.search([('product_id','=',record.product_id.id ), ('p_state','in',('draft','requisition'))], limit=1)
					if reqst_search:
					  record.po_request_id=reqst_search.id
					  line=self.env['stock.purchase.request.line'].create({'product_id':record.product_id.id,
						   'qty':math.ceil(record.qty), 'uom_id':record.uom_id.id,
						   'material_request_id':record.material_request_id.id,
						   'required_date':record.required_date,
						   'production_id':record.material_request_id.production_id.id,
						   'purchase_request_id':reqst_search.id})
						   
					  body ='<b>Purchase Request Sent for Product:  </b>'
					  body +='<ul><li> Purchase Request No. : '+str(reqst_search.name) +'</li></ul>'
					  body +='<ul><li> Product Name : '+str(reqst_search.product_id.name) +'</li></ul>' 
					  body +='<ul><li> Product Qty : '+str(record.qty) +'</li></ul>'
					  body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
					  body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
					  reqst_search.message_post(body=body)
					  record.material_request_id.message_post(body=body)
					else:
					  request=rq_data.create({'product_id':record.product_id.id, 
								  'material_request_id':record.material_request_id.id,
								   'production_id':record.material_request_id.production_id.id})
					  body='<b>Purchase Request Sent for Product:  </b>'
					  body +='<ul><li> Purchase Request No. : '+str(request.name) +'</li></ul>'
					  body +='<ul><li> Product Name : '+str(request.product_id.name) +'</li></ul>'
					  body +='<ul><li> Product Qty : '+str(record.qty) +'</li></ul>'
					  body +='<ul><li> Created By  : '+str(self.env.user.name) +'</li></ul>'
					  body +='<ul><li> Created Date  : '+str(date.today()) +'</li></ul>'
					  record.po_request_id=request.id
					  request.message_post(body=body)
					  record.material_request_id.message_post(body=body)
					  if request:
					     line=self.env['stock.purchase.request.line'].create({'product_id':record.product_id.id,
						  'qty':math.ceil(record.qty),
						  'required_date':record.required_date,
						  'production_id':record.material_request_id.production_id.id,
						  'material_request_id':record.material_request_id.id,
						  'uom_id':record.uom_id.id, 'purchase_request_id':request.id})

'''class mrpRawmaterialWastage(models.Model):
	_name='mrp.wastage.request'
	_inherit = ['mail.thread']
	_order='id desc'

	name=fields.Char('Name')
	production_id=fields.Many2one('mrp.production', string='Manufacturing No.')
        used_type=fields.Selection([('grinding','Grinding'),('scrap','Scrap')],string='Used Type')
        batch_ids=fields.One2many('mrp.order.batch.number','wastage_request_id')
        state=fields.Selection([('draft','Requested'),('approve','Approved'),('cancel','Cancelled')], 
   			   string='Status', default='draft')
        @api.model
        def create(self, vals):
        	if not vals.get('name'):
          		vals['name'] = self.env['ir.sequence'].next_by_code('mrp.wastage.request') or 'New'
       		result = super(mrpRawmaterialWastage, self).create(vals)
       		return result

	@api.multi
        def cancel_request(self):
            print"=========self=====",self
            for record in self:
                total_qty=0.0
                if record.batch_ids:
                   for  batch in record.batch_ids:
                        if batch.request_state == 'draft':
                           total_qty +=batch.product_qty
                           batch.write({'request_state':'cancel'})
                   print"uyyyyyyyyyy",total_qty,record.state 
                   record.production_id.requested_wastage_qty -=total_qty
                   record.write({'state':'cancel'})
                   print"=====ffffffffff====",record.production_id.remain_wastage_qty, 
                else:
                   record.write({'state':'cancel'})
	@api.multi
        def approve_request(self):
		for record in self:
                    warehouse=self.env['stock.warehouse']
                    location_id=0
                    if record.batch_ids:
                       if record.used_type == 'grinding':
                          location=warehouse.search([('code','=','GRDWH')],limit=1) 
                          location_id=location.lot_stock_id.id
                       else:
                          location=warehouse.search([('code','=','SCPWH')],limit=1)
                          location_id=location.lot_stock_id.id
                       picking_type=self.env['stock.picking.type'].search([('code','=','internal')],limit=1)
                       inventory=self.env['stock.inventory'].create({'name':"stock update for wastage Request No. -"+str(record.name),
                          'filter':'partial','location_id':location_id})
                       inventory.prepare_inventory()
                       print"jmmmmmmmmmmmmmm",inventory
                       lst=[]
                       for batch in record.batch_ids:
                           if batch.request_state == 'draft':
                              print"================",batch.wastage_product.sudo().qty_available,batch.product_qty,batch.wastage_product.sudo().incoming_qty
                              lst.append((0,0,{'product_id':batch.wastage_product.id,'product_uom_id':batch.uom_id.id,
                                        'product_qty':(batch.wastage_product.sudo().qty_available + batch.product_qty),
                                            'location_id':location_id}))#picking_type.default_location_dest_id.id}))
                              batch.write({'request_state':'requested'})
                       inventory.line_ids=lst
                       inventory.action_done()
                       print"================",inventory 
                       record.write({'state':'approve'})'''
                              
# COmented code for SHIFT schedule>>>>>>>>>>>>>>>>>>>>`
'''class MrpWordkorderShifts(models.Model):

	_name="mrp.workorder.raw.material.request"

	@api.multi
	def _get_picking_status(self):
		for rec in self:
			if rec.picking_id: 
				rec.send_picking_status=rec.picking_id.state
			if rec.rec_picking_id: 
				rec.rec_picking_status=rec.rec_picking_id.state
					
	name = fields.Char('Name')
	request_id=fields.Many2one('mrp.raw.material.request',string='Raw Material')
	workorder_id = fields.Many2one('mrp.production.workcenter.line','Workorder No.')
	production_id = fields.Many2one('mrp.production','Manufacturing No.',related='workorder_id.production_id')
	product_id = fields.Many2one('product.product', string='Product Name')
	sub_product = fields.One2many('mrp.workorder.rm.shifts.line','rm_request_id',string='Product Details')
    	qty = fields.Float('qty')
    	uom = fields.Many2one('product.uom', string='Unit')
    	wo_qty = fields.Float('qty')
    	wo_uom = fields.Many2one('product.uom', string='Unit')
    	date = fields.Datetime('Schedule Date')
    	picking_id = fields.Many2one('stock.picking','Delivery No.',help="Send Raw Material To Manufacturing Department")
    	send_picking_status = fields.Char(compute='_get_picking_status',help="Status of Send Raw Material To Manufacturing Department")
    	rec_picking_id = fields.Many2one('stock.picking','Delivery No.',help="Receive Raw Material Delivery no.")
    	rec_picking_status = fields.Char(compute='_get_picking_status',help="Status of Receive Raw Material Delivery no.")
	state=fields.Selection([('draft','Draft'),('request','Raw Material Request'),
				 ('picking','Delivery In Progress'),('hold','Hold'),('delivered','Delivered'),
				 ('receive','Received'),('cancel','Cancel')])
	date_history = fields.One2many('mrp.workorder.rm.shifts.date.history','rm_request_id',string='Re-schedule History')
	used_work_id = fields.Many2one('mrp.production.workcenter.line','Used in WO',help='Raw Material Shift USed for workorder')
	rm_state = fields.Selection([('draft','Requested'),('approve','Approved'),('partialy','Partialy Send'),
   			   ('send','Send'),('reject','Rejeted'),('cancel','Cancelled')],related='request_id.state')
   	wo_state = fields.Selection([('draft','Draft'),('pause','Pause'),('hold','On Hold'),('ready','Ready'),
    				('startworking', 'In Progress'),('done','Finished'),('cancel','Cancelled'),],
    				'Status', readonly=True, copy=False,related='workorder_id.state')
    				
	@api.multi
	def change_date(self):
		for res in self:
			form_view = self.env.ref('api_raw_material.reschedule_shift_form_view', False)
			context=self._context.copy()
			context.update({'default_rm_request_id':res.id,'default_date':res.date,})
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
'''
