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
from datetime import datetime
from datetime import datetime, date, time, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
import time
import math
import decimal
from urlparse import urljoin
from openerp import tools, SUPERUSER_ID
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class calendar_event(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    production_id=fields.Many2one('mrp.production', string='Manufacturing Order')

class MrpProduction(models.Model):
    _inherit='mrp.production'

    @api.model
    def _get_uom_id(self):
        return self.env["product.uom"].search([('name','=','Kg')], limit=1, order='id')[0]
    
    @api.v7
    def _compute_planned_workcenter(self, cr, uid, ids, context=None, mini=False):
        dt_end = datetime.now()
        if context is None:
            context = {}
        for po in self.browse(cr, uid, ids, context=context):
            dt_end = datetime.strptime(po.date_planned, '%Y-%m-%d %H:%M:%S') 
            if not po.date_start:
                self.write(cr, uid, [po.id], {
                    'date_start': po.date_planned
                }, context=context, update=False)
            old = None
            for  wci in range(len(po.workcenter_lines)):
                wc  = po.workcenter_lines[wci]
                
                if (old is None) or (wc.sequence>old):
                    dt = dt_end
                if context.get('__last_update'):
                    del context['__last_update']
                if dt:
                 if (wc.date_planned < dt.strftime('%Y-%m-%d %H:%M:%S')) or mini:
                    if wc.machine:
                       self.pool.get('mrp.production.workcenter.line').write(cr, uid, [wc.id],  {
                        #'date_planned': dt.strftime('%Y-%m-%d %H:%M:%S') #comented code is odoo default
                    }, context=context, update=False)
                    i = self.pool.get('resource.calendar').interval_get(
                        cr,
                        uid,
                        #passing False makes resource_resource._schedule_hours run 1000 iterations doing nothing
                        wc.workcenter_id.calendar_id and wc.workcenter_id.calendar_id.id or None,
                        dt,
                        wc.hour or 0.0
                    )
                    ### this changes use for Running parallel Workorders
                    dt_end =datetime.strptime(wc.date_planned_end, '%Y-%m-%d %H:%M:%S') if wc.date_planned_end else None
                    if i and wc.date_planned_end:
                        dt_end = datetime.strptime(wc.date_planned_end, '%Y-%m-%d %H:%M:%S')
                else: 
                       if wc.date_planned:
                          dt_end = datetime.strptime(wc.date_planned, '%Y-%m-%d %H:%M:%S')
                       if wc.date_planned_end:
                          dt_end = datetime.strptime(wc.date_planned_end, '%Y-%m-%d %H:%M:%S')

                old = wc.sequence or 0
            super(MrpProduction, self).write(cr, uid, [po.id], {
                'date_finished': dt_end
            })
        return dt_end

    @api.v7
    def _prepare_lines(self, cr, uid, production, properties=None, context=None):
        # search BoM structure and route
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        bom_point = production.bom_id
        bom_id = production.bom_id.id
        if not bom_point:
            bom_id = bom_obj._bom_find(cr, uid, product_id=production.product_id.id, properties=properties, context=context)
            if bom_id:
                bom_point = bom_obj.browse(cr, uid, bom_id)
                routing_id = bom_point.routing_id.id or False
                self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

        if not bom_id:
            raise UserError(_("Cannot find a bill of material for this product."))
        # get components and workcenter_lines from BoM structure
        if production.product_uom.id == bom_point.product_uom.id:
           factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
        else:
           if production.product_uom.name.upper()=='KG':
           	factor = production.product_qty / production.product_id.weight
   	   if production.product_uom.name.upper()=='PCS':
   	   	factor = production.product_qty * production.product_id.weight
        # product_lines, workcenter_lines
        return bom_obj._bom_explode(cr, uid, bom_point, production.product_id, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id, context=context)
    
    
    @api.multi 
    @api.depends('lot_ids.total_qty')
    def _n_get_produced_qty(self):
	for rec in self:
		qty=0.0
		if rec.lot_ids:
			for line in rec.lot_ids:
		            qty +=line.total_qty
		rec.n_produce_qty = qty
                rec.produce_uom_id=rec.product_uom.id
    @api.multi 
    @api.depends('workcenter_lines')
    def _n_get_produced_qty_now(self):
	for rec in self:
		qty=0.0
		if rec.workcenter_lines:
			for line in rec.workcenter_lines:
                            wo_id=self.env['mrp.production.workcenter.line'].search([('name','=',line.name)])
                            if wo_id.order_last==True:
                                for each_line in wo_id.batch_ids:
                                    qty +=each_line.product_qty
		rec.n_produce_qty_now = qty
                rec.produce_uom_id=rec.product_uom.id

    @api.multi
    def _get_scrap_qty(self):
	for rec in self:
		records=self.env['stock.move'].search([('origin','=',rec.name), ('state','=','assigned'),('location_dest_id.name','=','Scrap Location')])
		mo_qty=quality=0.0
		for line in records:
			if line.name:
				quality +=line.product_qty
			else:
				mo_qty +=line.product_qty
		rec.mo_scrap = mo_qty
		rec.quality_scrap = quality

    @api.multi
    def _get_approved_qty(self):
	for rec in self:
		records=self.env['stock.pack.operation'].search([('picking_id.origin','=',rec.name), ('picking_id.state','=','done'),('picking_id.picking_type_id.n_quality_ck','=',True)])
		qty=0.0
		for line in records:
			qty += line.qty_done
		rec.n_approved_qty = qty

    @api.multi
    def _get_qty_pcs(self):
    	for rec in self:
    	   if rec.product_uom.name == 'Kg':
    		rec.quality_pcs = rec.product_id.weight *rec.product_qty 
    
    @api.multi
    @api.depends('routing_id')
    def compute_routing(self):
        if self.routing_id:
            self.route_id=self.routing_id.id
    @api.multi
    @api.depends('workcenter_lines.date_planned','workcenter_lines.date_planned_end')
    def _get_completion_date(self):
    	for rec in self:
    		seq=0 
    		date=''
    		for line in rec.workcenter_lines:
    			if seq < line.sequence:
    				date = line.date_planned_end
    		rec.n_request_date = date
    
    @api.onchange('location_dest_id')
    def location_dest_onchange(self):
    	for record in self:
    		if record.location_dest_id.quality_ck_loc and not record.product_id.check_quality:
    			raise UserError("Product is not under quality check control.")
    			
    routing_process_ids=fields.One2many('mrp.rounting.process','production_id',
                            string='Routing Process') 
    production_reqst_id=fields.Many2one('production.request.detail')
    sale_id=fields.Many2one('sale.order' , string="Sale Order")
    route_id=fields.Many2one('mrp.routing' , string="Routing",compute='compute_routing')
    n_client_date =fields.Datetime('Requested Completion Date',help='Requested Completion Date')
#    n_request_date=fields.Datetime('Expected Completion Date',help='Expected Completion Date',store="Ture",compute="_get_completion_date")
    n_request_date=fields.Datetime('Expected Completion Date',help='Expected Completion Date')
    
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name")
    production_rqst_date=fields.Date('Puchase Date')
    half_purchase=fields.Boolean('Half Purchase')
    purchase_order_ids=fields.One2many('purchase.order', 'production_id', string="Purchase Order" , related='requisition_id.purchase_ids')
    requisition_id=fields.Many2one('purchase.requisition', string='Tender Number')
#CH_N073>>>
    n_purchase_date = fields.Date('PC Date', help='Purchase Completion Date')
    n_purchase_bool = fields.Boolean('Half Purchase')
    n_po =fields.Many2one('purchase.order' ,string="PO order")
    n_request_qty = fields.Float('Quantity Requested',help='Quantity Requested by Sale Support',related='request_line.n_order_qty')
    n_produce_qty = fields.Float('Quantity Transferred',help='Quantity Produced from Manufacture Order',compute='_n_get_produced_qty')
    n_produce_qty_now = fields.Float('Quantity Produced',help='Quantity Produced from Manufacture Order',compute='_n_get_produced_qty_now')
    produce_uom_id=fields.Many2one('product.uom', compute='_n_get_produced_qty')
    n_note = fields.Text('Instruction In PR',help='Instruction Given by Sale Support for Manufacture of this product',related='request_line.n_Note')
    n_approved_qty = fields.Float('Quantity Approved',help='Quantity Approved by Quality Check',compute='_get_approved_qty')

    mo_scrap = fields.Float('Mo Scrap Quantity',compute='_get_scrap_qty')
    quality_scrap = fields.Float('Quality Check Scraped',compute='_get_scrap_qty')
    uploaded_documents = fields.Many2many('ir.attachment','mrp_attachment_rel','mrp_doc','id','Scrap reason Documents')
    quality_pcs = fields.Float('Appx Qty in Pcs',compute='_get_qty_pcs')
    raw_available=fields.Boolean(default=False)
    mrp_sec_qty = fields.Float('Secondary Quantity', compute='Secondary_uom')
    mrp_sec_uom = fields.Many2one('product.uom', 'Secondary Unit',compute='Secondary_uom')
    mrp_third_qty = fields.Float('Third Quantity', compute='third_uom')
    mrp_third_uom = fields.Many2one('product.uom', 'Third Unit', compute='third_uom')
    mrp_third_qty_sheet = fields.Float('Third Quantity', compute='third_uom')
    mrp_third_uom_sheet= fields.Many2one('product.uom', 'Third Unit', compute='third_uom')
    order_produce_ids=fields.One2many('mrp.order.machine.produce', 'production_id', string='Product In Operations')
    order_pause_ids=fields.One2many('mrp.order.machine.pause', 'production_id', string='Pause Operations')
    workorder_count=fields.Integer("Work Orders Count", compute='count_orders')
    
    partner_id=fields.Many2one('res.partner', 'Customer Name')
    batch_id=fields.Many2one('mrp.order.batch.number','Batch Number')
    lot_ids=fields.One2many('stock.production.lot', 'production_id',string='Lot Details')
    product_lines= fields.One2many('mrp.production.product.line', 'production_id', 'Scheduled goods', readonly=False)
    parent_id=fields.Many2one('mrp.production','Parent Manufactruing No.')
    #sub_production_ids=fields.One2many('mrp.production','parent_id',string='Sub MO Details')
    #requisition_ids=fields.One2many('purchase.requisition','m_production_id',string='PRQ Details')
    date_planned = fields.Datetime('Schedule Starting Date', states={'draft': [('readonly', False)]}, required=False, copy=True,default='') #default='',compute='dateplanned')
    hold_order=fields.Selection([('active','Active'),('hold','Hold')],default='active', string='Order Status')
    total_shfit_required=fields.Float('Total Shift Required', compute='shiftcal')
    total_shfit_completed=fields.Float('Total Shift Completed',compute='shiftcal')
    planned_status=fields.Selection([('unplanned','Unplanned'),('partial','Partial planned'),('fully','Fully Planned'),
                               ('hold','Hold')], default='unplanned', string='planned Status', compute='plannedstatus')
    product_cat_type=fields.Selection([('all','Both'),('film','Films and Bags'),('injection','Injection')],string='Product Category', compute='cate_type')
    
    @api.multi
    def check_date_planned(self,date_planned):
        for record in self:
            if date_planned:
#                mo_name=self.env['stock.move'].search([('origin','ilike',record.name)])
                rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',record.id)])
                print "rm_idsrm_idsrm_ids",rm_ids.state
#                print "mo_namemo_name",mo_name
#                if mo_name:
#                    for each_mo in mo_name:
#                        each_mo.write({'date_expected':record.date_planned})
                if rm_ids:
                    for each in rm_ids:
                        pick_ids=self.env['stock.picking'].search([('material_request_id','=',each.id),('state','!=','done')])
                        if pick_ids:
                            for each_pick in pick_ids:
                                each_pick.write({'min_date':date_planned})
                        if each.state=='draft':
                            each.write({'request_date':date_planned})


    @api.multi
    def cancel_mrp(self):
	mo_form = self.env.ref('gt_order_mgnt.n_production_request_cancel_form', False)
        if mo_form:
            return {
                    'name':'Cancel Manufauring order with reason',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'production.cancel',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
             }
	
        return True
    @api.multi
    @api.depends('product_id')
    def cate_type(self):
        for  record in self:
             if record.product_id.categ_id.cat_type: 
                record.product_cat_type=record.product_id.categ_id.cat_type
    
    @api.multi
    @api.depends('workcenter_lines.shift_required', 'workcenter_lines.shift_produced')
    def shiftcal(self):
        for record in self:
            if record.workcenter_lines:
               record.total_shfit_required=sum(line.shift_required for line in record.workcenter_lines)
               record.total_shfit_completed=sum(com.shift_produced for com in record.workcenter_lines)
    
    @api.multi
    @api.depends('workcenter_lines')
    def plannedstatus(self):
        for record in self:
            count=count1=0
            if record.workcenter_lines:
               for line in record.workcenter_lines:
                    if line.date_planned:
                       count +=1
                    else:
                       count1 +=1
               if count < len(record.workcenter_lines):
                  record.planned_status='partial'
               if count == len(record.workcenter_lines):
                  record.planned_status='fully'
               if count1 == len(record.workcenter_lines):
                  record.planned_status='unplanned'
               if record.hold_order =='hold':
                  record.planned_status='hold'
    
    
    @api.multi
    def mrp_hold(self):
        context = self._context.copy()
        context.update({'default_production_id':self.id})
        hold_form = self.env.ref('gt_order_mgnt.mrp_production_hold_form', False)
        if hold_form:
                return {
                    'name':'Hold Manufaturing order with Work Orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.production.hold',
                    'views': [(hold_form.id, 'form')],
                    'view_id': hold_form.id,
                    'target': 'new',
                    'context': context,
             } 
    '''@api.multi
    def rm_schedule_request(self):
	context = self._context.copy()
        lst=[]
        qty=0.0 
        if self.delivery_ids  and self._context.get('raw'):
           for line in self.delivery_ids:
               if line.production_id and not line.purchase_id and not line.backorder_id:
                  qty +=line.mo_qty
        else:
           qty=0.0
        print"+++++++++++++++++++++=",qty
        for line in self.product_lines:
            if line.rm_type == 'stock' and self._context.get('raw'): 
               lst.append((0,0,{'product_id':line.product_id.id, 'uom_id':line.product_uom.id, 
                                'qty':(line.required_qty ), 
                                'production_id':self.id}))
            if line.rm_type == 'po' and self._context.get('po'):
               lst.append((0,0,{'product_id':line.product_id.id, 'uom_id':line.product_uom.id, 
                                'qty':(line.required_qty), 'production_id':self.id}))
            if line.rm_type == 'mo' and self._context.get('mo'):
               
               lst.append((0,0,{'product_id':line.product_id.id, 'uom_id':line.product_uom.id, 
                                'qty':(line.required_qty), 'production_id':self.id}))
	context.update({'default_production_id':self.id, 
                        'default_product_qty':(self.product_qty - qty if qty  else self.product_qty),
                         'default_rm_schedule_line_ids':lst ,'default_raw':True, 
                         'default_po':True, 'default_mo':True})
        mo_form = self.env.ref('gt_order_mgnt.mrp_production_rm_schedule_form', False)
        if mo_form:
                return {
                    'name':'Raw Material Schedule Request',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.production.rm.schedule',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
             }'''  

    @api.multi
    def open_scheduleworkorder(self):
        for line in self:
            order_cal_tree = self.env.ref('stock_merge_picking.view_mrp_workorder_calendar_inherite', False)
            order_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
            if order_cal_tree:
                return {
                    'name':'Schedule Work orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'calendar,',
                    'res_model': 'mrp.production.workcenter.line',
                    'views': [(order_cal_tree.id, 'calendar'),(order_form.id, 'form')],
                    'view_id': order_cal_tree.id, 
                    'target': 'current',
                    'domain':[('production_id','=',line.id)],
                    #'context':context
                    #'filter_domain':[('production_id','=',line.id)]
                }
        return True  

    @api.multi
    @api.depends('workcenter_lines')
    def count_orders(self):
        for record in self:
            record.workorder_count=len(record.workcenter_lines)
            
    @api.multi
    def open_workorders(self):
        for line in self:
            order_tree = self.env.ref('mrp_operations.mrp_production_workcenter_tree_view_inherit', False)
            order_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
            if order_tree:
                return {
                    'name':'Work Orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,',
                    'res_model': 'mrp.production.workcenter.line',
                    'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
                    'view_id': order_tree.id,
                    'target': 'current',
                    'domain':[('production_id','=',self.id)],
                }
        return True

    @api.multi
    @api.depends('product_id','product_qty','product_uom')
    def Secondary_uom(self):
        for record in self:
          if record.product_id and record.product_qty and record.product_uom:
            pcs=self.env['product.uom'].search([('name','=','Pcs')], limit=1)
            Kg=self.env['product.uom'].search([('name','=','Kg')], limit=1)
            if record.product_uom.name == 'Kg' and record.product_qty >0 and record.product_id.weight :
               record.mrp_sec_qty=math.ceil(record.product_qty / record.product_id.weight)
               record.mrp_sec_uom =pcs.id
            if record.product_uom.name == 'Pcs' and record.product_qty > 0 and record.product_id.weight:
               record.mrp_sec_qty=math.ceil(record.product_qty * record.product_id.weight)
               record.mrp_sec_uom =Kg.id
    @api.multi
    @api.depends('product_id','product_qty','product_uom','product_id.discription_line')
    def third_uom(self):
        for record in self:
            cal=0.0
            m=self.env['product.uom'].search([('name','=','m')], limit=1)
            if record.product_id and record.product_qty and record.product_uom and record.product_id.discription_line:
                   record.mrp_third_uom=m.id
                   record.mrp_third_uom_sheet=m.id
                   ln=wd=lt=rt=tp=bm=cal=0.0
                   for des in record.product_id.discription_line:
                       if des.attribute.name == 'Length':
                          ln =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Width':
                          wd =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Left gusset':
                          lt =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Right gusset':
                          rt =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Top Fold':
                          tp =float(des.value) if (des.value).isdigit() else 0.0
                       if des.attribute.name == 'Bottom gusset':
                          bm =float(des.value)
                   cal=ln+tp+bm
                   cal1=wd+lt+rt
                   if record.product_uom.name == 'Kg' and record.product_qty >0 and record.product_id.discription_line:
                      
                      record.mrp_third_qty =math.ceil(record.mrp_sec_qty * (cal)) * 0.01
                      record.mrp_third_qty_sheet =math.ceil (record.mrp_sec_qty * (cal1)) * 0.01
                   if record.product_uom.name == 'Pcs' and record.product_qty >0 and record.product_id.discription_line:
                      record.mrp_third_qty = math.ceil(record.product_qty * (cal)) * 0.01
                      record.mrp_third_qty_sheet = math.ceil(record.product_qty * (cal1)) * 0.01
                      

    @api.multi
    def get_mrp_calendar(self):
    	for rec in self:
    		value = dict(self.fields_get(allfields=['state'])['state']['selection'])[rec.state]
    		search_id=self.env['api.mrp.calendar'].search([('name','=',str(value))],limit=1)
    		if not search_id:
    			value_id=self.env['api.calendar.event'].search([('name','=','Manufacturing State')],limit=1)
    			if not value_id:
    				value_id = self.env['api.calendar.event'].create({'name':str('Manufacturing State')})
			search_id = self.env['api.mrp.calendar'].create({'name':str(value),'event_type':value_id.id})
    		rec.calendar_state=search_id.id
    
    calendar_state = fields.Many2one('api.mrp.calendar',string='Status',compute="get_mrp_calendar")
    
    @api.multi
    def print_order(self):
        return self.env['report'].get_action(self, 'mrp.report_mrporder')
        
    @api.multi
    def approve_prpurchase_date(self):
	self.n_purchase_bool =False
        self.n_purchase_date=self.n_po.n_request_date
	self.n_po.n_request_date_bool1=False
	self.n_po.n_request_date_bool=True
        self.n_po.message_post(body='<span style="color:green;font-size:14px;">Date Approved By MRP -:</span>\n '+
                                        'New Date:' +str(self.n_po.n_request_date))

    @api.multi
    def open_scrapped_history(self):
        for line in self:
            move_tree = self.env.ref('stock.view_move_tree', False)
            move_form = self.env.ref('stock.view_move_form', False)
            if move_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'stock.move',
                    'views': [(move_tree.id, 'tree'), (move_form.id, 'form')],
                    'view_id': move_tree.id,
                    'target': 'new',
                    'domain':[('origin','=',line.name), ('state','in',('done','assigned')),('location_dest_id.name','=','Scrap Location')],
                }

        return True 

  #CH_N050 >>
    n_request_date_bool = fields.Boolean(string="bool",default=False) 	
    n_request_date_bool1 = fields.Boolean(string="bool",default=False)
    n_request_bool= fields.Boolean(string="bool",default=False)
	
 #CH_N051>>>
    sale_line = fields.Many2one('sale.order.line', 'Sale Line')
    request_line = fields.Many2one('n.manufacturing.request', 'Request Line')
    n_packaging = fields.Many2one('product.packaging' ,string="Package Type")

    @api.multi
    def change_qty(self):
        order_form = self.env.ref('gt_order_mgnt.mrp_quantity_change_view', False)
        context = self._context.copy()
        context.update({'default_n_mo':self.id,'default_n_prev_qty':self.product_qty})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.quantity.change',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    	'context':context,}

    @api.model
    def create(self, vals):
	mo_id = super(MrpProduction, self).create(vals)
        product = self.env['product.product'].browse(mo_id.product_id.id)
        if product.categ_id.cat_type=='film':
            dest = self.env['stock.location'].search([('name','ilike','Input'),('location_id.name', '=', 'SH'),('usage','=', 'internal')])
        if product.categ_id.cat_type=='injection':
            dest = self.env['stock.location'].search([('name','ilike','Input'),('location_id.name', '=', 'DXB'),('usage','=', 'internal')])
            
        else:
            dest = self.env['stock.location'].search([('name','ilike','Input'),('location_id.name', '=', 'SH'),('usage','=', 'internal')])
        mo_id.location_dest_id=dest.id
        if mo_id.name:
           mo_id.name ='%s, %s'%(mo_id.name, mo_id.product_id.name)
	if mo_id.sale_line:
		status_list=[]
		search_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1) ## add status
		if search_id:
				status_list.append((4,search_id.id))
		new_id=self.env['sale.order.line.status'].search([('n_string','=','production_request')],limit=1)	#remove status
		if new_id:
			status_list.append((3,new_id.id))
		self.env['sale.order.line'].sudo().browse(mo_id.sale_line.id).write({'mo_id': mo_id.id,'n_status_rel':status_list})
	if mo_id.request_line:
		self.env['n.manufacturing.request'].sudo().browse(mo_id.request_line.id).write({'n_state':'mo_created','n_mo_number':mo_id.id})
	return mo_id

    @api.multi
    def action_produce(self, production_qty, production_mode, wiz=False):
	production_id = self._context.get('active_id') if self._context.get('active_id') else self.id
	for rec in self:
		r_qty=0.0
		p_qty = production_qty
		for p_produce in rec.move_created_ids2:
			if p_produce.state == 'done':
				p_qty += p_produce.product_uom_qty
                                
		if rec.sale_line:
		#CH_N078 >>> add code to send mail on production complete >>>
			temp_id = self.env.ref('gt_order_mgnt.email_template_MRP_complete')
			if temp_id:
				recipient_partners=str(self.sale_id.user_id.login)
				group = self.env['res.groups'].search([('name', '=', 'Sales Support Email')])
				for recipient in group.users:
	    				recipient_partners += ","+str(recipient.login)

				user_obj = self.env['res.users'].browse(self.env.uid)
				base_url = self.env['ir.config_parameter'].get_param('web.base.url')
				query = {'db': self._cr.dbname}
				fragment = {
				    'model': 'sale.order.line',
				    'view_type': 'form',
				    'id': self.sale_line.id,
				}
				url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))

				body_html = """<div>
	    <p> <strong>Production Update </strong></p><br/>
	    <p>Dear User,<br/>
            The production is updated as per below details:<br/>
            		<b>Sale Order No-:</b>  %s <br/>
                        <b>Product Name-:</b>  %s <br/>
                        <b>Produced Qty:</b>  %s <br/>
                        <b>Produced Date:</b>%s <br/>
                        <b>Moved to Quality Checking / Warehouse<br/>
                        <b>Production Status:</b> %s <br/>
                        <b>Requested Quantity:</b>  %s  <br/>
                        <b>Total Produced Qty Till Now:</b>  %s </p>
	    </div>"""%(self.sale_id.name or '',self.sale_line.product_id.name or '' +self.sale_line.product_id.default_code or '',str(production_qty),str(date.today()),str(rec.state),str(rec.n_request_qty),str(p_qty))

				body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order.line',self.sale_line.id, context=self._context)
				
				temp_id.write({'body_html': body_html, 'email_to':recipient_partners,'email_from': user_obj.partner_id.email})
				temp_id.send_mail(self.sale_line.id)
		#CH_N078 <<<<<<<<<<<<
		
		if rec.request_line:
			if rec.product_qty <= p_qty:
				n_status_rel=[]
				self.env['n.manufacturing.request'].sudo().browse(rec.request_line.id).write({'n_state':'done'})
				new_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1)  #remove status
				if new_id:
					n_status_rel.append([(3,new_id.id)])
				new_date_id=self.env['sale.order.line.status'].search([('n_string','=','date_request')],limit=1)  #remove status
				if new_date_id:
					n_status_rel.append([(4,new_date_id.id)])
				self.env['sale.order.line'].sudo().browse(rec.sale_line.id).write({'n_status_rel':n_status_rel})
				
				 
	return super(MrpProduction, self).action_produce(production_id, production_qty, production_mode, wiz)

    @api.model
    def default_get(self,fields):
        rec = super(MrpProduction, self).default_get(fields)
	obj = self.env['n.manufacturing.request'].browse(self._context.get('request_id'))
	if obj:
		rec.update({'request_line' : obj.id})
		if obj.n_product_id:
			rec.update({'product_id' : obj.n_product_id.id,'product_uom':obj.n_unit.id})
		if obj.n_sale_line:
			rec.update({'sale_id' :obj.n_sale_line.id,'partner_id':obj.n_sale_line.partner_id.id, 
                       'sale_name':obj.n_sale_line.name,'sale_ref':obj.n_sale_line.user_id.id})
		if obj.n_order_qty:
			rec.update({'product_qty' : obj.n_order_qty,'n_request_qty':obj.n_order_qty})
		if obj.n_delivery_date:
			rec.update({'n_client_date':obj.n_delivery_date})
		if obj.n_sale_order_line:
			rec.update({'sale_line' : obj.n_sale_order_line.id})
		if obj.n_packaging:
			rec.update({'n_packaging' : obj.n_packaging.id})
	return rec
    
    @api.v7
    def product_id_change(self, cr, uid, ids, product_id, product_qty=0, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        
        if not product_id:
            return {'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False,
                'product_tmpl_id': False
            }}
        result = super(MrpProduction,self).product_id_change(cr, uid, ids, product_id, product_qty, context)
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        if product.categ_id.cat_type=='film':
            dest = self.pool.get('stock.location').search(cr, uid, [('name','ilike','Input'),('location_id.name', '=', 'SH'),('usage','=', 'internal')], context=context)
        if product.categ_id.cat_type=='injection':
            dest = self.pool.get('stock.location').search(cr, uid, [('name','ilike','Input'),('location_id.name', '=', 'DXB'),('usage','=', 'internal')], context=context)
            
        else:
            dest = self.pool.get('stock.location').search(cr, uid, [('name','ilike','Input'),('location_id.name', '=', 'SH'),('usage','=', 'internal')], context=context)
        print "destdest------------",dest
        result['value'].update({'location_dest_id':self.pool.get('stock.location').browse(cr,uid,dest[0]).id})
        for res in product.packaging_ids:
		if res.pkgtype == 'primary':
			result['value'].update({'n_packaging':res.id})
        print "result---------------",result
        result['value'].update({'bom_id':False,'routing_id':False})
        return result
        
                
