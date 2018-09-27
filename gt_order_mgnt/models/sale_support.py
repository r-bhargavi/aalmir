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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See then_client_date
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from urlparse import urljoin
from urllib import urlencode
import json

class ReserveHistory(models.Model):
    _name = 'reserve.history'
    _order = "id desc"
        
    sale_line = fields.Many2one('sale.order.line', 'Sale Line')
    picking_id = fields.Many2one('stock.picking', 'Delivery Order')
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name")
    
    product_id = fields.Many2one("product.product", "Product")
    res_date = fields.Datetime('Reserve/Release Date', default=fields.Datetime.now)
    res_qty = fields.Float('Reserve/Release Qty')  #reserve qty
    res_uom = fields.Many2one("product.uom",related="product_id.uom_id", string="UOM")
    n_status=fields.Selection([('release','Release'),('reserve','Reserve'),('force_reserve','Force Reserve'),
    				('cancel','Cancel'),('r_t_dispatch','Ready to Dispatch'),('dispatch','Dispatched'),
    				('delivered','Delivered')],'Status')	#CH_N045
    n_reserve_Type=fields.Selection([('po','Purchase'),('mo','Manufacture'),('so','Stock'),('ext','Extra'),
    				     ('do','Delivery Order'),('co','Contract')],'Reserved From')
    
    #@api.multi
    #def reserve_qty_contract(self):
     #   for record in self:
       #     obj = self.env['contract.product.line'].browse(self._context.get('active_id')) 
         #   if record.avl_qty:
          #     print"%%%%%%%%%%%%%%%%%%%%%",record.avl_qty,obj.reserve_qty
           #    obj.update({'reserve_from_stock':obj.reserve_from_stock + record.res_qty, 'qty_avl':obj.qty_avl - record.res_qty })

#CH_N072 override create method to reserve quantity in quants
    @api.model
    def create(self,vals):
	res=super(ReserveHistory,self).create(vals)        
	if res.n_status=='reserve' and not res.picking_id:
		qty=0.0
		for line in self.search([('sale_line','=',res.sale_line.id)]):
			if line.n_status in ('release','cancel','r_t_dispatch','delivered'):
				qty -= line.res_qty
			if line.n_status in ('reserve','force_reserve'):
				qty += line.res_qty
		res_qty= qty
		moves=self.env['stock.move'].search([('n_sale_line_id','=',res.sale_line.id),
						     ('state','in', ('confirmed','partially_available')),
						  ('picking_id.sale_id','=',res.sale_line.order_id.id)],order='id asc')
		if not moves:
			raise UserError(_('There is no delivery order in Waiting/Partially Available'))
		
		print "Reserve Move start...-----------",moves,qty
		for rec in moves:
			print "INsside..........reserve move..",qty,rec,rec.product_uom_qty
			if qty >0 and qty >= rec.product_uom_qty:
				context={'sale_support':True,'res_qty':rec.product_uom_qty,'rel_stok':True,
					'reserve_only_ops':True if rec.reserved_quant_ids else False,
					'sale_move_id':rec,'sale_line_id':rec.procurement_id.sale_line_id.id}
				#rec.linked_move_operation_ids.unlink()
				rec.with_context(context).action_assign()
				#self.new_action_assign(rec,qty)
			elif qty >0 and qty < rec.product_uom_qty:
				context={'sale_support':True,'res_qty':qty,'rel_stok':True,
					'reserve_only_ops':True if rec.reserved_quant_ids else False,
					'sale_move_id':rec,'sale_line_id':rec.procurement_id.sale_line_id.id}
				rec.with_context(context).action_assign()
				#self.new_action_assign(rec,qty)
			else:
				break
			qty -= rec.product_uom_qty
			print "pppppppppppppp...-------",rec,qty
		print "ENd..................."
	return res
