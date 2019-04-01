 # -*- coding: utf-8 -*-
##############################################################################
#
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models ,api, _
from datetime import datetime, date, time, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
import re
from datetime import datetime
from openerp.exceptions import UserError, ValidationError
import logging
import math
import xlrd
from urlparse import urljoin
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class mrp_product_produce_line(models.Model):
    _inherit="mrp.product.produce.line"
    _description = "Product Produce Consume lines"
    
    remain_qty=fields.Float('Actual Remaining Qty')
    remain_consmed_qty=fields.Float('Calculated Remaining Qty')
    uom_id=fields.Many2one('product.uom' ,'Unit')
    produce_remain_id=fields.Many2one('mrp.product.produce', string="Produce")

class MrpProductProduce(models.Model):
    _inherit='mrp.product.produce'

    @api.model
    def default_get(self, fields):
        result= super(MrpProductProduce, self).default_get(fields)
        obj = self.env['mrp.production'].browse(self._context.get('active_id'))
        lot=self.env['stock.production.lot'].create({'product_id':obj.product_id.id}) 
        if lot:
                code=''
		if lot.product_id:
		   if lot.product_id.categ_id.cat_type == 'film':
		      code='FILM'
		   if lot.product_id.categ_id.cat_type == 'injection':
		      code='INJ'
		   lot.write({'name':code + lot.name})
        lst=[]
        if obj: 
           order=self.env['mrp.production.workcenter.line'].search([('production_id','=',obj.id),('order_last','=',True)])
           qty=total_qty=0.0
           uom=0
           name=''
           for line in order:
               batch=self.env['mrp.order.batch.number'].search([('production_id','=',obj.id),('order_id','=',line.id)])
               print "batch-------------------------",batch
               if batch:
                  for bt_batch in batch:
                      if bt_batch.product_qty > 0 and not bt_batch.lot_id:
                         lst.append(bt_batch.id)
                         qty +=bt_batch.product_qty 
                         uom   =bt_batch.uom_id.id
                         name=bt_batch.uom_id.name
               print "qty----------------",qty,obj.product_uom.id,uom
               result.update({'production_id':obj.id, 'product_qty':0.0,'batch_ids':lst})
               if obj.product_uom.id != uom:
                  if name == 'm' and line.process_type == 'psheet' :
                     total_qty=(obj.product_qty/obj.mrp_third_qty_sheet) * qty
                  if name == 'm' and line.process_type == 'ptube' :
                     total_qty=(obj.product_qty/obj.mrp_third_qty) * qty
                  if name == 'Pcs':
                     total_qty=(qty * obj.product_id.weight )
               else:
                     total_qty=qty
           result.update({'produced_qty':total_qty,'produced_uom_id':obj.product_uom.id, 'lot_id':lot.id})
        if obj.product_uom:
           result.update({'product_uom_id':obj.product_uom.id})
      
        return result

    complete_produce=fields.Boolean('Partial Complete', default=False)
    reason=fields.Text('Any Remark')
    production_id=fields.Many2one('mrp.production', 'Manufacturing No.')
    product_uom_id=fields.Many2one('product.uom' ,'Unit')
    batch_ids=fields.Many2many('mrp.order.batch.number',string='Batch Details')
    produced_qty=fields.Float()
    produced_uom_id=fields.Many2one('product.uom' ,'Unit')
    remain_lines = fields.One2many('mrp.product.produce.line', 'produce_remain_id', 'Products Consumed')
    actual_qty=fields.Float(compute='compute_actual_qty')
    
    @api.depends('batch_ids')
    def compute_actual_qty(self):
        if self.batch_ids:
            for each in self.batch_ids:
                self.actual_qty+=each.convert_product_qty

    @api.multi
    @api.onchange('complete_produce')
    def remain_raw_mrp(self): 
        for record in self:
            if record.complete_produce:
               lst=[]
               for line in record.production_id.product_lines:
                    lst.append((0,0,{'product_id':line.product_id.id, 'uom_id':line.product_uom.id,
                                      'remain_consmed_qty':line.remain_consumed, 'remain_qty':line.remain_consumed}))
               record.remain_lines=lst
               args=[]
               order=self.env['mrp.production.workcenter.line'].search([('production_id','=',record.production_id.id),('order_last','=',True)])
	       for line in order:
		   batch=self.env['mrp.order.batch.number'].search([('production_id','=',record.production_id.id),('order_id','=',line.id),('lot_id','=',False),('product_qty','>',0)])
		   if batch:
		      for bt_batch in batch:
                          args.append((bt_batch.id))
               record.batch_ids=args
            else:
               record.remain_lines=[]

    @api.multi
    @api.onchange('batch_ids')
    def productqty_batch(self):
        for record in self:
            if record.batch_ids:
               qty=total_qty=0.0
               name=''
               for line in record.batch_ids:
                   if line.production_id.product_uom.id != line.uom_id.id:
		          if line.uom_id.name == 'm' and line.order_id.process_type == 'psheet' :
		             total_qty=(line.production_id.product_qty/line.production_id.mrp_third_qty_sheet) * line.product_qty
		          if line.uom_id.name == 'm' and line.order_id.process_type == 'ptube' :
		             total_qty=(line.production_id.product_qty/line.production_id.mrp_third_qty) * line.product_qty
		          if line.uom_id.name == 'Pcs':
		             total_qty=(line.production_id.product_qty / line.production_id.mrp_sec_qty )* line.product_qty
		   else:
		          total_qty=(line.product_qty)
                   qty +=total_qty
               record.product_qty=round(qty, 2)
            else:
                 record.product_qty=0.0
    
    @api.multi
    def do_produce(self):

        obj = self.env['mrp.production'].browse(self._context.get('active_id')) 
        res=super(MrpProductProduce,self).do_produce()
        if not self.batch_ids:
            raise UserError("Please Select Batches to Transfer Qty")

        if obj.hold_order == 'hold':
           raise UserError("Manufacturing Order Hold by Production Department.Before Produce please confirmed to Production Department.")
        if self.product_qty != self.actual_qty:
           raise UserError("Selected Qty is not equal to Produced Qty in Batches Selected")
        if obj:
           for consume in self.consume_lines:
               print "consumeconsumeconsume",consume
               line_date=self.env['mrp.production.product.line'].search([('production_id','=',obj.id),('product_id','=',consume.product_id.id)])
               if line_date:
                  for pro_date in line_date:
                      pro_date.consumed_qty= pro_date.consumed_qty + consume.product_qty
        print "lot_idlot_id",self.lot_id
        if self.lot_id and not self.lot_id.production_id:
           self.lot_id.production_id=obj.id
        if self.lot_id:
           self.lot_id.total_qty =self.product_qty
           self.lot_id.product_uom_id=self.product_uom_id.id
