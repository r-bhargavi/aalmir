from datetime import date, datetime,timedelta
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError

class stock_picking(osv.osv):
    _inherit='stock.picking'

    def create(self,cr,uid,vals,context=None):
	#CH_N106 add code to get main LPO in DO as default >>>
	if vals.get('origin'):
		search_id=self.pool.get('sale.order').search(cr,uid,[('name','=',vals.get('origin'))])
                val=[]
		if search_id:
			for rec in self.pool.get('sale.order').browse(cr,uid,search_id):
				n_id=self.pool.get('customer.upload.doc').search(cr,uid,[('sale_id_lpo','=',rec.id),('lpo_number','=',rec.lpo_number)])
				if n_id:
					vals.update({'lpo_document_id':[(4,i) for i in n_id]})
	return super(stock_picking,self).create(cr,uid,vals)
   
    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                res[pick.id] = pick.launch_pack_operations and 'assigned' or 'draft'
                continue
            if any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue
            if all([x.state in ('delivered', 'cancel') for x in pick.move_lines]):
                res[pick.id] = 'delivered'
                continue
	    
            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2,'transit':3,'delivered':4,}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned', 3: 'transit', 4: 'delivered'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done','delivered')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res
    
    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    _columns={
               'state': fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type', 'launch_pack_operations'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),               
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
		('transit','Ready To Dispatch'),
                ('done', 'Done'),
                ('dispatch', 'Dispatched'),
                ('delivered','Delivered'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""),}
#CH_N111 add code to get  sale_order sale_id in quality form 

    @api.depends('move_lines')
    def _compute_sale_id(self):
        for picking in self:
            sale_order = False
            for move in picking.move_lines:
                if move.procurement_id.sale_line_id:
                    sale_order = move.procurement_id.sale_line_id.order_id
                    break
		elif move.n_sale_line_id:
			sale_order = move.n_sale_line_id.order_id
            picking.sale_id = sale_order.id if sale_order else False

    def action_second_validation(self, cr, uid, ids, context=None):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        pickings = self.browse(cr, uid, ids, context=context)
        for pick in pickings:
	    if  not pick.delivery_date:
               raise UserError('Please Add Delivery Date')
            if  not pick.delivery_doc:
               raise UserError('Please Add Delivery Receipt........... ')
            if pick.delivery_date < pick.dispatch_date:
            	 raise UserError('Delivered Date Must be greater than or equal to Dispatch date..')
            move_ids = [x.id for x in pick.move_lines if x.state in ['done']]
	    #pick.state='delivered'
	    if not pick.delivery_date:
	            pick.delivery_date=date.today()
	    record_dic={}
	    for line in pick.pack_operation_product_ids:
		sale_line=line.n_sale_order_line
		if sale_line:
			if not record_dic.get(sale_line.id):
				record_dic.update({sale_line.id:[line.product_id.id,line.qty_done,sale_line.product_uom_qty]})
			else:
				qty=record_dic.get(line.n_sale_order_line.id)[0]
				record_dic.update({sale_line.id:[line.product_id.id,line.qty_done+qty,sale_line.product_uom_qty]})
			qry="UPDATE reserve_history SET n_status ='delivered' where id =(select id from reserve_history where n_status ='dispatch' and sale_line="+str(sale_line.id)+" and picking_id="+str(pick.id)+" order by id asc limit 1)"
	   		cr.execute(qry)
	   		
	    for key,val in record_dic.items():
		cr.execute("select sum(res_qty) from reserve_history where n_status='delivered' and sale_line="+str(key))
		qty=cr.fetchone()[0]
		status_list=[]
		if (qty)>=val[2]:
			
			search_id=self.pool.get('sale.order.line.status').search(cr, uid, [('n_string','=','delivered')],limit=1)
			if search_id:
				status_list.append((4,search_id[0]))
			new_id=self.pool.get('sale.order.line.status').search(cr, uid, [('n_string','in',('partial_delivery','partial_dispatch','dispatch'))])
			for rec in new_id:
				status_list.append((3,rec))
		elif (qty)< val[2]:
			search_id=self.pool.get('sale.order.line.status').search(cr, uid, [('n_string','=','partial_delivery')],limit=1)
			if search_id:
				status_list.append((4,search_id[0]))
			new_id=self.pool.get('sale.order.line.status').search(cr, uid,[('n_string','in',('partial_dispatch','dispatch'))])
			for rec in new_id:
				status_list.append((3,rec))
		if status_list:		#CH_N123 add code to update status in sale support
			self.pool.get('sale.order.line').write(cr,uid,key,{'n_status_rel':status_list})
		delivery_ids=self.pool.get('mrp.delivery.date').search(cr,uid,[('n_picking_id','=',pick.id),('n_line_id1','=',key)])
		if delivery_ids:		#update delivery date in sale support delivery date table
			self.pool.get('mrp.delivery.date').write(cr,uid,delivery_ids[0],{'n_delivery_date':pick.delivery_date,
								'n_status':'delivered'})
		sale_ids=self.pool.get('sale.order.line').browse(cr,uid,[key])
		sale_ids._get_schedule_date()
            self.pool.get('stock.move').action_second_validation(cr, uid, move_ids, context=context)
        return True

class stock_move(osv.osv):
    _inherit='stock.move'
    _columns={
        	'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),                                  
                                   ('assigned', 'Available'),
                                   ('transit','Ready To Dispatch'),
                                   ('done', 'Done'),
                                   ('dispatch', 'Dispatched'),
                                   ('delivered','Delivered'),
                                   ], 'Status', readonly=True, select=True, copy=False,
         	help= "* New: When the stock move is created and not yet confirmed.\n"\
                       "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
                       "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
                       "* Available: When products are reserved, it is set to \'Available\'.\n"\
                       "* Done: When the shipment is processed, the state is \'Done\'."), 
		'n_sale_line_id':fields.related('procurement_id','sale_line_id',type='many2one',
				relation='sale.order.line',string='Sale Order Line')     #CH_N055
            	}
    
    def action_second_validation(self, cr, uid, ids, context=None):
        """ Changes the state to assigned.
        @return: True
        """
        move = self.browse(cr, uid, ids, context=context)
        for moves in move:
       		res = self.write(cr, uid, ids, {'state': 'delivered'}, context=context)
        	return res

