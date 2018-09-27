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

class CustomPurchaseDashboard(models.Model):
    _name = "custom.purchase.dashboard"
    
    @api.multi
    def _get_statedetail(self):
        days= datetime.today().day
        purchase_rqt=self.env['stock.purchase.request']
        purchase_prq=self.env['purchase.requisition']
        purchase_order=self.env['purchase.order']
        new_rqst=purchase_rqt.search([('p_state','=','draft')])
        prq_rqst=purchase_rqt.search([('p_state','=','requisition')])
        reject_rqst=purchase_rqt.search([('p_state','=','reject')])
        done_rqst=purchase_rqt.search([('p_state','=','done')])

        total_po=purchase_order.search(
            [('state','not in',('draft','sent', 'confirmed'))])
        total_tender=purchase_prq.search(
            [('state', '!=', 'cancel')])
        new_po_count = purchase_order.search(
            [('state', '=', 'draft')])
        sent_po_count = purchase_order.search(
            [('state', '=', 'sent')])
        awaiting_po_count = purchase_order.search(
            [('state', '=', 'awaiting')])
        rejected_po_count = purchase_order.search(
            [('state', '=', 'rejected')])
        approved_po_count = purchase_order.search(
            [('state', '=', 'to approve')])
        progress_po_count = purchase_order.search(
            [('state', '=', 'purchase')])
        po_sent_po_count = purchase_order.search(
            [('state', '=', 'sent po')])
        done_po_count = purchase_order.search(
            [('state', '=', 'done')])
        cancel_po_count = purchase_order.search(
            [('state', '=', 'cancel')])
        new_tender_count = purchase_prq.search(
            [('state', '=', 'draft')])
        progress_tender_count = purchase_prq.search(
            [('state', '=', 'in_progress')])
        bid_tender_count = purchase_prq.search(
            [('state', '=', 'open')])
        po_tender_count = purchase_prq.search(
            [('state', '=', 'done')])
        cancel_tender_count = purchase_prq.search(
            [('state', '=', 'cancel')])
        today_po_completed = purchase_order.search(
            [('n_request_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state','not in', ('cancel', 'done'))])
        tomorrow_po_completed = purchase_order.search(
            [('n_request_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')) ,('state','not in', ('cancel', 'done'))])
        week_po_completed = purchase_order.search(
            [('n_request_date','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state','not in', ('cancel', 'done'))])
        month_po_completed = purchase_order.search(
            [('n_request_date','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state','not in', ('cancel', 'done'))])
        #pending_rqst=purchase_order.search([('state','in',('draft','sent','purchase')),'|','|',('management_user','=',self.env.user.id),('procurement_user','=',self.env.user.id),('inventory_user','=',self.env.user.id)])
        pending_rqst=purchase_order.search([('state','=','awaiting')])
        lst_rqst=[]
        for pend in pending_rqst:
            if pend.management_user.id == self.env.user.id and not pend.approve_mgnt: 
               lst_rqst.append(pend.id)
            if pend.procurement_user.id == self.env.user.id and not pend.approve_prq: 
               lst_rqst.append(pend.id)
            
            if pend.inventory_user.id == self.env.user.id and not pend.approve_inv: 
               lst_rqst.append(pend.id)
        return {
		'total_tender':len(total_tender),
		'total_po':len(total_po),
		'new_po_count':len(new_po_count),
		'sent_po_count':len(sent_po_count),
                'awaiting_po_count':len(awaiting_po_count),
                'rejected_po_count':len(rejected_po_count),
                'approved_po_count':len(approved_po_count),
		'progress_po_count':len(progress_po_count),
                'po_sent_po_count':len(po_sent_po_count),
		'done_po_count':len(done_po_count),
		'cancel_po_count':len(cancel_po_count),
		'today_po_completed':len(today_po_completed),
		'tomorrow_po_completed':len(tomorrow_po_completed),
		'week_po_completed':len(week_po_completed),
		'month_po_completed':len(month_po_completed),
		'new_tender_count':len(new_tender_count),
		'progress_tender_count':len(progress_tender_count),
		'bid_tender_count':len(bid_tender_count),
		'po_tender_count':len(po_tender_count),
		'cancel_tender_count':len(cancel_tender_count),
                'new_rqst':len(new_rqst),
                'prq_rqst':len(prq_rqst),
                'reject_rqst':len(reject_rqst),
                'done_rqst':len(done_rqst),
                'pending_rqst':len(lst_rqst)
            }

    @api.one
    def _get_detail(self):
        self.status_dashboard = json.dumps(self._get_statedetail())

    status_dashboard = fields.Text(compute = '_get_detail')

    
    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name")
    
    @api.one
    def _kanban_dashboard_graph(self):
	    ids=self.env['account.journal'].search([('type','=','bank')],limit=1)
            self.kanban_dashboard_graph = json.dumps(ids.get_line_graph_datas())

    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    
    @api.multi
    def action_purchase(self):
        days= datetime.today().day
	domain=[]
	_name=''
        rq_tree=rq_form=''
	if self._context.get('request_new'):
		domain=[('p_state', '=','draft')]
		_name=' New Purchase Request'
		model='stock.purchase.request'
		rq_tree = self.env.ref('gt_order_mgnt.stock_purchase_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.stock_purchase_request_form',False)

	if self._context.get('request_prq'):
		domain=[('p_state', '=','requisition')]
		_name='Purchase Request convert into PRQ'
		model='stock.purchase.request'
		rq_tree = self.env.ref('gt_order_mgnt.stock_purchase_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.stock_purchase_request_form',False)

	if self._context.get('request_reject'):
		domain=[('p_state', '=','reject')]
		_name='Purchase Request Rejected'
		model='stock.purchase.request'
		rq_tree = self.env.ref('gt_order_mgnt.stock_purchase_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.stock_purchase_request_form',False)

        if self._context.get('request_done'):
		domain=[('p_state', '=','done')]
		_name='Purchase Request Done'
		model='stock.purchase.request'
		rq_tree = self.env.ref('gt_order_mgnt.stock_purchase_request_tree', False)
                rq_form =self.env.ref('gt_order_mgnt.stock_purchase_request_form',False)


        if self._context.get('prq_new'):
		domain=[('state', '=','draft')]
		_name=' New Purchase Requisition'
		model='purchase.requisition'
		rq_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
                rq_form =self.env.ref('purchase_requisition.view_purchase_requisition_form',False)

	if self._context.get('prq_cofirmed'):
		domain=[('state', '=', 'in_progress')]
		_name='Purchase Requisition In process'
		model='purchase.requisition'
		rq_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
                rq_form =self.env.ref('purchase_requisition.view_purchase_requisition_form',False)

	if self._context.get('prq_done'):
		domain=[('state', '=','done')]
		_name='Purchase Requisition Done'
		model='purchase.requisition'
		rq_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
                rq_form =self.env.ref('purchase_requisition.view_purchase_requisition_form',False)

        if self._context.get('prq_cancel'):
		domain=[('state', '=','cancel')]
		_name=' Cancelled Purchase Requisition'
		model='purchase.requisition'
		rq_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
                rq_form =self.env.ref('purchase_requisition.view_purchase_requisition_form',False)

        if self._context.get('purchase_new'):
		domain=[('state', '=','draft')]
		_name=' New Purchase Orders'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

	if self._context.get('purchase_sent'):
		domain=[('state', '=','sent')]
		_name='Sent Purchase Orders'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_awaiting'):
		domain=[('state', '=','awaiting')]
		_name='Awaiting Purchase Orders'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_rejected'):
		domain=[('state', '=','rejected')]
		_name='Rejected Purchase Orders'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_approved'):
		domain=[('state', '=','to approve')]
		_name='Approved Purchase Orders'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)
	if self._context.get('purchase_order'):
		domain=[('state', '=','purchase')]
		_name='Comfirmed Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_order_sent'):
		domain=[('state', '=','sent po')]
		_name='Sent Purchase Order to Vendor'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)
        if self._context.get('purchase_done'):
		domain=[('state', '=','done')]
		_name='Done Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_cancel'):
		domain=[('state', '=','cancel')]
		_name=' Cancelled Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_today'):
		domain=[('n_request_date','<', (datetime.now() + timedelta(1)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now() - timedelta(1)).strftime('%Y-%m-%d 23:59:59')), ('state','not in', ('cancel', 'done'))]
		_name='Todays Completed Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

	if self._context.get('purchase_tomorrow'):
		domain=[('n_request_date','<', (datetime.now() + timedelta(2)).strftime('%Y-%m-%d 00:00:00')),('n_request_date','>',(datetime.now()).strftime('%Y-%m-%d 23:59:59')) ,('state','not in', ('cancel', 'done'))]
		_name='Tomorrow Completed Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_week'):
		domain=[('n_request_date','<', (datetime.now() + timedelta(9)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() + timedelta(1)).strftime("%Y-%m-%d 23:59:59")),('state','not in', ('cancel', 'done'))]
		_name=' This Week  Completed Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('purchase_month'):
		domain=[('n_request_date','<', (datetime.now() + timedelta(30)).strftime("%Y-%m-%d 00:00:00")),('n_request_date','>',(datetime.now() - timedelta(days)).strftime("%Y-%m-%d 23:59:59")),('state','not in', ('cancel', 'done'))]
		_name=' This Month Completed Purchase Order'
		model='purchase.order'
		rq_tree = self.env.ref('purchase.purchase_order_tree', False)
                rq_form =self.env.ref('purchase.purchase_order_form',False)

        if self._context.get('request_pending'):
                pending_rqst=self.env['purchase.order'].search([('state','=','awaiting')])
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