#                override the confirm production button on mrp
    @api.multi
    def action_confirm(self):
	for rec in self:
                if not rec.bom_id:
                   raise UserError("BoM for the Product is not defined!!")
#                move_ids,location_id,location_dest_id=[],[],[]
                if not rec.product_id.product_tmpl_id.initial_weight:
                   raise UserError("Please Fill the Product Initial Weight")
                if not rec.n_request_date:
                   raise UserError("Please Fill the Completion Date")
                if not rec.date_planned:
                   raise UserError("Please Fill the Schedule Date")
		if not rec.n_request_date and rec.request_line and rec.request_line.request_type != 'stock' and not rec.contract_id:
			raise UserError("Please Update Manufacturing Complete Date")
			
		if rec.location_dest_id.quality_ck_loc and not rec.product_id.check_quality:
    			raise UserError("Product is not under quality check control. Please Select different Finished Location")
                if rec.request_line:
                    rec.request_line.n_state='scheduled'
                res=super(MrpProduction,self).action_confirm()
                print "re--------------------------------",res
#                for each_move in rec.move_created_ids:
#                    location_id.append(each_move.location_id.id)
#                    location_dest_id.append(each_move.location_dest_id.id)
                for move_line in rec.move_created_ids:
                    if rec.n_request_date:
                        move_line.date_expected=rec.n_request_date
                product_lst=[]
                if rec.product_id.product_tmpl_id.discription_line:
                   for line in rec.product_id.product_tmpl_id.discription_line:
                       product_lst.append((0,0,{'attribute':line.attribute.id,
                       'value':line.value,'unit':line.unit.id}))
                             
                workorders=self.env['mrp.production.workcenter.line'].search([('production_id','=',rec.id)], order='sequence desc')
                next_id=False
                for orders in workorders:
                	orders.next_order_id=next_id
                	orders.n_packaging=orders.production_id.n_packaging.id if orders.production_id.n_packaging else False
                	next_id=orders.id
                if workorders[0]:
                   workorders[0].order_last=True
                   workorders[0].each_batch_qty=workorders[0].production_id.n_packaging.qty if workorders[0].production_id.n_packaging else 0.0
                   workorders[0].req_product_qty=math.ceil((workorders[0].production_id.product_qty/workorders[0].production_id.n_packaging.qty))  if workorders[0].production_id.n_packaging else 0.0

                order_op=self.env['mrp.production.workcenter.line'].search([('production_id','=',rec.id)])
                if order_op:
                   kg=self.env["product.uom"].search([('name','=','Kg')], limit=1, order='id')[0]
                   rm_append=[]
                   for bom in  rec.bom_id.bom_line_ids:
                       rm_append.append((bom.id))
                   for bom_ln in rec.bom_id.bom_packging_line:
                       rm_append.append((bom_ln.id))
                   for order in order_op:
                       uom=0
                       qty=0.0
                       if order.workcenter_id.product_uom_id.name =='Pcs' and rec.product_uom.name == 'Pcs':
                           qty=rec.product_qty
                           uom=rec.product_uom.id
                       if order.workcenter_id.product_uom_id.name =='Pcs' and rec.product_uom.name == 'Kg':
                          qty=rec.mrp_sec_qty
                          uom=rec.mrp_sec_uom.id
                       if order.workcenter_id.product_uom_id.name =='Kg' and rec.product_uom.name == 'Pcs':
                          qty=rec.mrp_sec_qty  
                          uom=rec.mrp_sec_uom.id
                       if order.workcenter_id.product_uom_id.name =='Kg' and rec.product_uom.name == 'Kg':
                          qty=rec.product_qty 
                          uom=rec.product_uom.id
                       if order.workcenter_id.product_uom_id.name =='m' and order.process_id.process_type == 'ptube':
                          qty=rec.mrp_third_qty
                          uom=rec.mrp_third_uom.id
                       if order.workcenter_id.product_uom_id.name =='m' and order.process_id.process_type == 'psheet':
                          qty=rec.mrp_third_qty_sheet
                          uom=rec.mrp_third_uom_sheet.id

                       order.write({'wk_required_qty':math.ceil(qty),'wk_required_uom':uom})
                       
                       if order.wk_required_qty and order.process_id.process_type == 'raw':
                          print"djfgdfgdfgfd"
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(order.wk_required_qty/rec.product_id.weight)
                               if bom.product_id.product_material_type.string in ('raw','grinding') and bom.workcenter_id.process_id.process_type == 'raw':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(pcs_qty * bom.product_qty), 'production_id':rec.id,
                                    'next_order_id':order.next_order_id.id,
                                    'original_qty':(pcs_qty * bom.product_qty)}))
                          order.raw_materials_id=lst
                          
                       if order.process_id.process_type == 'cutting':
                          order.product_sepcification_ids=product_lst
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(rec.product_qty/rec.product_id.weight)
                               if bom.product_id and bom.workcenter_id.process_id.process_type == 'cutting':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(pcs_qty * bom.product_qty),'production_id':rec.id,
                                    'next_order_id':order.id,
                                   'original_qty':(pcs_qty * bom.product_qty)}))
                          order.raw_materials_id=lst
                          if rec.n_packaging.unit_id.name =='Kg':
                             qty=order.qty
                          else:
                             qty=order.wk_required_qty
                          order.req_product_qty=math.ceil((qty/rec.n_packaging.qty))  if rec.n_packaging else 0.0
                          order.each_batch_qty=rec.n_packaging.qty
                         
                          order.batch_unit=rec.n_packaging.uom_id.name
                          order.req_uom_id=rec.n_packaging.unit_id.id
                          '''if order.req_uom_id.name == 'Kg':
                              pack_qty=round(((rec.n_packaging.qty) / order.product.weight), 2) if rec.n_packaging else 0.0  
                              order.cutting_pac_qty=str(pack_qty)+str('Pcs')
                          else:
                               pack_qty=round(((rec.n_packaging.qty) * order.product.weight), 2)  if rec.n_packaging else 0.0
                               order.cutting_pac_qty=str(pack_qty)+str('Kg')'''
                         
                       if order.process_id.process_type == 'film':
                          order.product_sepcification_ids=product_lst
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(rec.product_qty/rec.product_id.weight)
                               if bom.product_id and bom.workcenter_id.process_id.process_type == 'film':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(pcs_qty * bom.product_qty),'production_id':rec.id, 
                                    'next_order_id':order.id,
                                    'original_qty':(pcs_qty * bom.product_qty)}))
                          order.raw_materials_id=lst
                          order.batch_unit='Rolls'
                          order.req_uom_id=kg.id
                       if order.process_id.process_type == 'psheet':
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(rec.product_qty/rec.product_id.weight)
                               if bom.product_id and bom.workcenter_id.process_id.process_type == 'psheet':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(pcs_qty * bom.product_qty),'production_id':rec.id,
                                    'next_order_id':order.id,
                                    'original_qty':(pcs_qty * bom.product_qty)}))
                          order.raw_materials_id=lst
                          order.batch_unit='Rolls'
                          order.req_uom_id=kg.id
                          if not order.product.discription_line:
                             raise UserError(_('Please Fill  product Specification.')) 
                             
                       if order.process_id.process_type == 'injection':
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(rec.product_qty/rec.product_id.weight)
                               rm_ids=self.env['mrp.production.product.line'].search(
                               				[('product_id','=',bom.product_id.id),
                               				 ('production_id','=',rec.id)])
                               if rm_ids:
                                  for each_rm in rm_ids:
                                     rm_qty=each_rm.product_qty
                                     if bom.product_id and bom.workcenter_id.process_id.process_type == 'injection':
                                        lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                          'qty':(rm_qty),'production_id':rec.id,
                                          'next_order_id':order.id,
                                          'original_qty':(rm_qty)})) 
                          order.raw_materials_id=lst      
                          
                       if order.process_id.process_type == 'other':
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               qty=self.env['mrp.production.product.line'].search([('production_id','=',rec.id),('product_id','=',bom.product_id.id)],limit=1)
                               if bom.product_id and bom.workcenter_id.process_id.process_type == 'other':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(qty.product_qty),'production_id':rec.id,
                                    'next_order_id':order.id,
                                    'original_qty':qty.product_qty})) 
                          order.raw_materials_id=lst 
                       if order.process_id.process_type == 'ptube':
                          lst=[]
                          for bom in self.env['mrp.bom.line'].browse(rm_append):
                               pcs_qty=(rec.product_qty/rec.product_id.weight)
                               if bom.product_id and bom.workcenter_id.process_id.process_type == 'ptube':
                                  lst.append((0,0,{'product_id':bom.product_id.id, 'uom_id':bom.product_uom.id,
                                    'qty':(pcs_qty * bom.product_qty), 'production_id':rec.id, 
                                    'next_order_id':order.id,
                                    'original_qty':(pcs_qty * bom.product_qty)}))
                          order.raw_materials_id=lst
                          order.batch_unit='Rolls'
                          order.req_uom_id=kg.id
                         
                          if not order.product.discription_line:
                             raise UserError(_('Please Fill  product Specification.')) 
	return 0


    product_qty = fields.Float('Quantity Scheduled', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    '''@api.multi
    def action_schedule_route(self):
        context = self._context.copy()
        for record in self:
            ls=[]
            for line in record.routing_id.workcenter_lines:
                for process in line.workcenter_id.machine_type_ids:
                    machine=self.env['machinery'].search([('machine_type_ids','=',process.id)])
                    for machine_name in machine:
                        order=self.env['mrp.production.workcenter.line'].search([('machine','=',machine_name.id),('state','in',('draft','startworking','pause')), ('workcenter_id','=',record.routing_id.workcenter_lines[0].workcenter_id.id)])
                        order1=self.env['mrp.production.workcenter.line'].search([('machine','=',machine_name.id),('state','in',('draft','startworking','pause')), ('workcenter_id','=',record.routing_id.workcenter_lines[0].workcenter_id.id)])
                        for rec in order:
                            for rec1 in order1:
                                if rec.date_planned_end > rec1.date_planned_end:
                                   ls.append((0,0,{'machine':rec.machine.id,'order_id':rec.id,
                                    'date_planned_end':rec.date_planned_end }))
            #print"====",ls
            #record.machine_schedule_ids=ls
        #order=self.env['mrp.production.workcenter.line'].search([('machine','=',self.machine.id),('state','in',('draft','startworking','pause')), ('id','!=', self.id)])
        #lst=[]
        #for rec in order:
            #lst.append((0,0,{'name':rec.name, 'state':rec.state, 'date_planned':rec.date_planned,
                          #  'production_id':rec.production_id.id,'product':rec.product.id,'qty':rec.qty,
                           # 'uom':rec.uom.id,'workcenter_id':rec.workcenter_id.id,'cycle':rec.cycle,
                          #  'hour':rec.hour,'machine':rec.machine.id,'date_planned_end':rec.date_planned_end}))
            
        context.update({'default_production_id':self.id,
          'default_workcenter_id':record.routing_id.workcenter_lines[0].workcenter_id.id,
           'default_machine_schedule_ids':ls})
        mo_form = self.env.ref('gt_order_mgnt.mrp_work_order_schedule_form', False)
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.production.workcenter.line.schedule',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
             }'''
#CH_N051<<
    @api.multi
    def schedule_date(self):
	order_form = self.env.ref('gt_order_mgnt.manufacturing_date_history_form_view', False)
	context = self._context.copy()
        print "self.n_request_dateself.n_request_date",self.n_request_date
	context.update({'default_n_line_id':self.sale_line.id,'default_n_prevoiusdate':self.n_request_date,
                        'mo_state':True if self.state in ('drfat' 'confirmed') else False,
                        'default_mo_schedule_date':self.date_planned,
			'default_n_prevoiusdate1':self.n_request_date,'default_n_status':'draft','default_n_mo':self.id})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.complete.date',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,}

class n_manufacturing_request(models.Model):
    _name = 'n.manufacturing.request'
    #_inherit = ['mail.thread','ir.needaction_mixin']
    _order = "id desc"
    
    #@api.model
    #def _needaction_domain_get(self):
    #	return [('n_state', '=', 'draft')]

    @api.model
    def create(self, vals):
    	category=self.env['product.category'].search([('id','=',vals.get('n_category'))])
#    	if category.cat_type == 'film':
    	if category.cat_type == 'film':
        	vals['name'] = self.env['ir.sequence'].next_by_code('film.production.request') or 'New'
	elif category.cat_type == 'injection':
		vals['name'] = self.env['ir.sequence'].next_by_code('injection.production.request') or 'New'
	else:
		raise UserError('Please Select proper Category')
		
        result = super(n_manufacturing_request, self).create(vals)
#        if result.n_sale_order_line and result.n_order_qty > result.n_sale_order_line.pending_qty:
#		raise UserError(_('Your order more than pending quantity')
#        if not vals.get('n_sale_line',False):
#            result.with_context(not_from_dashboard=True).n_save()
        return result

    @api.multi
    def get_desc(self):
	for line in self:
	    if line.n_sale_order_line: 
		    line.n_product_desc = line.n_sale_order_line.name 
	    else:
	    	    line.n_product_desc = line.n_product_id.description_mrp
	return True

    name=fields.Char('Production Request No.')
    n_sale_line = fields.Many2one('sale.order', 'Sale Line')
#    n_partner_id = fields.Many2one(related='n_sale_line.partner_id', string="Customer")
    n_partner_id = fields.Many2one("res.partner",string="Customer")
    n_sale_order_line = fields.Many2one('sale.order.line', 'Sale Order Line')
    n_delivery_date = fields.Datetime('Requested Date')
    n_order_qty = fields.Float('Order Qty',track_visibility='always')
    n_product_id = fields.Many2one("product.product", "Product",track_visibility='always')
    n_default_code = fields.Char(related='n_product_id.default_code', string="Product Number",track_visibility='always')
    n_category = fields.Many2one("product.category" ,string="Product category",
							domain=[('cat_type','in',('film','injection'))])
							
    n_state = fields.Selection([ ('new','New'),('draft', 'Draft'),
#				('purchase', 'Purchase'),
                                ('mo_created', 'MO created'),
				('scheduled', 'Scheduled'),                                
				('manufacture', 'In-Production'),				
				('done', 'Done'),
				('cancel', 'Cancelled'), ], 'Status', readonly=True, 
				copy=False, default='new',track_visibility='always',
			help="'New': Production request created but not sent to production\n	\
			     'Draft': Production request sent to production\n \
                             'MO Created': Manufacturing order created but production not confirmed\n \
                             'Scheduled': MO created, scheduled and confirmed for raw material requests\n \
                             'In-Production': Production started for this request\n")
    #CH_N038 add >>	
    n_Note = fields.Text(string="Note",track_visibility='always')
    n_product_desc = fields.Char(compute =get_desc, string="Product Description",track_visibility='always')
    n_mo_number = fields.Many2one("mrp.production","MO Number")
    date_planned = fields.Datetime(related='n_mo_number.date_planned') #default='',compute='dateplanned')
    n_request_date = fields.Datetime(related='n_mo_number.n_request_date',string="Expected Completion Date") #default='',compute='dateplanned')

    n_produce_qty = fields.Float(related='n_mo_number.n_produce_qty',string="Qty Transferred")
    n_produce_qty_now = fields.Float(related='n_mo_number.n_produce_qty_now',string="Qty Produced")
    n_po_number	= fields.Many2one("purchase.requisition","TE Number")

    #CH_N045 add>>
    n_exist_pr = fields.Boolean(string='Exist', default=False)
    new_date_bool = fields.Boolean(string='New Date Bool', default=False)
    reminder_sent = fields.Boolean(string='Reminder sent', default=False)
    reminder_mo_sent = fields.Boolean(string='Reminder MO sent', default=False)
    bom_reminder_visible = fields.Boolean(string='BoM reminder', compute='_compute_bom_reminder_visibility')
    mo_reminder_visible = fields.Boolean(string='Mo Create reminder', compute='_compute_mo_reminder_visibility')
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name")
    custmor_id=fields.Many2one('customer.product' ,string="Contract Name")
    con_pro_id=fields.Many2one('contract.product.line' ,string="Contract Name")
    n_packaging = fields.Many2one('product.packaging' ,string="Packaging")
    remain_bool=fields.Boolean('remain bool')
    remaining_contract_qty=fields.Float('Remaining Qty',track_visibility='always')
    
    #CH_N068>>
    n_unit =fields.Many2one('product.uom','Unit')
    check_bool=fields.Boolean('Check',default=False)
    cancel_reason=fields.Text('Reason For Cancel',track_visibility='always')
    
    request_type=fields.Selection([('stock','From Stock'),('sale','Sale Support'),
    				   ('raw','Raw Materail'),('contract','Contract')],string="Requested From",default='sale')
    
    transfer_ids = fields.Many2many('stock.move','production_request_move_rel',
    					'transfer_id','move_id' ,string="Transfers",copy=False)
    					
    batches_ids = fields.Many2many('mrp.order.batch.number','produciton_request_batch_rel',
    					'request_id','batch_id','Batch Number',copy=False)
    		
    #CH_N122 add code to show cancel records to sale support if check_bool is true then record is not visible 
    @api.multi	
    def check_cancel(self):
	self.check_bool= True
	return True

    @api.multi
    @api.onchange('n_order_qty')
    def check_remaining_qty(self):
        for record in self:
            if record.remaining_contract_qty:
               if record.n_order_qty > record.remaining_contract_qty:
                  record.remain_bool=True
               else:
                  record.remain_bool=False
    @api.multi
    @api.onchange('n_product_id')
    def check_product(self):
        for record in self:
            if record.n_product_id:
                record.n_unit=record.n_product_id.uom_id.id
                record.n_category=record.n_product_id.categ_id.id
                  
    @api.multi
    def contract_save(self):
        self.con_pro_id.production_id=self.id
        self.n_Note=self.n_Note
        self.request_type='contract'
        return True

    @api.multi
    def cancel_pr(self):
	if self.n_state == 'draft':
		mo_form = self.env.ref('gt_order_mgnt.n_production_request_cancel_form', False)
		return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'production.cancel',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'new',
             }
	else:
		 raise UserError(_('Your can not cancel This Production Request')) 
        return True

    @api.multi
    def n_save(self):
	#CH_N054  >>>>>>>>>>>>>
	status_list=[]
	