#           create pikcing if no pick for mrp finished move from input to stock
#           if pick already exist not in done then append the transfer to same pick
           picking_type_2=self.env['stock.picking.type'].search([('code','=','internal'),('default_location_dest_id','=',obj.location_dest_id.id)],limit=1)
           print "picking_type_2picking_type_2picking_type_2picking_type_2",picking_type_2
           stck_location=self.env['stock.location'].search([('actual_location','=',True),('location_id','=',obj.location_dest_id.location_id.id)])
           pick_exist=self.env['stock.picking'].search([('origin','=',obj.name),('location_id','=',obj.location_dest_id.id),('location_dest_id','=',stck_location.id),('picking_type_id','=',picking_type_2.id),('state','not in',('done','cancel'))])
           print "pick_existpick_existpick_existpick_existpick_exist",pick_exist
           if not pick_exist:
              pick_exist=self.env['stock.picking'].create({'origin':obj.name,'location_id':obj.location_dest_id.id,'location_dest_id':stck_location.id,'picking_type_id':picking_type_2.id})
              print "picking_createpicking_createpicking_create-123-456--79--------------",pick_exist
           print "moves ino bj-------------------",obj.move_created_ids
           self.env['stock.move'].create({'origin':obj.name,'product_id':obj.product_id.id,'product_uom_qty':self.product_qty,'picking_id':pick_exist.id,'picking_type_id':picking_type_2.id,'product_uom':self.product_uom_id.id,'name':obj.product_id.name,'location_id':obj.location_dest_id.id,'location_dest_id':stck_location.id})
           pick_exist.action_confirm()
           pick_exist.action_assign()
        if obj.move_created_ids:
            obj.move_created_ids[0].write({'date_expected':obj.n_request_date})
        for batch_line in self.batch_ids:
            op_id=pick_exist.pack_operation_product_ids
            op_id.write({'batch_number':[(4, batch_line.id)]})
#            op_id.write({'batch_number':[(6,0,batch_line.id)]})
            batch_line.write({'lot_id':self.lot_id.id,'production_id':obj.id,'logistic_state':'ready','batch_tfred':True})
        body='<b>Produced Qty In Production:</b>'
        body +='<ul><li> Production No.   : '+str(obj.name) +'</li></ul>'
        body +='<ul><li> Lot No.          : '+str(self.lot_id.name) +'</li></ul>'
        body +='<ul><li> Product Name.     : '+str(obj.product_id.name) +'</li></ul>'
        body +='<ul><li> Product Qty.     : '+str(self.product_qty)+str(self.product_uom_id.name) +'</li></ul>'
        body +='<ul><li> Produced By      : '+str(self.env.user.name) +'</li></ul>' 
        body +='<ul><li> Date             : '+str(datetime.now() + timedelta(hours=4))+'</li></ul>' 
        obj.message_post(body=body)
        ### Mo not done
        if obj.state == 'done':
           obj.state ='in_production'
        return res
 
 
# complete mo when done then serach for main move pick exist or not if not then create and alocate batches  to it
    @api.multi
    def api_do_produce(self):
    	for record in self:
		res=super(MrpProductProduce,self).do_produce()
		production_id =self.env['mrp.production'].search([('id','=',self._context.get('active_id'))])
                print "production_idproduction_idproduction_id",production_id
                if self.lot_id and not self.lot_id.production_id and production_id:
		   self.lot_id.production_id=production_id.id
		if self.lot_id:
                   self.lot_id.total_qty =self.product_qty
                   self.lot_id.product_uom_id=self.product_uom_id.id
                   picking_type_2=self.env['stock.picking.type'].search([('code','=','internal'),('default_location_dest_id','=',production_id.location_dest_id.id)],limit=1)
                   print "picking_type_2picking_type_2picking_type_2picking_type_2",picking_type_2
                   stck_location=self.env['stock.location'].search([('actual_location','=',True),('location_id','=',production_id.location_dest_id.location_id.id)])
                   pick_exist=self.env['stock.picking'].search([('origin','=',production_id.name),('location_id','=',production_id.location_dest_id.id),('location_dest_id','=',stck_location.id),('picking_type_id','=',picking_type_2.id),('state','!=','done')])
                   print "pick_existpick_existpick_existpick_existpick_exist",pick_exist
                   if not pick_exist and self.product_qty>0.0:
                      pick_exist=self.env['stock.picking'].create({'origin':production_id.name,'location_id':production_id.location_dest_id.id,'location_dest_id':stck_location.id,'picking_type_id':picking_type_2.id})
                      print "picking_createpicking_createpicking_create-123-456--79--------------",pick_exist
                   self.env['stock.move'].create({'origin':production_id.name,'product_id':production_id.product_id.id,'product_uom_qty':self.product_qty,'picking_id':pick_exist.id,'picking_type_id':picking_type_2.id,'product_uom':self.product_uom_id.id,'name':production_id.product_id.name,'location_id':production_id.location_dest_id.id,'location_dest_id':stck_location.id})
                   pick_exist.action_confirm()
                   pick_exist.action_assign()

                for batch_line in self.batch_ids:
                   op_id=pick_exist.pack_operation_product_ids
                   op_id.write({'batch_number':[(4, batch_line.id)]})
                   batch_line.write({'lot_id':self.lot_id.id,'production_id':production_id.id,'logistic_state':'ready','batch_tfred':True})
	        production_id.state='done'
