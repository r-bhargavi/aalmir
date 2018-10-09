from openerp import fields, models ,api, _,SUPERUSER_ID
from openerp.exceptions import UserError, ValidationError
import logging
from datetime import datetime, date, timedelta
import openerp.addons.decimal_precision as dp
import math
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)
import json

def subset_sum_batches1(batches, target, partial=[]):
    qty_sum = sum([q.approve_qty for q in partial])	
    if qty_sum  == target:		# check if the partial sum is equals to target
	return partial
    if qty_sum >= target:		# if sum is greater than quantity continue
	return  False	
    for i in range(len(batches)):
	n = batches[i]
	remaining = batches[i+1:]
	qty_sum_q = sum([q.approve_qty for q in partial+[n]])	# check if sum of next record is not going beyond
	if qty_sum_q > target:
		diff = target - qty_sum
		if not any([ diff < q.approve_qty for q in remaining]):
			break
	result_batches=subset_sum_batches(remaining, target, partial+[n])
	if result_batches:
		return result_batches
		
    if qty_sum > target:
    	diff = target - qty_sum
    	if not any([ diff < q.approve_qty for q in batches]):
		return False
    return False
    
def subset_sum_batches(batches, target):
	try:
		partial=[]
		diff=0.0
		for i,start in enumerate(batches):
			partial=[start]
			remaining=batches[i+1:]
			for j,next in enumerate(remaining):
		    		partial.append(next)
		    		qty_sum = sum([q.approve_qty for q in partial])		
		    		if qty_sum  == target:		# check if the partial sum is equals to target
					return partial
		    		if qty_sum >= target:		# if sum is greater than quantity continue
		    			diff = qty_sum - next.approve_qty
		    			partial.pop()
		    			flag=True
		    			if not any([ diff < q.approve_qty for q in remaining[j:]]):
						break
			if flag and diff:
				if not any([ diff < q.approve_qty for q in batches[i:]]):
					break
		return False
	except :
		pass
				