#	if self.n_order_qty > self.n_sale_order_line.pending_qty:
#		raise UserError(_('Your order more than pending quantity')) 
		
	self.n_state='draft'

	self.request_type='sale'
        self.n_partner_id=self.n_sale_line.partner_id.id
	search_id=self.env['sale.order.line.status'].search([('n_string','=','production_request')],limit=1) ## add status
	if search_id:
		status_list.append((4,search_id.id))
	new_id=self.env['sale.order.line.status'].search([('n_string','=','new')],limit=1)	#remove status
	if new_id:
		status_list.append((3,new_id.id))
	if self.n_sale_order_line:
		self.n_sale_order_line.n_status_rel = status_list
		self.n_sale_order_line.pending_qty -= self.n_order_qty
		self.n_packaging = self.n_sale_order_line.product_packaging.id if self.n_sale_order_line.product_packaging else self.env['product.packaging'].search([('product_tmpl_id','=',self.n_product_id.product_tmpl_id.id),('pkgtype','=','primary')],limit=1).id
	#CH_N054 <<<<<<<<<<<<<<
        user_obj = self.env['res.users'].browse(self.env.uid)
        temp_id = self.env.ref('gt_order_mgnt.email_template_producton_req_again')
        if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                          'model': 'n.manufacturing.request',
                          'view_type': 'form',
                          'id': self.id,
                         }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                print "urlurl",url
                text_link = _("""<a href="%s">%s</a> """) % (url,self.name)
                group,send_user_name=False,''
                recipient_partners=[]
                if self.n_category.cat_type=='film':
                        group = self.env['res.groups'].search([('name', 'in', ('Film manager','Get BoM Alert'))])
                elif self.n_category.cat_type=='injection':
                        group = self.env['res.groups'].search([('name', 'in', ('Injection manager','Get BoM Alert'))])
                print "groupgroupgroupgroupgroupgroup",group
                for groups in group:
                    for recipient in groups.users:
                        if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                             recipient_partners.append(recipient.login)
                             send_user_name=recipient.name
                if self.n_sale_order_line:
                    recipient_partners.append(self.n_sale_order_line.order_id.user_id.login)
                send_user = ",".join(recipient_partners)
                product_data = ''.join(['[',str(self.n_product_id.default_code if self.n_product_id.default_code else ''),']',self.n_product_id.name])
                bom_id=self.env['mrp.bom'].search([('product_id','=',self.n_product_id.id)])
                if not bom_id:
                    new_subject='API-ERP Production Alert:BoM required,New request %s received for %s'%(str(self.name),'['+self.n_product_id.default_code+']'+' '+self.n_product_id.name)
                else:
                    new_subject='API-ERP Production Alert:New request %s received for %s'%(str(self.name),'['+self.n_product_id.default_code+']'+' '+self.n_product_id.name)
                print "new_subjectnew_subject",new_subject
                if self.n_delivery_date:
                    n_date=datetime.strftime(datetime.strptime(self.n_delivery_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d')           
                else:
                    n_date=''
                if not self.n_Note:
                    note=''
                else:
                    note=self.n_Note
                body_html = """<div> 
                        <strong><p>Dear User,<br/>
                        <p>New production request is raised as per below details</strong></p><br/>

                                <p>Request Number : <b>%s</b> </p>
                                <p>Product:<b>%s</b> </p>
                                <p>Instructions from Sale Support:<b>%s</b> </p>
                                <p>Requested completion date: <b>%s</b> </p>
                                <p>Sales Order Number:<b>%s</b> </p>
                                <p>Customer Name:<b>%s</b> </p>
                                <p>Sales Person:<b>%s</b> </p>
                                <p>Quantity :<b>%s</b> \t%s </p>
                                <p>Packaging :<b>%s</b> </p>
                        </p>
                        </div>"""%(str(text_link),product_data,note,str(n_date),str(self.n_sale_order_line.order_id.name) if self.n_sale_order_line else '',str(self.n_sale_order_line.order_id.partner_id.name),str(self.n_sale_order_line.order_id.user_id.name) if self.n_sale_order_line else str(self.n_partner_id.name) if self.n_partner_id else '',str(self.n_order_qty),str(self.n_unit.name),str(self.n_packaging.name))
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',self.n_sale_line.id, context=self._context)
                print "body_htmlbody_htmlbody_html",body_html
                if bom_id:
                    body_html +="<table class='table' style='font-family:arial; text-align:left;'><tr><th>BoM Name </th></tr>" 
                    for line in bom_id:
                        #term_qry="select  date_planned from mrp_production_workcenter_line where id in (select DISTINCT order_id from workorder_raw_material where product_id ="+str(line.product_id.id)+ "and production_id =" +str(record.id) +") limit 1"
                            #self.env.cr.execute(term_qry)
                            #schedule_order=self.env.cr.fetchone()
                        body_html +="<tr><td>%s</td></tr>"%(str(line.code)) 
#                            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
#                            query = {'db': self._cr.dbname}
#                            fragment = {
#                                          'model': 'mrp.raw.material.request',
#                                          'view_type': 'form',
#                                          'id': rm_rqst.id,
#                                         }
#                            url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
#                            print "urlurl",url
#                            text_link = _("""<a href="%s">%s</a> """) % (url,"VIEW REQUEST")
#                            body_html +='<li> <b>RM Request :</b> '+str(text_link) +'</li>'
                    body_html +="</table>"
                else:
                    body_html+= """<div> 

                        <p style="color:red"> <strong>No BOM created till now, BOM required.</strong></p><br/>
                        </div>"""
                temp_id.write({'body_html': body_html,'subject':new_subject,
                                'email_to' : send_user, 'email_from': user_obj.partner_id.email})
                print "send_usersend_user",send_user,body_html
                temp_id.send_mail(self.n_sale_line.id if self.n_sale_line else False)
			
#		if self.n_exist_pr:
#		    temp_id = self.env.ref('gt_order_mgnt.email_template_producton_req_again')
#		    if temp_id:
#			base_url = self.env['ir.config_parameter'].get_param('web.base.url')
#			query = {'db': self._cr.dbname}
#			fragment = {
#			    'model': 'sale.order',
#			    'view_type': 'form',
#			    'id': self.n_sale_line.id,
#			}
#			url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
#			text_link = _("""<a href="%s">%s</a> """) % (url,self.n_sale_line.name)
#
#			body_html = """<div> 
#		<p> <strong>Production Request Again</strong></p><br/>
#		<p>Dear %s,<br/>
#		    <b>%s </b>Production Request sent : for <b>%s </b>  Product:%s Of Quantity :%s<br/>
#		</p>
#		</div>#"""%(self.n_sale_line.user_id.name or '', user_obj.name or '', text_link,str(self.n_product_id.product_tmpl_id.name),str(self.n_order_qty))
#
#			body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',self.n_sale_line.id, context=self._context)
#			n_emails=str(self.n_sale_line.user_id.login)
#			temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': user_obj.partner_id.email})
#			temp_id.send_mail(self.n_sale_line.id)
	return True
    
    
    @api.multi 
    @api.depends('n_product_id')
    def _compute_bom_reminder_visibility(self):
	for rec in self:
            bom_id=self.env['mrp.bom'].search([('product_id','=',rec.n_product_id.id)])
            if not bom_id:
                rec.bom_reminder_visible=True
            else:
                rec.bom_reminder_visible=False
    @api.multi 
    @api.depends('n_product_id')
    def _compute_mo_reminder_visibility(self):
	for rec in self:
            mo_id=self.env['mrp.production'].search([('request_line','=',rec.id)])
            if not mo_id:
                rec.mo_reminder_visible=True
            else:
                rec.mo_reminder_visible=False
                
    @api.multi
    def send_reminder_to_create_mo(self):
        
        user_obj = self.env['res.users'].browse(self.env.uid)
        temp_id = self.env.ref('gt_order_mgnt.email_template_producton_req_again')
        if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                          'model': 'n.manufacturing.request',
                          'view_type': 'form',
                          'id': self.id,
                         }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                print "urlurl",url
                text_link = _("""<a href="%s">%s</a> """) % (url,self.name)
                group,send_user_name=False,''
                recipient_partners=[]
                if self.n_category.cat_type=='film':
                        group = self.env['res.groups'].search([('name', 'in', ('Film manager','Get BoM Alert'))])
                elif self.n_category.cat_type=='injection':
                        group = self.env['res.groups'].search([('name', 'in', ('Injection manager','Get BoM Alert'))])
                print "groupgroupgroupgroupgroupgroup",group
                for groups in group:
                    for recipient in groups.users:
                        if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                             recipient_partners.append(recipient.login)
                             send_user_name=recipient.name
                if self.n_sale_order_line:
                    recipient_partners.append(self.n_sale_order_line.order_id.user_id.login)
                    
                send_user = ",".join(recipient_partners)
                product_data = ''.join(['[',str(self.n_product_id.default_code),']',self.n_product_id.name])
                bom_id=self.env['mrp.bom'].search([('product_id','=',self.n_product_id.id)])
                new_subject='Production Reminder: Awaiting timeline for Production request %s received for %s'%(str(self.name),'['+self.n_product_id.default_code+']'+' '+self.n_product_id.name+', '+self.n_partner_id.name if self.n_partner_id else '')
                if self.n_delivery_date:
                    n_date=datetime.strftime(datetime.strptime(self.n_delivery_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d')           
                else:
                    n_date=''
                if not self.n_Note:
                    note=''
                else:
                    note=self.n_Note
                body_html = """<div> 
                        <strong><p>Dear User,<br/>
                        <p>Below production request was raised but the response from production is yet not received, Awaiting production timeline.</strong></p><br/>
                                <p>Request Number : <b>%s</b> </p>
                                <p>Product:<b>%s</b> </p>
                                <p>Instructions from Sale Support:<b>%s</b> </p>
                                <p>Requested completion date: <b>%s</b> </p>
                                <p>Sales Order Number:<b>%s</b> </p>
                                <p>Customer Name:<b>%s</b> </p>
                                <p>Sales Person:<b>%s</b> </p>
                                <p>Quantity :<b>%s</b> \t%s </p>
                                <p>Packaging :<b>%s</b> </p>
                        </p>
                        </div>"""%(str(text_link),product_data,note,str(n_date),str(self.n_sale_order_line.order_id.name) if self.n_sale_order_line else '',str(self.n_sale_order_line.order_id.partner_id.name) if self.n_sale_order_line else str(self.n_partner_id.name) if self.n_partner_id else '',str(self.n_sale_order_line.order_id.user_id.name),str(self.n_order_qty),str(self.n_unit.name),str(self.n_packaging.name))
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',self.n_sale_line.id, context=self._context)
                print "body_htmlbody_htmlbody_html",body_html
                temp_id.write({'body_html': body_html,'subject':new_subject,
                                'email_to' : send_user, 'email_from': user_obj.partner_id.email})
                print "send_usersend_user",send_user,body_html
                self.write({'reminder_mo_sent':True})
                temp_id.send_mail(self.n_sale_line.id if self.n_sale_line else False)
	return True
    @api.multi
    def send_reminder_bom(self):
        bom_id=self.env['mrp.bom'].search([('product_id','=',self.n_product_id.id)])

    	# raise Error till manufacturing module is not installed.
#    	raise UserError('You dot\' have access to creaete Manufacturing Order\n Please Create Transfer Production')
    	#raise UserError('Manufacturing module is not fully intalled')
        temp_id = self.env.ref('gt_order_mgnt.email_template_producton_req_again')
        user_obj = self.env['res.users'].browse(self.env.uid)

        if temp_id and not bom_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                          'model': 'n.manufacturing.request',
                          'view_type': 'form',
                          'id': self.id,
                         }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                print "urlurl",url
                text_link = _("""<a href="%s">%s</a> """) % (url,self.name)
                group,send_user_name=False,''
                recipient_partners=[]
                group = self.env['res.groups'].search([('name', '=', 'Get BoM Alert')])
                print "groupgroupgroupgroupgroupgroup",group
                for groups in group:
                    for recipient in groups.users:
                        if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                             recipient_partners.append(recipient.login)
                             send_user_name=recipient.name

                send_user = ",".join(recipient_partners)
                product_data = ''.join(['[',str(self.n_product_id.default_code),']',self.n_product_id.name])
                new_subject='API-ERP BOM Alert: Production stopped for %s as BOM not available.'%str('['+self.n_product_id.default_code+']'+' '+self.n_product_id.name)
                if self.n_delivery_date:
                    n_date=datetime.strftime(datetime.strptime(self.n_delivery_date,tools.DEFAULT_SERVER_DATETIME_FORMAT).date(), '%Y-%m-%d')           
                else:
                    n_date=''
                body_html = """<div> 
                        <p>Dear User,<br/>
                        <p>This is to inform you that manufacturing supervisor tried to create Manufacturing order for below request but was not successful as there is no BOM defined for %s</p>
                        <p>Kindly issue BOM at your earliest so that MO can be planned and started.</p><br/>
					<p>Request Number : <b>%s</b> </p>
		    			<p>Product:<b>%s</b> </p>
		    			<p>Instructions from Sale Support:<b>%s</b> </p>
		    			<p>Requested completion date: <b>%s</b> </p>
		    			<p>Sales Order Number:<b>%s</b></p>
                                        <p>Customer Name:<b>%s</b> </p>
		    			<p>Sales Person:<b>%s</b> </p>
		    			<p>Quantity :<b>%s</b>%s</p>
		    			<p>Packaging :<b>%s</b></p>
				</p>
				</div>"""%('['+str(self.n_product_id.default_code)+']'+' '+str(self.n_product_id.name),str(text_link),'['+str(self.n_product_id.default_code)+']'+' '+str(self.n_product_id.name),str(self.n_Note) or '',str(n_date),str(self.n_sale_order_line.order_id.name),str(self.n_sale_order_line.order_id.partner_id.name),str(self.n_sale_order_line.order_id.user_id.name),str(self.n_order_qty),str(self.n_unit.name),str(self.n_packaging.name))
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',self.n_sale_line.id if self.n_sale_line else False, context=self._context)
                print "body_htmlbody_htmlbody_html",body_html
                temp_id.write({'body_html': body_html,'subject':new_subject,
                                'email_to' : send_user, 'email_from': user_obj.partner_id.email})
                print "send_usersend_user",send_user,body_html
#                self.message_post(body=body_html)

                temp_id.send_mail(self.n_sale_line.id if self.n_sale_line else False)
                self.write({'reminder_sent':True})
        return True
    
    @api.multi
    def manu_order_history(self):
	order_form = self.env.ref('gt_order_mgnt.mrp_production_form_view_aalmir_ext', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'mrp.production',
	    'domain':[('request_line','=',self.id)],
            'views': [(order_form.id, 'tree')],
            'view_id': order_form.id,
            'target': 'new',
        }
    @api.multi
    def acknowledge_approved(self):
        for rec in self:
            if rec.n_sale_order_line:
                rec.n_sale_order_line.approve_producton_date()

            else:
                if rec.n_mo_number:
                    rec.n_mo_number.n_request_date_bool1=False
                    rec.n_mo_number.n_request_date_bool=True
                    rec.n_mo_number.message_post(body='<span style="color:green;font-size:14px;">New Date Approved By Sale support -:</span>\n '+
                                    'New Date:'+str(rec.n_mo_number.n_request_date) +'\t')
            rec.new_date_bool=False
            
    @api.multi
    def send_request_production(self):
        self.n_save()

#        self.write({'n_state':'draft'})
    @api.multi
    def create_manufacturing_order(self):

	context = self._context.copy()
        context.update({'request_id':self.id, 'default_contract_id':self.contract_id.id})
        if self.n_partner_id:
            context.update({'default_partner_id':self.n_partner_id.id})
        mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        print "Self>dfsfsdfsdfdsf",context
        bom_id=self.env['mrp.bom'].search([('product_id','=',self.n_product_id.id)])
#        if any(bom.state == 'approve' for bom in bom_id):
#            print "nothing to be done---------------------"
#        else:
#            raise UserError('You are not allowed to create MO request as the BoM is still not approved')
#
#        if not bom_id:
#            raise UserError('You are not allowed to create MO request as the BoM is still not issued for Product')
        if mo_form:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.production',
                    'views': [(mo_form.id, 'form')],
                    'view_id': mo_form.id,
                    'target': 'current',
                    'context': context,
             }

    @api.multi
    def create_production_transfer(self):
    	''' remove this after manufacturing is online'''
	form_view = self.env.ref('stock.view_picking_form', False)
	picking_type_obj=self.env['stock.picking.type']
	if any([ x.state not in ('done','cancel') for x in self.transfer_ids]):
		raise UserError('You have already running Transfer')
	context=self._context.copy()
	if self.n_sale_line.warehouse_id:
		manu_type = picking_type_obj.search([('name','=','Manufacturing Transfers'),
						     ('warehouse_id','=',self.n_sale_line.warehouse_id.id)])
	     	
		context.update({'default_ntransfer_type':'manufacturing','default_origin':self.name,
		'default_picking_type_id':manu_type.id if manu_type else self.n_sale_line.warehouse_id.int_type_id.id,
		'default_move_lines':[(0,0,{'product_id':self.n_product_id.id,'product_uom':self.n_unit.id,
					'product_uom_qty':self.n_order_qty,
					'scrapped': False,'state':'draft','picking_type_id':manu_type.id,
					'location_id':manu_type.default_location_src_id.id,
					'location_dest_id':manu_type.default_location_dest_id.id,
					'name':'[{}]{}'.format(self.n_product_id.default_code,self.n_product_id.name)})],
				})
	else:
		raise UserError('No Sale Order found, please contact administrator')	
        if form_view:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'stock.picking',
		'views': [(form_view.id, 'form')],
                'view_id': form_view.id,
                'target': 'current',
                'context':context,
            }

    @api.multi
    def create_purchase_order(self):
        po_form = self.env.ref('purchase.purchase_order_form', False)
        if po_form:
		self.n_state='purchase'
        	return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'purchase.order',
		    'views': [(po_form.id, 'form')],
		    'view_id': po_form.id,
		    'target': 'current',
		    'context': context,
		    'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
		}

    @api.multi
    def show_product(self):
        po_form = self.env.ref('product.product_template_only_form_view', False)
        if po_form:
        	return {
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'product.template',
		    'views': [(po_form.id, 'form')],
		    'view_id': po_form.id,
		    'target': 'current',
		    'res_id': self.n_product_id.id,
		    'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
		}