#		if production_id.state == 'done' and production_id.remain_wastage_qty:
#                   raise UserError("Wastage Qty remaining in manufacturing order.") 
		for line in production_id.move_lines:
			line.state='cancel'
		for rec in production_id.move_created_ids:
			rec.state='cancel'
		stock_id =self.env['stock.move'].search([('name','=',production_id.name),('state','=','waiting'),('product_id','=',production_id.product_id.id)])
		stock_id.write({'state':'cancel'})
		for res in production_id.move_created_ids2:
		    if res.state=='cancel':
			res.production_id=False
		new_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1)  #remove status
		if new_id:
			self.env['sale.order.line'].sudo().browse(production_id.sale_line.id).write({'n_status_rel':[(3,new_id.id)]})
#                        find all wo related to production and delete all batches which are not all produced while closing MO
                wo_ids=self.env['mrp.production.workcenter.line'].search([('production_id','=',production_id.id)])
                print "wo_idswo_ids",wo_ids
                if wo_ids:
                    batch_ids=self.env['mrp.order.batch.number'].search([('production_id','=',production_id.id),('order_id','in',wo_ids.ids),('convert_product_qty','=',0.0)])
                    print "batch_idsbatch_ids",batch_ids
                    if batch_ids:
                        for each_batch in batch_ids:
                            each_batch.unlink()
                        
		if record.complete_produce:  
                   for order in production_id.workcenter_lines:
                       order.state ='done'
		   temp_id = self.env.ref('gt_order_mgnt.email_template_partial_production')
		   if temp_id and production_id.move_lines2:
				user_obj = self.env['res.users'].browse(self.env.uid)
				base_url = self.env['ir.config_parameter'].get_param('web.base.url')
				query = {'db': self._cr.dbname}
				fragment = {
				    'model': 'mrp.production',
				    'view_type': 'form',
				    'id': production_id.id,
				}
				url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
				text_link = _("""<a href="%s">%s</a> """) % (url,production_id.name)
				body_html = """<div> 
			<p><b>Dear: User,</b><br/>
                        <b>Production Request Number :</b>%s <br/>
		         <b>Manufacturing Number :</b>%s <br/>
                         <b>Customer Name :</b>%s <br/>
                         <b>Product Name :</b>[%s]%s <br/>
		          <b>  Quantity Scheduled :</b> %s %s<br/> 
                          <b>  Quantity Produced:</b> %s %s<br/>
                          <b>  Packaging:</b> %s <br/>
		          <b>  Completed By :</b> %s<br/>
                          <b>  Requested Completion Date :</b> %s <br/>
                          <b>  Expected Completion Date :</b> %s <br/>
                          <b>  Completed Date :</b> %s <br/>
                          <b>  Wastage Allowed :</b> %s %s <br/> 
                          <b>  Wastage Produced :</b> %s %s<br/> 
		        </p>
		          <p> <b>  Remarks : </b>%s <br/></p>
		         <h3 style='margin-left:200px;color:blue'>Manufacturing WorkOrders Details</h3>
		        
			</div>"""%(production_id.request_line.name if production_id.request_line else '', text_link or '',
                       production_id.partner_id.name, production_id.product_id.default_code,
                       production_id.product_id.name,
                       production_id.product_qty,production_id.product_uom.name,
                       production_id.n_produce_qty,production_id.produce_uom_id.name, 
                       production_id.n_packaging.name,
                       self.env.user.name , production_id.n_client_date,
                       production_id.n_request_date,str(date.today()), 
                       production_id.wastage_allow or '0',production_id.allow_wastage_uom_id.name or 'Kg',
                       production_id.total_wastage_qty or '0',production_id.allow_wastage_uom_id.name or 'Kg',
                       self.reason)
                                body_html +="<table class='table' style='width:100%; height: 50%;font-family:arial; text-align:left;'><tr><th>WorkOrder Name </th><th>Machine Name</th><th>Required qty</th><th>Produced qty</th><th>Wastage qty</th></tr>" 
                                for order in production_id.workcenter_lines:
                                    body_html +="<tr><td>%s</td><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s %s</td></tr>"%(str(order.name),str(order.machine.name), str(round(order.wk_required_qty,2)),str(order.wk_required_uom.name),str(round(order.total_product_qty if order.total_product_qty else 0.0,2)),str(order.total_uom_id.name if order.total_uom_id else ''), str(round(order.total_wastage_qty if order.total_wastage_qty else 0.0, 2)),str(order.wastage_uom_id.name if order.wastage_uom_id else ''))  
                                    order.state ='done'
                                body_html +="</table>"
                                body_html +="<br></br>"
                                body_html +="<h3 style='margin-left:200px;color:blue'>System Calculated Raw Material Details :</h3>"
		                body_html +="<table class='table' style='width:100%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th>Required qty</th><th>Received qty</th><th>Consumed qty</th><th> Remaining qty</th></tr>"        
                                for line in production_id.product_lines:
                                    if line.product_id:
                                          rm_qty=line.receive_qty - line.consumed_qty
                                          body_html +="<tr><td>%s</td><td>%s %s</td><td>%s %s</td><td>%s %s</td><td>%s %s</td></tr>"%(str(line.product_id.name), str(round(line.product_qty,2)),str(line.product_uom.name),str(round(line.receive_qty,2)),str(line.product_uom.name),str(round(line.consumed_qty if line.consumed_qty else 0.0,2)),str(line.product_uom.name), str(round(rm_qty,2)),str(line.product_uom.name))  

		                body_html +="</table>" 
                                body_html +="<br></br>"
                                picking_type=self.env['stock.picking.type'].search([('code','=','incoming'),('default_location_dest_id','=',production_id.location_dest_id.id)],limit=1)
                                print "picking_typepicking_typepicking_type",picking_type
                                return_picking=self.env['stock.picking'].create({'picking_type_id':picking_type.id,
                                       'location_dest_id':picking_type.default_location_dest_id.id ,
                                        'origin':production_id.name,
                                        'return_raw_picking':True,
                                        'note':record.reason,
                                        'location_id':production_id.location_src_id.id,
                                        'production_id':production_id.id}) 
                                body_rm=''
                                for remain in record.remain_lines:
                                    if remain.remain_qty:
                                       move=self.env['stock.move'].create({'picking_id':return_picking.id,
		                                 'product_id':remain.product_id.id,
		                                  'product_uom_qty':remain.remain_qty,
                                                   'product_uom':remain.uom_id.id,
		                                   'picking_type_id':picking_type.id,
		                                   'location_dest_id':picking_type.default_location_dest_id.id, 
		                                   'location_id':production_id.location_src_id.id, 
		                                   'name':production_id.name})
                                       body_rm +="<tr><td>%s</td><td>%s %s</tr>"%(str(remain.product_id.name), str(round(remain.remain_qty,2)),str(remain.uom_id.name)) 
                                body_html +="</table>"
                                if not return_picking.move_lines:
                                    return_picking.unlink()
                                else:
                                    return_picking.action_confirm()
                                    body_html +="<h3 style='margin-left:200px;color:blue'>Remaining Raw Material As Per Production </h3>"
                                    body_html +="<table class='table' style='width:100%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th>Remaining qty</th></tr>"
                                    body_html +=body_rm
                                    body_html +="<p><b>Return Raw Material Internal Transfer No:"+str(return_picking.name)+"</b></p>"
                                
				body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.production',production_id.id, context=self._context)
                                group = self.env['res.groups'].search([('name', '=', 'MO Closing Receiving')])
                                print "groupgroupgroupgroup",group
                                if group:
                                    user_ids = self.env['res.users'].sudo().search([('groups_id', 'in', [group.id])])
                                    print "user_idsuser_ids",user_ids
                                    email_to = ''.join([user.partner_id.email + ',' for user in user_ids])
                                    email_to = email_to[:-1]
                                    print "email_toemail_to",email_to
                                else:
                                    email_to=str(production_id.user_id.login)