class StockMove(models.Model):
     _inherit='stock.move'

     product_hs_code=fields.Char('Hs Code', related='product_id.product_hs_code',readonly=True)
     gross_weight=fields.Float('Gross Weight', related='product_id.weight',readonly=True)
     scrap_reason=fields.Selection([('reject','Quality not Good'),('min','Minimum Quantity ' )], string="Scrap Reason")
     uploaded_documents = fields.Many2many('ir.attachment','move_attachment_rel','move_doc','id','Scrap Documents')
     split_id=fields.Many2one('stock.picking.split')
     split_qty=fields.Float('Split Qty')
     rm_qty=fields.Float('Remaining Qty', compute='total_remaining_qty')  
     split_move_id=fields.Many2one('stock.move') 
     production_req = fields.Many2many('n.manufacturing.request','production_request_move_rel',
    		'move_id','transfer_id' ,string="Transfers")
     pack_qty = fields.Float('Packets', compute='_get_packets_qty')
     
     @api.multi
     def _get_packets_qty(self):
     	for rec in self:
     		if rec.product_packaging and rec.product_qty:
     			rec.pack_qty = math.ceil(rec.product_qty/rec.product_packaging.qty)
     @api.multi
     @api.depends('product_uom_qty', 'split_qty')
     def total_remaining_qty(self):
         for record in self:
             if record.split_qty:
                record.rm_qty=record.product_uom_qty - record.split_qty
	
     @api.model
     def create(self,vals):
	#CH_N055 add code to get line id in stock move #proper working is need to be check
	# Updated on 10th July2018
	res = super(StockMove,self).create(vals)
	print "VVVVVVVVVVVvv",vals
	if res and res.procurement_id and res.procurement_id.sale_line_id :
	   	res.write({'date_expected':res.procurement_id.sale_line_id.order_id.client_date,
	   		     'product_packaging':res.procurement_id.sale_line_id.product_packaging.id})
	return res

     @api.v7
     def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        quant_obj = self.pool.get("stock.quant")
        move_val = self.pool.get("stock.move")
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise UserError(_('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            scrap=move.scrap_reason
            uploaded=move.uploaded_documents
            scrap_txt = 'Minimum Quantity' if move.scrap_reason == 'min' else 'Quality not Good'
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise UserError(_('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            default_val = {
                'location_id': source_location.id,
                'product_uom_qty': quantity,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
                'scrap_reason':scrap,
                'uploaded_documents':uploaded.ids
            }
            new_move = self.copy(cr, uid, move.id, default_val)
            for mv in move_val.browse(cr, uid, new_move, context=context):
                mv.scrap_reason=scrap
                mv.uploaded_documents=uploaded.ids
                
            mrp=self.pool.get('mrp.production')
            mrp_search=mrp.search(cr, uid,[('name','=', move.origin)],context=context)
            for mp in mrp.browse(cr, uid, mrp_search, context=context):
                mp.uploaded_documents=uploaded.ids
                message = _('<h4 style="color:red"> <b>Moved to scrap.</b> <li>Product : %s </li><li>Quantity :%s %s</li> <li>Reason: %s</li></h4> <li>Documents :') % (move.product_id.name ,quantity, mp.product_uom.name,scrap_txt)
                mp.message_post(body=message, attachment_ids=move.uploaded_documents)
            
            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    attachments=move.uploaded_documents and [('move.uploaded_documents', sign.decode('base64'))] or []
                    message = _('<h4 style="color:red"> <b>Moved to scrap.</b> <li>Product : %s </li><li>Quantity :%s %s</li> <li>Reason: %s</li></h4> <li>Documents :') % (move.product_id.name ,quantity, uom,scrap_txt)
                    move.picking_id.message_post(body=message, attachments=attachments)

            # We "flag" the quant from which we want to scrap the products. To do so:
            #    - we select the quants related to the move we scrap from
            #    - we reserve the quants with the scrapped move
            # See self.action_done, et particularly how is defined the "preferred_domain" for clarification
            scrap_move = self.browse(cr, uid, new_move, context=context)
            if move.state == 'done' and scrap_move.location_id.usage not in ('supplier', 'inventory', 'production'):
                domain = [('qty', '>', 0), ('history_ids', 'in', [move.id])]
                # We use scrap_move data since a reservation makes sense for a move not already done
                quants = quant_obj.quants_get_preferred_domain(cr, uid, quantity, scrap_move, domain=domain, context=context)
                quant_obj.quants_reserve(cr, uid, quants, scrap_move, context=context)

        self.action_done(cr, uid, res, context=context)
	#code to create scrap picking
	for record in self.browse(cr, uid, ids, context=context):
	   if record.picking_id.picking_type_code != 'incoming':
                mrp_search = self.pool.get('mrp.production').search(cr,uid,[('name','=',record.origin),('state','!=','done')])
                if mrp_search:
                   self.pool.get('stock.move').write(cr,uid,res,{'production_id':mrp_search[0],'state':'done'})
                else:
		   picking_search = self.pool.get('stock.picking').search(cr,uid,[('origin','=',record.picking_id.name),('state','!=','done')])
 		   if picking_search:
			self.pool.get('stock.move').write(cr,uid,res,{'picking_id':picking_search[0],'state':'assigned'})
		   else:
			location = self.pool.get('stock.location').search(cr,uid,[('usage','=','internal'),('active','=',True),('scrap_location','=',True)],limit=1)
			cr.execute("select id from stock_picking_type where code='internal' and n_scrap_ck=True")
			picking_type=cr.fetchone()
			name = self.pool.get('ir.sequence').next_by_code(cr,uid,'scrap.sequence') or 'New'
			picking_id=self.pool.get('stock.picking').copy(cr,uid,record.picking_id.id,
						{'origin':record.picking_id.name,'location_dest_id':record.picking_id.location_id.id,
						'picking_type_id':picking_type[0] if picking_type else False,'min_date':date.today(),'name':name,
						'location_id':location[0] if location else False,'move_lines':[]},context=context)
			self.pool.get('stock.move').write(cr,uid,res,{'picking_id':picking_id,'state':'assigned'})
        return res

class Stock_Vahicle_Number(models.Model):
     _name='stock.vahicle.number'
     name=fields.Char('Number')

class StockPickingSplit(models.Model):
     _name='stock.picking.split'

     name=fields.Char('Name')
     move_line_id=fields.One2many('stock.move', 'split_id')
     required_date=fields.Datetime('Delivery Date') 
     picking_id=fields.Many2one('stock.picking','Delivery Order')
     qty_exceed=fields.Boolean(compute='total_remaining_qty')

     @api.multi
     @api.depends('move_line_id.product_uom_qty', 'move_line_id.split_qty')
     def total_remaining_qty(self):
         for record in self:
             for line in record.move_line_id:
                 if line.split_qty:
                    if line.split_qty > line.product_uom_qty:
                       record.qty_exceed=True
                       
     @api.multi
     def create_new_delivery_order(self):
        list_l=sh_l=[],[]
        for rec in self:
             new_picking=rec.picking_id.copy({'move_lines':[],'note':'','min_date':rec.required_date,
             					'parent_pick_id':rec.picking_id.id})
             picking_msg='<span style="color:red">New Delivery Order created on split qty</span> - New Delivery Order Number-: \n'+str(new_picking.name)
             product_data={}
             if rec.picking_id.pack_operation_product_ids:
             	for op in rec.picking_id.pack_operation_product_ids:
             		if product_data.get(str(op.product_id.id)):
             			p_qty = product_data.get(str(op.product_id.id))
             			product_data.update({str(op.product_id.id):p_qty+op.product_qty})
     			else:
             			product_data.update({str(op.product_id.id):op.product_qty})
             	rec.picking_id.with_context({'sale_support':True}).do_unreserve()
	
	     for line in rec.move_line_id:
		 if line.product_uom_qty<line.split_qty:
			raise UserError('Split Quantity is not greater Than Quantity')
		 if (line.product_uom_qty-line.split_qty)>0:
	                 line.split_move_id.product_uom_qty =  line.product_uom_qty-line.split_qty 
		 if (line.product_uom_qty-line.split_qty)==0:
			line.split_move_id.unlink()
		 if line.split_qty >0.0:
		 	n_vlas=({'procure_method':line.split_move_id.procure_method,'origin':line.split_move_id.origin,
		 		'partner_id':line.split_move_id.partner_id.id,'name':line.split_move_id.name,
				'rule_id':line.split_move_id.rule_id.id,'n_sale_line_id':line.split_move_id.n_sale_line_id.id,
				'sequence':line.split_move_id.sequence,'price_unit':line.split_move_id.price_unit,
				'date':line.split_move_id.date,'priority':line.split_move_id.priority,
				'warehouse_id':line.split_move_id.warehouse_id.id,'product_uom_qty':line.split_qty,
				'picking_type_id':line.split_move_id.picking_type_id.id ,
				'procurement_id':line.split_move_id.procurement_id.id,
				'group_id':line.split_move_id.group_id.id,'picking_id':new_picking.id})
		 	line.write(n_vlas)
		#CH_N080 >>>add code create schedule date record
			self.env['mrp.delivery.date'].create({'n_dispatch_date_d':rec.required_date,
							'n_status':'waiting','n_picking_id':new_picking.id,
							'n_line_id1':line.split_move_id.n_sale_line_id.id,
							'n_type':'partial'})
			line.split_move_id.n_sale_line_id._get_schedule_date()
		#CH_N081 <<<<<<<<
		 picking_msg += '<span style="color:red">Delivery Qty Is Split </span>- New Qty-: '+str(line.rm_qty)+' '+ 'Old Qty:-'+str(line.product_uom_qty)
		 
	     rec.picking_id.message_post(body=picking_msg)
	     if product_data and rec.picking_id.picking_type_id.code=='outgoing':
	     	for reserve in rec.picking_id.move_lines_related:
	     		if product_data.get(str(reserve.product_id.id)):
	     			prd_qty = product_data.get(str(reserve.product_id.id))
				if prd_qty >= reserve.product_uom_qty:
					context={'sale_support':True,'res_qty':reserve.product_uom_qty,
						'reserve_only_ops':True if reserve.reserved_quant_ids else False,
						'sale_move_id':reserve,'sale_line_id':reserve.procurement_id.sale_line_id.id}
					reserve.with_context(context).action_assign()
					product_data.pop(str(reserve.product_id.id))
				elif prd_qty < reserve.product_uom_qty:
					context={'sale_support':True,'res_qty':prd_qty,
						'reserve_only_ops':True if reserve.reserved_quant_ids else False,
						'sale_move_id':reserve,'sale_line_id':reserve.procurement_id.sale_line_id.id}
					reserve.with_context(context).action_assign()
					product_data[str(reserve.product_id.id)] -= reserve.product_uom_qty
     			
             for pick in new_picking:
		pick.message_post(body='<span style="color:red">Old Delivery Order Number-: </span>'+str(rec.picking_id.name))
		if product_data and pick.picking_type_id.code=='outgoing':
			for n_reserve in pick.move_lines_related:
				if product_data.get(str(n_reserve.product_id.id)):
					prd_qty = product_data.get(str(n_reserve.product_id.id))
					if prd_qty >= n_reserve.product_uom_qty:
						context={'sale_support':True,'res_qty':n_reserve.product_uom_qty,
							'reserve_only_ops':True if n_reserve.reserved_quant_ids else False,
							'sale_move_id':n_reserve,'sale_line_id':n_reserve.procurement_id.sale_line_id.id}
						n_reserve.with_context(context).action_assign()
						product_data.pop(str(reserve.product_id.id))
					elif prd_qty < n_reserve.product_uom_qty:
						context={'sale_support':True,'res_qty':prd_qty,
							'reserve_only_ops':True if n_reserve.reserved_quant_ids else False,
							'sale_move_id':n_reserve,'sale_line_id':n_reserve.procurement_id.sale_line_id.id}
						n_reserve.with_context(context).action_assign()
						product_data[str(n_reserve.product_id.id)] -= n_reserve.product_uom_qty
         	 	
             return {
		    'name': 'Split delivery Order',
		    'view_type': 'form',
		    'view_mode': 'tree,form',
		    'res_model': 'stock.picking',
		    'res_id':rec.picking_id.id,
		    'type': 'ir.actions.act_window_close',
		    'target' : 'current',
		}
         
class StockPicking(models.Model):
     _inherit='stock.picking' 
     
     @api.model
     def create(self, vals):
	picking = super(StockPicking, self).create(vals)
	sale_order = self.env['sale.order'].search([('name','=',picking.origin)])
	if sale_order:
		picking.report_company_name=sale_order.report_company_name.id
           	picking.partner_id=sale_order.partner_id.id
           	picking.partner_shipping_id=sale_order.partner_shipping_id.id
		if sale_order.is_reception:
			picking.term_of_delivery=False
		# to udpate Schedule_date(min date)
		s_date= False
		for rec in sale_order.order_line:
			if rec.n_schdule_date:
				if not s_date :
					s_date=rec.n_schdule_date
				elif rec.n_schdule_date < s_date:
					s_date=rec.n_schdule_date
			else:
				if rec.n_client_date:
					s_date=datetime.strptime(rec.n_client_date,'%Y-%m-%d')-timedelta(days=int(rec.n_transit_time))
					break
		if s_date and picking.picking_type_code=='outgoing':
			picking.min_date = s_date
	return picking

     @api.multi
     def get_customer_credit(self):
	for record in self:
		if record.partner_id and record.sale_id.is_reception != True:
		    partner_id = record.partner_id.parent_id if record.partner_id.parent_id else record.partner_id
		    n_date=date.strftime(datetime.strptime(partner_id.from_date,'%Y-%m-%d'), '%Y-%m-%d') if partner_id.from_date else ''    
		    n_date1=date.strftime(datetime.strptime(partner_id.to_date,'%Y-%m-%d'), '%Y-%m-%d ') if partner_id.to_date else '' 
		    todate=date.strftime(date.today(),'%Y-%m-%d')  

		    if  todate >= n_date  and todate <= n_date1 and partner_id.credit_currency_id:
		        record.credit_limit= partner_id.credit_currency_id.compute(partner_id.credit_limit,record.n_quotation_currency_id) 
		    else:
		        record.credit_limit=0.0
 
#CH_N106 add code to get quotation currency 
     @api.multi
     def _get_sale_currency(self):
	for record in self:
		if record.sale_id:
			record.n_quotation_currency_id=record.sale_id.report_currency_id.id
		else:
			record.n_quotation_currency_id=self.env.user.company_id.currency_id.id
     
     @api.multi
     def _get_return_data(self):
	for  res in self:
		return_ids=self.env['stock.picking'].search([('origin','=',res.name),('name','ilike','RE')])
		res.return_order = str(len(return_ids))

     consignee_id=fields.Many2one('res.partner', string='Consignee To', related='sale_id.partner_id')
     manufactured_id=fields.Many2one('res.company', string='Manufactured By')
     report_currency_id = fields.Many2one('res.currency', related='sale_id.report_currency_id', string="Converted Currency")

     #invoice_number=fields.Char(string='Invoice Number')

     origin_id=fields.Many2one('res.country', string='Origin of Goods', default=lambda self: self.env['res.country'].search([('code', '=','AE')]))

     total_gross_weight=fields.Float('Total Net Wt(Kg)', compute='total_gross_weight_val')
     total_net_weight=fields.Float('Total Gross Wt(Kg)', compute='totalweight')
     shipment_mode=fields.Selection([('sea', 'Sea'), ('road', 'Road'), ('air', 'Air')], string="Shipment Mode")
     container_size=fields.Char('Container size')
     container_no=fields.Char('Container No')
     type_of_picking=fields.Selection([('exrprtcart', 'Standard export carton')], string="Type of Picking")
     invoice_ids = fields.Many2many("account.invoice", string='Invoices',copy=False)

     dispatch_date=fields.Datetime('Dispatch Date',copy=False)
     dispatch_doc = fields.Many2many('ir.attachment','dispatch_attachment_rel','dispatch_doc','id','Dispatch Documents',help="1. Delivery Pictures \n 2. Security stamped DO.",copy=False)
     dispatch_doc_name = fields.Char(string='Doc Name',copy=False)

     delivery_date=fields.Datetime('Delivery Date',copy=False)
     delivery_doc = fields.Many2many('ir.attachment','delivery_attachment_rel','delivery_doc','id','Delivered Documents',copy=False)
     delivery_doc_name = fields.Char(string='Doc Name',copy=False)
     
     reverse_reason=fields.Selection([('reject', 'Goods Rejected'), ('notdelivered', 'Not Delivered')], string="Reverse  Reason",copy=False)
     return_order=fields.Char('Return orders',compute="_get_return_data")

     vehicle_number=fields.Many2one('stock.vahicle.number',string='Vehicle Number',copy=False)
     employee_id=fields.Many2one('hr.employee', string="Driver Name",copy=False)
     #invoice_id=fields.Many2one('account.invoice', 'Invoice Number',copy=False)

     credit_limit = fields.Float(string="Credit Allowed",readonly=True , compute="get_customer_credit")
     customer_invoice_pending_amt=fields.Float('Other Pending Credit', compute='get_customer_pending_amount', help='Customer Other pntransfer_typeending credit amount')
     amount_total = fields.Float(string='Order Remaining Amount', compute='total_sale_amount', help="Current Sale Order Remaining Amount (Total Sale order Amount - current invoice amount)")
     credit_bool=fields.Boolean('Credit Bool', compute='amount_bool_check')
     total_delivery_amount=fields.Float('Current Delivery Amount', compute='total_delivery_qty_price_amount', help="Total Current Delivery Order Amount")
     n_quotation_currency_id=fields.Many2one('res.currency','Currency', compute=_get_sale_currency)
     
     parent_pick_id=fields.Many2one('stock.picking', 'Parent Delivery Order')
     qty_exceed=fields.Boolean('Qty Exceed')
     mark_as_final=fields.Boolean('Mark As Final Delivery Order')
     total_current_invoice=fields.Float("Order Pending Invoice", compute='totalpendinginvoice' ,help="Current Invoice Amount of sale order ")
     
     is_pending=fields.Boolean(compute='invoice_pend_bool')
     stop_delivery=fields.Boolean('Stop Delivery', compute='stopDeliverycheck')
     allow_delivery=fields.Boolean('Allow Delivery')
     lpo_document_id=fields.Many2many('customer.upload.doc', 'customer_rel' ,'customer_stock_rel',
                     string="PO Number")		# for LPO relation
     split_count=fields.Integer(compute='total_splitdelivery')
     incoming_doc = fields.Many2many('ir.attachment','incoming_attachment_rel','incoming_doc','id','Incoming Documents', copy=False)

     purchase_id=fields.Many2one('purchase.order', string='Purchase Order',copy=True)
     production_id=fields.Many2one('mrp.production', string="Manufacturing No.")
     work_order_id=fields.Many2one('mrp.production.workcenter.line')
     request_sch_date_mo=fields.Datetime('Request By', related='work_order_id.date_planned')
     ## add boolean field for print report
     manufactured_by=fields.Char('Manufactured By', default='Aal Mir Plastic Industries ,PO Box 4537, Sharjah, UAE.')
     check_origin=fields.Boolean(default=True) 
     check_manuf=fields.Boolean(default=True)
     check_gross=fields.Boolean()
     check_net=fields.Boolean()
     check_ship=fields.Boolean()
     check_employee=fields.Boolean()
     check_vehicle=fields.Boolean()
     check_invoice=fields.Boolean()
     check_cont_sz=fields.Boolean()
     check_cont_no=fields.Boolean()
     check_picktype=fields.Boolean()
     check_lpo=fields.Boolean(default=False)
     partner_shipping_id=fields.Many2one('res.partner',string='Delivery Address')
     check_destination=fields.Boolean(default=False)
     check_hs=fields.Boolean('Print HS Code on Report')
     check_pallet=fields.Boolean('Print Packing/Pallet on Report')
     check_packaging=fields.Boolean('Print Packaging on Report')
     schedule_date=fields.Datetime(related='min_date',string='Scheduled Date')
     check_donumber=fields.Boolean('Print D.O No. on Report',default=True)
     check_date_withcol=fields.Boolean('Date With Column on Print',default=True)
     check_date_withnotcol=fields.Boolean('Only Date Column on Print')
     check_sale=fields.Boolean('Sale Order on Print',default=True,help="Sales Order Number on report")
     check_saleperson=fields.Boolean('Sales Person on Print',default=True,help="Sales Person Name on report")
     print_copy=fields.Integer('Report Copies', default=1)
     report_name=fields.Char('Report Name', default='Delivery Order')

     check_term=fields.Boolean('Delivery Term',default=False,copy=False)
     show_stamp=fields.Boolean('Show Stamp on Report',default=True)
     term_of_delivery=fields.Many2one('stock.incoterms',string='Delivery Term', compute='add_term')

     total_qty=fields.Float('Total Qty', compute='totalqty')
     total_pallet=fields.Float('Total Pallet Qty', compute='totalqty')
     total_pack=fields.Float('Total Pack Qty', compute='totalqty')
     
     ntransfer_type=fields.Selection([('receipt','Receipt'),('po_return','Receipt Return'),
     					('internal','Internal'),('internal_return','Internal Return'),
     					('do_return','Do Return'),('develiry','Delivery')],
     				      string="Type of Operation") # to check record is for what purpose
     				      
     customer_name_report=fields.Char('Customer Name on Report',default='Customer Name')
     report_company_name=fields.Many2one('res.company','LetterHead Company Name', default=lambda self: self.env['res.company']._company_default_get('stock.picking'))
     destination_report=fields.Char('Destination on Report', default='Destination')
     check_partner=fields.Boolean(default=True)
     invoice_done=fields.Boolean(default=False)

     picking_status=fields.Selection([('draft','Draft'),('pick_list','In Picking'),
     					('r_t_dispatch','Ready To dispatch'),
     					('dispatch','Dispatch')],string='Picking Status',default='draft',copy=False)
				# to set picking list status
     					
     total_primary_cbm=fields.Char('Primary CBM(M3)', compute='_total_primary_cbm')
     total_secondary_cbm=fields.Char('Total Order CBM(M3)', compute='_total_secondary_cbm')    
     packaging_info=fields.Text(compute='_empty_pack_info')
     secondary_weight=fields.Text(compute='_empty_pack_info', string='Secondary Weight')
     check_lpo_line=fields.Boolean('Print LPO No. in Product Line',default=False)
     check_primary_cbm=fields.Boolean(default=False)
     check_secondary_cbm=fields.Boolean(default=False)
     #check_secondary_wt=fields.Boolean(default=False)
	
     @api.multi
     @api.depends('origin')
     def add_term(self):
        for record in self:
		if record.origin:
			sale=self.env['sale.order'].search([('name','=',record.origin)], limit=1)
			if sale:
                  		record.term_of_delivery=sale.incoterm.id
			else:
               			purchase=self.env['purchase.order'].search([('name','=',record.origin)], limit=1)
               			if purchase:
                  			record.term_of_delivery=purchase.incoterm_id.id
		if record.sale_id:
			record.term_of_delivery=record.sale_id.incoterm.id

     @api.multi
     @api.depends('pack_operation_product_ids.primary_cbm','pack_operation_product_ids.secondary_cbm')
     def _empty_pack_info(self):
         for record in self:
            info=''
            weight=0.0
            for pack in record.pack_operation_product_ids:
                for packg in pack.product_id.packaging_ids:
			if packg and packg.pkgtype =='secondary':
				weight +=(pack.net_weight) + (pack.total_pallet_qty * packg.uom_id.product_id.weight)
                record.secondary_weight=weight
                if not pack.primary_cbm: 
                   info +="Primay Packaging:   "+  str(pack.product_id.name )+"\n"
               
                if not pack.secondary_cbm:
                   info +="Secondary Packaging:  "+ str(pack.product_id.name )+"\n"
                else:
                   info +=""
            record.packaging_info=info

     @api.multi
     @api.depends('pack_operation_product_ids.primary_cbm','pack_operation_product_ids.secondary_cbm')
     def _total_primary_cbm(self):
        for record in self: 
            total_pm_cbm=0.0
            for pack in record.pack_operation_product_ids:
                if pack.primary_cbm:
                   total_pm_cbm +=round(pack.primary_cbm,4)
                else:
                   total_pm_cbm =0.0
            record.total_primary_cbm=total_pm_cbm

     @api.multi
     @api.depends('pack_operation_product_ids.secondary_cbm')
     def _total_secondary_cbm(self):
        for record in self:
            total_sc_cbm=0.0
            for pack in record.pack_operation_product_ids:
                if pack.secondary_cbm:
                   total_sc_cbm +=round(pack.secondary_cbm,4)
                else:
                   total_sc_cbm =0.0
                  
            record.total_secondary_cbm=float(total_sc_cbm) + float(record.total_primary_cbm) 

     @api.multi
     @api.depends('pack_operation_product_ids.product_qty','pack_operation_product_ids.qty_done', 'pack_operation_product_ids.total_pallet_qty','pack_operation_product_ids.pack_qty')
     def totalqty(self):
        for record in self:
            if record.pack_operation_product_ids:
               total=0.0
               for line in record.pack_operation_product_ids:
                   if line.product_id.type != 'service':
                      total +=line.qty_done if line.qty_done else line.product_qty
               record.total_qty=total
               record.total_pack=sum(line.pack_qty for line in record.pack_operation_product_ids)
               record.total_pallet=sum(line.total_pallet_qty for line in record.pack_operation_product_ids)

     @api.multi
     @api.depends('pack_operation_product_ids.net_weight')
     def totalweight(self):
        for record in self:
            if record.pack_operation_product_ids:
               record.total_net_weight=sum(line.net_weight for line in record.pack_operation_product_ids)
            else:
                record.total_net_weight=0.0
                
     @api.multi
     def amount_bool_check(self):
         for record in self:
	     if record.picking_type_code == 'outgoing' and record.state not in ('transit','done','delivered','cancel'):
	     	if not record.sale_id.cr_state:
			total_amount=record.customer_invoice_pending_amt + record.total_current_invoice
			if total_amount > record.credit_limit:
                           if record.allow_delivery==True:
				record.credit_bool =False
			   elif record.sale_id.stop_delivery == True:
			       	record.credit_bool =True
			   else:
				 record.credit_bool =False 
			else:
			   record.credit_bool =False
	     	else:
		     total_amount=record.customer_invoice_pending_amt + record.amount_total
		     if total_amount > record.credit_limit:
			   if record.allow_delivery==True:
				record.credit_bool =False
			   elif record.sale_id.stop_delivery == True:
			       	record.credit_bool =True
			   else:
				 record.credit_bool =False 
		     else:
			   record.credit_bool =False
	     else:
		record.credit_bool =False
            
     @api.multi
     def stopDeliverycheck(self):
         for record in self:
             if record and record.picking_type_code == 'outgoing' and record.sale_id.cr_state == 'request':
                
                record.stop_delivery=record.sale_id.stop_delivery
             else:
                record.stop_delivery=False
             
     @api.multi
     @api.depends('sale_id')
     def totalpendinginvoice(self):
         for record in self:
	     if record.sale_id and not record.sale_id.is_reception:
		     invoice=self.env['account.invoice'].search([('sale_id', '=', record.sale_id.id)])
		     if invoice:
		        total_pay_amt1=0.0
		        currency_id=record.n_quotation_currency_id if record else self.env.user.company_id.currency_id
		        for inv in invoice:
		            if inv.state in ('open', 'paid'):
		               d = json.loads(inv.payments_widget)
		               if d:
		                  for payment in d['content']:
		                    total_pay_amt1 += inv.currency_id.compute((payment['amount']),currency_id)
                               else:
                                    total_pay_amt1 += inv.currency_id.compute(inv.amount_total,currency_id)
                              
                       
			if  record.sale_id.converted_amount_total >= total_pay_amt1 :                 
		        	record.total_current_invoice=record.sale_id.converted_amount_total - total_pay_amt1 
			else:
				record.total_current_invoice=0.0

     @api.multi
     def send_block_rqst(self):
         for record in self:
             credit=self.env['res.partner.credit'].search([('sale_id','=',record.sale_id.id),('state','=','approve')])
             if credit:
                for cr in credit:
                    cr.partner_id.message_post(body='Credit Block Request from Delivery:  '+str(record.name))
                    cr.state='request'
                    cr.deliery_note='Please Unblock Credit Request of Delivery No.'+str(record.name)
                    cr.delivery_id=record.id
                record.message_post(body="Credit Request Send to Accountant")
             else:
                credit_rqst=self.env['res.partner.credit'].search([('sale_id','=',record.sale_id.id),('delivery_id','=',record.id),
                                                            ('state','=','request')])
                if credit_rqst:
                   for cr_rqst in credit_rqst:
                       cr_rqst.partner_id.message_post(body='please Check Credit Request '+' '+str(cr_rqst.delivery_id.name)+ 'Date   '+str(date.today()))
                       cr_rqst.deliery_note= 'please Check Credit Request ' +str(date.today())
                else:
                    if record.partner_id.parent_id:
                       record.partner_id.parent_id.write({'crdit_ids': [(0, 0, {
				'sale_id': record.sale_id.id,
				'sale_amount': record.sale_id.amount_total,
				'credit_ask': 0.0,
				'inv_paid': 0.0 ,
                                'partner_id':record.partner_id.parent_id.id,
                                'state':'request',
                                'delivery_id':record.id
		               })]})
                       record.partner_id.parent_id.message_post(body="Credit Request Send to Accountant  for Delivery Order:"+str(record.name))
                    else:
                        record.partner_id.write({'crdit_ids': [(0, 0, {
				'sale_id': record.sale_id.id,
				'sale_amount': record.sale_id.amount_total,
				'credit_ask': 0.0,
				'inv_paid': 0.0 ,
                                'partner_id':record.partner_id.id,
                                'state':'request',
                                'delivery_id':record.id
		               })]})
                        record.partner_id.message_post(body="Credit Request Send to Accountant  for Delivery Order:"+str(record.name))
                    record.message_post(body="Credit Request Send to Accountant")
             record.allow_delivery=False         

     @api.multi
     def credit_rqst_stock(self):
        for line in self:
            move_tree = self.env.ref('gt_order_mgnt.customer_credit_tree', False)
            move_form = self.env.ref('gt_order_mgnt.customer_credit_form', False)
            if move_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'res.partner.credit',
                    'views': [(move_tree.id, 'tree'), (move_form.id, 'form')],
                    'view_id': move_tree.id,
                    'target': 'current',
                    'domain':[('sale_id','=',self.sale_id.id)],
                }

        return True
     
     @api.multi
     @api.depends('total_current_invoice')
     def invoice_pend_bool(self):
         for record in self:
             if record and record.total_current_invoice > 0.0:
                record.is_pending=True
     @api.multi
     def total_splitdelivery(self):
         for record in self:
             split=self.env['stock.picking'].search([('parent_pick_id', '=', record.id)])  
             if split:
                record.split_count=len(split) 
                      
     @api.multi
     def action_child_delivery(self):
	do_tree = self.env.ref('stock.vpicktree', False)
	do_form = self.env.ref('stock.view_picking_form', False)
        if do_form:
            return {
		'name':"Split Delivery orders History",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'stock.picking',
		'views': [(do_tree.id, 'tree'), (do_form.id, 'form')],
                'view_id': do_tree.id,
                'target': 'current',
		'domain':[('parent_pick_id', '=', self.id)],
            }

     @api.multi
     def split_picking_data(self):
	order_form = self.env.ref('gt_order_mgnt.view_picking_form_split_aalmir', False)
	context = self._context.copy()
        list_l=[]  
        for line in self.move_lines:
            list_l.append((0,0,{'product_id':line.product_id.id,'name':line.name, 'state':line.state,
            			'product_uom_qty':line.product_uom_qty,'product_uom':line.product_uom.id,
            			'location_id':line.location_id.id,'location_dest_id':line.location_dest_id.id,
            			'split_move_id':line.id}))
	context.update({'default_move_line_id':list_l, 'default_picking_id':self.id })
        return {'name':'Split Main Delivery Order',
            	'type': 'ir.actions.act_window',
            	'view_type': 'form',
            	'view_mode': 'form',
            	'res_model': 'stock.picking.split',
            	'views': [(order_form.id, 'form')],
            	'view_id': order_form.id,
            	'target': 'new',
	    	'context':context,
		}


     @api.multi
     def open_return_orders(self):
	action = self.env.ref('stock.action_picking_tree_all')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        pick_ids = self.env['stock.picking'].search([('origin','=',self.name),('name','ilike','RE')])._ids

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',pick_ids)]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
	return result

     @api.multi
     def reverse_from_dispatch(self):			
        ''' Click by Manager To reverse from the Picking List(ready to Dispatch) state to previous state '''
        for rec in self:
                if rec.picking_status=='pick_list':
                    if any(line.pick_qty>=1 for line in rec.pack_operation_product_ids):
                        raise UserError("Still some qty are in pick location.Cant revert please contact logistic unit!!")

	     	if rec.picking_status != 'pick_list':
	     		raise UserError("Operation is not in proper state. You Can't Revert Back Please Contact Administrtor")
	     	rec.picking_status='draft'	
		if rec.sale_id.auto_invoice and rec.invoice_ids:
			for invoice in rec.invoice_ids:
				if invoice.state=='draft':
					invoice.action_cancel()
					rec.invoice_ids = [(3,invoice.id)]
					
		# to Update reserve in sale order
		for operation in rec.pack_operation_product_ids:
			if operation.n_sale_order_line:
				reserve_line=self.env['reserve.history'].search([
								('picking_id','=',rec.id),
								('product_id','=',operation.product_id.id),
								('sale_line','=',operation.n_sale_order_line.id),
								('res_qty','=',operation.qty_done),
								('n_status','=','r_t_dispatch')],limit=1)
				reserve_line.unlink()
								
								
	self.message_post(body="<li>Delivery order is <b>Revert Back</b> from Picking state</li>")
	
     @api.multi
     def create_auto_invoice(self):
     	'''Function to create invoice on delivery in AUTO invoice in sale orde
     		1) Draft invoice is created on sales support(validate)/INventory(Force validate) 
     		2) auto validate invoice on dispatch if it was not validated.
     		3) In draft case if quantity is changed current is cancelled and new invoce is created.'''
     		
     	for rec in self:
     		invoice_val=self.env['account.invoice']
        	account_line=self.env['account.invoice.line']
        	journal_id = invoice_val.default_get(['journal_id'])['journal_id']
        	invoice_picking_ids = []
		if rec.sale_id.auto_invoice:
                    invoice =invoice_val.create({'partner_id':rec.sale_id.partner_id.id,
                             'partner_invoice_id':rec.sale_id.partner_invoice_id.id,
                             'name': rec.sale_id.name,  'origin': rec.sale_id.name,
                             'type': 'out_invoice','journal_id': journal_id,
                             'n_lpo_receipt_date':rec.sale_id.lpo_receipt_date,
                             'n_lpo_issue_date':rec.sale_id.lpo_issue_date,
                             'n_lpo_document':rec.sale_id.lpo_document,
                             'document_id':[(6, 0, [x.id for x in  rec.lpo_document_id])],
                             'currency_id':rec.sale_id.n_quotation_currency_id.id \
                             			if rec.sale_id.n_quotation_currency_id \
                             			else rec.sale_id.currency_id.id ,
                             'user_id': rec.sale_id.user_id and rec.sale_id.user_id.id,    
                             'team_id': rec.sale_id.team_id.id, 'sale_id':rec.sale_id.id,
                             'account_id': rec.sale_id.partner_invoice_id.property_account_receivable_id.id,
                             'payment_term_id': rec.sale_id.payment_term_id.id,
                             'fiscal_position_id': rec.sale_id.fiscal_position_id.id or  rec.sale_id.partner_invoice_id.property_account_position_id.id })
                    
		    invoice.compute_taxes()
                    rec.invoice_ids=[(6, 0, [x.id for x in invoice])]
                    body='<ul><b>Product Quantity</b>'
                    for line in rec.pack_operation_product_ids: 
                        account = line.product_id.property_account_income_id or line.product_id.categ_id.property_account_income_categ_id
                        quantity = line.qty_done if line.qty_done else line.product_qty
                        inv_line=account_line.create({'invoice_id':invoice.id,'product_id':line.product_id.id, 
				    'quantity':quantity,
				    'lpo_documents':line.lpo_documents,
				    'invoice_line_tax_ids': [(6, 0, [x.id for x in  line.n_sale_order_line.tax_id])],
				    'uom_id':line.product_uom_id.id,'name':line.product_id.name, 
				    'price_unit':line.n_sale_order_price,
				    'account_id':line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id,})

                        inv_line.write({'sale_line_ids': [(6, 0, [line.n_sale_order_line.id])]})
                        body += '<li> [{}]{} : {} {}</li>'.format(inv_line.product_id.default_code,
                        		inv_line.product_id.name,inv_line,quantity,inv_line.uom_id.name)
                        #create invoice for service product
                        for sale_line in rec.sale_id.order_line:
                            if line.product_id.id != sale_line.product_id.id:
                               if sale_line.qty_invoiced < sale_line.product_uom_qty and sale_line.product_id.type !='product':
                                   inv_line=account_line.create({'invoice_id':invoice.id,
		                              	'product_id':sale_line.product_id.id, 
		                              	'quantity':(sale_line.product_uom_qty - sale_line.qty_invoiced),
		                              	'lpo_documents':line.lpo_documents,
		                              	'invoice_line_tax_ids': [(6, 0, [x.id for x in  sale_line.tax_id])],
		                              	'uom_id':sale_line.product_uom.id,
		                              	'name':sale_line.product_id.name, 
		                              	'price_unit':sale_line.price_unit,
              					'account_id':sale_line.product_id.property_account_income_id.id or sale_line.product_id.categ_id.property_account_income_categ_id.id,})
                                   inv_line.write({'sale_line_ids': [(6, 0, [sale_line.id])]})
                   	body +='</ul>'
                   	invoice.message_post(body)
                    return invoice
           	return True
           	
     @api.multi
     def send_to_dispatch(self):			
        ''' Click by Sale Support/Inventory To send in Picking state..'''
     	self.picking_status='pick_list'
        for rec in self:
            if rec.picking_type_id.code == 'outgoing' and rec.sale_id:
            	body="<ul> <b> Delivery Order is Validated and	<br> \
            			\n Quantity set to Picking and Dispatch</b>"
		
		delivery_data={}
                for operation in rec.pack_operation_product_ids:
			if operation.n_sale_order_line.product_uom_qty < operation.n_sale_order_line.qty_delivered:
                		rec.qty_exceed=True
			if not operation.qty_done:
				operation.qty_done = operation.product_qty
			body += '<li>Product : {}  {} {} </li>'.format(operation.product_id.name,operation.qty_done,\
							operation.product_uom_id.name)
			# add product in sale order line  when delivered qty is greater than order qty
			
			if operation.n_sale_order_line:
		    		if operation.product_id.type !='product':
		    			continue
	   			delivery_data[operation.n_sale_order_line.id] = delivery_data[operation.n_sale_order_line.id] +operation.qty_done  if delivery_data.get(operation.n_sale_order_line.id) else operation.qty_done
   			
	   	# code to check & Create Invoice in AUTO Invoice		
		if rec.sale_id.auto_invoice and not rec.invoice_ids:
			inovice=self.create_auto_invoice()
		elif rec.sale_id.auto_invoice and rec.invoice_ids:
			invoice_data={}
		    	for invoice in rec.invoice_ids:
	    			for inv in invoice.invoice_line_ids:
	    				if inv.product_id.type !='product':
		    				continue
					for so_line in inv.sale_line_ids:
						invoice_data[so_line.id] = invoice_data[so_line.id] + inv.quantity  if invoice_data.get(so_line.id) else inv.quantity
			
			equal = greater = less = False		
			for do_prd in delivery_data:
				if not invoice_data.get(do_prd,False):
					line_ids = self.env['sale.order.line'].search([('id','=',do_prd)])
					raise UserError("Product '{}' was not in Invoice".format(line_ids.product_id.name))
				if delivery_data.get(do_prd) == invoice_data.get(do_prd):
					equal=True
				elif delivery_data.get(do_prd) > invoice_data.get(do_prd):
					greater=True
				elif delivery_data.get(do_prd) < invoice_data.get(do_prd):
					less=True
			
			for invoice in rec.invoice_ids:
		    		if greater or less:
		    			raise UserError('Invoice Quantity in not matching with Delivery Quantity \n \
		    				Please Update Invoice Quantity')
		    			
		body += '</ul>'
                rec.message_post(body)
        return True 

     @api.multi
     def do_transfer(self):
     	'''Inherite this method for purchase order invoice create..'''
	return_val = super(StockPicking,self).do_transfer()
        invoice_val=self.env['account.invoice']
        account_line=self.env['account.invoice.line']
        uom_obj = self.env['product.uom']
        journal_id = invoice_val.default_get(['journal_id'])['journal_id']
        invoice_picking_ids = []
        for rec in self:
		if rec.picking_type_id.code == 'incoming' and rec.purchase_id and not  rec.purchase_id.payment_term_id.advance_per and not rec.purchase_id.milestone_ids:
		       journal = self.env['account.journal'].search([('type', '=', 'purchase'),('company_id','=',rec.company_id.id)], limit=1) 
		       invoice=self.env['account.invoice'].create({'purchase_id':rec.purchase_id.id, 
		             'type': 'in_invoice','origin':rec.purchase_id.name,
		             'account_id':rec.partner_id.property_account_payable_id.id,
		             'partner_id':rec.partner_id.id,'payment_term_id':rec.purchase_id.payment_term_id.id,
		             'journal_id':journal.id,'currency_id':rec.purchase_id.currency_id.id})
		       for line in rec.pack_operation_product_ids:
		           for p_line in rec.purchase_id.order_line:
		                if line.product_id.id == p_line.product_id.id and line.qty_done:
		                   account = account_line.get_invoice_line_account('in_invoice', p_line.product_id, rec.purchase_id.fiscal_position_id, self.env.user.company_id)
		                   qty_uom = uom_obj._compute_qty(line.product_uom_id.id,line.qty_done,\
		                   			 p_line.product_uom.id)
				   inv_line =account_line.create({
						    'purchase_line_id': p_line.id,
				                    'invoice_id':invoice.id,
						    'name': p_line.name,
						    'origin': rec.purchase_id.origin,
						    'uom_id': p_line.product_uom.id,
						    'product_id': p_line.product_id.id,
						    'account_id': account_line.with_context({'journal_id': journal.id, 'type': 'in_invoice'})._default_account(),
						    'price_unit': p_line.order_id.currency_id.compute(p_line.price_unit, rec.purchase_id.currency_id, round=False),
						    'quantity': qty_uom,
						    'discount': 0.0,
				                    'account_id':account.id,
						    'account_analytic_id': p_line.account_analytic_id.id,
		                                    'invoice_line_tax_ids': [(6, 0, [x.id for x in  p_line.taxes_id])],
						})
		                else:
		                    if not p_line.qty_invoiced and p_line.product_id.type == 'service':
		                       inv_line_service =account_line.create({
						    'purchase_line_id': p_line.id,
				                    'invoice_id':invoice.id,
						    'name': p_line.name,
						    'origin': rec.purchase_id.origin,
						    'uom_id': p_line.product_uom.id,
						    'product_id': p_line.product_id.id,
						    'account_id': account_line.with_context({'journal_id': journal.id, 'type': 'in_invoice'})._default_account(),
						    'price_unit': p_line.order_id.currency_id.compute(p_line.price_unit, rec.purchase_id.currency_id, round=False),
						    'quantity': p_line.product_qty,
						    'discount': 0.0,
				                    'account_id':account.id,
						    'account_analytic_id': p_line.account_analytic_id.id,
		                                    'invoice_line_tax_ids': [(6, 0, [x.id for x in  p_line.taxes_id])],
						})
		       invoice.compute_taxes()
		       rec.invoice_ids=[(6, 0, [x.id for x in invoice])]
		       invoice.picking_ids=[(6, 0, [x.id for x in rec])]
		       invoice.date_due=invoice.payment_date_inv
		elif rec.picking_type_id.code == 'incoming' and rec.purchase_id and rec.purchase_id.payment_term_id.advance_per or rec.purchase_id.milestone_ids:
		       account_line = self.env['account.invoice.line']
		       p_invoice=self.env['account.invoice']
		       journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1) 
		       invoice=p_invoice.search([('origin','=',rec.purchase_id.name)],limit=1)
		       new_invoice=False
		       if invoice.state == 'paid':
		          new_invoice=p_invoice.create({'purchase_id':rec.purchase_id.id, 
		                      'type': 'in_invoice','origin':rec.purchase_id.name,
		                      'account_id':rec.partner_id.property_account_payable_id.id,
		                      'partner_id':rec.partner_id.id,
		                      'payment_term_id':rec.purchase_id.payment_term_id.id,
		                      'journal_id':journal.id,
		                      'currency_id':rec.purchase_id.currency_id.id})
		       for line in rec.pack_operation_product_ids:
		           for p_line in rec.purchase_id.order_line:
		               account = account_line.get_invoice_line_account('in_invoice', p_line.product_id, rec.purchase_id.fiscal_position_id, self.env.user.company_id)
		               if line.product_id.id == p_line.product_id.id:
		                  if p_line.qty_received > p_line.product_qty:
		                     if invoice.state == 'draft':
		                        for inv_line in invoice.invoice_line_ids:
		                            if inv_line.product_id.id == p_line.product_id.id:
		                               inv_line.write({'quantity':inv_line.quantity +(p_line.qty_received - p_line.product_qty)}) 
		                               p_line.write({'qty_invoiced':p_line.qty_invoiced+(p_line.qty_received - p_line.product_qty)})
		                        invoice.compute_taxes()
		                     if new_invoice:
		                        inv_line =account_line.create({
						    'purchase_line_id': p_line.id,
				                    'invoice_id':new_invoice.id,
						    'name': p_line.name,
						    'origin': rec.purchase_id.origin,
						    'uom_id': p_line.product_uom.id,
						    'product_id': p_line.product_id.id,
						    'account_id': account_line.with_context({'journal_id': journal.id, 'type': 'in_invoice'})._default_account(),
						    'price_unit': p_line.order_id.currency_id.compute(p_line.price_unit, rec.purchase_id.currency_id, round=False),
						    'quantity': (p_line.qty_received - p_line.product_qty),
						    'discount': 0.0,
				                    'account_id':account.id,
						    'account_analytic_id': p_line.account_analytic_id.id,
		                                    'invoice_line_tax_ids': [(6, 0, [x.id for x in  p_line.taxes_id])],
						})
		                        new_invoice.compute_taxes()
				     if invoice.state == 'open':
		                        move_id=[]
		                        if invoice.payment_move_line_ids:
		                           for move_line in invoice.payment_move_line_ids:
		                               move_id.append(move_line.id)
		                               res=move_line.remove_move_reconcile()
		                        invoice.action_cancel()
		                        invoice.action_cancel_draft()
		                        for inv_line in invoice.invoice_line_ids:
		                            if inv_line.product_id.id == p_line.product_id.id:
		                               inv_line.write({'quantity':inv_line.quantity +(p_line.qty_received - p_line.product_qty)}) 
		                               p_line.write({'qty_invoiced':p_line.qty_invoiced+(p_line.qty_received - p_line.product_qty)})
		                        invoice.compute_taxes()

        return return_val     
 

     @api.multi
     @api.depends('sale_id')
     def total_sale_amount(self):
         for record in self:
             total_inv=0.0
             if record.sale_id and not record.sale_id.is_reception:
                if record.sale_id.invoice_ids:
                   for invoice in record.sale_id.invoice_ids:
                       if invoice.state in ('open','draft', 'paid'):
                          d = json.loads(invoice.payments_widget)
                          if d:
                            for payment in d['content']:
                               total_inv +=invoice.currency_id.compute(payment['amount'],record.n_quotation_currency_id)
			       
		   if record.sale_id.converted_amount_total >= total_inv:
			record.amount_total=record.sale_id.converted_amount_total - total_inv
		   else:
                   	record.amount_total=0.0
                else:
                    record.amount_total=record.sale_id.converted_amount_total

     @api.multi
     @api.depends('pack_operation_product_ids.price_subtotal')
     def total_delivery_qty_price_amount(self):
         for record in self:
             	amount=0.0#sum(record.line.price_subtotal
		if not record.sale_id.is_reception:
	     		for line in record.pack_operation_product_ids:
				currency=record.sale_id.n_quotation_currency_id if record.sale_id else self.env.user.company_id.currency_id
				if currency:
					amount+=currency.compute(line.price_subtotal,record.n_quotation_currency_id)
	     	record.total_delivery_amount=amount
    
     @api.multi
     def get_customer_pending_amount(self):
         for record in self:
	    if record.picking_type_id.code == 'outgoing' and record.sale_id and record.state not in ('transit','done','delivered','cancel') and not record.sale_id.is_reception:
                credit_currency_id=record.partner_id.credit_currency_id if record.partner_id.credit_currency_id else self.env.user.company_id.currency_id
                for record in self:
                     total=0.0
                     partner_id=[record.sale_id.partner_id.id]
		     for prtn in self.env['res.partner'].search([('parent_id','=',record.sale_id.partner_id.id)]):
			 partner_id.append(prtn.id)
                     invoice=self.env['account.invoice'].search([('state','=','open'),('sale_id', '!=', record.sale_id.id),('partner_id','in',tuple(partner_id))])
                     if invoice:
                        pay=0.0
                        for inv in invoice:
                            total += inv.residual_new1
                        record.customer_invoice_pending_amt=inv.currency_id.compute((total),credit_currency_id)
            else:
                record.customer_invoice_pending_amt=0.0           

     @api.multi
     def aalmir_picking_print(self):
        self.ensure_one()
        self.write({'printed': True})
        return self.env['report'].get_action(self, 'gt_order_mgnt.report_delivery_aalmir')
               
     @api.multi
     @api.depends('pack_operation_product_ids.gross_weight')
     def total_gross_weight_val(self):
        for record in self:
            if record.pack_operation_product_ids:
               record.total_gross_weight=sum(line.gross_weight for line in record.pack_operation_product_ids)
            else:
                record.total_gross_weight=0.0
 
     #### Add invoice history in stock
     @api.multi
     def open_invoices_history(self):
        for line in self:
            if not line.invoice_ids:
                raise UserError('No Invoices available!')
            invoice_tree = self.env.ref('account.invoice_tree', False)
            invoice_form = self.env.ref('account.invoice_form', False)
            if line.purchase_id:
            	invoice_tree = self.env.ref('account.invoice_supplier_tree', False)
            	invoice_form = self.env.ref('account.invoice_supplier_form', False)
            if invoice_tree:
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'account.invoice',
                    'views': [(invoice_tree.id, 'tree'), (invoice_form.id, 'form')],
                    'view_id': invoice_tree.id,
                    'target': 'current',
                    'domain':[('id','in',line.invoice_ids.ids)],
                }
        return True