class productionCancel(models.TransientModel):
    _name="production.cancel"

    cancel_reason=fields.Text('Reason', required=True)
    
    @api.multi
    def mo_cancel(self):
        for record in self: 
            reason_body = ''
            obj=self.env['mrp.production'].search([('id','=',self._context.get('active_id'))])
            body='<b>Manufacturing Order Cancelled:</b>'
            body +='<ul><li> Manufacturing No.    : '+str(obj.name) +'</li></ul>'
            body +='<ul><li> Product Name.  : '+str(obj.product_id.name) +'</li></ul>'
            body +='<ul><li> Customer Name. : '+str(obj.partner_id.name) +'</li></ul>'
            body +='<ul><li> Cancelled By   : '+str(self.env.user.name) +'</li></ul>' 
            body +='<ul><li> Cancelled Date : '+str(datetime.now() + timedelta(hours=4)) +'</li></ul>' 
            body +='<ul><li> Reason         : '+str(record.cancel_reason) +'</li></ul>'
            
            reason_body = 'Manufacturing Order {} Cancelled\n'.format(str(obj.name).split(',')[0])
            reason_body +='Cancelled By   : '+str(self.env.user.name) +'\n' 
            reason_body +='Cancelled Date : '+str(datetime.now() + timedelta(hours=4)) +'\n' 
            reason_body +='Reason         : '+str(record.cancel_reason) +'\n'
            
            if obj.state == 'draft':
               obj.signal_workflow('button_cancel')
               
            if obj.state == 'confirmed':
               rm_request=self.env['mrp.raw.material.request'].search([('production_id','=',obj.id), ('state','in',('draft','approve'))])
               if rm_request:
                  if rm_request.state == 'draft':
                     rm_request.state = 'cancel'
                  else:
                     rm_request.mo_cancel=True
                     picking_type=self.env['stock.picking.type'].search([('code','=','internal')],limit=1)
                     return_picking=self.env['stock.picking'].create({'picking_type_id':picking_type.id,
                                       'location_dest_id':picking_type.default_location_dest_id.id ,
                                        'origin':obj.name,
                                        'location_id':obj.location_src_id.id,
                                        'production_id':obj.id})
                     body_p =''
                     for line in obj.product_lines:
                         if line.receive_qty:
                            rm_qty=line.receive_qty - line.consumed_qty
                            if rm_qty >0:
                               body_p +="<tr><td>%s</td><td>%s %s</td></tr>"%(str(line.product_id.name), round((rm_qty), 2), str(line.product_uom.name)) 
                               move=self.env['stock.move'].create({'picking_id':return_picking.id,
                                         'product_id':line.product_id.id,
                                          'product_uom_qty':rm_qty,'product_uom':line.product_uom.id,
                                           'picking_type_id':picking_type.id,
                                           'location_dest_id':picking_type.default_location_dest_id.id, 
                                           'location_id':obj.location_src_id.id, 
                                           'name':obj.name})
                     if not return_picking.move_lines:
                        return_picking.unlink()
                     else:
                        body +='<ul><li> Raw Material Transfer No.: '+str(return_picking.name) +'</li></ul>'
                        body +="<table class='table' style='width:60%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th> qty</th></tr>"
                        body += body_p
                        body +="</table>"
                        return_picking.message_post(body=body)
                        return_picking.action_confirm()
                        
               obj.message_post(body=body)
               rm_request.message_post(body=body)
               obj.action_cancel()
            if obj.request_line:
            	obj.request_line.n_state='cancel'
            	obj.request_line.cancel_reason = reason_body
            	mo_ids=self.env['mrp.production'].search([('request_line.n_sale_line.id','=',obj.request_line.n_sale_line.id),('state','not in',('done','cancel'))])
            	if mo_ids:
	            	search_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1)
        		obj.request_line.n_sale_line.n_status_rel=[(3,search_id.id)]
		obj.request_line.n_sale_order_line.pending_qty += abs(obj.n_request_qty-obj.n_produce_qty) 	
            '''if obj.state in ('ready','in_production'): 
               print"PPPPPPPPPPPPPPPPPPPPPPPPP"
               workorders=self.env['mrp.production.workcenter.line'].search([('production_id','=',obj.id)], order='sequence desc')
               for orders in workorders:
                   if orders.total_product_qty: 
                       print"WWWWWWWWWWWWWWWWWW",orders.name, orders.total_product_qty
                       raise UserError(_("You can not cancel Manufacturing order because some qty is produced so.Please Collect Produced Qty From Work Order(%s) and Partial done Manufacuting order." )%(orders.name))
               picking_type=self.env['stock.picking.type'].search([('code','=','internal')],limit=1)
               return_picking=self.env['stock.picking'].create({'picking_type_id':picking_type.id,
                                       'location_dest_id':picking_type.default_location_dest_id.id ,
                                        'origin':obj.name,
                                        'location_id':obj.location_src_id.id,
                                        'production_id':obj.id})
               for line in obj.product_lines:
               print"++++linelinelineline+++=",line
               if line.receive_qty:
                  rm_qty=line.receive_qty - line.consumed_qty
                  if rm_qty >0:
                     move=self.env['stock.move'].create({'picking_id':return_picking.id,
                                         'product_id':line.product_id.id,
                                          'product_uom_qty':rm_qty,'product_uom':line.product_uom.id,
                                           'picking_type_id':picking_type.id,
                                           'location_dest_id':picking_type.default_location_dest_id.id, 
                                           'location_id':obj.location_src_id.id, 
                                           'name':obj.name})
               if not return_picking.move_lines:
                  return_picking.unlink()
               else:
                  return_picking.action_confirm()'''
      
    @api.multi
    def save(self):
	obj=self.env['n.manufacturing.request'].search([('id','=',self._context.get('active_id'))])
	if not self.cancel_reason:
           raise UserError(_('Please give the proper reason for cancel.................')) 
        else:
	   qty=0.0
	   for line in self.env['reserve.history'].search([('sale_line','=',obj.n_sale_order_line.id)]):
			if line.n_status in ('release','cancel','delivered') :
				qty -= line.res_qty
			if line.n_status in ('reserve','r_t_dispatch'):
				qty += line.res_qty
	   obj.n_sale_order_line.pending_qty = (obj.n_sale_order_line.product_uom_qty - qty) if (obj.n_sale_order_line.product_uom_qty - qty)>1 else 0
	   search_id=self.env['sale.order.line.status'].search([('n_string','=','production_request')],limit=1)
	   obj.n_sale_line.n_status_rel=[(3,search_id.id)]
	   obj.n_state='cancel'
	   obj.cancel_reason=self.cancel_reason
	   if self._context.get('cancel_from_ss'):
	   	obj.check_bool=True
	   else:
		user_obj = self.env['res.users'].browse(self.env.uid)
		temp_id = self.env.ref('gt_order_mgnt.email_template_producton_req_again')
	    	if temp_id:
	    		group,send_user_name=False,''
	    		recipient_partners=[]
			group = self.env['res.groups'].search([('name', '=', 'Sales Support Email')])
		       	for recipient in group.users:
			   if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
		    	   	recipient_partners.append(recipient.login)

		       	send_user = ",".join(recipient_partners)
		        product_data = ''.join(['[',str(obj.n_product_id.default_code),']',obj.n_product_id.name])
			body_html = """<div> 
				<p> <strong>Production Request (Cancel)</strong></p><br/>
				<p>Request Number : <b>%s</b> </p>
	    			<p>Product:<b>%s</b> </p>
	    			<p>Quantity :<b>%s</b> \t%s </p>
	    			</br>
				<p><b>Cancel Reason </b></p>
					<p> %s </p>
				</div>"""%(str(obj.name),product_data,str(obj.n_order_qty),str(obj.n_unit.name),str(self.cancel_reason))
			new_subject='Production Request Cancel({})'.format(obj.name)
			body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order',obj.n_sale_line.id, context=self._context)
			#code is comented due to security restriction(crm.lead) (need to work )
			#temp_id.write({'body_html': body_html,'subject':new_subject,
					#'email_to' : send_user, 'email_from': user_obj.partner_id.email})
			#temp_id.sudo().send_mail(obj.n_sale_line.id)