#				n_emails=str(production_id.user_id.login)
				temp_id.write({'body_html': body_html, 'email_to' : email_to, 'email_from': str(production_id.user_id.login)})
				temp_id.send_mail(production_id.id)
	return True

class MrpProduction(models.Model):
    _inherit='mrp.production'


    product_qty = fields.Float('Quantity Scheduled', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)

    @api.model
    def create(self,vals):
    	res_id = super(MrpProduction,self).create(vals)
    	search_id =self.env['mrp.production.calendar.data'].search([('production_id','=',res_id.id)])
    	if not search_id:
		name=res_id.name if res_id.name else '' 
		name +="["+res_id.partner_id.name +"] " if res_id.partner_id else ''
		name += res_id.product_id.default_code if res_id.product_id else ''
		name += "-" +res_id.product_id.name if res_id.product_id else ''
    		self.env['mrp.production.calendar.data'].create({'production_id':res_id.id,'name':name})
	return res_id

class MrpWorkcenterPructionline(models.Model):
    _inherit = 'mrp.production.workcenter.line'

    production_data = fields.Many2one('mrp.production.calendar.data', string='Prodcution Value')
    
    @api.model
    def create(self,vals):
    	res_id = super(MrpWorkcenterPructionline,self).create(vals)
    	search_id =self.env['mrp.production.calendar.data'].search([('production_id','=',res_id.production_id.id)])
    	if search_id:
		res_id.production_data=search_id.id
	return res_id


class MrpProductionData(models.Model):
    _name = 'mrp.production.calendar.data'

    production_id = fields.Many2one('mrp.production', string='Prodcution')
    name = fields.Char(string='Prodcution')
    cal_type = fields.Selection([('mo_plannig','Mo Planning'),('normal','Normal')])
   