#CH_N072 override create method to avoid create record

    @api.multi
    def new_action_assign(self,move_id,res_qty):
    	print "test.....calling..",move_id,res_qty
    	for rec in move_id:
    		pack_id=self.env['stock.pack.operation'].create({'pack_lot_ids': [], 'package_id': False, 
    					'location_dest_id':rec.location_dest_id.id, 'product_id': rec.product_id.id,
					 'product_qty': res_qty, 'product_uom_id': rec.product_uom.id, 
					 'location_id': rec.location_id.id, 'picking_id': rec.picking_id.id,
					 'owner_id': False,'n_sale_order_line':rec.procurement_id.sale_line_id.id,
					 'lpo_documents':rec.procurement_id.sale_line_id.lpo_documents})
		print "pack Create..",pack_id
    		loc_id=[rec.procurement_id.warehouse_id.lot_stock_id.id]
		l_id=[]
		while True:
			loc=self.env['stock.location'].search([('location_id','in',loc_id),('id','not in',l_id)])
			if loc:
				loc_id.extend(loc._ids)
				l_id.extend(loc._ids)
			else:
				break

		domain=[('product_id','=',rec.product_id.id),('location_id','in',loc_id),('reservation_id','=',False)]
		quants=self.env['stock.quant'].search(domain,order='location_id asc')
		print "quants...",quants,domain
		qts=[]
		for qnt in quants:
    			if qnt.qty == res_qty:
    				qnt.reservation_id=rec.id
    				qts.append(qnt.id)
    				data=self.env['stock.move.operation.link'].create({'reserved_quant_id': qnt.id, 'operation_id': pack_id.id, 'move_id': rec.id, 'qty': res_qty})
    				print "create opeartion....",data
    				break
			elif qnt.qty > res_qty:
				qnt.copy(default={'qty':qnt.qty-res_qty})
				qnt.reservation_id=rec.id
				qts.append(qnt.id)
				data=self.env['stock.move.operation.link'].create({'reserved_quant_id': qnt.id, 'operation_id': pack_id.id, 'move_id': rec.id, 'qty': res_qty})
				print "create opeartion....else",data
				break
			else:
				qnt.reservation_id=rec.id
				res_qty -= qnt.qty
				qts.append(qnt.id)
				data=self.env['stock.move.operation.link'].create({'reserved_quant_id': qnt.id, 'operation_id': pack_id.id, 'move_id': rec.id, 'qty': res_qty})
				print "create opeartion....continue",data
	move_id.picking_id.recompute_pack_op=False		
	return True
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    #_inherit = ['ir.needaction_mixin']

    @api.model
    def _needaction_count(self, domain=None):
	return 12

    @api.multi
    def get_order_nbr(self):
        for line in self:
	    line.order_number =""
	    request_id=self.env['n.manufacturing.request'].search([('n_sale_order_line','=',line.id)])
	    if request_id:
		for rec in request_id:
		   if rec.n_state != 'cancel':
			line.order_number += str(rec.name) +"[("+str(int(rec.n_order_qty))+")\n"
			mo_record=self.env['mrp.production'].search([('request_line','=',rec.id)])
			for mo in mo_record:
				produce_qty=0.0
				for stock in mo.move_created_ids2:
					produce_qty += stock.product_uom_qty
				line.order_number += str(str(mo.name).split(',')[0]) +"("+str(int(produce_qty))+"/"+str(int(mo.product_qty))+")\n"
            
			te_record=self.env['purchase.requisition'].search([('request_id','=',rec.id)])
			for te in te_record:
				t_qty=0.0
				te_number =po_number=''
				for te_line in te.line_ids:
					t_qty += te_line.product_qty
				te_number += str(te.name)+"("+str(t_qty)+")\n"
				po_record=self.env['purchase.order'].search([('requisition_id','=',te.id)])
				for po in po_record:
				    if po.state != 'cancel':
					n_order_qty=n_received=0.0
					for po_order in po.order_line:
						n_order_qty += po_order.product_qty
						n_received += po_order.qty_received
					po_number += str(po.name) +"("+str(int(n_received))+"/"+str(int(n_order_qty))+")\n"
				line.order_number += po_number if po_number else te_number
			line.order_number += "]\n"

    @api.multi
    def _get_days(self):
	for rec in self:
                if rec.n_client_date:
		    if datetime.strptime(rec.n_client_date,'%Y-%m-%d').date() <= date.today():
			flag=False		
			if rec.n_status_rel:
				for line in rec.n_status_rel:
					if line.n_string=='delivered':
						flag=True
			days =abs(date.today()-datetime.strptime(rec.n_client_date,'%Y-%m-%d').date()).days
			if flag:
				rec.n_no_of_days=rec.n_no_of_days
				rec.n_delivery ='dated'
			else:
				rec.n_no_of_days=days
				rec.n_delivery ='dated'
		    else:
			days=abs(datetime.strptime(rec.n_client_date,'%Y-%m-%d').date()-date.today()).days
			rec.n_no_of_days=0
			if days==0:
				rec.n_delivery ='today'
			elif days > 0 and days <=7 :
				rec.n_delivery ='week'
			elif days >7 and days <=15:
				rec.n_delivery ='2week'

    @api.multi
    @api.depends('product_id.qty_available','reserved_qty')
    def get_available_qty(self):
     #CH_N073 to get available qty>>>
	for line in self:
		loc_id=[line.order_id.warehouse_id.lot_stock_id.id]
		l_id=[]
		while True:
			loc=self.env['stock.location'].search([('location_id','in',loc_id),('id','not in',l_id)])
			if loc:
				loc_id.extend(loc._ids)
				l_id.extend(loc._ids)
			else:
				break
				
		domain=[('product_id','=',line.product_id.id),('location_id','in',loc_id),('reservation_id','=',False)]
		quants=self.env['stock.quant'].search(domain)
		qty=0.0
		for rec in quants:
			if rec.qty>0:
				qty+=rec.qty
		line.available_qty = qty #if line.n_status_rel.n_string !='delivered' else 0

    @api.multi
    @api.depends('reserved_qty','product_uom_qty','available_qty')
    def get_pending_qty(self):
     #CH_N073 to get Pending qty>>>
	for line in self:
	   qty=st_qty=0.0
	   for rec in self.env['reserve.history'].search([('sale_line','=',line.id)]):
		if rec.n_reserve_Type not in ('mo','po'):
		   	if rec.n_status in ('release','cancel'):
				qty -= rec.res_qty
		   	if rec.n_status in ('reserve','force_reserve'):
				qty += rec.res_qty
	   production_req = self.env['n.manufacturing.request'].search([('n_sale_order_line','=',line.id),
	   								('n_state','not in',('cancel','new'))])
	   if production_req:
		qty1=0.0
		for rec1 in production_req:
			done_qry="select sum(qty_done) from stock_pack_operation where n_sale_order_line="+str(line.id)+" and product_id="+str(line.product_id.id)+" and picking_id in (select id from stock_picking where location_id IN (select id from stock_location where quality_ck_loc=True) and picking_type_id in (select id from stock_picking_type where n_quality_ck=True))"
		   	self.env.cr.execute(done_qry)
			record=self.env.cr.fetchone()
			if rec1.n_mo_number.state =='done':
				qty1 =record[0]
			if qty1 == 0.0 :
                                qty +=rec1.n_order_qty
		if qty1:
			qty = qty+qty1
		if line.product_uom_qty >= qty and qty>0.0:
			st_qty=line.product_uom_qty - qty
		else:
			st_qty=0.0
	   else:
		if line.product_uom_qty >= qty:
			st_qty=line.product_uom_qty-qty
		else:
			st_qty=0.0
	   line.pending_qty = abs(st_qty)
     #CH_N073 end<<<<<

