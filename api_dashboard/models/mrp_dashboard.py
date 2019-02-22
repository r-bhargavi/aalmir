from openerp import fields, models ,api, _
from openerp.exceptions import UserError, ValidationError
import logging
from datetime import datetime
import datetime
from dateutil.relativedelta import *
from datetime import date,datetime,timedelta
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
import json

class CustomMrpDashboard(models.Model):
    _name = "custom.mrp.dashboard"
    
    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name")
    active = fields.Boolean('Active',default=True)
    
    @api.multi
    def _get_statedetail(self):
        days= datetime.today().day
        mrp_production=self.env['mrp.production']
        purchase_order=self.env['purchase.order']
        mrp_workorder=self.env['mrp.production.workcenter.line']
        mrp_request=self.env['n.manufacturing.request']
        bom_request=self.env['mrp.bom']
        picking_obj=self.env['stock.picking']
        location_obj=self.env['stock.location']
        
        total_mrp_count = self.env['mrp.production'].search(
            [])
        complete_mrp_count = mrp_production.search(
            [('state', '=', 'done')])
        new_mrp_count = mrp_production.search(
            [('state', '=', 'draft')])
        awaiting_mrp_count = mrp_production.search(
            [('state', '=', 'confirmed')])
	cancel_mrp_count = mrp_production.search(
            [('state', '=', 'cancel')])
        hold_mrp_count = mrp_production.search(
            [('hold_order', '=', 'hold')])
        progress_mrp_count = mrp_production.search(
            [('state', '=', 'in_production')])
        today_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        tomorrow_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        week_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        month_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        today_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'done')])
        tomorrow_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'done')])
        week_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'done')])
        month_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'done')])
        ### MRP Work Orders
        today_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'draft')])
        tomorrow_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('state', '=', 'draft'))])
        week_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'draft')])
        month_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>', (datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'draft')])
    
        new_work_count = mrp_workorder.search(
            [('state', '=', 'draft')])
        start_work_count = mrp_workorder.search(
            [('state', '=', 'startworking')])
        pause_work_count = mrp_workorder.search(
            [('state', '=', 'pause')])
        done_work_count = mrp_workorder.search(
            [('state', '=', 'done')])
        cancel_work_count = mrp_workorder.search(
            [('state', '=', 'cancel')])        
        hold_work_count = mrp_workorder.search(
            [('hold_order', '=', 'hold')])
        ready_work_count = mrp_workorder.search(
            [('state', '=', 'ready')])

        mrp=mrp_production.search([('state', 'in', ('draft', 'confirmed','ready','in_production'))])
        pur=pur_conf=pur_done=pur_cancel=0
        
        for mpr_line in mrp:
            purchase=purchase_order.search([('production_ids','=',mpr_line.id),('state','=','draft')]) 
            purchase_conf=purchase_order.search([('production_ids','=',mpr_line.id),('state','=','purchase')]) 
            purchase_done=purchase_order.search([('production_ids','=',mpr_line.id),('state','=','done')]) 
            purchase_cancel=purchase_order.search([('production_ids','=',mpr_line.id),('state','=','cancel')])  
            pur += len(purchase)
            pur_conf +=len(purchase_conf)
            pur_done +=len(purchase_done)
            pur_cancel +=len(purchase_cancel)
            
        sales_request_count = len(mrp_request.search([('request_type', '=', 'sale'),('n_state','=','draft')]))
	contract_request_count = len(mrp_request.search([('request_type', '=', 'contract'),('n_state','=','draft')]))
        stock_request_count = len(mrp_request.search([('request_type', '=', 'stock'),('n_state','=','draft')]))
        material_request_count = len(mrp_request.search([('request_type', '=', 'raw'),('n_state','=','draft')]))
        bom_request_count = len(bom_request.search([('state','in',('sent_for_app','app_rem_sent'))]))
        bom_app_request_count = len(bom_request.search([('state','=','approve')]))
        bom_rej_request_count = len(bom_request.search([('state','=','reject')]))
        bom_draft_request_count = len(bom_request.search([('state','=','draft')]))
        rm_virtual_available = picking_obj.search([('ntransfer_type', '=','rm_production'),('state','!=','done')])
        rm_virtual_done = picking_obj.search([('ntransfer_type', '=','rm_production'),('state','=','done')])
        
        loc_id=location_obj.search([('usage','=','production')],limit=1)
	done_pick=picking_obj.search([('location_id','=',loc_id.id),('state','=','done')])
	done_names = [ pic.name for pic in done_pick ]
	
	reject_trns_count = picking_obj.search([('location_dest_id','=',loc_id.id),('name','like','RE')])
	
	done_pick=picking_obj.search([('origin','in',done_names),('state','not in',('done','cancel'))])
	waiting_trns_count = picking_obj.search([('name','in',[pic.origin for pic in done_pick])])
	
	done_pick=picking_obj.search([('origin','in',done_names),('state','=','done')])
       	done_trns_count = picking_obj.search([('name','in',[pic.origin for pic in done_pick])])
        
        draft_trns_count = picking_obj.search([('location_id','=',loc_id.id),('state','not in',('done','cancel'))])
        return {
		'today_work_start':len(today_work_start),
		'tomorrow_work_start':len(tomorrow_work_start),
		'week_work_start':len(week_work_start),
		'month_work_start':len(month_work_start),
		'new_work_count':len(new_work_count),
		'start_work_count':len(start_work_count),
		'pause_work_count':len(pause_work_count),
		'done_work_count':len(done_work_count),
		'cancel_work_count':len(cancel_work_count),
		'hold_work_count':len(hold_work_count),
                'ready_work_count':len(ready_work_count),
		'total_mrp_count':len(total_mrp_count),
		'complete_mrp_count':len(complete_mrp_count),
		'cancel_mrp_count':len(cancel_mrp_count),
		'hold_mrp_count':len(hold_mrp_count),
		'new_mrp_count':len(new_mrp_count),
		'awaiting_mrp_count':len(awaiting_mrp_count),
		'progress_mrp_count':len(progress_mrp_count),
		'today_mrp_start':len(today_mrp_start),
		'tomorrow_mrp_start':len(tomorrow_mrp_start),
		'week_mrp_start':len(week_mrp_start),
		'month_mrp_start':len(month_mrp_start),
		'today_mrp_completed':len(today_mrp_completed),
		'tomorrow_mrp_completed':len(tomorrow_mrp_completed),
		'week_mrp_completed':len(week_mrp_completed),
		'month_mrp_completed':len(month_mrp_completed),
		'total_purchase_new':pur,
		'total_purchase_confirmed':pur_conf,
		'total_purchase_done':pur_done,
		'total_purchase_cancel':pur_cancel,
                'sales_request_count':(sales_request_count),
                'bom_request_count':(bom_request_count),
                'bom_app_request_count':(bom_app_request_count),
                'bom_rej_request_count':(bom_rej_request_count),
                'bom_draft_request_count':(bom_draft_request_count),
                'contract_request_count':(contract_request_count),
                'stock_request_count':(stock_request_count),
                'material_request_count':(material_request_count),
                'rm_virtual_available':len(rm_virtual_available),
                'rm_virtual_done':len(rm_virtual_done),
                
                'draft_trns_count':len(draft_trns_count),
                'reject_trns_count':len(reject_trns_count),
                'waiting_trns_count':len(waiting_trns_count),
                'done_trns_count':len(done_trns_count),
               }
    @api.one
    def _get_detail(self):
        self.status_dashboard = json.dumps(self._get_statedetail())

    status_dashboard = fields.Text(compute = '_get_detail')

    @api.multi
    def action_stateopen(self):
	domain=[]
	_name=''
        if self._context.get('n_state') == 'not_receive':
		domain=[('ntransfer_type', '=','rm_production'),('state','!=','done')]
		_name='RM Delivery Not Received'

        if self._context.get('n_state') == 'received':
		domain=[('ntransfer_type', '=','rm_production'),('state','=','done')]
		_name='RM Delivery Received'

	rq_tree = self.env.ref('stock.vpicktree', False)
        rq_form =self.env.ref('stock.view_picking_form',False)
        if rq_tree:
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model':'stock.picking',
		'views': [(rq_tree.id, 'tree'),(rq_form.id, 'form')],
                'view_id': rq_tree.id,
                'target': 'current',
		'domain':domain,
            }

    '''@api.one
    def _get_count(self):
        days= datetime.today().day
        mrp_production=self.env['mrp.production']
        mrp_workorder=self.env['mrp.production.workcenter.line']
        total_mrp_count = self.env['mrp.production'].search(
            [])
        #total_new_pr=self.env['n.manufacturing.request'].search([('n_state', '=', 'draft')])
        #total_new_history=self.env['n.manufacturing.request'].search([('n_state', 'not in', ('draft','new'))])
        complete_mrp_count = mrp_production.search(
            [('state', '=', 'done')])
        new_mrp_count = mrp_production.search(
            [('state', '=', 'draft')])
        awaiting_mrp_count = mrp_production.search(
            [('state', '=', 'confirmed')])
	cancel_mrp_count = mrp_production.search(
            [('state', '=', 'cancel')])
        hold_mrp_count = mrp_production.search(
            [('hold_order', '=', 'hold')])
        progress_mrp_count = mrp_production.search(
            [('state', '=', 'in_production')])
        today_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        tomorrow_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        week_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        month_mrp_start = mrp_production.search(
            [('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state', 'in', ('draft','in_production','confirmed', 'ready'))])
        today_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'done')])
        tomorrow_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'done')])
        week_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'done')])
        month_mrp_completed = mrp_production.search(
            [('n_request_date','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'done')])
        ### MRP Work Orders
        today_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'draft')])
        tomorrow_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('state', '=', 'draft'))])
        week_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'draft')])
        month_work_start = mrp_workorder.search(
            [('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>', (datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'draft')])
    
        new_work_count = mrp_workorder.search(
            [('state', '=', 'draft')])
        start_work_count = mrp_workorder.search(
            [('state', '=', 'startworking')])
        pause_work_count = mrp_workorder.search(
            [('state', '=', 'pause')])
        done_work_count = mrp_workorder.search(
            [('state', '=', 'done')])
        cancel_work_count = mrp_workorder.search(
            [('state', '=', 'cancel')])        
        hold_work_count = mrp_workorder.search(
            [('hold_order', '=', 'hold')])
        self.today_work_start=len(today_work_start)
        self.tomorrow_work_start=len(tomorrow_work_start)
        self.week_work_start=len(week_work_start)
        self.month_work_start=len(month_work_start)

        self.new_work_count=len(new_work_count)
        self.start_work_count=len(start_work_count)
        self.pause_work_count=len(pause_work_count)
        self.done_work_count=len(done_work_count)
        self.cancel_work_count=len(cancel_work_count)
        self.hold_work_count=len(hold_work_count)
        #self.total_new_history=len(total_new_history)
        self.total_mrp_count=len(total_mrp_count)
        #self.total_new_pr=len(total_new_pr)
        self.complete_mrp_count = len(complete_mrp_count)
        self.cancel_mrp_count = len(cancel_mrp_count)
        self.hold_mrp_count = len(hold_mrp_count)
        self.new_mrp_count = len(new_mrp_count)
        self.awaiting_mrp_count = len(awaiting_mrp_count)
        self.progress_mrp_count = len(progress_mrp_count)
        self.today_mrp_start=len(today_mrp_start)
        self.tomorrow_mrp_start=len(tomorrow_mrp_start)
        self.week_mrp_start=len(week_mrp_start)
        self.month_mrp_start=len(month_mrp_start)
        self.today_mrp_completed=len(today_mrp_completed)
        self.tomorrow_mrp_completed=len(tomorrow_mrp_completed)
        self.week_mrp_completed=len(week_mrp_completed)
        self.month_mrp_completed=len(month_mrp_completed)
        mrp=self.env['mrp.production'].search([('state', 'in', ('draft', 'confirmed','ready','in_production'))])
        pur=pur_conf=pur_done=pur_cancel=0
        for mpr_line in mrp:
            purchase=self.env['purchase.order'].search([('production_ids','=',mpr_line.id),('state','=','draft')]) 
            purchase_conf=self.env['purchase.order'].search([('production_ids','=',mpr_line.id),('state','=','purchase')]) 
            purchase_done=self.env['purchase.order'].search([('production_ids','=',mpr_line.id),('state','=','done')]) 
            purchase_cancel=self.env['purchase.order'].search([('production_ids','=',mpr_line.id),('state','=','cancel')])  
            pur += len(purchase)
            pur_conf +=len(purchase_conf)
            pur_done +=len(purchase_done)
            pur_cancel +=len(purchase_cancel)
        self.total_purchase_new=pur
	self.total_purchase_confirmed=pur_conf
        self.total_purchase_done=pur_done
        self.total_purchase_cancel=pur_cancel
    
        #manufacturing Requests
        sales_request_count=len(self.env['n.manufacturing.request'].search([('request_type', '=', 'sale'),('n_state','=','draft')]))
	contract_request_count=len(self.env['n.manufacturing.request'].search([('request_type', '=', 'contract'),('n_state','=','draft')]))
        stock_request_count=len(self.env['n.manufacturing.request'].search([('request_type', '=', 'stock'),('n_state','=','draft')]))
        material_request_count=len(self.env['n.manufacturing.request'].search([('request_type', '=', 'raw'),('n_state','=','draft')]))
        bom_request_count=len(self.env['mrp.bom'].search([('state','in',('sent_for_app','app_rem_sent'))]))
        bom_app_request_count=len(self.env['mrp.bom'].search([('state','=','approve')]))
        bom_rej_request_count=len(self.env['mrp.bom'].search([('state','=','reject')]))
        bom_draft_request_count=len(self.env['mrp.bom'].search([('state','=','draft')]))
   
    
    
    
    complete_mrp_count = fields.Integer(compute='_get_count')
    cancel_mrp_count = fields.Integer(compute='_get_count')
    hold_mrp_count = fields.Integer(compute='_get_count')
    progress_mrp_count = fields.Integer(compute='_get_count')
    new_mrp_count = fields.Integer(compute='_get_count')
    awaiting_mrp_count = fields.Integer(compute='_get_count')
    today_mrp_start=fields.Integer(compute='_get_count')
    tomorrow_mrp_start=fields.Integer(compute='_get_count')
    week_mrp_start=fields.Integer(compute='_get_count')
    month_mrp_start=fields.Integer(compute='_get_count')
    total_purchase_new=fields.Integer(compute='_get_count')
    total_purchase_confirmed=fields.Integer(compute='_get_count')
    total_purchase_done=fields.Integer(compute='_get_count')
    total_purchase_cancel=fields.Integer(compute='_get_count')
    today_mrp_completed=fields.Integer(compute='_get_count')
    tomorrow_mrp_completed=fields.Integer(compute='_get_count')
    week_mrp_completed=fields.Integer(compute='_get_count')
    month_mrp_completed=fields.Integer(compute='_get_count')
    #total_new_pr=fields.Integer(compute='_get_count')
    total_mrp_count=fields.Integer(compute='_get_count')
    #total_new_history=fields.Integer(compute='_get_count')
    ### work orders planned
   
    today_work_start=fields.Integer(compute='_get_count')
    tomorrow_work_start=fields.Integer(compute='_get_count')
    week_work_start=fields.Integer(compute='_get_count')
    month_work_start=fields.Integer(compute='_get_count')
    new_work_count = fields.Integer(compute='_get_count')
    start_work_count = fields.Integer(compute='_get_count')
    pause_work_count = fields.Integer(compute='_get_count')
    done_work_count = fields.Integer(compute='_get_count')
    cancel_work_count = fields.Integer(compute='_get_count')
    hold_work_count = fields.Integer(compute='_get_count')'''
    
    #@api.one
    #def _kanban_dashboard_graph(self):