class StockPackOperation(models.Model):
     _inherit='stock.pack.operation' 
    
     @api.model
     def create(self,vals):
	picking_id=vals.get('picking_id')
	product_id=vals.get('product_id')
	if product_id and picking_id and not vals.get('n_sale_order_line'):
		line_id=self.env['stock.move'].search([('picking_id','=',picking_id),('product_id','=',product_id)],limit=1)
                p_name=''
		if line_id.n_sale_line_id:
			vals.update({'n_sale_order_line':line_id.n_sale_line_id.id})
			if line_id.n_sale_line_id.product_packaging:
				vals.update({'packaging_id':line_id.n_sale_line_id.product_packaging.id})
	record = super(StockPackOperation,self).create(vals)   
	prev_id= self.env['stock.picking'].search([('name','=',record.picking_id.origin),('state','=','done')],limit=1)
	if prev_id:
		prev_pkg= self.search([('picking_id','=',prev_id.id),('product_id','=',product_id)])
		if prev_pkg.packaging_id:
			record.packaging_id=prev_pkg.packaging_id.id
			record.pack_qty=math.ceil((record.qty_done if record.qty_done else record.product_qty)/record.packaging_id.qty)
		if prev_pkg.secondary_pack:
			record.secondary_pack = prev_pkg.secondary_pack.id
	elif not record.packaging_id:
		pick_id= self.env['stock.picking'].search([('origin','=',record.picking_id.origin),('state','=','done'),('picking_type_code','=','incoming')],limit=1)
		if pick_id:
			prev_pkg= self.search([('picking_id','=',pick_id.id),('product_id','=',product_id)])
			if prev_pkg.packaging_id:
				record.packaging_id=prev_pkg.packaging_id.id
				record.pack_qty=math.ceil((record.qty_done if record.qty_done else record.product_qty)/record.packaging_id.qty)
			if prev_pkg.secondary_pack:
				record.secondary_pack = prev_pkg.secondary_pack.id
				
	if not record.packaging_id:
		for pkg in record.product_id.packaging_ids:
			if pkg.pkgtype == 'primary' and not record.packaging_id:
				record.packaging_id =pkg.id
				break
	return record

     gross_weight = fields.Float('Net Weight(Kg)', compute='grossweight' , store=True)## add new field gross weight
     net_weight = fields.Float('Gross Weight(Kg)', compute='netweight' , store=True)## add new field net weight

     product_hs_code = fields.Char('HS Code', related='product_id.product_hs_code')
     packaging_id = fields.Many2one('product.packaging',string='Packaging')
     pack_qty = fields.Integer('Packaging Qty', compute='total_packet_quantity',store=True)
     secondary_pack = fields.Many2one('product.packaging' ,string='Secondary Packaging')
     hide_packaging = fields.Boolean('Secondary pakcaging Hide',compute='total_pkg_pallet')
     pallet_no=fields.Float('Packing/Pallet', compute='total_pkg_pallet',store=True)
     total_pallet_qty = fields.Float('Total Pallets', compute='total_pkg_pallet',store=True,help="Total pallets Required for this Product")
     