#CH_N038 start add fields functions.>>
    @api.multi
    def _get_tolerance(self):
        for line in self:
            n_tolerance= line.product_id.n_production_tolerance
	    per_tol=0.0	
	    if line.mo_id.state=='done':
	    	if line.product_id.n_production_tolerance:
			produce_qty=0.0
			for rec in line.mo_id.move_created_ids2:
			    if rec.state=='done':
				produce_qty += rec.product_uom_qty
			qty=produce_qty - line.mo_id.product_qty
			per_tol=(float(qty)/float(line.mo_id.product_qty))*100
	    #line.n_tolerance = "("+str(int(n_tolerance))+"/"+str(abs(int(per_tol)))+")\n" comented on aamir requirement 7th june
	#CH_N126 new code on 7th June
	    manu_id = self.env['mrp.production'].search([('sale_line','=',line.id),('state','=','done')])
	    tolerance=''
	    for rec in manu_id:	
		produce_qty=rec.product_qty
		for res in rec.move_created_ids2:
			if res.state=='done':
				produce_qty -= res.product_uom_qty
		val= produce_qty*-1 if produce_qty > 0.0  else abs(produce_qty)
	    	tolerance += str(rec.name)+"("+str(val)+")\n"	#CH_N127 add to change the sign of qty (produce_qty*-1)
	    line.n_tolerance = tolerance
	    if int(abs(per_tol)) > int(n_tolerance):
	    	line.n_exceed_tolerance = True

    @api.multi
    @api.depends('order_id.lpo_receipt_date','order_id.delivery_day_3','order_id.force_date','order_id.pop_receipt_date',
	'order_id.delivery_day_type','order_id.delivery_day','order_id.delivery_date1')
    def get_client_date(self):
	for rec in self:	    
	  #Client Date >>
	    n_client_date=n_date=False
	    if rec.order_id.delivery_day_3 == 'confirmed_purchase_order':
		if rec.order_id.lpo_receipt_date:
			n_date=rec.order_id.lpo_receipt_date
		elif rec.order_id.signed_quote_receipt_date:
			n_date=rec.order_id.signed_quote_receipt_date
		elif rec.order_id.email_confirmation_date:
			n_date=rec.order_id.email_confirmation_date
		else:
			n_date=rec.order_id.force_date

	    if rec.order_id.delivery_day_3 == 'receipt_of_payment':
		if rec.order_id.force_date:
			if not rec.order_id.pop_receipt_date:
				n_date=rec.order_id.force_date
			else:
				n_date=rec.order_id.pop_receipt_date
		else:
			invoice_paid_date=False
			invoice_ids=self.env['account.invoice'].search([('advance_invoice','=',True),('sale_id','=',rec.order_id.id)],limit=1)
			if invoice_ids:
				payment_date=self.env['account.move'].search([('name','=',invoice_ids.name)],limit=1)
				if payment_date:
					invoice_paid_date=payment_date.date
			if not invoice_paid_date:
				if not rec.order_id.pop_receipt_date:
					n_date=rec.order_id.force_date
				else:
					n_date=rec.order_id.pop_receipt_date
			else:
				n_date=invoice_paid_date
	    if not n_date:
			n_date=str(date.today())
	    if rec.order_id.delivery_day_type=='days' and n_date:
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.order_id.delivery_day))
	    elif rec.order_id.delivery_day_type=='weeks' and n_date :
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.order_id.delivery_day)*7)
	    elif rec.order_id.delivery_day_type=='months' and n_date :
			n_client_date = datetime.strptime(n_date,'%Y-%m-%d')+timedelta(days=int(rec.order_id.delivery_day)*30)
	    elif rec.order_id.delivery_day_type=='Date':
			n_client_date= rec.order_id.delivery_date1
	    rec.n_client_date=n_client_date
	   #CH_N073<<<<