class MrpCompleteDate(models.Model):
    _inherit = "mrp.complete.date"
    
    produce_delay=fields.Float()
    produce_delay_injection=fields.Float()
    
    change_film=fields.Boolean('Film Lead Time')
    change_injection=fields.Boolean('Injection Lead Time')
    change_option=fields.Selection([('option','Select change Option'),('sale','Sale'),('purchase','Purchase'),('delivery','Delivery'),
                                  ('mrp','Manufacturing')], string="Description Change Option", default='option')

    @api.multi
    def changeleadtimeadmin(self):
        for record in self:
             product_search=self.env['product.template'].search([('categ_id.cat_type','=','film')],limit=1)
             product=self.env['product.template'].search([('categ_id.cat_type','=','film')])
             product_search_injection=self.env['product.template'].search([('categ_id.cat_type','=','injection')],limit=1)
             product_injection=self.env['product.template'].search([('categ_id.cat_type','=','injection')])
             old=product_search.sale_delay
             old_injection=product_search_injection.sale_delay
             qry_film="Update product_template set sale_delay="+str(abs(self.produce_delay))+" where categ_id=(select id from product_category where cat_type='film')"
             qry_injection="Update product_template set sale_delay="+str(abs(self.produce_delay_injection))+" where categ_id=(select id from product_category where cat_type='injection')"
             if record.change_film: 
                self.env.cr.execute(qry_film)
                for pro in product:
                    pro.message_post(body='<span style="color:blue;">Manufacturing Lead Time Change:</span>'+'<br></br>'+'Old Lead Time'+str(old)+'  ' +'New Lead Time '+str(record.produce_delay ))
                    for variant in pro.product_variant_ids:
                        variant.message_post(body='<span style="color:blue;">Manufacturing Lead Time Change:</span>'+'<br></br>'+'Old Lead Time:  '+str(old)+'  ' +'New Lead Time:  '+str(record.produce_delay ))
             if record.change_injection:
                self.env.cr.execute(qry_injection)
                for inj in product_injection:
                    inj.message_post(body='<span style="color:blue;">Manufacturing Lead Time Change:</span>'+'<br></br>'+'Old Lead Time:   '+str(old_injection)+'  ' +'New Lead Time:  '+str(record.produce_delay_injection))
                    for variant in inj.product_variant_ids:
                        variant.message_post(body='<span style="color:blue;">Manufacturing Lead Time Change:</span>'+'<br></br>'+'Old Lead Time:   '+str(old_injection)+'  ' +'New Lead Time:  '+str(record.produce_delay_injection))
            
class ProductTemplate(models.Model):
    _inherit='product.template'	

    capacity_per_cycle=fields.Float('Capacity Per Cycle')
    time_cycle=fields.Float('Time Cycle')
    
    @api.onchange('initial_weight')
    def onchange_weight(self):
    	if self.initial_weight:
    		self.weight=self.initial_weight
    
class ProductDiscription(models.Model):
    _inherit = "n.product.discription"
	
class ProductDiscriptionValue(models.Model):
    _inherit = "n.product.discription.value"
		
