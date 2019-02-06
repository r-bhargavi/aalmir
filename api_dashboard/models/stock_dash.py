from openerp import fields, models ,api, _
from openerp.exceptions import UserError, ValidationError
import logging
import openerp.addons.decimal_precision as dp
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
from datetime import datetime, date, timedelta
import json

class procurement_compute(models.Model):
    _inherit = 'procurement.orderpoint.compute'

    @api.multi
    def procure_calculation(self):
       
        #threaded_calculation = threading.Thread(target=self._procure_calculation_orderpoint, args=(cr, uid, ids, context))
       # threaded_calculation.start()
        return {'type': 'ir.actions.act_window_close'}
  
class CustomStockDashboard(models.Model):
    _name = "custom.stock.dashboard"

    @api.multi
    def get_count(self):
    	'''TO Open MSQ Product from Dashboard.'''
        for record in self:
	    reorder = self.env['stock.warehouse.orderpoint'].search([('active','=',True),('product_min_qty','>',0)])
	    product=[]
	    for line in reorder:
		if line.product_id.qty_available <= line.product_min_qty:
		   product.append((line.product_id.product_tmpl_id.id))
            p_tree = self.env.ref('product.product_template_tree_view', False)
            p_form = self.env.ref('product.product_template_only_form_view', False)
            context=self._context.copy()
            context.update({'msq':True,'group_by':'type'})
            if p_form:
               return {
			'name':"Minimum Stock Product List",
		        'type': 'ir.actions.act_window',
		        'view_type': 'form',
		        'view_mode': 'tree',
		        'res_model': 'product.template',
			'views': [(p_tree.id, 'tree'), (p_form.id, 'form')],
		        'view_id': p_tree.id,
		        'target': 'current',
		        'context':context,
			'domain':[('id','in',product)],
		    }

    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name") 
    @api.one
    def _kanban_dashboard_graph(self):
	    ids=self.env['account.journal'].search([('type','=','bank')],limit=1)
            self.kanban_dashboard_graph = json.dumps(ids.get_line_graph_datas())

    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    
    @api.multi
    def _get_statedetail(self):
        raw_request=self.env['mrp.raw.material.request']
        stock_picking=self.env['stock.picking']
        wastgae_request=self.env['mrp.order.batch.number']
	new_state=raw_request.search([('state', '=','draft'),('request_type', '=','normal')])
	approved_state=raw_request.search([('state', '=','approve'),('request_type', '=','normal')])
	cancel_state=raw_request.search([('state', '=','cancel'),('request_type', '=','normal')])

        extra_new_state=raw_request.search([('state', '=','draft'),('request_type', '=','extra')])
	extra_approved_state=raw_request.search([('state', '=','approve'),('request_type', '=','extra')])
	extra_cancel_state=raw_request.search([('state', '=','cancel'),('request_type', '=','extra')])
   
        new_wastage=wastgae_request.search([('request_state','=','draft'),('used_type','in',('grinding','scrap'))])
        approved_wastage=wastgae_request.search([('request_state','=','requested'),('used_type','in',('grinding','scrap'))])
        cancel_wastage=wastgae_request.search([('request_state','=','cancel'),('used_type','in',('grinding','scrap'))])
       
	rm_virtual_today=stock_picking.search([('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59'))])
        rm_virtual_tomorrow=stock_picking.search([('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59'))])

        rm_virtual_delay=stock_picking.search([('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59'))])
	schedule_picking=self.env['mrp.workorder.rm.shifts'].search([('status', '=','request')])
        total_proudct_min_qty=0.0
	reorder = self.env['stock.warehouse.orderpoint'].search([])
	for line in reorder:
	     if line.product_id.qty_available <= line.product_min_qty:
		total_proudct_min_qty += 1
        return_raw_material=stock_picking.search([('state','not in',('done','cancel')),('return_raw_picking','=',True)])

        pending_rqst=self.env['purchase.order'].search([('state','=',('awaiting'))])
        lst_rqst=[]
        for pend in pending_rqst:
            if pend.management_user.id == self.env.user.id and not pend.approve_mgnt: 
               lst_rqst.append(pend.id)
            if pend.procurement_user.id == self.env.user.id and not pend.approve_prq: 
               lst_rqst.append(pend.id)
            
            if pend.inventory_user.id == self.env.user.id and not pend.approve_inv: 
               lst_rqst.append(pend.id)

	return {
		'new_request':len(new_state),
		'approved_state':len(approved_state),
		'cancel_state':len(cancel_state),
                'extra_new_request':len(extra_new_state),
		'extra_approved_state':len(extra_approved_state),
		'extra_cancel_state':len(extra_cancel_state),
		'schedule_picking':len(schedule_picking),
                'total_proudct_min_qty':total_proudct_min_qty,
                'rm_virtual_today':len(rm_virtual_today),
                'rm_virtual_tomorrow':len(rm_virtual_tomorrow),
                'rm_virtual_delay':len(rm_virtual_delay),
                'new_wastage':len(new_wastage),
                'approved_wastage':len(approved_wastage),
                'cancel_wastage':len(cancel_wastage),
                'return_raw_material':len(return_raw_material),
                'pending_rqst':len(lst_rqst)
		}
		
    @api.one
    def _get_detail(self):
        self.status_dashboard = json.dumps(self._get_statedetail())

    status_dashboard = fields.Text(compute = '_get_detail')
    
    @api.multi
    def action_stateopen(self):
        print"YYYYYYYYYYYYYYy",self._context
	domain=[]
	_name=''
        rq_tree=rq_form=''
	if self._context.get('n_state') == 'new':
		domain=[('state', '=','draft'),('request_type', '=','normal')]
		_name='New Raw Material Request'
		model='mrp.raw.material.request'
		rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

	if self._context.get('n_state') == 'approve_request':
		domain=[('state', '=','approve'),('request_type', '=','normal')]
		_name='Approve Request'
		model='mrp.raw.material.request'
	        rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

	if self._context.get('n_state') == 'cancel':
		domain=[('state', '=','cancel'),('request_type', '=','normal')]
		_name='Cancel Request'
		model='mrp.raw.material.request'
                rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

        if self._context.get('n_state') == 'extra_new':
		domain=[('state', '=','draft'),('request_type', '=','extra')]
		_name='Extra New Raw Material Request'
		model='mrp.raw.material.request'
		rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

	if self._context.get('n_state') == 'extra_approve_request':
		domain=[('state', '=','approve'),('request_type', '=','extra')]
		_name='Extra RM Approve Request'
		model='mrp.raw.material.request'
	        rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

	if self._context.get('n_state') == 'extra_cancel':
		domain=[('state', '=','cancel'),('request_type', '=','extra')]
		_name='Extra RM Cancel Request'
		model='mrp.raw.material.request'
                rq_tree = self.env.ref('api_raw_material.mrp_production_rawmaterial_request_tree', False)
                rq_form =self.env.ref('api_raw_material.mrp_production_rawmaterial_request_form',False)

	if self._context.get('rm_delivery') == 'today':
		domain=[('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59'))]
		_name='Todays RM Delivery'
		model='stock.picking'
		rq_tree = self.env.ref('stock.vpicktree', False)
                rq_form =self.env.ref('stock.view_picking_form',False)

        if self._context.get('rm_delivery') == 'tomorrow':
		domain=[('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59'))]
		_name='Todays RM Delivery'
		model='stock.picking'
		rq_tree = self.env.ref('stock.vpicktree', False)
                rq_form =self.env.ref('stock.view_picking_form',False)

        if self._context.get('rm_delivery') == 'delay':
		domain=[('ntransfer_type', '=','rm_virtual'),('min_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('min_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59'))]
		_name='Todays RM Delivery'
		model='stock.picking'
		rq_tree = self.env.ref('stock.vpicktree', False)
                rq_form =self.env.ref('stock.view_picking_form',False)

        if self._context.get('raw_stock'):
		domain=[('state','not in',('done','cancel')),('return_raw_picking','=',True)]
		_name='Return Raw Material Details'
		model='stock.picking'
		rq_tree = self.env.ref('stock.vpicktree', False)
                rq_form =self.env.ref('stock.view_picking_form',False)

        if self._context.get('n_state') == 'wastage_new':
		domain=[('request_state','=','draft'),('used_type','in',('grinding','scrap'))]
		_name='New Wastage Request'
		model='mrp.order.batch.number'
		rq_tree = self.env.ref('api_raw_material.mrp_wastage_btach_tree', False)

        if self._context.get('n_state') == 'wastage_approved':
		domain=[('request_state','=','requested'),('used_type','in',('grinding','scrap'))]
		_name='Approved Wastage Request'
		model='mrp.order.batch.number'
		rq_tree = self.env.ref('api_raw_material.mrp_wastage_btach_tree', False)

        if self._context.get('n_state') == 'wastage_cancel':
		domain=[('request_state','=','cancel'),('used_type','in',('grinding','scrap'))]
		_name='Cancelled Wastage Request'
		model='mrp.order.batch.number'
		rq_tree = self.env.ref('api_raw_material.mrp_wastage_btach_tree', False)
        print"==================",rq_tree
        if self._context.get('request_pending'):
                pending_rqst=self.env['purchase.order'].search([('state','=',('awaiting'))])
		lst_rqst=[]
		for pend in pending_rqst:
		    if pend.management_user.id == self.env.user.id and not pend.approve_mgnt: 
		       lst_rqst.append(pend.id)
		    if pend.procurement_user.id == self.env.user.id and not pend.approve_prq: 
		       lst_rqst.append(pend.id)
		    
		    if pend.inventory_user.id == self.env.user.id and not pend.approve_inv: 
		       lst_rqst.append(pend.id)
		domain=[('id','in',lst_rqst)]

		_name='Pending Purchase Approval'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)
        if rq_tree:
            views=[]
            if rq_tree and rq_form:
               views=[(rq_tree.id, 'tree'),(rq_form.id, 'form')]
            else:
               views=[(rq_tree.id, 'tree')]
            return {
		'name':_name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': model,
		'views': views,
                'view_id': rq_tree.id,
                'target': 'current',
		'domain':domain,
            }