#CH_N038 end <<<<

    @api.multi
    @api.depends('partner_shipping_id','partner_shipping_id.city_id','partner_shipping_id.city_id.transit_time')
    def _get_transttime(self):  #add code to get transit time for delivery
	for rec in self:
	   #transit time >>> CH_N073 >>>
	    transit_time=0.0
	    if rec.order_id.state in ('done','cancel'):	  #add condition to store value of existing records when state is done
		transit_time=rec.n_transit_time
	    elif rec.partner_shipping_id and rec.order_id.incoterm.code != 'EXF': 
		if rec.partner_shipping_id.city_id:
			 transit_time=rec.partner_shipping_id.city_id.transit_time
	    rec.n_transit_time = transit_time

    @api.multi
    @api.depends('n_manu_date','n_client_date','n_transit_time','n_qty_delivered')
    def _get_schedule_date(self):
	for rec in self:
	    n_client_date=''
	    #qry="select min(n_dispatch_date_d) from mrp_delivery_date where id in (select max(id) from mrp_delivery_date where n_picking_id in (SELECT distinct n_picking_id from mrp_delivery_date where n_line_id1="+str(rec.id)+" and n_picking_id not in (select id from stock_picking where state in ('done','delivered'))) group by n_picking_id)"
	    qry="SELECT min(n_dispatch_date_d) from mrp_delivery_date where n_line_id1="+str(rec.id)+" and n_picking_id not in (select id from stock_picking where state in ('done','delivered'))"
	    self.env.cr.execute(qry)
	    date=self.env.cr.fetchone()   
	    if date and date[0] != None:
		n_client_date = date[0]
	    else:
		qry="SELECT min(n_dispatch_date_d) from mrp_delivery_date where n_line_id1="+str(rec.id)+" and n_picking_id in (select id from stock_picking where state in ('done','delivered'))"
		self.env.cr.execute(qry)
		n_date=self.env.cr.fetchone() 
		if n_date:
			n_client_date = n_date[0]
	    if not n_client_date:
		if rec.n_manu_date:
			n_client_date=datetime.strptime(rec.n_manu_date,'%Y-%m-%d') +timedelta(1)
	        elif rec.n_client_date:
			n_client_date=datetime.strptime(rec.n_client_date,'%Y-%m-%d') - timedelta(rec.n_transit_time)
	    rec.n_schdule_date = n_client_date
	    rec.n_delivery_status = 'draft'

    @api.multi
    def _get_delivery_qty(self):
	for rec in self:
		qry ="select sum(res_qty) from reserve_history where sale_line="+str(rec.id)+" and n_status in ('dispatch','delivered')"
		self.env.cr.execute(qry)
		result=self.env.cr.fetchone()
		rec.n_qty_delivered = result[0] if result else 0.0
		if rec.product_uom_qty == result[0]:
			rec.n_delivery_status='delivered'