#CH_N055 add fields to get date history and proper values start >>>
     n_sale_order_line = fields.Many2one('sale.order.line','Sale order line')
     n_sale_order_price =fields.Float('Unit Price',related='n_sale_order_line.price_unit')
     price_subtotal = fields.Float('Total amount', compute='total_price_amount')
#CH_N074>>
     lpo_documents = fields.Many2many('customer.upload.doc','sale_order_line_pack_rel','pack_id','doc_id',string='LPO Documents')
     primary_cbm = fields.Float('Primary CBM(M3)', compute='cal_primary_cbm')
     secondary_cbm = fields.Float('Secondary CBM(M3)', compute='cal_primary_cbm')
     external_no = fields.Char('External No.', compute='product_ext_no')

     @api.multi
     @api.depends('product_id')
     def product_ext_no(self):
	for record in self:
		if record.product_id and record.n_sale_order_line:
			cust=self.env['customer.product'].search([('product_id','=',record.product_id.id),('pricelist_id','=',record.n_sale_order_line.pricelist_id.id)], limit=1)
			if cust:
                            record.external_no=cust.ext_product_number
			else:
                            record.external_no=''

     @api.multi
     @api.depends('product_id.packaging_ids','pack_qty')
     def cal_primary_cbm(self):
        for record in self: 
    		for packg in record.product_id.packaging_ids:
                    if packg.pkgtype == 'primary':
                       length=self.env['n.product.discription'].search([('attribute.name','=','Length'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
                       width=self.env['n.product.discription'].search([('attribute.name','=','Width'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
                       height=self.env['n.product.discription'].search([('attribute.name','=','Height'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
		       record.primary_cbm=((float(length.value) * float(width.value) * float(height.value)) * record.pack_qty)/1000000
                    if packg.pkgtype == 'secondary':
                       length=self.env['n.product.discription'].search([('attribute.name','=','Length'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
                       width=self.env['n.product.discription'].search([('attribute.name','=','Width'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
                       height=self.env['n.product.discription'].search([('attribute.name','=','Height'),('product_id','=',packg.uom_id.product_id.product_tmpl_id.id)], limit=1)
		       record.secondary_cbm=((float(length.value) * float(width.value) * float(height.value)) * record.total_pallet_qty)/1000000   

     @api.multi
     @api.onchange('qty_done','packaging_id')
     def onchange_packaging(self):
        for record in self:
	    if record.picking_id.state not in ('transit','dispatch','done','delivered','cancel'):
	    	if record.packaging_id:
	    		if 'store' in record.packaging_id.uom_id.unit_type.mapped('string'):
				record.secondary_pack = False
				break
				
    			for packg in record.product_id.packaging_ids:
	   			if record.secondary_pack:
	   				break
   				if packg.pkgtype == 'secondary' and packg.unit_id.id==record.packaging_id.uom_id.id:
					record.secondary_pack = packg.id
					break
					
     @api.multi
     @api.depends('packaging_id','qty_done')
     def total_packet_quantity(self):
     	''' Update total packets according to Selected Primary packaging '''
     	for rec in self: 
     		if rec.picking_id.state not in ('transit','done','delivered','cancel'):
     			if rec.packaging_id:
     				qty = rec.qty_done if rec.qty_done else rec.product_qty
				rec.pack_qty=math.ceil(qty/rec.packaging_id.qty)
		
     @api.multi
     @api.depends('pack_qty','secondary_pack')
     def total_pkg_pallet(self):
     	'''Update Total Pallets and Required Pallets '''
        for record in self:
        	if record.picking_id.state not in ('transit','done','delivered','cancel'):
        		if record.pack_qty and record.secondary_pack:
              			record.pallet_no = record.secondary_pack.qty
				record.total_pallet_qty=math.ceil(record.pack_qty/record.secondary_pack.qty)
				record.hide_packaging = False
			elif record.packaging_id:
				if 'store' in record.packaging_id.uom_id.unit_type.mapped('string') or record.secondary_pack:
					record.pallet_no = record.packaging_id.qty
					record.total_pallet_qty = record.pack_qty
					record.hide_packaging = True
      
     @api.multi
     @api.depends('product_id','product_qty', 'qty_done','product_id.weight','packaging_id',\
     					'packaging_id.uom_id','secondary_pack','secondary_pack.uom_id')
     def netweight(self):
        for record in self:
            if record.packaging_id and record.picking_id.state not in ('transit','done','delivered','cancel'):
                record.net_weight = record.gross_weight+(record.pack_qty *record.packaging_id.uom_id.product_id.weight) + (record.total_pallet_qty * record.secondary_pack.uom_id.product_id.weight)

     @api.multi
     @api.depends('product_id','product_qty','qty_done','product_id.weight')
     def grossweight(self):
        for record in self:
		if record.picking_id.state not in ('transit','done','delivered','cancel'):
            		if record.product_id.weight:
               			record.gross_weight=((record.qty_done if record.qty_done else record.product_qty) * (record.product_id.weight if record.product_uom_id.name !='Kg' else 1))
            		else:
               			record.gross_weight = (record.qty_done if record.qty_done else record.product_qty) if record.product_uom_id.name =='Kg' else 0.0

     @api.multi
     @api.depends('product_qty', 'n_sale_order_price', 'qty_done')
     def total_price_amount(self):
         for record in self:
             if not record.qty_done:
                record.price_subtotal= record.product_qty * record.n_sale_order_price 
             if record.qty_done:
                record.price_subtotal= record.qty_done * record.n_sale_order_price
             if record.qty_done and record.product_qty:
                record.price_subtotal= record.qty_done * record.n_sale_order_price

#CH_N055
class stockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def _process(self, cancel_backorder=False):
    	'''To update delivery schedule date in sale support history '''
        self.ensure_one()
	super(stockBackorderConfirmation,self)._process(cancel_backorder)
        if not cancel_backorder:
		backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', self.pick_id.id)])
		for rec in backorder_pick:
			for line in rec.move_lines:
				if line.n_sale_line_id:
					self.env['mrp.delivery.date'].create({'n_dispatch_date_d':rec.min_date,
									'n_status':'waiting',
									'n_picking_id':rec.id,'n_type':'full',
									'n_line_id1':line.n_sale_line_id.id})
					line.n_sale_line_id._get_schedule_date()	

class stock_move_scrap(models.Model):
    _inherit = "stock.move.scrap"
    _description = "Scrap Products"

    scrap_reason=fields.Selection([('reject','Quality not Good'),('min','Quantity is Less' )], string="Scrap Reason")
    uploaded_documents = fields.Many2many('ir.attachment','scrap_attachment_rel','scrap_doc','id','Scrap Documents')
    available_qty = fields.Float('Available Qty')
    #mrp_id=fields.Many2one('mrp.production', string="MRP")
    
    @api.multi
    def move_scrap(self):
        obj = self.env['stock.move'].browse(self._context.get('active_id'))
        picking = self.env['stock.picking'].browse(self._context.get('active_id'))
	if self.product_qty > obj.product_qty:
		raise UserError(_("Please Enter Quantity less than or equal availabel Quantity"))
        if self.scrap_reason:
           obj.scrap_reason=self.scrap_reason
	#CH_N118 add code for quantity update
        if self.uploaded_documents:
	   search_ids=self.env['mrp.production'].search([('name','=',obj.name)])
	   if search_ids:
           	search_ids.uploaded_documents=self.uploaded_documents
	obj.product_uom_qty -= self.product_qty
	scrp_qty=self.product_qty
	res = super(stock_move_scrap, self).move_scrap()
        return res
#CH_N0#55 end<<<<<

    @api.model
    def default_get(self, fields):
        result= super(stock_move_scrap, self).default_get(fields)
        obj = self.env['stock.move'].browse(self._context.get('active_id'))
	if obj:
            result.update({'available_qty':obj.product_uom_qty if obj.product_uom_qty else 0.0})
        return result
        
class stockQuant(models.Model):
    _inherit = 'stock.quant' 
    
    #@api.multi
    #def _get_inventory_value(self,quant):
    #	print "QQQQQQQQQQQQQQQQQQ"
    #    return quant.product_id.standard_price * quant.qty
         
    @api.multi
    def write(self,vals):
    	print "quants....write..",vals,self
        return super(stockQuant, self).write(vals)
    	
    @api.model
    def create(self,vals):
    	res = super(stockQuant, self).create(vals)
    	print "quant..Create..",vals,res
        return res

#Inherite Method to update quantity in quants
    @api.v7
    def quants_get_preferred_domain(self, cr, uid, qty, move, ops=False, lot_id=False, domain=None, preferred_domain_list=[], context={}):
    	print "-----------quants_get_preferred_domain..order_mgnt",context
	if context.get('sale_support'):
		qty=context.get('res_qty')
        return super(stockQuant,self).quants_get_preferred_domain(cr, uid, qty, move, ops, lot_id, domain, preferred_domain_list, context)
               
class StockProductionLot(models.Model):
    _inherit='stock.production.lot'
    
    batch_ids=fields.One2many('mrp.order.batch.number','lot_id', string='Batch Details')
    production_id=fields.Many2one('mrp.production','Manufacturing No.')
    total_qty=fields.Float('Total Qty')
    product_uom_id=fields.Many2one('product.uom','Unit of Measure')

    @api.multi
    @api.depends('quant_ids')
    def total_lot_qty(self):
        for record in self:
            if record.quant_ids:
               record.total_qty=sum(line.qty for line in record.quant_ids)
               record.product_uom_id=record.quant_ids[0].product_uom_id.id
               
class StockMoveOperationLink(models.Model):
    _inherit='stock.move.operation.link'
    
    @api.model
    def create(self,vals):
    	res=super(StockMoveOperationLink,self).create(vals)
    	return res