#	    ids=self.env['account.journal'].search([('type','=','bank')],limit=1)
   #         self.kanban_dashboard_graph = json.dumps(ids.get_line_graph_datas())

   # kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    @api.multi
    def action_completed_mrp(self):
    	domain=[]
        days= datetime.today().day
    	name=""
    	if self._context.get('n_state')=='today':
    		domain=[('n_request_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')),('state', '=', 'done')]
    		name="Today MRP Completed"
	if self._context.get('n_state')=='tomorrow':
    		domain=[('n_request_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')),('state', '=', 'done')]
    		name="Tomorrow Start MRP"
	if self._context.get('n_state')=='week':
    		domain=[('n_request_date','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'done')]
    		name="Week Start MRP"
	if self._context.get('n_state')=='done':
    		domain=[('n_request_date','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state', '=', 'done')]
    		name="Month Start MRP"
    		
	mo_tree = self.env.ref('mrp.mrp_production_tree_view', False)
	mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        if mo_form:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'mrp.production',
		'views': [(mo_tree.id, 'tree'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }
            
    @api.multi
    def action_planning_mrp(self):
    	domain=[]
    	name=""
    	if self._context.get('n_state')=='today':
    		domain=[('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))]
    		name="Today Start MRP"
	if self._context.get('n_state')=='tomorrow':
    		domain=[('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', 'in', ('draft','in_production','confirmed', 'ready'))]
    		name="Tomorrow Start MRP"
	if self._context.get('n_state')=='week':
    		domain=[('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")), ('state', 'in', ('draft','in_production','confirmed', 'ready'))]
    		name="Week Start MRP"
	if self._context.get('n_state')=='done':
    		domain=[('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")), ('state', 'in', ('draft','in_production','confirmed', 'ready'))]
    		name="Month Start MRP"
    		
	mo_tree = self.env.ref('mrp.mrp_production_tree_view', False)
	mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        if mo_form:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'mrp.production',
		'views': [(mo_tree.id, 'tree'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }
            
    @api.multi
    def action_open_mrp(self):
    	domain=[]
    	name=""
    	if self._context.get('n_state') == 'new':
    		domain=[('state', '=', 'draft')]
    		name="New Start Manufacture Orders"
	if self._context.get('n_state')=='waiting':
    		domain=[('state', '=', 'confirmed')]
    		name=" Awaiting Raw materials"
	if self._context.get('n_state')=='in-process':
    		domain=[('state', '=', 'in_production')]
    		name=" In-Process Order"
	if self._context.get('n_state')=='done':
    		domain=[('state', '=', 'done')]
    		name=" Done Manufacture Order"
	if self._context.get('n_state')=='cancel':
    		domain=[('state', '=', 'cancel')]
    		name=" Cancel Manufacture Order"
        if self._context.get('n_state')=='hold':
    		domain=[('hold_order', '=', 'hold')]
    		name=" Hold Manufacture Order"
        		
	mo_tree = self.env.ref('mrp.mrp_production_tree_view', False)
	mo_form = self.env.ref('mrp.mrp_production_form_view', False)
        if mo_form:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'mrp.production',
		'views': [(mo_tree.id, 'tree'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }

    @api.multi
    def action_purchase_open(self):
    	domain=[]
    	name=""
    	if self._context.get('n_state')=='new':
    		domain=[('state', '=', 'draft'),('production_ids', '!=', [])]
    		name=" New Purchase Order"
	if self._context.get('n_state')=='confirmed':
    		domain=[('state', '=', 'purchase'),('production_ids', '!=', [])]
    		name=" Confirmed Purchase Order"
	if self._context.get('n_state')=='done':
    		domain=[('state', '=', 'done'),('production_ids', '!=', [])]
    		name=" Done Purchase Order"
	if self._context.get('n_state')=='cancel':
    		domain=[('state', '=', 'cancel'),('production_ids', '!=', [])]
    		name=" Cancel Purchase Order"
    	
	po_tree = self.env.ref('purchase.purchase_order_tree', False)
        if po_tree:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'purchase.order',
                'view_id': po_tree.id,
                'target': 'current',
		'domain':domain,
            }
            
    @api.multi
    def action_planning_workorders(self):
    	domain=[]
        days= datetime.today().day
    	name=""
    	if self._context.get('n_state')=='today':
    		domain=[('date_planned','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'draft')]
    		name="Today Start Work Orders"
	if self._context.get('n_state')=='tomorrow':
    		domain=[('date_planned','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('date_planned','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')), ('state', '=', 'draft')]
    		name="Tomorrow Start Work Orders"
	if self._context.get('n_state')=='week':
    		domain=[('date_planned','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'draft')]
    		name="Week Start Work Orders"
	if self._context.get('n_state')=='month':
    		domain=[('date_planned','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('date_planned','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")), ('state', '=', 'draft')]
    		name="Month Start Work Orders"
    		
	mo_tree = self.env.ref('stock_merge_picking.view_mrp_machine_calendar_inherite', False)
	mo_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
        if mo_tree:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'calendar',
                'res_model': 'mrp.production.workcenter.line',
		'views': [(mo_tree.id, 'calendar'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }
            
    @api.multi
    def action_workorder_open(self):
    	domain=[]
    	name=""
    	if self._context.get('n_state')=='new':
    		domain=[('state', '=', 'draft')]
    		name=" New Work Orders"
	if self._context.get('n_state')=='start':
    		domain=[('state', '=', 'startworking')]
    		name="Start Work Orders"
	if self._context.get('n_state')=='pause':
    		domain=[('state', '=', 'pause')]
    		name="Pause Work Orders"
	if self._context.get('n_state')=='completed':
    		domain=[('state', '=', 'done')]
    		name="Completed Work Orders"
    	if self._context.get('n_state')=='cancel':
    		domain=[('state', '=', 'cancel')]
    		name="Cancelled Work Orders"
        if self._context.get('n_state')=='hold':
    		domain=[('hold_order', '=', 'hold')]
    		name="Hold Work Orders"
        if self._context.get('n_state')=='ready':
    		domain=[('state', '=', 'ready')]
    		name="Ready Work Orders"

        mo_tree = self.env.ref('mrp_operations.mrp_production_workcenter_tree_view_inherit', False)
	mo_form = self.env.ref('mrp_operations.mrp_production_workcenter_form_view_inherit', False)
        if mo_form:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'mrp.production.workcenter.line',
		'views': [(mo_tree.id, 'tree'), (mo_form.id, 'form')],
                'view_id': mo_tree.id,
                'target': 'current',
		'domain':domain,
            }

# for opening record of production requests

    '''sales_request_count = fields.Integer(compute='_get_count')
    contract_request_count = fields.Integer(compute='_get_count')
    stock_request_count = fields.Integer(compute='_get_count')
    material_request_count = fields.Integer(compute='_get_count')'''
    
    @api.multi
    def action_open_production(self):
    	domain=[]
    	name=""
    	if self._context.get('n_state')=='sales':
    		domain=[('request_type', '=', 'sale'),('n_state','=','draft')]
    		name=" New Requests from Sales"
	if self._context.get('n_state')=='contract':
    		domain=[('request_type', '=', 'contract'),('n_state','=','draft')]
    		name=" New Requests from Contratc"
	if self._context.get('n_state')=='stock':
    		domain=[('request_type', '=', 'stock'),('n_state','=','draft')]
    		name=" New Requests from Stock"
	if self._context.get('n_state')=='raw_material':
    		domain=[('request_type', '=', 'raw'),('n_state','=','draft')]
    		name=" New Requests for Raw Material Mo"
        tree_view = self.env.ref('gt_order_mgnt.n_production_request_tree_history', False)
	form_view = self.env.ref('gt_order_mgnt.mrp_production_request_form', False)
        if tree_view:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'n.manufacturing.request',
		'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
                'view_id': tree_view.id,
                'target': 'current',
		'domain':domain,
            }
            
            
            # for opening records of BOMs pending approval

    '''bom_request_count = fields.Integer(compute='_get_count')
    bom_app_request_count = fields.Integer(compute='_get_count')
    bom_rej_request_count = fields.Integer(compute='_get_count')
    bom_draft_request_count = fields.Integer(compute='_get_count')'''
    
    @api.multi
    def action_open_bomp(self):
    	domain=[]
    	name=""
    	if self._context.get('state')=='sent_for_app':
    		domain=[('state', 'in', ('sent_for_app','app_rem_sent'))]
    		name="BOM Awaiting approval"
        if self._context.get('state')=='bom_approved':
                domain=[('state', '=', 'approve')]
                name="Approved BOM's"
        if self._context.get('state')=='bom_rejected':
                domain=[('state', '=', 'reject')]
                name="Rejected BOM's"
        if self._context.get('state')=='bom_draft':
                domain=[('state', '=', 'draft')]
                name="Draft BOM's"
                
        tree_view = self.env.ref('mrp.mrp_bom_tree_view', False)
	form_view = self.env.ref('mrp.mrp_bom_form_view', False)
        if tree_view:
            return {
		'name':name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'mrp.bom',
		'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
                'view_id': tree_view.id,
                'target': 'current',
		'domain':domain,
            }
            
            
            
    @api.multi
    def action_create_transfer(self):
	domain=[]
	form_view = self.env.ref('stock.view_picking_form', False)
	warehouse_obj=self.env['stock.warehouse']
	location_obj=self.env['stock.location']
	picking_type_obj=self.env['stock.picking.type']
	context=self._context.copy()
	if context.get('warehouse_name'):
		warehouse_id=warehouse_obj.search([('name','=',context.get('warehouse_name'))])
		manu_type = picking_type_obj.search([('name','=','Manufacturing Transfers'),('warehouse_id','=',warehouse_id.id)])
		context.update({'default_picking_type_id':manu_type.id if manu_type else warehouse_id.int_type_id.id,
				'default_ntransfer_type':'manufacturing',
				})
	else:
		raise UserError('No context found, please contact administrator')	
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
    def action_open_transfers(self):
	domain=[]
	tree_view = self.env.ref('stock.vpicktree', False)
	form_view = self.env.ref('stock.view_picking_form', False)
	location_obj=self.env['stock.location']
	pick_obj=self.env['stock.picking']
	context=self._context.copy()
	loc_id=location_obj.search([('usage','=','production')],limit=1)
	done_pick=pick_obj.search([('location_id','=',loc_id.id),('state','=','done')])
	done_names = [ pic.name for pic in done_pick ]
	if context.get('n_state')=='reject':
		domain.extend((('location_dest_id','=',loc_id.id),('name','like','RE')))
	elif context.get('n_state')=='waiting':
		done_pick=pick_obj.search([('origin','in',done_names),('state','not in',('done','cancel'))])
		domain.append(('name','in',[pic.origin for pic in done_pick]))
	elif context.get('n_state')=='done':
		done_pick=pick_obj.search([('origin','in',done_names),('state','=','done')])
		domain.append(('name','in',[pic.origin for pic in done_pick]))
	elif context.get('n_state')=='draft':
		domain.extend((('location_id','=',loc_id.id),('state','not in',('done','cancel'))))
	else:
		raise UserError('No context found in opening Transfers, please contact administrator')
	
        if form_view:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'stock.picking',
		'views': [(tree_view.id,'tree'),(form_view.id, 'form')],
                'view_id': tree_view.id,
                'target': 'current',
                'domain':domain,
                'context':context,
            }    
    