#CH_N116 add code to get invoice qty>>
    @api.multi
    def total_invoice_qty(self):
        for record in self:
	    total_inv=total_inv_pay=0.0
	    invoice=self.env['account.invoice'].search([('sale_id','=',record.order_id.id),('state','in',('open','paid', 'draft'))])
	    invoice_ids = record.mapped('invoice_lines').mapped('invoice_id')
	    for inv in invoice:
	           if inv.state in ('open', 'paid'):
	              d = json.loads(inv.payments_widget) 
	              if d:
	                 for payment in d['content']:
	                    total_inv_pay += payment['amount']
		   to_currency=record.order_id.report_currency_id if record.order_id.report_currency_id else record.order_id.n_quotation_currency_id
	           total_inv  += inv.currency_id.compute(inv.amount_total,to_currency)   #CH_N103 add convert currency 
	    record.invoice_data = '('+str(total_inv_pay)+'/'+str(total_inv) +')'

#CH_N044 end <<
    available_qty = fields.Float('Available Qty',compute='get_available_qty',digits_compute = dp.get_precision('Product'),)
    reserved_qty = fields.Float('Reserved qty', digits_compute=dp.get_precision('Product'),default=0.0)
    pending_qty = fields.Float('Pending qty',compute='get_pending_qty', digits_compute=dp.get_precision('Product'),store=True)
    pr_id = fields.Many2one('purchase.order', 'PO Number')
    mo_id = fields.Many2one('mrp.production', 'MO Number')
    order_number = fields.Char('MO/PO Number', compute=get_order_nbr)
    bom_id = fields.Many2one('mrp.bom', 'BOM', domain=[('id', '<=', 0)])
    supplier_id = fields.Many2one('res.partner', 'Vendor', domain=[('supplier', '=', True)])
    res_ids = fields.One2many('reserve.history', 'sale_line', 'Reserve History')
    order_id = fields.Many2one('sale.order', string='Order Reference', required=True, ondelete='cascade', index=True,copy=False)

    date_order=fields.Datetime(related='order_id.date_order', string="Sale Order Date")
    partner_shipping_id=fields.Many2one('res.partner', string="Delivery Location", related="order_id.partner_shipping_id",store=True)
    lpo_number = fields.Char(related='order_id.lpo_number', string="PO Number")
    lpo_receipt_date = fields.Date(related='order_id.lpo_receipt_date', string="PO Receipt Date")
    lpo_issue_date = fields.Date(related='order_id.lpo_issue_date',string='PO Issued Date')
    payment_term =fields.Many2one("account.payment.term", related="order_id.payment_term_id", string="Payment Term")
    default_code = fields.Char(related='product_id.default_code', string="Product Number")
    
    n_delivery = fields.Selection([('today', 'Today'),
                                ('week', 'Week'),
			        ('2week', '2Week'),
                                ('dated', 'out_Dated')], string="Delivery Time", compute='_get_days',)
    n_no_of_days = fields.Integer(compute='_get_days', string="Delivery Days Excess")

    n_status_rel = fields.Many2many('sale.order.line.status','sale_order_line_status_rel','sale_id','status_id','Status')
    n_tolerance = fields.Char(compute='_get_tolerance' , string="Production Tolerance (%)")  
    n_client_date = fields.Date(string="Client Delivery Date",compute='get_client_date',store=True)
    n_manu_date = fields.Date(string="Manufacture Complete Date")
    n_schdule_date = fields.Date(string="Schedule Dispatch Date",compute='_get_schedule_date',store=True)
    n_delivery_status = fields.Selection([ ('draft', 'Draft'),('delay', 'Delayed'),
					('ready_t_dispatch', 'Ready To Dispatch'),
					('dispatch', 'Dispatch'),
					('delivered', 'Delivered'),
					('done', 'Done'),
					('cancel', 'Cancelled')], string='Delivery Status',default='draft',compute='_get_delivery_qty')
    n_transit_time = fields.Integer(string="Transit Time",compute='_get_transttime',store=True)
    payment_date=fields.Datetime(related='order_id.payment_date', string="Due Date")

    n_produce_qty = fields.Float('Produced/Received Qty', digits_compute=dp.get_precision('Product'),default=0.0)
    n_extra_qty = fields.Float('Extra Produce/Received Qty', digits_compute=dp.get_precision('Product'),default=0.0)

    new_date_bool = fields.Boolean("New Productoin date", default=False)
    n_exceed_tolerance = fields.Boolean("Exceed Tolerance", default=False, compute='_get_tolerance')

    date_ids = fields.One2many('mrp.complete.date', 'n_line_id', 'DATE history')
    n_qty_delivered = fields.Float('delivered qty',compute='_get_delivery_qty')
    delivery_ids = fields.One2many('mrp.delivery.date', 'n_line_id1', 'DATE history')
    prd_ids = fields.One2many('n.manufacturing.request', 'n_sale_order_line', 'Production Request')

    invoice_data=fields.Char(compute='total_invoice_qty', string="Invoice Count")
    #n_lpo_numbers=fields.Char(compute='get_lpo_numbers', string="Call offs",store=True)

    @api.multi
    def create_purchase_order(self):
        line = self[0]
        if not line.supplier_id:
            raise UserError('Please select Vendor for the Product %s'%line.product_id.name or line.name)
        context = {'supplier_id': line.supplier_id.id, 'sale_id': line.order_id.id, 'line_id':line.id}
        if line.supplier_id:
            po_form = self.env.ref('purchase.purchase_order_form', False)
            if po_form:
                return {'name':'Purchase Order',
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
    def create_purchase_requisition(self):
        purchase_req = self.env['purchase.requisition']
        for line in self:
            requisition_data = {'user_id':self._uid, 'line_ids':[(0,0,{'product_id':line.product_id and line.product_id.id or False,
                                                      'product_qty':line.pending_qty,
                                                      'product_uom_id':line.product_uom and line.product_uom.id or False})]}
            purchase_request = purchase_req.create(requisition_data)
            line.pr_id = purchase_request.id
            context = {'active_id':purchase_request.id, 'active_ids':[purchase_request.id]}
            if purchase_request:
                pr_tree = self.env.ref('purchase_requisition.view_purchase_requisition_tree', False)
                pr_form = self.env.ref('purchase_requisition.view_purchase_requisition_form', False)
                if pr_tree:
                    return {'name':'Purchase Requisition',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'purchase.requisition',
                        'views': [(pr_tree.id, 'tree'), (pr_form.id,'form')],
                        'view_id': pr_tree.id,
                        'target': 'current',
                        'context': context,
                        'domain':[('id','=',purchase_request.id)],
                    }
        return True
        
#CH_N039 add code to send production request from sale support >>>
    @api.multi
    def create_manufacturing_order(self):
        line = self[0]
        mo_form = self.env.ref('gt_order_mgnt.n_production_request_form', False)
	line_id =self.env['n.manufacturing.request'].search([('n_sale_order_line','=',self.id),('n_state','!=','cancel')])
	n_flag=False
	#CH_N047 >>>> 
	delivery_ids=self.env['mrp.delivery.date'].search([('n_line_id','=',self.id)])
	if not delivery_ids:
		#main_id=self.env['delivery.date.history'].create({'n_line_id':rec.sale_line.id})
		self.env['mrp.delivery.date'].create({'n_line_id':self.id,'n_line_id1':self.id})
	#CH_N047 <<<<<
	if line_id:
		n_flag=True
        if mo_form:
		
		context = self._context.copy()
		#packg=self.product_packaging.id if self.product_packaging else self.env['product.packaging'].search([
		#					('product_tmpl_id','=',self.product_id.product_tmpl_id.id),
		#					('pkgtype','=','primary')],limit=1).id
		packg=self.product_packaging.id
		context.update({'default_n_sale_line':self.order_id.id,'default_n_sale_order_line':self.id,
				'default_n_delivery_date':self.n_schdule_date,'default_n_exist_pr':n_flag,#CH_N045 add field to PR exist or not for more than one request
				'default_n_packaging':packg,
				'default_n_order_qty':self.pending_qty,'default_n_product_id':self.product_id.id,
				'default_n_unit':self.product_uom.id,
				'default_n_category':self.product_id.categ_id.id,
				'default_n_default_code':self.product_id.default_code,})
				
                return {'name':'Manufacturing Order',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'n.manufacturing.request',
                    'view_id': mo_form.id,
                    'target': 'new',
                    'context': context,
                    'flags': {'form': {'options': {'mode': 'edit'}}}
                }
#CH_N039 end
    @api.multi
    def reserve_do(self):
        reserve_form = self.env.ref('gt_order_mgnt.sale_support_reserve_wizard_form_view', False)
        if self.reserved_qty >= self.product_uom_qty:
			raise UserError('You are already reserved for order')
        if reserve_form:
            return {'name':'Reserve Quantity',
		    'type': 'ir.actions.act_window',
		    'view_type': 'form',
		    'view_mode': 'form',
		    'res_model': 'sale.support.reserve.release.wizard',
		    'views': [(reserve_form.id, 'form')],
		    'view_id': reserve_form.id,
		    'target': 'new',
		    'context': {'line_id': self.id,'n_status':'reserve'},}

#CH_N045 >>>    
    @api.multi
    def release_do(self):
        release_form = self.env.ref('gt_order_mgnt.sale_support_release_wizard_form_view', False)
        if release_form:
            return {'name':'Release Quantity',
        	    'type': 'ir.actions.act_window',
        	    'view_type': 'form',
        	    'view_mode': 'form',
        	    'res_model': 'sale.support.reserve.release.wizard',
        	    'views': [(release_form.id, 'form')],
        	    'view_id': release_form.id,
        	    'target': 'new',
        	    'context': {'line_id': self.id,'n_status':'release'},
            }

    ### Add invoice history vml
    @api.multi
    def open_invoices(self):
	return self.order_id.action_view_invoice()

    @api.multi
    def open_pickings(self):
    	print "*-**--*-*"
        for line in self:
            picking_tree = self.env.ref('stock.vpicktree', False)
            picking_form = self.env.ref('stock.view_picking_form', False)
	    #context=self._context.copy()
	    #context.update({'lpo_name': True})
	    move=self.env['stock.move'].search([('procurement_id.sale_line_id','=',line.id)])
	    print ",,,-----------",move,[i.picking_id.id for i in move]
            if picking_tree and move:
                return {'name':'Delivery orders',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'stock.picking',
                    'views': [(picking_tree.id, 'tree'), (picking_form.id, 'form')],
                    'view_id': picking_tree.id,
                    'target': 'current',
		    #'context':context,
                    'domain':[('id','in',[i.picking_id.id for i in move])],
                }
        return True

# add code to remove the sum in group by
    def read_group(self,cr,uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,lazy=True):
        if 'customer_lead' in fields:
            fields.remove('customer_lead')
	if 'price_unit' in fields:
	    fields.remove('price_unit')
	#if 'reserved_qty' in fields:
	#	fields.remove('reserved_qty')
	#if 'pending_qty' in fields:
	#	fields.remove('pending_qty')
	#if 'n_extra_qty' in fields:
	#	fields.remove('n_extra_qty')
        return super(SaleOrderLine, self).read_group(cr,uid,domain,fields, groupby, offset, limit=limit, context=context, orderby=orderby,lazy=lazy)

#CH_N040 add open sale order from sale support view >>>> 
    @api.multi
    def open_sale_order(self):
	order_form = self.env.ref('sale.view_order_form', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
	    'res_id': self.order_id.id,
            'target': 'current',
	    'context':{'show_sale': True},
	    'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}}
#CH_N040 <<

#CH_N043 add open Delivery Date Information view from sale support view >>>> 
    @api.multi
    def n_delivery_date_info(self):
	order_tree = self.env.ref('gt_order_mgnt.delivery_date_view', False)
	order_form = self.env.ref('gt_order_mgnt.delivery_date_view_form', False)
        return {'name':'Schedule Delivery Dates',
            	'type': 'ir.actions.act_window',
            	'view_type': 'form',
            	'view_mode': 'tree',
            	'res_model': 'mrp.delivery.date',
	    	'domain':[('n_line_id1','=',self.id)],
            	'views': [(order_tree.id, 'tree'),(order_form.id, 'form')],
            	'view_id': order_form.id,
            	'target': 'new',}

#add open Extra Quantity view from sale support view >>>> 
    @api.multi
    def n_extra(self):
	order_form = self.env.ref('gt_order_mgnt.extra_quantity_view', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'n.extra.quantity',
	    'domain':[('n_line_id','=',self.id)],
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':{'default_n_sale_order_line':self.id},
        }
#CH_N047<<
#CH_N050 >>	
    @api.multi
    def approve_producton_date(self):
	search_id=self.env['sale.order.line.status'].search([('n_string','=','date_request')],limit=1) ## add status
	if search_id:
		self.n_status_rel=[(3,search_id.id)]
	for rec in self.env['mrp.complete.date'].search([('n_line_id','=',self.id)],limit=1,order='id desc'):
		rec.n_status='done'
		rec.n_user_id=self.env.uid	#update aproved user
		if rec.n_mo:
			rec.n_mo.n_request_date_bool1=False
			rec.n_mo.n_request_date_bool=True
                        rec.n_mo.message_post(body='<span style="color:green;font-size:14px;">New Date Approved By Sale support -:</span>\n '+
                                        'New Date:'+str(rec.n_nextdate) +'\t'+ 'Old Date:' +str(rec.n_prevoiusdate1))
		if rec.n_po:
			rec.n_po.n_request_date_bool1=False
			rec.n_po.n_request_date_bool=True
		self.n_manu_date=rec.n_nextdate
		self.new_date_bool=False
        return True
#CH_N051 >>to open manufacture history
    @api.multi
    def manu_date_history(self):
	order_form = self.env.ref('gt_order_mgnt.manufacturing_date_history_view', False)
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'mrp.complete.date',
	    'domain':[('n_line_id','=',self.id),('n_status','!=','draft')],
            'views': [(order_form.id, 'tree')],
            'view_id': order_form.id,
            'target': 'new',
        }
#CH_N051<<<
#CH_N085 >> to Cancel Production Request >>>
    @api.multi
    def production_request_history(self):
	mo_form = self.env.ref('gt_order_mgnt.n_production_request_tree_sales_support', False)
	return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'n.manufacturing.request',
                    'domain':[('n_sale_order_line','=',self.id)],
		    'views': [(mo_form.id, 'tree')],
		    'view_id': mo_form.id,
		    'target': 'new',
                }