class productImportData(models.TransientModel):
    _name = "product.import.data"

    name=fields.Char('File name')
    new_upload=fields.Binary('Upload File',attachment=True)

    @api.multi
    def update_name(self):
        import base64
    	FILENAME = "/home/aalmir/"+str(self.name)
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
    	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	f_row=[]
        domain=[]
        for row in range(max_nb_row) :
		if row == 0:
			f_row = book.sheet_by_index(0).row_values(row)
			continue
		else:
                   header=f_row
                   i=0
                   name=''
                   p_name=''
                   p_code=''
                   print"hhhhhh",header
                   for rec in book.sheet_by_index(0).row_values(row):
                       if len(header)>= i and header[i] !='':
			  header_name=str(header[i]) 
                       if header_name == 'Name':
                          if i==0:
                              print"ttttttttt",rec
                              p_name =rec
                       if header_name == 'code':
                          p_code=rec
                          print"yyyyyyyyyyy", p_name
                          print'ccccccccc',p_code
                          product_tmpl=self.env['product.product'].search([('default_code','=',str(p_code))])
                          print"TTTTTTTTt",product_tmpl
                          if product_tmpl:
		                  name +=product_tmpl.name[0:11]+" "
		                  des_p=self.env['n.product.discription'].search([('product_id','=',product_tmpl.product_tmpl_id.id)])
		                  if des_p:
				     for des in des_p:
		                         if des.unit:
				            name +=str(des.value)+"X"
		                     name += " "+"CM"
		                     name +=" " + str(product_tmpl.description_purchase)
                                  product_tmpl.product_tmpl_id.name=name
                                  product_tmpl.product_tmpl_id.description_purchase=name
		                  print"111",product_tmpl, name
                                  pro_uom=self.env['product.uom'].search([('product_id','=',product_tmpl.id)])
                                  print"____________--",pro_uom
                                  if pro_uom:
                                     pro_uom.name=name
                                  product_tmpl.packaging_uom_id=pro_uom.id
		       i +=1

    @api.multi
    def import_carton(self):
    	import base64
    	FILENAME = "/home/aalmir/"+str(self.name)
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
    	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	f_row=[]
        uom_type=[]
        product_uom_id=self.env['product.uom'].search([('name','=','Pcs')],limit=1)
        if not product_uom_id:
               raise UserError(('Default Product Uom not Found'))
        material_type=self.env['product.material.type'].search([('string','=','packaging')],limit=1)
        if not material_type:
               raise UserError(('Default Product Material Type not found'))
        carton_type=self.env['product.raw.material.type'].search([('main_id','=',material_type.id),('string','=','carton')],limit=1)
        cat_id=self.env['product.category'].search([('cat_type','=','all')])
        if not cat_id:
               raise UserError(('Default Product Category All not found'))
        length=self.env['n.product.discription.value'].search([('name','=','Length')],limit=1)
        if not length:
               raise UserError(('Default Product Length not found'))
        width=self.env['n.product.discription.value'].search([('name','=','Width')],limit=1)
        if not width:
               raise UserError(('Default Product Width not found'))
        height=self.env['n.product.discription.value'].search([('name','=','Height')],limit=1)
        if not height:
               raise UserError(('Default Product Height not found'))
        remarks=self.env['n.product.discription.value'].search([('name','=','Remarks')],limit=1)
        if not remarks:
               raise UserError(('Default Product Remarks not found'))
        uom=self.env['product.uom'].search([('name','=','cm')],limit=1)
        if not uom:
               raise UserError(('Default Product Specification UOM not found'))
        uom_categ=self.env['product.uom.categ'].search([('name','=','Unit')], limit=1)
        if not uom_categ:
               raise UserError(('Default Product UOM Category not found'))
        p_uom_type=self.env['product.uom.type'].search([('string','=','pri_packaging')],limit=1)
        if not p_uom_type:
               raise UserError(('Default Primary Packaging Type not found'))
        s_uom_type=self.env['product.uom.type'].search([('string','=','sec_packaging')],limit=1)
        if not s_uom_type:
               raise UserError(('Default Secondary Packaging Type not found'))
        uom_type.append((4,p_uom_type.id))
        uom_type.append((4,s_uom_type.id))
        product_data={}
        product=False
        product_name=''
        list_l=[]
	for row in range(max_nb_row) :
		if row == 0:
			f_row = book.sheet_by_index(0).row_values(row)
			continue
		else:
                   header=f_row
                   i=0
                   for rec in book.sheet_by_index(0).row_values(row):
                       if len(header)>= i and header[i] !='':
			  header_name=str(header[i]) 
                       if header_name == 'Type':
                          if i==0:
                             product_name +=str(rec)+" "
                             product_data.update({'product_material_type':material_type.id,
                                          'uom_id':product_uom_id.id,'uom_po_id':product_uom_id.id,
                                          'raw_material_type':carton_type.id,'categ_id':cat_id.id,
                                          'matstrg':'packaging'})
                       if header_name == 'LENGTH':
                          product_name +=str(rec)+"X"
                          list_l.append((0,0,{'value':rec,'attribute':length.id, 'unit':uom.id}))
                       if header_name == 'WIDTH':
                          product_name +=str(rec)+"X"
                          list_l.append((0,0,{'value':rec,'attribute':width.id, 'unit':uom.id}))
                       if header_name == 'HEIGHT':
                          product_name +=str(rec)+"CM"
                          list_l.append((0,0,{'value':rec,'attribute':height.id, 'unit':uom.id}))
                       if header_name == 'WEIGHT':
                          product_data.update({'weight':rec,'initial_weight':rec})
                       if header_name == 'Description':
                          product_name +=" "+str(rec)
                          list_l.append((0,0,{'value':str(rec),'attribute':remarks.id}))
                          product_data.update({'description_purchase':product_name})
                       i +=1
                   product_data.update({'name':product_name,'discription_line':list_l})
                   if product_data.get('message_follower_ids'):
                      product_data.pop('message_follower_ids')
                   product=self.env['product.template'].create(product_data)
                   product_id=self.env['product.product'].search([('product_tmpl_id','=',product.id)])
                   product_uom=self.env['product.uom'].create({'name':product_name,
		                'product_id':product_id.id,'product_type':carton_type.id,
		                'unit_type':uom_type, 'category_id':uom_categ.id})
                   print"PPPPPPPPPPPPP",product,product.discription_line,product_uom
                   if product_uom:
                      product.packaging_uom_id=product_uom.id
                   list_l=[]
                   product_name=''
                   body='<b>Created Product and Product UOM From Import File.  </b>'
                   body +='<li> Product Type: '+str('Carton') +'</li>'
                   body +='<li> Product UOM: '+str(product_uom.name) +'</li>'
                   body +='<li> Created By: '+str(self.env.user.name) +'</li>'
                   body +='<li> Created Date: '+str(date.today()) +'</li>' 
		   product.message_post(body=body)             
    @api.multi
    def import_sale(self):
    	import base64
    	FILENAME = "/home/aalmir/"+str(self.name)
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	f_row=[]
        pipeline=self.env['crm.lead'].create({'name':'tes','is_contract':True})
        for row in range(max_nb_row) :
		if row == 0:
			f_row = book.sheet_by_index(0).row_values(row)
			continue
		else:
			header=f_row
			i=0
                        qty=price_val=update_qty=0.0
                        product_val={}
                        product_id=customer_id=customer_product=False
                        payment_term=delivery_term=currency_id=False
			header_name=''
                        for rec in book.sheet_by_index(0).row_values(row):
				if len(header)>= i and header[i] !='':
					header_name=str(header[i]) 
				if header_name == 'Product External code':
                                   if i==0:
				      record=self.env['customer.product'].search([('ext_product_number','=',rec )],limit=1)
				      if record:
                                         customer_product=record.id
					 product_id=record.product_id.id
                                         currency_id=record.pricelist_id.currency_id.id
                                         product_val.update({'product_id':record.product_id.id,
                                                   'price_unit':record.avg_price,
                                                   'final_price':record.avg_price,
                                                   'fixed_price':record.avg_price,
                                                   'name1':record.product_id.name,
                                                   'pricelist_type':'1',
                                                   'product_packaging':record.product_packaging.id,
                                                   'customer':record.customer_id.id,
                                                   'pricelist_id':record.pricelist_id.id,
                                                   'name':record.product_id.name})
				      else:
					raise UserError("Product Number"+str(int(rec))+"is not Found")
			        if header_name == 'Customer Name':
                                   record=self.env['res.partner'].search([('name','=',rec )])
                                   if record:
                                      pipeline.write({'name':record.name,'partner_id':record.id,
                                                      'type':'opportunity'})
                                      customer_id=record.id
                                      product_val.update({'customer':record.id})
                                   else:
                                     raise UserError("Customer Number"+str(int(rec))+"is not Found") 
				if header_name == 'Qty':
                                   qty=rec
                                   product_val.update({'product_uom_qty':qty})

                                if header_name == 'Delivery Term':
                                   term=self.env['stock.incoterms'].search([('name','=',rec)],limit=1)
                                   if term :
                                     delivery_term=term
                                   else:
                                     raise UserError("Delivery Term"+str(rec)+"is not Found") 
                                if header_name == 'Payment Term':
                                   p_term=self.env['account.payment.term'].search([('name','=',rec)],limit=1)
                                   if term :
                                     payment_term=p_term
                                   else:
                                     raise UserError("Payment Term"+str(rec)+"is not Found") 
                                   '''price=self.env['product.pricelist.item'].search([('cus_product_id','=',customer_product),('min_quantity','<',update_qty),('qty','>',update_qty)])
                                   print"PricePPPPPPPP",price, price.fixed_price, update_qty
                                   if price:
                                      price_val=price.fixed_price
                                      product_val.update({'product_uom_qty':qty,'price_unit':price_val})
                                   else:
                                      raise UserError("Price"+str(price)+"is not Found")'''
                                   
                                if header_name == 'Unit':
                                   unit_s=self.env['product.uom'].search([('name','=',rec)], limit=1)
                                   if unit_s :
                                     unit=unit_s
                                     product_val.update({'product_uom':unit.id})
                                   else:
                                     raise UserError("Product Unit"+str(rec)+"is not Found") 
				if header_name == 'PO Number':
                                   record=self.env['customer.upload.doc'].search([('lpo_number','=',rec)])
                                   print"kumar",record, rec, product_id
                                   if record:
                                      order_line=self.env['sale.order.line'].search([('product_id','=',product_id),('order_id','=',record.sale_id_lpo.id)]) 
                                      print"&&&&&*78888888888888",order_line.product_id
                                      if order_line:
                                         order_line.product_uom_qty +=qty
                                         update_qty += order_line.product_uom_qty
                                      else:
                                        if record.sale_id_lpo: 
                                           product_val.update({'order_id':record.sale_id_lpo.id})
                                           new_line=self.env['sale.order.line'].create(product_val)
                                        else:
                                           pass
                                           '''sale=self.env['sale.order'].create({'partner_id':customer_id,
                                              'opportunity_id':pipeline.id,'incoterm':delivery_term.id,
                                               'payment_term_id':payment_term.id,'delivery_day':'60',
                                                'delivery_day_type':'days',
                                                'validity_date':date.today()+timedelta(days=30),
                                                'delivery_day_3':'confirmed_purchase_order',
                                                'n_quotation_currency_id':currency_id}) '''
                                           #record.sale_id_lpo=sale.id
                                           #product_val.update({'order_id':record.sale_id_lpo.id})
                                          # new_line=self.env['sale.order.line'].create(product_val)
                                   else:
                                      print"gupta",product_val
                                      lpo=self.env['customer.upload.doc'].create({'lpo_number':rec})
                                      sale=self.env['sale.order'].create({'partner_id':customer_id,
                                              'opportunity_id':pipeline.id, 'incoterm':delivery_term.id,
                                              'payment_term_id':payment_term.id,'delivery_day':'60',
                                               'validity_date':date.today()+timedelta(days=30),
                                               'delivery_day_type':'days',
                                               'delivery_day_3':'confirmed_purchase_order',
                                               'n_quotation_currency_id':currency_id})
                                      lpo.sale_id_lpo=sale.id
                                      product_val.update({'order_id':sale.id})
                                      new_line=self.env['sale.order.line'].create(product_val)
				i +=1
    @api.multi
    def import_data(self):
    	import base64
    	FILENAME = "/home/sagar/"+str(self.name)
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	f_row=[]
	s_row=[]
	t_row=[]
	for row in range(max_nb_row) :
		if row == 0:
			f_row = book.sheet_by_index(0).row_values(row)
			continue
		elif row == 1:
			s_row = book.sheet_by_index(0).row_values(row)
			continue
		elif row == 2:
			t_row = book.sheet_by_index(0).row_values(row)
			continue
		else:
			header=f_row
			main_header=s_row
			sub_header=t_row
			i=p_count=0
			header_name=main_header_name=sub_header_name=''
			product_id=False
			bomMaster_id=bom_id=False
			pkg_search=[]
			pkg_vals={}
			product_vals={}
			for rec in book.sheet_by_index(0).row_values(row):
				if len(header)>= i and header[i] !='':
					header_name=str(header[i]) 
				if len(main_header)>=i and main_header[i]!='':
					main_header_name=str(main_header[i])
				if len(sub_header)>=i and sub_header[i] !='':
					sub_header_name=str(sub_header[i])
				
				if header_name == 'PRODUCT NUMBER':
					if i==0:
						if not float(rec):
							raise UserError("Product Number"+str(int(rec))+"is not Proper")
						record=self.env['product.product'].search([('default_code','=',int(rec))])
						if record:
							product_id=record
						else:
							raise UserError("Product Number"+str(int(rec))+"is not Found")
					if i==1:
						product_vals.update({'external_product_number':str(rec)})
					if i==2:
						categ_id=self.env['product.category'].search([('name','=',str(rec))])
						if categ_id:
							product_vals.update({'categ_id':categ_id.id})
					if i==3:
						product_vals.update({'initial_weight':str(rec/1000.0)})
					if i==5:
						product_vals.update({'weight':str(rec/1000.0)})
						
				if header_name == 'PRODUCT DESCRIPTION':
					attr_id=self.env['n.product.discription.value'].search([('name','=',str(sub_header_name))])
					if not attr_id:
						attr_id=self.env['n.product.discription.value'].create({'name':str(sub_header_name)})
						self.env['n.product.discription'].create({'attribute':attr_id.id,'value':str(rec),'product_id':product_id.id})
					else:	
						attributes=self.env['n.product.discription'].search([('attribute','=',attr_id.id),('product_id','=',product_id.id)])
						if not attributes:
							self.env['n.product.discription'].create({'attribute':attr_id.id,'value':str(rec),'product_id':product_id.id})
						else:
							attributes.write({'value':str(rec)})
							
				if header_name == 'Material Code':
					bomMaster_id=self.env['mrp.bom.master'].search([('name','=',str(rec))])
					if not bomMaster_id:
						bomMaster_id=self.env['mrp.bom.master'].create({'name':str(rec)})
						
				if header_name == 'MATERIAL COMPOSITION':
				    n_product_id = self.env['product.product'].search([('name','=',str(main_header_name))])
				    if not n_product_id:
				    	material_id=self.env['product.material.type'].search([('string','=','raw')],limit=1)
				    	n_product_id=self.env['product.product'].create({'name':str(main_header_name),'product_material_type':[(4,material_id.id)],'sale_ok':False,'purchase_ok':True})
				    bom_line=self.env['mrp.bom.master.line'].search([('master_id','=',bomMaster_id.id),('product_id','=',n_product_id.id)])
				    if not bom_line and int(rec)>0:
					self.env['mrp.bom.master.line'].create({'master_id':bomMaster_id.id,'product_id':n_product_id.id,'percentage':rec})
				
				if main_header_name == 'PACKING':
					if p_count==0:
						pkg_type=self.env['product.uom'].search([('name','=',str(rec))])
						pkg_search.append(('uom_id','=',pkg_type.id))
						pkg_vals.update({'uom_id':pkg_type.id})
					if p_count==1:
						uom_type=self.env['product.uom'].search([('name','=',str(rec))])
						pkg_search.append(('unit_id','=',uom_type.id))
						pkg_vals.update({'unit_id':uom_type.id})
					if p_count==2 and str(rec):
						pkg_search.append(('qty','=',str(rec)))
						pkg_vals.update({'qty':str(rec)})
					if p_count==3 and str(rec):
						pkg_search.append(('qty','=',str(rec)))
						pkg_vals.update({'qty':str(rec)})
					if p_count==4 and str(rec):
						pkg_vals.update({'name':str(rec)})
					p_count+=1
				i+=1
			product_id.write(product_vals)	
			if bomMaster_id:
				bom_id=self.env['mrp.bom'].search([('master_id','=',bomMaster_id.id),('product_tmpl_id','=',product_id.product_tmpl_id.id)])
				if not bom_id:
				    line_dict=[]
				    uom_id=self.env['product.uom'].search([('name','=','Kg')],limit=1)
				    uom=uom_id.id if uom_id  else False
				    for res in bomMaster_id.master_line:
				    	qty =(res.percentage*1/100)
				    	line_dict.append((0,0,{'product_id':res.product_id.id,
						    	'percentage':res.percentage,'product_qty':qty,
				    			'product_efficiency':1,'product_uom':uom}))
				    self.env['mrp.bom'].create({
								'master_id':bomMaster_id.id,
								'product_tmpl_id':product_id.product_tmpl_id.id,
								'product_qty':1.0,
								'weight':product_id.weight,
								'bom_line_ids':line_dict})
								
			pkg_search.append(('product_tmpl_id','=',product_id.product_tmpl_id.id))
			search_id=self.env['product.packaging'].search(pkg_search)
			if not search_id:
				pkg=self.env['product.uom'].search([('id','=',str(pkg_vals.get('uom_id')))])
				uom=self.env['product.uom'].search([('id','=',str(pkg_vals.get('unit_id')))])
				p_name=str(pkg_vals.get('qty'))+str(uom.name)+'/'+str(pkg.name)
				pkg_vals.update({'product_tmpl_id':product_id.product_tmpl_id.id})
			 	if pkg_vals.get('name') is None:
			 		pkg_vals.update({'name':pkg_vals.get('name')}) 
			 	self.env['product.packaging'].create(pkg_vals)
				