class MrpBom(models.Model):
    
    _inherit = "mrp.bom"
   
    @api.v7
    def _prepare_wc_line(self, cr, uid, bom, wc_use, level=0, factor=1, context=None):
        wc = wc_use.workcenter_id
        d, m = divmod(factor,1)#divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
        mult = (d + (m and 1.0 or 0.0))
        cycle =0.0#mult * wc_use.cycle_nbr 
        test=float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
        return {
            'name': tools.ustr(wc_use.name) + ' - ' + tools.ustr(bom.product_tmpl_id.name_get()[0][1]),
            'workcenter_id': wc.id,
            'sequence': level + (wc_use.sequence or 0),
            'cycle': cycle,
            'hour': float(wc_use.hour_nbr * mult + ((wc.time_start or 0.0) + (wc.time_stop or 0.0) + cycle * (wc.time_cycle or 0.0)) * (wc.time_efficiency or 1.0)),
        }

    @api.model
    def _get_uom_id(self):
        return self.env["product.uom"].search([('name','=','Pcs')], limit=1, order='id')[0]

    @api.v7
    def onchange_product_tmpl_id(self, cr, uid, ids, product_tmpl_id, product_qty=0, context=None):
        """ Changes UoM and name if product_id changes.
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        res = {}
        if product_tmpl_id:
            prod = self.pool.get('product.template').browse(cr, uid, product_tmpl_id, context=context)
            res['value'] = {
                #'product_uom': prod.uom_id.id,
                'code':prod.default_code,
            }
        return res

    @api.onchange('master_id')
    def onchange_bomMaster(self):
        if self.master_id:
            self.code='%s, %s' % (self.product_tmpl_id.default_code,self.master_id.name)
            line_dict=[]
            #uom_id=self.env['product.uom'].search([('name','=','Kg')],limit=1)
            #uom=uom_id.id if uom_id  else self.product_uom.id
            for rec in self.master_id.master_line:
            	qty = rec.quantity if rec.quantity else (rec.percentage*self.product_qty/100) if self.product_qty else 1
                
                line_dict.append((0,0,{'product_id':rec.product_id,'percentage':rec.percentage,
                        'product_qty':qty,'product_efficiency':1}))
            self.bom_line_ids=line_dict
            
#            point1 in bom changes
            
    active = fields.Boolean('Active',default=True)
    sale_line = fields.Many2one('sale.order.line', 'Sale Line')        
    master_id = fields.Many2one('mrp.bom.master','BOM Code')
    product_weight = fields.Float('Weight of Product',digits=dp.get_precision('Stock Weight'),related="product_tmpl_id.initial_weight",readonly=True)
    weight = fields.Float('Weight of (Product+Wastage)',digits=dp.get_precision('Stock Weight'),
                               compute='totalwastage_weight')
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",readonly=True,default=_get_uom_id)
      
    bom_packging_line = fields.One2many('mrp.bom.line','bom_packaging_id','Packaging Material')
    bom_wastage_ids=fields.One2many('mrp.bom.wastage.type','bom_id', string='Wastage Details')
    one_time_wastage_ids=fields.One2many('mrp.bom.wastage.one.time','bom_id', string='One Time Wastage')
    product_id = fields.Many2one('product.product', 'Product Name',help="Product for BOM",domain="[('product_tmpl_id.product_material_type.string','not in',('packaging','raw','asset'))]")
    state = fields.Selection([('draft','Draft'),('sent_for_app','Sent For Approval'),('app_rem_sent','Approval Reminder Sent'),('approve','Approved'),
   			   ('reject','Rejected')],default='draft',track_visibility='always' )
    general_remarks=fields.Text('General Remarks',track_visibility='always' )
    remarks=fields.Text('Remarks on Approval',track_visibility='always' )
    refuse_reason = fields.Char(string='Reject Reason',track_visibility='always' )

    
    
    
    @api.multi
    def set_bom_to_draft(self):
        self.write({'state':'draft'})
        
    @api.multi
    def send_for_approval(self):
        if not self.bom_line_ids:
            raise UserError(_('Please Enter Raw Material/Components before sending for approval!!'))

        temp_id = self.env.ref('gt_order_mgnt.email_template_for_bom_approval')
        user_obj = self.env['res.users'].browse(self.env.uid)

        if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                          'model': 'mrp.bom',
                          'view_type': 'form',
                          'id': self.id,
                         }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                print "urlurl",url
                text_link = _("""<a href="%s">%s</a> """) % (url,self.code)
                group,send_user_name=False,''
                recipient_partners=[]
                group = self.env['res.groups'].search([('name', '=', 'Can Approve/Reject BOM')])
                print "groupgroupgroupgroupgroupgroup",group
                for groups in group:
                    for recipient in groups.users:
                        if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                             recipient_partners.append(recipient.login)
                             send_user_name=recipient.name

                send_user = ",".join(recipient_partners)
                new_subject='API-MRP BOM Alert: BoM Approval Requested for %s.'%str('['+self.product_id.default_code+']'+' '+self.product_id.name)
                body_html = """<div> 
                        <p>Dear User,<br/>
                        <p>Kindly Approve BOM at your earliest so that MO can be planned and started.</p><br/>
		    			<p>Product:<b>%s</b> </p>
		    			<p>Request Ref:<b>%s</b> </p>
		    			<p>BOM Code:<b>%s</b> </p>
		    			<p>Created By<b>%s</b> </p>
				</p>
				</div>"""%('['+str(self.product_id.default_code)+']'+' '+str(self.product_id.name),str(text_link),str(self.code),str(self.env.user.name))
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.bom',self.id, context=self._context)
                print "body_htmlbody_htmlbody_html",body_html
                temp_id.write({'body_html': body_html,'subject':new_subject,
                                'email_to' : send_user, 'email_from': self.env.user.email})
                print "send_usersend_user",send_user,body_html
#                self.message_post(body=body_html)
                temp_id.send_mail(self.id)
                self.write({'state':'sent_for_app'})
        return True
    @api.multi
    def send_approval_reminder(self):
        if not self.bom_line_ids:
            raise UserError(_('Please Enter Raw Material/Components before sending for approval!!'))

        temp_id = self.env.ref('gt_order_mgnt.email_template_for_bom_approval')
        user_obj = self.env['res.users'].browse(self.env.uid)

        if temp_id:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                query = {'db': self._cr.dbname}
                fragment = {
                          'model': 'mrp.bom',
                          'view_type': 'form',
                          'id': self.id,
                         }
                url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
                print "urlurl",url
                text_link = _("""<a href="%s">%s</a> """) % (url,self.code)
                group,send_user_name=False,''
                recipient_partners=[]
                group = self.env['res.groups'].search([('name', '=', 'Can Approve/Reject BOM')])
                print "groupgroupgroupgroupgroupgroup",group
                for groups in group:
                    for recipient in groups.users:
                        if recipient.login not in recipient_partners and str(recipient.login) != str(user_obj.partner_id.email):
                             recipient_partners.append(recipient.login)
                             send_user_name=recipient.name

                send_user = ",".join(recipient_partners)
                new_subject='API-MRP BOM Alert: BoM Approval Reminder for %s.'%str('['+self.product_id.default_code+']'+' '+self.product_id.name)
                body_html = """<div> 
                        <p>Dear User,<br/>
                        <p>Kindly Approve BOM at your earliest so that MO can be planned and started.</p><br/>
		    			<p>Product:<b>%s</b> </p>
		    			<p>Request Ref:<b>%s</b> </p>
		    			<p>BOM Code:<b>%s</b> </p>
		    			<p>Created By<b>%s</b> </p>
				</p>
				</div>"""%('['+str(self.product_id.default_code)+']'+' '+str(self.product_id.name),str(text_link),str(self.code),str(self.env.user.name))
                body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.bom',self.id, context=self._context)
                print "body_htmlbody_htmlbody_html",body_html
                temp_id.write({'body_html': body_html,'subject':new_subject,
                                'email_to' : send_user, 'email_from': self.env.user.email})
                print "send_usersend_user",send_user,body_html
#                self.message_post(body=body_html)
                temp_id.send_mail(self.id)
                self.write({'state':'app_rem_sent'})
        return True
    @api.multi
    def approve_bom(self):
       cofirm_form = self.env.ref('gt_order_mgnt.approve_bom_wizard_wizard_view_form', False)
       if cofirm_form:
            return {
                        'name':'Approve BOM',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'approve.bom.wizard',
                        'views': [(cofirm_form.id, 'form')],
                        'view_id': cofirm_form.id,
                        'target': 'new'
                    }
#        self.write({'state':'approve'})
    @api.multi
    def reject_bom(self):
       cofirm_form = self.env.ref('api_account.pay_cancel_wizard_view_form', False)
       if cofirm_form:
            return {
                        'name':'Reject BOM',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'cancel.pay.reason.wizard',
                        'views': [(cofirm_form.id, 'form')],
                        'view_id': cofirm_form.id,
                        'target': 'new'
                    }
#        self.write({'state':'reject'})
    @api.multi 
    @api.depends('product_weight' ,'bom_wastage_ids')  
    def totalwastage_weight(self):
        for record in self:
            if record.bom_wastage_ids:
               wastage_per=sum(line.value for line in record.bom_wastage_ids)
               wastage_kg= (record.product_weight *wastage_per)/100
               record.weight=wastage_kg + record.product_weight
            else:
               record.weight=record.product_weight

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
    	if self.product_id:
    		self.product_tmpl_id=self.product_id.product_tmpl_id.id
    
    #@api.v7
    #def onchange_product_tmpl_id(self, cr, uid, ids, product_tmpl_id, product_qty=0, context=None):
    	# inherite to overrride and stop existing onchnage functionality
    #	pass
      
    @api.multi        
    def name_get(self):
        res = []
        for record in self:
            name =record.code #record.product_tmpl_id.name
            if record.master_id:
                name = '%s' % (record.code)
            res.append((record.id, name))
        return res
    
    @api.onchange('routing_id')
    def routing_onchange(self):    
    	if self.routing_id:
    		process=[]	
		for res in self.routing_id.workcenter_lines:
			process.append(res.workcenter_id.id)	
		for bom in self.bom_line_ids:
			if bom.workcenter_id.id not in process:
				bom.workcenter_id=False
		for pkg in self.bom_packging_line:
			if pkg.workcenter_id.id not in process:
				pkg.workcenter_id=False
    		for wstg in self.bom_wastage_ids:
			if wstg.workcenter_id.id not in process:
				wstg.workcenter_id=False
				
    @api.multi
    def recompute_qty(self):
        percentage=0.0
        for rec in self.bom_line_ids:
           if rec.product_uom.name.upper()=='KG' and not rec.percentage:
           	raise UserError(_('Please Enter Percentage Material'))
           if rec.product_uom.name.upper()=='KG':
        	percentage += rec.percentage
	if percentage!=0 and percentage != 100.0:
		raise UserError(_('Kg unit Component Percentage Total Should be Equals to 100'))
	weight = self.weight
	for record1 in self.bom_line_ids:
		if record1.product_uom.name.upper()=='PCS':
			weight -= record1.product_qty*record1.product_id.weight 
	for record in self.bom_line_ids:
	    if record.product_uom.name.upper()=='KG':
		    if self.product_uom.name.upper()=='PCS':
			record.product_qty = (record.percentage*weight/100)*self.product_qty
		    if self.product_uom.name.upper()=='KG':
        		record.product_qty = (record.percentage*self.product_qty/100)
    
    @api.model     
    def create(self,vals):
        if vals.get('bom_line_ids'):
    		percentage=0.0
    		product_id=self.env['product.template'].search([('id','=',vals.get('product_tmpl_id'))])
    		if not product_id.weight:
    			raise UserError(_('Please Enter Product weight in product form'))
    		weight = product_id.weight if product_id else 0.0
    		for line1 in vals.get('bom_line_ids'):
#                        if not vals.get('workcenter_id'):
#                            raise UserError(_('Please Select Process in BoM Lines!!'))

    			if type(line1[2]) == dict:
    			    uom_id=line1[2].get('uom_name')
    			    if uom_id and uom_id.upper()=='PCS':
    			        if line1[2].get('product_qty')==0 or not line1[2].get('product_qty'):
    			    		raise UserError(_('Please Enter Quantity of Material'))
    			        product_id = self.env['product.product'].search([('id','=',line1[2].get('product_id'))])
    			    	weight -= line1[2].get('product_qty')*product_id.weight
    			    		
    		product_qty = float(vals.get('product_qty')) if vals.get('product_qty') else 1
    		for line in vals.get('bom_line_ids'):
    			if type(line[2]) == dict:
    			    uom_id=line[2].get('uom_name')
    			    if uom_id and uom_id.upper()=='KG':
    			    	if line[2].get('percentage')==0 or not line[2].get('percentage'):
    			    		raise UserError(_('Please Enter Percentage of Material'))
    				percentage +=line[2].get('percentage')
				n_qty=(line[2].get('percentage')*weight/100)*product_qty
    				line[2].update({'product_qty':n_qty})
    			    if uom_id and uom_id.upper()=='PCS':
    				line[2].update({'product_qty':product_qty})
			
		if percentage!=0 and percentage != 100.0:
			raise UserError(_('Kg Unit Component Percentage Total Should be Equals to 100'))
    	return super(MrpBom,self).create(vals)
    	
    @api.multi     
    def write(self,vals):
    	for record in self: 
                if self.env['mrp.production'].search([('bom_id', 'in', self.ids), ('state', 'not in', ['done', 'cancel'])],):
                   raise UserError(_('You can not Change a Bill of Material with running manufacturing orders.\nPlease Craete New  Bill of Material.'))
    		qty=0.0
		id_list=[]
		product_id=False
		if vals.get('product_tmpl_id'):
    			product_id=self.env['product.template'].search([('id','=',vals.get('product_tmpl_id'))])
		product_id=record.product_tmpl_id
    		if not product_id.weight:
    			raise UserError(_('Please Enter Product weight in product form'))
    		weight = product_id.weight if product_id else 0.0
                print "valsvalsvals",vals
	    	if vals.get('bom_line_ids'):
                    for each in vals.get('bom_line_ids'):
                        print "each-----------------",each
                        if each[2] and each[2].get('percentage'):
                            id_list.append(each[1])
                            qty += each[2].get('percentage')
                    print "qtyqtyqtyqtyqty now-------",qty
                    if qty!=100.0:
                        for each_line in record.bom_line_ids:
                            if each_line.id not in id_list and each_line.uom_name.upper()=='KG':
                                qty += each_line.percentage
#                                print "line---------------",line
#                                dxfdsdff
#	    			if type(line[2]) == dict:
#	    				uom=line[2].get('uom_name')
#                                        print "uomuomuomuom",uom
#    			    		if uom and uom.upper()=='KG':
#			    			if line[2].get('percentage')==0 or not line[2].get('percentage'):
#	    			    			raise UserError(_('Please Enter Percentage of Material'))
#	    					qty +=line[2].get('percentage')
                            elif each_line.uom_name and each_line.uom_name.upper()=='PCS':
                                if each_line.product_qty==0:
                                    raise UserError(_('Please Enter Quantity of Material'))

#					elif uom and uom.upper()=='KG' and not line[2].get('percentage'):
#			    			for rec in self.bom_line_ids:
#							if rec.id == line[1]:
#								qty += rec.percentage
#					elif line[2].get('percentage')==0 and line[1]:
#						raise UserError(_('Please Enter Percentage of Material'))
#					elif line[2].get('percentage') and line[1]:
#						for rec in self.bom_line_ids:
#						    if rec.uom_name.upper()=='KG':
##							if rec.id == line[1]:
#                                                        qty += line[2].get('percentage')
#                            elif each_line.product_qty==0:
#                                    for rec in self.bom_line_ids:
#                                        if rec.id == line[1] and rec.uom_name.upper()=='PCS' :
#                                                    raise UserError(_('Please Enter Quantity of Material'))
#				elif line[0] != 2:
#                                        print "line-------",line
#					for rec in self.bom_line_ids:
#					    if rec.uom_name.upper()=='KG':
#						if rec.id == line[1]:
#                                                    id_list.append(rec.id)
#                                                    qty += rec.percentage
#		if id_list:
#                        print "id list-----------",id_list
#			for rec in self.bom_line_ids:
#			    if rec.uom_name.upper()=='KG':
#				if rec.id not in id_list:
#                                        print "rec-------------",rec.id
#					qty += rec.percentage
#                                        print "qty--------------",qty
                    print "qtyqtyqty12344",qty

                    if qty>0 and round(qty,1)!=round(100.0,1):
                            raise UserError(_('Component Percentage Total Should be Equals to 100'))
				
		super(MrpBom,self).write(vals)
		if vals.get('bom_line_ids') or vals.get('product_qty'):
			product_qty = vals.get('product_qty') if vals.get('product_qty') else self.product_qty
			weight = self.weight
			for record1 in self.bom_line_ids:	# deduct Pcs component weight from total weight
				if record1.product_uom.name.upper()=='PCS':
					weight -= record1.product_qty*record1.product_id.weight 
			
			for record in self.bom_line_ids:
			    if record.uom_name.upper()=='KG':
			    	if weight <= 0.0:
					_logger.info('API-EXCEPTION.. Pcs Component Total weight should be less than Main Product weight')
					raise UserError(_('Pcs Component Total weight should be less than Main Product weight'))
				if self.product_uom.name.upper()=='PCS':
        				record.product_qty = (record.percentage*weight/100)*self.product_qty
	    			if self.product_uom.name.upper()=='KG':
        				record.product_qty = (record.percentage*self.product_qty/100)
    	return True

    @api.v7     
    def _bom_explode(self, cr, uid, bom, product, factor, properties=None, level=0, routing_id=False, previous_products=None, master_bom=None, context=None):
        """ Finds Products and Work Centers for related BoM for manufacturing order.
        @param bom: BoM of particular product template.
        @param product: Select a particular variant of the BoM. If False use BoM without variants.
        @param factor: Factor represents the quantity, but in UoM of the BoM, taking into account the numbers produced by the BoM
        @param properties: A List of properties Ids.
        @param level: Depth level to find BoM lines starts from 10.
        @param previous_products: List of product previously use by bom explore to avoid recursion
        @param master_bom: When recursion, used to display the name of the master bom
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing Work Center details.
        """
        uom_obj = self.pool.get("product.uom")
        routing_obj = self.pool.get('mrp.routing')
        master_bom = master_bom or bom


        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            if product_rounding:
                factor = tools.float_round(factor,
                                           precision_rounding=product_rounding,
                                           rounding_method='UP')
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)

        result = []
        result2 = []

        routing = (routing_id and routing_obj.browse(cr, uid, routing_id)) or bom.routing_id or False
        print "routingrouting",routing
        if routing:
            for wc_use in routing.workcenter_lines:
                result2.append(self._prepare_wc_line(
                    cr, uid, bom, wc_use, level=level, factor=factor,
                    context=context))

        for bom_line_id in bom.bom_line_ids:
            if self._skip_bom_line(cr, uid, bom_line_id, product, context=context):
                continue
            if set(map(int, bom_line_id.property_ids or [])) - set(properties or []):
                continue

            if previous_products and bom_line_id.product_id.product_tmpl_id.id in previous_products:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.code or "", bom_line_id.product_id.name_get()[0][1]))

            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            bom_id = self._bom_find(cr, uid, product_id=bom_line_id.product_id.id, properties=properties, context=context)

            #If BoM should not behave like kit, just add the product, otherwise explode further
            if (not bom_id) or (self.browse(cr, uid, bom_id, context=context).type != "phantom"):
                result.append(self._prepare_consume_line(
                    cr, uid, bom_line_id, quantity, context=context))
            else:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(cr, uid, bom_id, context=context)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(cr, uid, bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_explode(cr, uid, bom2, bom_line_id.product_id, quantity2,
                    properties=properties, level=level + 10, previous_products=all_prod, master_bom=master_bom, context=context)
                result = result + res[0]
                result2 = result2 + res[1]
        
        for line in bom.bom_packging_line:
            if self._skip_bom_line(cr, uid, line, product, context=context):
                continue
            if set(map(int, line.property_ids or [])) - set(properties or []):
                continue

            if previous_products and line.product_id.product_tmpl_id.id in previous_products:
                raise UserError(_('BoM "%s" contains a BoM line with a product recursion: "%s".') % (master_bom.code or "", line.product_id.name_get()[0][1]))

            quantity = _factor(line.product_qty * factor, line.product_efficiency, line.product_rounding)
            bom_id = self._bom_find(cr, uid, product_id=line.product_id.id, properties=properties, context=context)

            #If BoM should not behave like kit, just add the product, otherwise explode further
            if (not bom_id) or (self.browse(cr, uid, bom_id, context=context).type != "phantom"):
                result.append(self._prepare_consume_line(
                    cr, uid, line, quantity, context=context))
            else:
                all_prod = [bom.product_tmpl_id.id] + (previous_products or [])
                bom2 = self.browse(cr, uid, bom_id, context=context)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(cr, uid, line.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_explode(cr, uid, bom2, line.product_id, quantity2,
                    properties=properties, level=level + 10, previous_products=all_prod, master_bom=master_bom, context=context)
                result = result + res[0]
                result2 = result2 + res[1]

        return result, result2
class MrpBomWastageType(models.Model):
    _name = "mrp.bom.wastage.type"
    
    name=fields.Many2one('wastage.type', string="Name")
    value=fields.Float('Wastage %',digits_compute=dp.get_precision('Wastage Percent Decimal'))
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process") 
    bom_id=fields.Many2one('mrp.bom')
class MrpBomWastageOneTime(models.Model):
    _name = "mrp.bom.wastage.one.time"
    
    name=fields.Many2one('wastage.type', string="Name")
    value=fields.Float('Wastage Kg',digits_compute=dp.get_precision('Wastage Percent Decimal'))
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process") 
    bom_id=fields.Many2one('mrp.bom')

class WastageType(models.Model):
    _name = "wastage.type" 
    
    name=fields.Char('Name')


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"
    
    @api.multi
    @api.depends('product_qty')
    def compute_qpp(self):
        for rec in self:
            if rec.product_qty:
                rec.product_qty_qpp=rec.product_qty
    
    @api.onchange('qty_per_packging')
    def onchange_bomPackging(self):
        print "sdfdsfsfsfdsfdsfsdf",self.qty_per_packging
        if self.qty_per_packging:
            self.product_qty=1/self.qty_per_packging
    
    product_qty = fields.Float('Product Quantity', required=True,digits=dp.get_precision('BoM Line Qty Required'))
    product_qty_qpp = fields.Float('Qty Required',digits=dp.get_precision('BoM Line Qty Required'),compute='compute_qpp')
    qty_per_packging = fields.Float('Quantity per Packaging', digits=dp.get_precision('BoM Line Qty Required'))
    bom_id = fields.Many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True, required=False)
    product_uom =fields.Many2one('product.uom','Unit',readonly=True,related='product_id.uom_id')
    
    uom_name= fields.Char('uom Name',related="product_id.uom_id.name",help="This field is used to make fields readonly ")
    percentage = fields.Float('Percentage(%)')
    bom_packaging_id = fields.Many2one('mrp.bom','BOM',readonly=True)
#    workcenter_id= fields.Many2one('mrp.workcenter', string="Process", required=True)
    workcenter_id= fields.Many2one('mrp.workcenter', string="Process")
    
class MrpBomMaster(models.Model):
	
    _name = "mrp.bom.master"
    
    name = fields.Char('BOM Code',required=True)
    master_line = fields.One2many('mrp.bom.master.line','master_id',string='Bom Material')

    @api.model     
    def create(self,vals):
        if vals.get('master_line'):
    		qty=0.0
    		for line in vals.get('master_line'):
    			p_type=['all']
    			if type(line[2]) == dict:
    				uom_name=self.env['product.product'].search([('id','=',line[2].get('product_id'))])
		    		if uom_name and uom_name.uom_id.name.upper()=='KG':
		    			if line[2].get('percentage')==0 or not line[2].get('percentage'):
    			    				raise UserError(_('Please Enter Percentage Material'))
    					qty +=line[2].get('percentage')
				if uom_name and uom_name.uom_id.name.upper()=='PCS':
		    			if line[2].get('quantity')==0 or not line[2].get('quantity'):
    			    				raise UserError(_('Please Enter Percentage Material'))
    				if len(p_type)==1:
    					p_type.append(uom_name.categ_id.cat_type)
    					
				if uom_name.categ_id.cat_type not in p_type:
					raise UserError(_('Please Select the raw material product of same product type '))
		print "qty now on create function mrp bom mastaer-----------",qty			
		if qty!=0 and qty != 100.0:
			raise UserError(_('Raw Materials/Components Composition Total Should be Equals to 100'))
	else:
		raise UserError(_('Please Enter products in Component '))
    	return super(MrpBomMaster,self).create(vals)
    	
    @api.multi     
    def write(self,vals):
    	qty=0.0
	id_list=[]
        if vals.get('master_line'):
            for each in vals.get('master_line'):
                print "each-----------------",each
                if each[2] and each[2].get('percentage'):
                    id_list.append(each[1])
                    qty += each[2].get('percentage')
            print "qtyqtyqtyqtyqty now-------",qty
            if qty!=100.0:
                for each_line in self.master_line:
                    if each_line.id not in id_list and each_line.uom_name.upper()=='KG':
                        qty += each_line.percentage
#                                print "line---------------",line
#                                dxfdsdff
#	    			if type(line[2]) == dict:
#	    				uom=line[2].get('uom_name')
#                                        print "uomuomuomuom",uom
#    			    		if uom and uom.upper()=='KG':
#			    			if line[2].get('percentage')==0 or not line[2].get('percentage'):
#	    			    			raise UserError(_('Please Enter Percentage of Material'))
#	    					qty +=line[2].get('percentage')
                    elif each_line.uom_name and each_line.uom_name.upper()=='PCS':
                        if each_line.product_qty==0:
                            raise UserError(_('Please Enter Quantity of Material'))

#			
#    	if vals.get('master_line'):
#    		p_type=['all']
#    		for rec in self.master_line:
#    			p_type.append(rec.product_id.categ_id.cat_type)
#    		for line in vals.get('master_line'):
#    			if type(line[2]) == dict:
#    				product_id = self.env['product.product'].search([('id','=',line[2].get('product_id'))]) if line[2].get('product_id') else self.env['mrp.bom.master.line'].search([('id','=',line[1])]).product_id
#
#		    		if product_id and product_id.uom_id.name.upper()=='KG':
#		    			if line[2].get('percentage')==0 or not line[2].get('percentage'):
#    			    			raise UserError(_('Please Enter Percentage Material'))
#    					qty +=line[2].get('percentage')
#				elif product_id and product_id.uom_id.name.upper()=='PCS':
#		    			if line[2].get('quantity')==0:
#    			    			raise UserError(_('Please Enter Quantity Material'))
#
#				elif product_id and product_id.uom_id.name.upper()=='KG' and not line[2].get('percentage'):
#		    			for rec in self.master_line:
#						if rec.id == line[1]:
#							qty += rec.percentage
#				elif line[2].get('percentage')==0 and line[1]:
#						raise UserError(_('Please Enter Percentage of Material'))
#				elif line[2].get('percentage') and line[1]:
#				    if product_id.uom_id.name.upper()=='KG':
#					qty += line[2].get('percentage')
#				elif line[2].get('quantity')==0 and line[1]:
#				    if product_id.uom_id.name.upper()=='PCS':
#				    	if line[2].get('quantity')==0:
#		    				raise UserError(_('Please Enter Percentage Material'))
#    				
#    				if len(p_type)==1:
#    					p_type.append(product_id.categ_id.cat_type)
#    				
#				if product_id.categ_id.cat_type not in p_type:
#					raise UserError(_('Please Select the raw material product of same product type '))
#
#			else:
#				for rec in self.master_line:
#				    if rec.uom_name.upper()=='KG':
#					if rec.id == line[1]:
#						id_list.append(rec.id)
#						qty += rec.percentage
#	if id_list:
#		for rec in self.master_line:
#		    if rec.uom_name.upper()=='KG':
#			if rec.id not in id_list:
#				qty += rec.percentage
        print "qty dyring write function master bom----------------",qty
	if  qty >0 and qty != 100:
		raise UserError(_('Raw Materials/Components Composition Total Should be Equals to 100'))
    	return super(MrpBomMaster,self).write(vals)
   
class MrpBomMasterLine(models.Model):
    _name = "mrp.bom.master.line"
    
    master_id = fields.Many2one('mrp.bom.master','Code')
    product_id =fields.Many2one('product.product','Product',required=True)
    percentage = fields.Float('Percentage(%)')
    uom_name= fields.Char('uom Name',related="product_id.uom_id.name",help="This field is used to make fields readonly ")
    quantity = fields.Integer('Quantity')
    
class ApiMrpCalendar(models.Model):
    _name='api.mrp.calendar'
    
    name=fields.Char('Name')
    event_type=fields.Many2one('api.calendar.event','Event Type')
    #api_table=fields.Many2one('api.calendar.model','Model Type')
    color = fields.Integer('Color Index')

class ApiCalendarEvent(models.Model):
   _name="api.calendar.event"
   
   name=fields.Char('Event Name')

class MrpWorkcentor(models.Model):
   _inherit= "mrp.workcenter"
   
   @api.model
   def name_search(self, name, args=None, operator='ilike',limit=100):
        if self._context.get('bom_true') and self._context.get('routing') :
                routing=self.env['mrp.routing'].search([('id','=',self._context.get('routing'))])
                ids=[]
                for rec in routing:
                	for line in rec.workcenter_lines:
                		ids.append((line.workcenter_id.id,line.workcenter_id.name))
		return ids	
        
        return super(MrpWorkcentor,self).name_search(name, args, operator=operator,limit=limit)

class MrpPrdocutionHold(models.Model):
     _name='mrp.production.hold'
     production_id=fields.Many2one('mrp.production', string='Manufacturing No.')  
     reason=fields.Text('Reason', required='1')
     document=fields.Binary('Document')
     reminder_date=fields.Datetime('Reminder Date')
     
     @api.multi
     def active_mo(self):
        for rec in self:
            rec.production_id.hold_order='active'
            orders=self.env['mrp.production.workcenter.line'].search([('production_id','=',rec.production_id.id),('state','=','hold')]),
            if orders:
               for order_data in orders:
                   for order in order_data:
                       order.hold_order='active'
                       if order.hold_state == 'startworking':
                          play_his=self.env['mrp.order.machine.pause'].create({'production_id':rec.production_id.id,
                                   'order_id':order.id, 'product_id':order.product.id,
                                   'machine':order.machine.id, 'state':'play'})
                          #order.action_resume() 
                       order.state=order.hold_state
                       pause=self.env['mrp.order.machine.pause'].search([('state','=','hold'),('order_id','=',order.id)], limit=1)
                       if pause:
                          for pause_data in pause:
                              pause.date_end=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                              pause.state='holdc'
                       if order.date_planned:
                          order.wk_planned_status='fully'

                       else:
                          order.wk_planned_status='unplanned'
                       
               temp_id = self.env.ref('gt_order_mgnt.email_template_active_mo')
               if temp_id:
	          user_obj = self.env['res.users'].browse(self.env.uid)
	          base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	          query = {'db': self._cr.dbname}
	          fragment = {
	            'model': 'mrp.production',
		     'view_type': 'form',
		     'id': rec.production_id.id,
		      }
                  url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	          text_link = _("""<a href="%s">%s</a> """) % (url,rec.production_id.name)
	          body_html = """<div> 
			  <p> <strong>Active hold Manufacturing order</strong><br/><br/>
			  <b>Dear: %s,</b><br/>
		          <b>Production Number :</b>%s ,<br/>
		         <b>Customer Name :</b>%s ,<br/>
		          <b>Product Name :</b>%s ,<br/>
                          <b>Scheduled Qty :</b>%s ,%s<br/>
		          <b>  Reason : </b>%s<br/>
                          <b>  Date : </b>%s<br/>
                          <b>  Active By : </b>%s<br/>
			</p>
			</div>"""%(rec.production_id.user_id.name, text_link or '',rec.production_id.partner_id.name,
		            rec.production_id.product_id.name, rec.production_id.product_qty,rec.production_id.product_uom.name, rec.reason, date.today(), self.env.user.name)
	          body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.production',rec.production_id.id, context=self._context)
	          n_emails=str(rec.production_id.user_id.login)
	          temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': str(rec.production_id.user_id.login)})
	          temp_id.send_mail(rec.production_id.id)
	          
     @api.multi
     def hold_mo(self):
        for rec in self:
            alarm_obj = self.env['calendar.alarm']
            user = self.env['res.users'].browse(self.env.uid)
            name = rec.production_id.name
            event_obj = self.env['calendar.event']
            alarm = alarm_obj.search([('type','=', 'notification'),('duration','=', 10), ('interval','=','minutes')], limit=1)
	    email = alarm_obj.search([('type','=', 'email'),('duration','=', 15), ('interval','=','minutes')], limit=1)
            a_id = []
            if alarm:
                a_id.append(alarm.ids)
	    if email:
		a_id.append(email.ids)
            #attachment=[]
            #attachment.append(('Hold Docs', rec.document))
            event=event_obj.create({'name':rec.production_id.name, 'start_date':rec.reminder_date,
                                     'description':rec.reason, 'start':rec.reminder_date,
                                     'stop':rec.reminder_date,'alarm_ids' : [(6, 0, [a_id])],
                                     'duration' : 0.5,
                                     'production_id':rec.production_id.id,
                                     'partner_ids' : [(6, 0, [user.partner_id.id])],
                                     'alarm_ids' : [(6, 0, [a_id])],
                                     #'comment_id' : rec.production_id.id,
                                     'event_name': '[Hold Manufacturing Order Reminder] ' + (rec.production_id.name or ''),})
            orders=self.env['mrp.production.workcenter.line'].search([('production_id','=',rec.production_id.id),('state','in',('draft','pause', 'startworking'))])
            if orders:
               for order in orders:
                   play_his=self.env['mrp.order.machine.pause'].create({'production_id':rec.production_id.id,
                                    'order_id':order.id, 'product_id':order.product.id,
                                    'machine':order.machine.id, 'state':'hold'})
                   rec.production_id.hold_order='hold'
                   order.hold_order='hold'
                   order.wk_planned_status='hold'
                   order.hold_state=order.state
                   if order.state == 'startworking':
                      play=self.env['mrp.order.machine.pause'].search([('state','=','play'),('order_id','=',order.id)],limit=1)
                      if play:
                         play.date_end=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                         play.state='playc'
                      order.state='hold'
                      #order.action_pause()
                     # order.signal_workflow('button_pause')
                   else:
                      pause=self.env['mrp.order.machine.pause'].search([('state','=','pause'),('order_id','=',order.id)],limit=1)
                      if pause:
                         pause.date_end=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                         pause.state='resume'
                      order.state='hold'
   
               temp_id = self.env.ref('gt_order_mgnt.email_template_hold_mo')
               if temp_id:
	          user_obj = self.env['res.users'].browse(self.env.uid)
	          base_url = self.env['ir.config_parameter'].get_param('web.base.url')
	          query = {'db': self._cr.dbname}
	          fragment = {
	            'model': 'mrp.production',
		     'view_type': 'form',
		     'id': rec.production_id.id,
		      }
                  url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
	          text_link = _("""<a href="%s">%s</a> """) % (url,rec.production_id.name)
                  query1 = {'db': self._cr.dbname}
	          fragment1 = {
	            'model': 'calendar.event',
		     'view_type': 'form',
		     'id':event.id,
		      }
                  event_url = urljoin(base_url, "/web?%s#%s" % (urlencode(query1), urlencode(fragment1)))
	          event_link = _("""<a href="%s">%s</a> """) % (url,event.name)
	          body_html = """<div> 
			  <p> <strong>Hold Manufacturing order</strong><br/><br/>
			  <b>Dear: %s,</b><br/>
		          <b>Production Number :</b>%s ,<br/>
		         <b>Customer Name :</b>%s ,<br/>
		          <b>Product Name :</b>%s ,<br/>
                          <b>Scheduled Qty :</b>%s ,%s<br/>
                          <b>Produced Qty :</b>%s,%s,<br/>
		          <b>  Reason : </b>%s<br/>
                          <b>  Date : </b>%s<br/>
                          <b>  Hold By : </b>%s<br/>
                         <b>  Reminder Date : </b>%s<br/>
                          <b>  Calendar Event : </b>%s<br/>
			</p>
			</div>"""%(rec.production_id.user_id.name, text_link or '',rec.production_id.partner_id.name,
		            rec.production_id.product_id.name,rec.production_id.product_qty,rec.production_id.product_uom.name, rec.production_id.n_produce_qty,rec.production_id.produce_uom_id.name, rec.reason, date.today(), self.env.user.name, 
rec.reminder_date, event_link or '')
	          body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.production',rec.production_id.id, context=self._context)
	          n_emails=str(rec.production_id.user_id.login)
	          temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': str(rec.production_id.user_id.login)})
	          temp_id.send_mail(rec.production_id.id)
	         