#CH_N085 <<<<

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    @api.model
    def default_get(self, fields):
        result = super(PurchaseOrder, self).default_get(fields)
        if self._context.has_key('line_id') and self._context.get('line_id', False):
            result.update({'sale_line': self._context.get('line_id')})
        return result

    sale_line = fields.Many2one('sale.order.line', 'Sale Line')

    @api.model
    def create(self, vals):
        sal_line = self._context.get('line_id')
        if self._context.get('supplier_id'):
            vals.update({'sale_line': self._context.get('line_id'), 'partner_id': self._context.get('supplier_id')})
        po_id = super(PurchaseOrder, self).create(vals)
        if sal_line:
            self.env['sale.order.line'].sudo().browse(sal_line).write({'po_id': po_id.id})
        return po_id
    
    @api.onchange('sale_line')
    def onchange_sale_line(self):
        if self.sale_line:
            self.partner_id = self.sale_line.supplier_id.id
            return

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    @api.model
    def default_get(self, fields):
        result = super(PurchaseOrderLine, self).default_get(fields)
        if self._context.has_key('line_id') and self._context.get('line_id', False):
            result.update({'sale_line': self._context.get('line_id')})
        return result

    sale_line = fields.Many2one('sale.order.line', 'Sale Line')

    @api.onchange('sale_line')
    def onchange_sale_line(self):
        if self.sale_line:
            self.product_id = self.sale_line.product_id.id
            self.product_qty = self.sale_line.pending_qty
            self.product_uom = self.sale_line.product_uom
            return
    