class MrpConfigSettings(models.Model):
    _inherit='mrp.config.settings'
    
    process_shift_time=fields.Float('Process Shift Time')
   
    @api.multi
    def importProduct(self):
        order_form = self.env.ref('stock_merge_picking.product_import_data', False)
        return {
            'name':'Import Product',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.import.data',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
            'context':{'product':True}
         }
    
    states_re= fields.Many2many('api.mrp.calendar','api_config_state_rel','state_id','config_id',stirng='State Color')
    @api.multi
    def UpdateShifttime(self): 
        for record in self:
            process=self.env['mrp.workcenter'].search([])
            body ='<b>Process Shift Time  changed</b>'
            body +='<ul><li>New Shift Time : '+str(record.process_shift_time) +'</li></ul>'
            body +='<ul><li>Changed By. : '+str(self.env.user.name) +'</li></ul>'
            body +='<ul><li>Changed Date  : '+str(date.today()) +'</li></ul>'
            for pro in process:
                pro.shift_time=record.process_shift_time
                pro.message_post(body=body)

      
class SaleConfigSettings(models.Model):
    _inherit='sale.config.settings'

    @api.multi
    def importsaleorder(self):
        order_form = self.env.ref('stock_merge_picking.product_import_data', False)
        return {
            'name':'Import Product',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.import.data',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
            'context':{'sale':True}
         }
    
    @api.multi
    def importcarton(self):
        order_form = self.env.ref('stock_merge_picking.product_import_data', False)
        return {
            'name':'Import Carton Product and Carton UOM',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.import.data',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
            'context':{'carton':True}
         }

    @api.multi
    def changeleadtime(self):
        order_form = self.env.ref('stock_merge_picking.product_leadtime_change', False)
        product_search=self.env['product.template'].search([('categ_id.cat_type','=','film')],limit=1)
        product_injection=self.env['product.template'].search([('categ_id.cat_type','=','injection')],limit=1)
        context = self._context.copy()
        context.update({'default_produce_delay':product_search.sale_delay, 'default_produce_delay_injection':product_injection.sale_delay})
        return {
            'name':'Change Manufacturing Lead Time',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.complete.date',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,
            'context':{'lead':True}
         }

