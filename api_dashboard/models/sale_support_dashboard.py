from openerp import fields, models ,api, _
from openerp.exceptions import UserError, ValidationError
import logging
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta
import json

class CustomSalesDashboard(models.Model):
    _name = "custom.sales.dashboard"
 
    @api.one
    def _get_count(self):
        lines=[]
	awaiting_count = self.env['sale.order'].search([('state', '=', 'awaiting'),('due_payment','=','done')])
	awaiting_invoice_count = self.env['sale.order'].search([('state', '=', 'awaiting'),('due_payment','!=','done')])
        orders_count = self.env['sale.order'].search([('state', '=', 'sale')])
        orders_done_count = self.env['sale.order'].search([('state', '=', 'done')])
        not_match="select id  from sale_order_line where qty_delivered != qty_invoiced and state ='sale'"
        self._cr.execute(not_match)
        lines=[i[0] for i in self._cr.fetchall()]
        lines = self.env['sale.order.line'].search([('product_id.type','=','product'),('id','in',lines)])
        lines = self.env['sale.order'].search([('id', 'in',[x.order_id.id for x in lines]),('is_reception','=',False)])
        self.orders_count = len(orders_count)
        self.orders_done_count = len(orders_done_count)
	self.awaiting_count =len(awaiting_count)
	self.awaiting_invoice_count =len(awaiting_invoice_count)
        self.not_match=len(set(lines))
 
    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name")
    orders_count = fields.Integer(compute = '_get_count')
    orders_done_count = fields.Integer(compute= '_get_count')
    awaiting_count = fields.Integer(compute = '_get_count')
    awaiting_invoice_count = fields.Integer(compute = '_get_count')
    not_match = fields.Integer(compute = '_get_count')
    
    @api.one
    def _kanban_dashboard_graph(self):
	    ids=self.env['account.journal'].search([('type','=','bank')],limit=1)
            self.kanban_dashboard_graph = json.dumps(ids.get_line_graph_datas())

    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    @api.multi
    def action_sales(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'awaiting':
		domain=[('state', '=', 'awaiting'),('due_payment','=','done')]
		_name = "Awaiting Orders"
	if self._context.get('n_state') == 'awaiting_inv':
		domain=[('state', '=', 'awaiting'),('due_payment','!=','done')]
		_name = "Awaiting Orders"
	if self._context.get('n_state') == 'sale':
		domain=[('state', '=', 'sale')]
		_name = "Sale Orders"
	if self._context.get('n_state') == 'done':
		_name = "Done Orders"
		domain=[('state', '=', 'done')]
	if self._context.get('n_state') == 'not_match':
                lines=[]
		_name = "Delivered/Innvoiced Quantity Mismatch"
                not_match="select id  from sale_order_line where qty_delivered != qty_invoiced and state ='sale'"
                self._cr.execute(not_match)
                lines=[i[0] for i in self._cr.fetchall()]
                lines = self.env['sale.order.line'].search([('product_id.type','=','product'),('id','in',lines)])
		domain=[('id', 'in', [x.order_id.id for x in lines]),('is_reception','=',False)]	
	po_tree = self.env.ref('sale.view_order_tree', False)
	po_form = self.env.ref('sale.view_order_form', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'sale.order',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
                'context':{'show_sale':True}
            }

#CH_N075<<<<< Sale Details END

#CH_N075<<<<< Sale Status START>>

    @api.multi
    def _get_statedetail(self):
	ids1=self.env['sale.order.line.status'].search([('n_string','=','new')])
	new_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids1.id])])

	ids2=self.env['sale.order.line.status'].search([('n_string','=','production_request')])
	pr_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids2.id])])

	ids3=self.env['sale.order.line.status'].search([('n_string','=','manufacture')])
	man_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids3.id])])
	
	prch=self.env['sale.order.line.status'].search([('n_string','=','purchase')])
	purchase=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[prch.id])])

	ids4=self.env['sale.order.line.status'].search([('n_string','=','warehouse')])
	ware_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids4.id])])

	ids5=self.env['sale.order.line.status'].search([('n_string','=','quality_check')])
	qac_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids5.id])])

	ids6=self.env['sale.order.line.status'].search([('n_string','=','r_t_dispatch')])
	rtdisp_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids6.id])])

	ids7=self.env['sale.order.line.status'].search([('n_string','=','dispatch')])
	disp_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids7.id])])

	ids8=self.env['sale.order.line.status'].search([('n_string','=','partial_dispatch')])
	pardisp_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids8.id])])

	ids9=self.env['sale.order.line.status'].search([('n_string','=','partial_delivery')])
	pardel_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids9.id])])

	ids10=self.env['sale.order.line.status'].search([('n_string','=','delivered')])
	delv_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids10.id])])

	ids11=self.env['sale.order.line.status'].search([('n_string','=','partial_invoice')])
	parinv_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids11.id])])

	ids12=self.env['sale.order.line.status'].search([('n_string','=','invoiced')])
	inv_state=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids12.id])])

	ids13=self.env['sale.order.line.status'].search([('n_string','=','date_request')])
	date_req=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids13.id])])
	
	ids14=self.env['sale.order.line.status'].search([('n_string','=','extra_product')])
	ext_qty=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids14.id])])
	
	ids15=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')])
	pre_qty=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids15.id])])
	
	ids16=self.env['sale.order.line.status'].search([('n_string','=','paid')])
	paid_qty=self.env['sale.order.line'].search([('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids16.id])])

	cancel_pr = self.env['n.manufacturing.request'].search([('n_state','=','cancel'),('check_bool','=',False)])
	#new_rm_request=self.env['mrp.raw.material.request'].search([('state','=','draft'),('request_type','=','normal')])
        #extra_rm_request=self.env['mrp.raw.material.request'].search([('state','=','draft'),('request_type','=','extra')])
        #transfer_orders=self.env['stock.picking'].search([('state','=','confirmed'),('production_id','!=',False)])
	instrct=0
	new_id=self.env['process.instruction'].search([('id','>',0)],limit=1)
	if new_id:
		for rec in new_id.all_messages_line:
			if self.env.user.id != rec.create_uid.id:
				rec_user=[]		# to store send users
				for n_usr in rec.send_user_id:
					rec_user.append(n_usr.id)  # get send users
				if self.env.user.id in rec_user:	#compare current user with send users
					rd_user=[]
					for m_usr in rec.read_user_id:
						print "inside---"
						rd_user.append(m_usr.id) 
					if self.env.user.id not in rd_user:
						instrct +=1
	return {
		'new_state':len(new_state),
		'production_request':len(pr_state),
		'purchase':len(purchase),
		'manufacture':len(man_state),
		'warehouse':len(ware_state),
		'quality_check':len(qac_state),
		'r_t_dispatch':len(rtdisp_state),
		'dispatch':len(disp_state),
		'partial_dispatch':len(pardisp_state),
		'partial_delivery':len(pardel_state),
		'delivered':len(delv_state),
		'partial_invoice':len(parinv_state),
		'invoiced':len(inv_state),
		'date_request':len(date_req),
                'paid':len(paid_qty),
                'pre_stock':len(pre_qty),
                #'transfer':len(transfer_orders),
		'extra_qty':len(ext_qty),
		'cancel_pr_request':len(cancel_pr),
		'instrct':instrct,
		}
    @api.one
    def _get_detail(self):
        self.status_dashboard = json.dumps(self._get_statedetail())

    status_dashboard = fields.Text(compute = '_get_detail')

#CH_N129<<<<< Get Instruction<<<
    @api.multi
    def action_instruction(self):
    	sale_ids=[]
	new_id=self.env['process.instruction'].search([('id','>',0)])
	if new_id:
            for each_new in new_id:
		for rec in each_new.all_messages_line:
			if self.env.user.id != rec.create_uid.id:
				rec_user=[]		# to store send users
				for n_usr in rec.send_user_id:
					rec_user.append(n_usr.id)  # get send users
				if self.env.user.id in rec_user:	#compare current user with send users
					rd_user=[]
					for m_usr in rec.read_user_id:
						print "inside---"
						rd_user.append(m_usr.id) 
					if self.env.user.id not in rd_user:
						sale_ids.append(rec.sale_id.id)
						
	so_tree = self.env.ref('gt_sale_quotation.sale_quotation_view_quotation_tree', False)
	so_form = self.env.ref('sale.view_order_form', False)
        if so_form:
            return {
		'name':"Sale Orders List",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'sale.order',
		'views': [(so_tree.id, 'tree'), (so_form.id, 'form')],
                'view_id': so_tree.id,
                'target': 'current',
		'domain':[('id', 'in',sale_ids)],
            }

    @api.multi
    def action_stateopen(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'new':
		ids=self.env['sale.order.line.status'].search([('n_string','=','new')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='New Records'

	if self._context.get('n_state') == 'production_request':
		ids=self.env['sale.order.line.status'].search([('n_string','=','production_request')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Production Request Sent'

	if self._context.get('n_state') == 'manufacture':
		ids=self.env['sale.order.line.status'].search([('n_string','=','manufacture')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Manufacturing'

	if self._context.get('n_state') == 'purchase':
		ids=self.env['sale.order.line.status'].search([('n_string','=','purchase')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Purchase'

	if self._context.get('n_state') == 'warehouse':
		ids=self.env['sale.order.line.status'].search([('n_string','=','warehouse')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Warehouse'

	if self._context.get('n_state') == 'quality_check':
		ids=self.env['sale.order.line.status'].search([('n_string','=','quality_check')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Quality Check'

	if self._context.get('n_state') == 'r_t_dispatch':
		ids=self.env['sale.order.line.status'].search([('n_string','=','r_t_dispatch')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Ready To Dispatch'

	if self._context.get('n_state') == 'dispatch':
		ids=self.env['sale.order.line.status'].search([('n_string','=','dispatch')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Dispatch'
	if self._context.get('n_state') == 'partial_dispatch':
		ids=self.env['sale.order.line.status'].search([('n_string','=','partial_dispatch')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Partial Dispatch'

	if self._context.get('n_state') == 'partial_delivery':
		ids=self.env['sale.order.line.status'].search([('n_string','=','partial_delivery')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='In Partial Delivery'

	if self._context.get('n_state') == 'delivered':
		ids=self.env['sale.order.line.status'].search([('n_string','=','delivered')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Delivery'

	if self._context.get('n_state') == 'partial_invoice':
		ids=self.env['sale.order.line.status'].search([('n_string','=','partial_invoice')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Partial Invoice'

	if self._context.get('n_state') == 'invoiced':
		ids=self.env['sale.order.line.status'].search([('n_string','=','invoiced')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Invoiced'

	if self._context.get('n_state') == 'date_request':
		ids=self.env['sale.order.line.status'].search([('n_string','=','date_request')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Production Requested'
	if self._context.get('n_state') == 'extra_qty':
		ids=self.env['sale.order.line.status'].search([('n_string','=','extra_product')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Extra Product Reserved'
	if self._context.get('n_state') == 'paid_qty':
		ids=self.env['sale.order.line.status'].search([('n_string','=','paid')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Paid Product'
	if self._context.get('n_state') == 'pre_stock':
		ids=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')])
		domain=[('product_id.name','not in',('Advance Payment','Deposit Product')),('order_id.state','=','sale'),('state','!=','done'),('n_status_rel', 'in',[ids.id])]
		_name='Pre-Stock Products'
	
	po_tree = self.env.ref('gt_order_mgnt.sale_support_view_new', False)
        if po_tree:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'sale.order.line',
		'views': [(po_tree.id, 'tree')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }
    @api.multi
    def action_rawmaterial(self):
	domain=[]
	_name=''
        lst=[]
        rq_tree=0
        rq_form=0
        res_model=''
	if self._context.get('n_reqeust') == 'request':
		ids=self.env['mrp.raw.material.request'].search([('state','=','draft'),('request_type','=','normal')])
                for ln in  ids:
                    lst.append((ln.id))
		domain=[('id', 'in',lst)]
		_name='Raw Material Requested'
                res_model='mrp.raw.material.request'
                rq_tree = self.env.ref('gt_order_mgnt.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.mrp_production_rawmaterial_request_form',False)
        if self._context.get('n_reqeust') == 'extra':
		ids=self.env['mrp.raw.material.request'].search([('state','=','draft'),('request_type','=','extra')])
                for ln in  ids:
                    lst.append((ln.id))
		domain=[('id', 'in',lst)]
		_name='Extra Raw Material Requested'
                res_model='mrp.raw.material.request'
                rq_tree = self.env.ref('gt_order_mgnt.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.mrp_production_rawmaterial_request_form',False)
	if self._context.get('n_reqeust') == 'transfer':
		ids=self.env['stock.picking'].search([('state','=','confirmed'),('production_id','!=',False)])
                for ln in  ids:
                    lst.append((ln.id))
		domain=[('id', 'in',lst)]
		_name='New Transfers Orders'
                res_model='stock.picking'
                rq_tree = self.env.ref('stock.vpicktree', False)
                rq_form =self.env.ref('stock.view_picking_form',False)
        if rq_tree:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': res_model,
		'views': [(rq_tree.id, 'tree'),(rq_form.id, 'form')],
                'view_id': rq_tree.id,
                'target': 'current',
		'domain':domain,
            }
#CH_N075<<<<< Sale Status END<<<
    @api.multi
    def action_openpr(self):
	po_tree = self.env.ref('gt_order_mgnt.n_production_request_tree_history', False)
        if po_tree:
            return {
		'name':'Cancel Production Requests',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'n.manufacturing.request',
		'views': [(po_tree.id, 'tree')],
                'view_id': po_tree.id,
                'target': 'current',
		'context':{'show_cancel':True},
		'domain':[('n_state','=','cancel'),('check_bool','=',False)],
            }

#CH_N075<<<<< Delivery Start>>

    @api.multi
    def _get_delivery(self):
	todays_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '=',datetime.strftime(date.today(),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
	tomorrow_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '=',datetime.strftime(date.today()+timedelta(1),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
	thisweek_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today(),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(6),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
	nextweek_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(7),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(13),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
	month_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(7),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(30),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
        next_month_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(30),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(60),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])

	delay_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('min_date', '<',datetime.strftime(date.today(),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))])
        dispatch_rescheduled = 0
	for rec in self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('state','=','transit')]):
		if rec.min_date != rec.dispatch_date:
			dispatch_rescheduled += 1

	dispatch_delivery = self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('state','=','done')])

	yesterday_delivery = self.env['stock.picking'].search([('min_date', '=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('state','in',('done','delivered'))])
	previousweek_delivery = self.env['stock.picking'].search([('min_date', '<=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('min_date', '>=',datetime.strftime(date.today()-timedelta(7),'%Y-%m-%d')),('state','in',('done','delivered'))])
	prevoiusmonth_delivery = self.env['stock.picking'].search([('min_date', '<=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('min_date', '>=',datetime.strftime(date.today()-timedelta(30),'%Y-%m-%d')),('state','in',('done','delivered'))])

	return {
		'todays_delivery': len(todays_delivery),
		'tomorrow_delivery': len(tomorrow_delivery),
		'thisweek_delivery': len(thisweek_delivery),
		'nextweek_delivery': len(month_delivery),
		'thismonth_delivery': len(nextweek_delivery),
                'next_month_delivery':len(next_month_delivery),
		'delay_delivery':len(delay_delivery),
		'dispatch_rescheduled':dispatch_rescheduled,
		'dispatch_delivery':len(dispatch_delivery),
		'yesterday_delivery': len(yesterday_delivery),
		'previousweek_delivery':len(previousweek_delivery),
		'prevoiusmonth_delivery': len(prevoiusmonth_delivery),}

    @api.one
    def _get_deliverydata(self):
        self.delivery_dashboard = json.dumps(self._get_delivery())

    delivery_dashboard = fields.Text(compute = '_get_deliverydata')

    @api.multi
    def action_delivery(self):
	domain=[]
	_name=''
	if self._context.get('n_state') == 'n_today':
		domain=[('picking_type_code','=','outgoing'),('min_date', '=',datetime.strftime(date.today(),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "Todays Delivery Orders"
	if self._context.get('n_state') == 'n_tommr':
		domain=[('picking_type_code','=','outgoing'),('min_date', '=',datetime.strftime(date.today()+timedelta(1),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "Tomorrow Deliver Orders"
	if self._context.get('n_state') == 'n_week':
		domain=[('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today(),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(6),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "This Week Delivery Orders"
	if self._context.get('n_state') == 'n_nweek':
		domain=[('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(7),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(13),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "Next Week Delivery Orders"
	if self._context.get('n_state') == 'n_month':
		domain=[('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(7),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(30),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "This Month Delivery Orders"
        if self._context.get('n_state') == 'next_month':
		domain=[('picking_type_code','=','outgoing'),('min_date', '>=',datetime.strftime(date.today()+timedelta(30),'%Y-%m-%d')),('min_date', '<=',datetime.strftime(date.today()+timedelta(60),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "Next Month Delivery Orders"

	if self._context.get('n_state') == 'n_delay':
		domain=[('picking_type_code','=','outgoing'),('min_date', '<',datetime.strftime(date.today(),'%Y-%m-%d')),('state','not in',('done','delivered','cancel'))]
		_name = "Delayed Delivery Orders"

	if self._context.get('n_state') == 'n_dispatch':
		domain=[('picking_type_code','=','outgoing'),('state','=','done')]
		_name = "Dispatched Delivery Orders"
	
	if self._context.get('n_state') == 'n_rescheduled':
		li_ids=[]
		for rec in self.env['stock.picking'].search([('picking_type_code','=','outgoing'),('state','=','transit')]):
			if rec.min_date != rec.dispatch_date:
				li_ids.append(rec.id)
		domain=[('id', 'in',li_ids)]
		_name = "Re-scheduled Dispatch Date"

	if self._context.get('n_state') == 'n_yester':
		domain=[('picking_type_code','=','outgoing'),('min_date', '=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('state','in',('done','delivered','cancel'))]
		_name = "YesterDay's Delivery Orders"
	if self._context.get('n_state') == 'n_prevw':
		domain=[('picking_type_code','=','outgoing'),('min_date', '<=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('min_date', '>=',datetime.strftime(date.today()-timedelta(7),'%Y-%m-%d')),('state','in',('done','delivered'))]
		_name = "Prevoius Week Delivery Orders"
	if self._context.get('n_state') == 'n_prevm':
		domain=[('picking_type_code','=','outgoing'),('min_date', '<=',datetime.strftime(date.today()-timedelta(1),'%Y-%m-%d')),('min_date', '>=',datetime.strftime(date.today()-timedelta(30),'%Y-%m-%d')),('state','in',('done','delivered'))]
		_name = "Prevoius Month Delivery Orders"

	po_tree = self.env.ref('stock.vpicktree', False)
	po_form = self.env.ref('stock.view_picking_form', False)
        if po_form:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'stock.picking',
		'views': [(po_tree.id, 'tree'), (po_form.id, 'form')],
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }
#CH_N075<<<<< Delivery  END<<<

#CH_N105 action for credit requests
    @api.multi
    def action_quotation(self):
	qo_tree = self.env.ref('gt_sale_quotation.sale_quotation_view_quotation_tree', False)
	qo_form = self.env.ref('sale.view_order_form', False)
        if qo_form:
            return {
		'name':"Quotaion List",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'sale.order',
		'views': [(qo_tree.id, 'tree'), (qo_form.id, 'form')],
                'view_id': qo_tree.id,
                'target': 'current',
		'domain':[('state', 'in', ('draft','sent'))],
            }
    @api.multi
    def action_sale(self):
	so_tree = self.env.ref('gt_sale_quotation.sale_quotation_view_quotation_tree', False)
	so_form = self.env.ref('sale.view_order_form', False)
        if so_form:
            return {
		'name':"Sale Orders List",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'sale.order',
		'views': [(so_tree.id, 'tree'), (so_form.id, 'form')],
                'view_id': so_tree.id,
                'target': 'current',
		'domain':[('state', '=', 'sale')],
            }
    @api.multi
    def _get_credit(self):
	credit_request = self.env['res.partner.credit'].search([('state','=','request'),('delivery_id','=',False)])
	credit_approved = self.env['res.partner.credit'].search([('state','=','approve'),('sale_id.state','=','awaiting'),('delivery_id','=',False)])
	credit_reject = self.env['res.partner.credit'].search([('state','=','reject'),('delivery_id','=',False)])

	credit_request_delivery = self.env['res.partner.credit'].search([('state','=','request'),('delivery_id','!=',False)])
	credit_approved_delivery = self.env['res.partner.credit'].search([('state','=','approve'),('delivery_id','!=',False)])
	credit_reject_delivery = self.env['res.partner.credit'].search([('state','=','reject'),('delivery_id','!=',False)])
	return {
		'credit_request': len(credit_request),
		'credit_approved': len(credit_approved),
		'credit_reject': len(credit_reject),
		'credit_request_delivery': len(credit_request_delivery),
		'credit_approved_delivery': len(credit_approved_delivery),
		'credit_reject_delivery': len(credit_reject_delivery),}

    @api.one
    def _get_credit_request(self):
        self.credit_request_dashboard = json.dumps(self._get_credit())

    credit_request_dashboard = fields.Text(compute = '_get_credit_request')

    @api.multi
    def action_credit_request(self):
	domain=[]
	_name=''
	if self._context.get('n_credit') == 'request':
		domain=[('state','=','request')]
		_name = 'Customer Credit Request (Sale Order)'
	if self._context.get('n_credit') == 'approve':
		domain=[('state','=','approve'),('sale_id.state','=','awaiting'),('delivery_id','=',False)]
		_name = 'Customer Credit Approved (Sale Order)'
	if self._context.get('n_credit') == 'reject':
		domain=[('state','=','reject')]
		_name = 'Customer Credit Reject (Sale Order)'

	if self._context.get('n_credit') == 'd_request':
		domain=[('state','=','request'),('delivery_id','!=',False)]
		_name = 'Customer Credit Request (Delivery Order)'
	if self._context.get('n_credit') == 'd_approve':
		domain=[('state','=','approve'),('delivery_id','!=',False)]
		_name = 'Customer Credit Approved (Delivery Order)'
	if self._context.get('n_credit') == 'd_reject':
		domain=[('state','=','reject'),('delivery_id','!=',False)]
		_name = 'Customer Credit Reject (Delivery Order)'
        return {
            'name': _name,
            'view_type': 'form',
            'view_mode': 'tree,',
            'res_model': 'res.partner.credit',
            'view' : [(self.env.ref('gt_order_mgnt.customer_credit_tree').id, 'tree')],
            'type': 'ir.actions.act_window',
           'domain' : domain,
            'context' : {'search_default_requested' : 1}
        }
   
    @api.multi
    def action_order_contract_expr(self):
        requests = self.env['customer.contract'].search([('expiry_date', '<',date.today() + timedelta(7) )])
        return {
            'name': 'Expr Contract Order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'customer.contract',
            'view' : [(self.env.ref('gt_order_mgnt.customer_contract_tree_view').id, 'tree'), (self.env.ref('gt_order_mgnt.customer_contract_form_view').id, 'form')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_requested' : 1}
        }

    @api.multi
    def action_order_contract_expr(self):
        requests = self.env['customer.contract'].search([('expiry_date', '<',date.today() + timedelta(7) )])
        return {
            'name': 'Contract Product MSQ',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'customer.contract',
            'view' : [(self.env.ref('gt_order_mgnt.customer_contract_tree_view').id, 'tree'), (self.env.ref('gt_order_mgnt.customer_contract_form_view').id, 'form')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests._ids)],
            'context' : {'search_default_requested' : 1}
        }

    @api.multi
    def action_open_exp_contract(self):
        records = self.env['customer.contract'].search([('sale_id', '!=', False),('state','in',('contract','sale'))])
        requests=[]
	for req in records:
            	for pro in req.contract_line:
                	if pro.qty_avl_open < pro.product_msq:
                   		requests.append(pro.id)
        return {
            'name': 'Expire Contract Order',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'contract.product.line',
            'view' : [(self.env.ref('gt_order_mgnt.customer_contract_line_tree_view').id, 'tree')],
            'type': 'ir.actions.act_window',
            'domain' : [('id', 'in', requests)],
            'context' : {'search_default_requested' : 1}
        }
        
    @api.multi
    def get_expr_contract_data_product(self):
        for obj in self:
            count =0
            requests = self.env['customer.contract'].search([('sale_id', '!=', False),('state','in',('contract','sale'))])
            for req in requests:
            	for pro in req.contract_line:
                	if pro.qty_avl_open < pro.product_msq:
                   		count +=1
            obj.expr_contract_product = count
                
    @api.multi
    def get_expr_contract_data(self):
        for obj in self:
            requests = self.env['customer.contract'].search([('expiry_date', '<',date.today() + timedelta(7) )]) 
            obj.expr_contract = len(requests)
            
    expr_contract_product=fields.Integer("#Expr contract", compute=get_expr_contract_data_product)
    expr_contract=fields.Integer("#Expr contract", compute=get_expr_contract_data)