#CH_N047 add code to show extra reserver qty >>>>>>
class n_ExtraQty(models.Model):
	_name = "n.extra.quantity"

	n_sale_order_line =fields.Many2one('sale.order.line','sale order Line')
	n_sale_order =fields.Many2one('sale.order','sale order',related='n_sale_order_line.order_id')
	
	n_extra_qty = fields.Float('Extra qty', related='n_sale_order_line.n_extra_qty')
	n_qty = fields.Float('Quantity', digits_compute=dp.get_precision('Product'),default=0.0)

	@api.multi
	def n_release(self):
		if self.n_extra_qty < self.n_qty:
			raise UserError('You cannot Release more than available quantity!')
		if self.n_qty < 0.0 :
			raise UserError('Please Enter Proper quantity!')

		self.n_sale_order_line.n_extra_qty=self.n_extra_qty - self.n_qty
		return True

	@api.multi
	def n_reserve(self):
		if self.n_extra_qty < self.n_sale_order_line.product_uom_qty:
			raise UserError('You cannot Reserve more than order quantity!.')
		if self.n_extra_qty < self.n_qty:
			raise UserError('You cannot Reserve more than available quantity!.')
		if self.n_qty < 0.0 :
			raise UserError('Please Enter Proper quantity!')
		vals={'product_id':self.n_sale_order_line.product_id.id,'res_qty':self.n_qty,
			'n_status':'reserve','n_reserve_Type':'ext',
			'res_date':date.today(),'sale_line':self.n_sale_order_line.id}
		self.env['reserve.history'].create(vals)
		qty=0.0
		for line in self.env['reserve.history'].search([('sale_line','=',self.n_sale_order_line.id)]):
			if line.n_status == 'release' :
				qty -= float(line.res_qty)
			if line.n_status == 'reserve' :
				qty += float(line.res_qty)
		self.n_sale_order_line.reserved_qty=qty
		self.n_sale_order_line.n_extra_qty=self.n_extra_qty - self.n_qty
		return True	
#CH_N047 <<<<

