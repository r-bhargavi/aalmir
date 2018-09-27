
# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from urllib import urlencode
from urlparse import urljoin
from openerp import tools
from datetime import datetime, date, timedelta
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import json

def subset_sum_batches22(batches, target, partial=[]):
	qty_sum = sum([q.approve_qty for q in partial])
	if qty_sum  == target:		# check if the partial sum is equals to target
		return partial
	if qty_sum >= target:		# if sum is greater than quantity continue
		return  False	
	for i in range(len(batches)):
		n = batches[i]
		remaining = batches[i+1:]
		return_batches=subset_sum_batches(remaining, target, partial+[n])
		if return_batches:
			return return_batches
	return False

def subset_sum_batches(batches, target):
	try:
		partial=[]
		diff=0.0
		for i,start in enumerate(batches):
			if start.convert_product_qty >target:
				continue
			elif start.convert_product_qty == target: # check if the partial sum is equals to target
				return [partial]
			partial=[start]
			remaining=batches[i+1:]
			for j,next in enumerate(remaining):
		    		partial.append(next)
		    		qty_sum = sum([q.convert_product_qty for q in partial])		
		    		if qty_sum  == target:		# check if the partial sum is equals to target
					return partial
		    		if qty_sum >= target:		# if sum is greater than quantity continue
		    			diff = qty_sum - next.convert_product_qty
		    			partial.pop()
		    			flag=True
		    			if not any([ diff < q.convert_product_qty for q in remaining[j:]]):
						break
			if flag and diff:
				if not any([ diff < q.convert_product_qty for q in batches[i:]]):
					break
		return []
	except :
		pass
        	    
class saleSupportReserveRelease(models.TransientModel):
    _name = 'sale.support.reserve.release.wizard'
    
    @api.model
    def default_get(self, fields):
        result= super(saleSupportReserveRelease, self).default_get(fields)
        status=''
	if self._context.has_key('n_status') and self._context.get('n_status', False):
            result.update({'status':self._context.get('n_status')})

	if self._context.has_key('line_id') and self._context.get('line_id', False):
		status=self._context.get('n_status')
            	result.update({'sale_line':self._context.get('line_id')})
		line_id = self.env['sale.order.line'].search([('id','=',self._context.get('line_id'))])
		total_qty=qty=0.0
		if status=='reserve':
			loc_id=[line_id.order_id.warehouse_id.lot_stock_id.id]
			l_id=[]
			while True:
				loc=self.env['stock.location'].search([('location_id','in',loc_id),('id','not in',l_id)])
				if loc:
					loc_id.extend(loc._ids)
					l_id.extend(loc._ids)
				else:
					break

			domain=[('product_id','=',line_id.product_id.id),('location_id','in',loc_id),('reservation_id','=',False)]
			quants=self.env['stock.quant'].search(domain)
			qty=0.0
			for rec in quants:
				qty +=rec.qty
			quants_all=self.env['stock.quant'].search([('product_id','=',line_id.product_id.id),('location_id.actual_location','=',True)])
			for rec in quants_all:
				if rec.qty > 0:
					total_qty += rec.qty
				
		if status=='release':
			for line in self.env['reserve.history'].search([('sale_line','=',line_id.id)]):
				if line.n_status in ('release','cancel','delivered','r_t_dispatch','dispatch') :
			    		qty -= line.res_qty
				elif line.n_status in ('reserve'):
					qty += line.res_qty
			
			qty=0 if qty <0 else qty # in force reserve condition qty is less
			
		order_qty = line_id.product_uom_qty
		qty = qty if qty >0 else 0	
		result.update({'avl_qty': qty,'order_qty':order_qty,'total_avl_qty': total_qty})
		result.update({'res_qty': qty if status =='release' else (abs(line_id.pending_qty) if line_id.pending_qty<qty else qty if line_id.pending_qty else abs(line_id.product_uom_qty-qty))})
		result.update({'product_id': line_id.product_id.id and line_id.product_id.id or False})
        return result

    sale_line = fields.Many2one('sale.order.line', 'Sale Line')
    picking_id = fields.Many2one('stock.picking', 'Delivery Order')
    contract_id=fields.Many2one('customer.contract' ,string="Contract Name")
    
    product_id = fields.Many2one("product.product", "Product")
    res_date = fields.Datetime('Reserve/Release Date', default=fields.Datetime.now)
    res_qty = fields.Float('Reserve/Release Qty')  #reserve qty
    res_uom = fields.Many2one("product.uom",related="product_id.uom_id", string="UOM")
    status=fields.Selection([('release','Release'),('reserve','Reserve'),('cancel','Cancel'),('r_t_dispatch','Ready to Dispatch'),('delivered','Delivered')],'Status')	#CH_N045
    
    order_qty = fields.Float('Order Qty')
    order_uom = fields.Many2one("product.uom",related="sale_line.product_uom",string="UOM")	
    avl_qty = fields.Float('Available Qty')	
    avl_uom = fields.Many2one("product.uom",related="product_id.uom_id", string="UOM")
    total_avl_qty = fields.Float('Total Stock Quantity')
    total_uom = fields.Many2one("product.uom",related="product_id.uom_id", string="UOM")
    packaging = fields.Many2one("product.packaging",related="sale_line.product_packaging", string="Packaging")
    
    picking_policy = fields.Selection([('direct', 'Deliver each product when available'),
        				('one', 'Deliver all products at once')],
        				related="sale_line.order_id.picking_policy",
        				string='Shipping Policy',)
    @api.multi
    def reserve(self):
	for rec in self:
		if rec.res_qty <= 0.0:
			raise UserError('Please Enter Reserve quantity!!')
		if rec.res_qty > rec.avl_qty:
			raise UserError('You cannot reserve more than available quantity!!')
		if rec.res_qty  > rec.order_qty:
			raise UserError('You cannot reserve more than Order quantity!!')
		if (rec.res_qty+rec.sale_line.reserved_qty) > rec.order_qty:
			raise UserError('You cannot reserve more than Order quantity!!')

		search_id=self.env['mrp.order.batch.number'].search([('approve_qty','>',0),('store_id','!=',False),
							('logistic_state','=','stored'),('sale_id','=',False),
							('product_id','=',rec.product_id.id)],order='id')
		if search_id:
			numbers=[srch for srch in search_id]
			#print "kkkkkkkkkk,,,",len(numbers),search_id
			result_batches=subset_sum_batches(numbers,rec.res_qty)
			res_btch_qty=rec.res_qty
			if not result_batches:
				raise UserError("There are no group of Batches found with referance to your Entered \
						 Quantity\n please Increase or Decrease the quantity")
			for batch in result_batches:
				res_btch_qty -= batch.approve_qty
				batch.write({'logistic_state':'reserved','sale_line_id':rec.sale_line.id,
						'sale_id':rec.sale_line.order_id.id})
				if res_btch_qty<0:
					err	
		
		qty=0
		sale_line_vals={}
		n_status_rel=[]
		reserve_obj=self.env['reserve.history']
                if rec.sale_line:
                   vals={}
                   vals.update({'product_id':rec.product_id.id,'n_reserve_Type':'so','res_qty':rec.res_qty,
                   		'n_status':rec.status,'sale_line':rec.sale_line.id})
                   reserve_obj.create(vals)	# create reserve history
                  
                   for line in reserve_obj.search([('sale_line','=',rec.sale_line.id)]):
			if line.n_status in ('release','cancel','delivered'):
				qty -= line.res_qty
			if line.n_status in ('reserve','force_reserve'):  #r_t_dispatch
				qty += line.res_qty
		   				
		   print "ENd.......Reserve..!!!!",qty
		   st_qty = rec.sale_line.product_uom_qty - qty if rec.sale_line.product_uom_qty - qty >=0 else 0
		#CH_N054  >>>>>>>>>>>>>
		search_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1)
		if search_id:
			n_status_rel.append((4,search_id.id))
		new_id=self.env['sale.order.line.status'].search([('n_string','=','new')],limit=1)
		if new_id:
			n_status_rel.append((3,new_id.id))

		sale_line_vals.update({'pending_qty':st_qty,'reserved_qty':qty,'n_status_rel':n_status_rel})
		rec.sale_line.write(sale_line_vals)
	#CH_N047 >>>> to check first MRP delivery date if not then add
		delivery_ids=self.env['mrp.delivery.date'].search([('n_line_id1','=',rec.sale_line.id)])
		if not delivery_ids:
			self.env['mrp.delivery.date'].create({'n_line_id':rec.sale_line.id,
								'n_line_id1':rec.sale_line.id})
	#CH_N047 <<<<<
		print "ENd.......Reserve..!!!!............"
        return True

    @api.multi
    def release(self):
        for rec in self:
        	if rec.res_qty <= 0.0:
			raise UserError('Please Enter Release quantity!!')
		if rec.res_qty  > rec.avl_qty:
			raise UserError('You cannot release more than Reserve quantity!!')
			
		result=False
		search_id=self.env['mrp.order.batch.number'].search([('approve_qty','>',0),('store_id','!=',False),
							('logistic_state','=','reserved'),('sale_id','!=',False),
							('sale_line_id','=',rec.sale_line.id),
							('product_id','=',rec.product_id.id)],order='id desc')
		if search_id:
			numbers=[srch for srch in search_id]
			print "kkkkkkk,,,",numbers
			result=subset_sum_batches(numbers,rec.res_qty)		
		
		if not result:
			raise UserError("There are no group of Batches found with referance to your Entered Quantity\n \
				please Increase or Decrease the quantity")
				
		qty=st_qty=res_qty=0
		reserve_obj=self.env['reserve.history']
		sale_line_vals={}
                if rec.sale_line:
                   vals={}
                   vals.update({'product_id':rec.product_id.id,'res_qty':rec.res_qty,'n_status':rec.status,
                   		'sale_line':rec.sale_line.id})
                   reserve_obj.create(vals)	# create reserve history
                   
		for line in self.env['reserve.history'].search([('sale_line','=',rec.sale_line.id)]):
			if line.n_status in ('release','cancel','delivered','r_t_dispatch','dispatch') :
				res_qty -= line.res_qty
			if line.n_status in ('reserve','force_reserve'):#
				res_qty += line.res_qty
		
		qty = res_qty	
		print "qqqqqqqqqq/..........",qty		
		if rec.sale_line.product_uom_qty >= qty:
			st_qty = rec.sale_line.product_uom_qty - qty
		n_status_rel=[]
		if qty==0.0:
			#CH_N054  >>>>>>>>>>>>>
			search_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1)
			if search_id:
				n_status_rel.append((3,search_id.id))
			if not rec.sale_line.n_status_rel:
				new_id=self.env['sale.order.line.status'].search([('n_string','=','new')],limit=1)
				if new_id:
					n_status_rel.append((4,new_id.id))
			#CH_N055 <<<<<<<<<<<<<<<<<<<
			reserve_move=self.env['stock.move'].search([('n_sale_line_id','=',rec.sale_line.id),
							('state','in', ('confirmed', 'assigned','partially_available')),
							('picking_id.sale_id','=',rec.sale_line.order_id.id),
							('picking_id.picking_status','=','draft')],order='id asc')
			print "9999",reserve_move
			reserve_move.with_context({'sale_support':True}).do_unreserve()
			pack_op=self.env['stock.pack.operation'].search([('n_sale_order_line','=',rec.sale_line.id),
					('picking_id.state','not in',('done','delivered','transit')),
					('picking_id.picking_status','=','draft')])
			print ",,,,,,,,,,,,,,",pack_op
			#if pack_op:
			#	for op in pack_op:
			#		pack_op.unlink()
		else:
			reserve_move=self.env['stock.move'].search([('n_sale_line_id','=',rec.sale_line.id),
							('state','in', ('partially_available','confirmed', 'assigned')),
							('picking_id.sale_id','=',rec.sale_line.order_id.id),
							('picking_id.picking_status','=','draft')],order='id asc')
			for move in reserve_move:
				print "INsside..........323233",qty,move,move.product_uom_qty
				if qty >0 and qty >= move.product_uom_qty:
					context={'sale_support':True,'rel_stok':True,'res_qty':move.product_uom_qty,
						 #'reserve_only_ops':True if move.reserved_quant_ids else False,
						'sale_move_id':move,'sale_line_id':move.procurement_id.sale_line_id.id}
					#for link in move.linked_move_operation_ids:
					#	print "kkkkkkkkkkkk*****k",link
						#link.unlink()
						#link.operation_id=False
					move.with_context(context).action_assign()
					#move.with_context({'sale_support':True,'res_qty':move.product_uom_qty}).action_assign()
				elif qty >0 and qty < move.product_uom_qty:
					context={'sale_support':True,'res_qty':qty,'rel_stok':True,
						#'reserve_only_ops':True if move.reserved_quant_ids else False,
						'sale_move_id':move,'sale_line_id':move.procurement_id.sale_line_id.id}
					move.with_context(context).action_assign()
					#move.with_context({'sale_support':True,'res_qty':qty}).action_assign()
				else:
					break
				qty -= move.product_uom_qty
			
		sale_line_vals.update({'pending_qty':st_qty,'reserved_qty':res_qty,'n_status_rel':n_status_rel})
		rec.sale_line.write(sale_line_vals) 
		
		result_batches=False
		search_id=self.env['mrp.order.batch.number'].search([('approve_qty','>',0),('store_id','!=',False),
							('logistic_state','=','reserved'),('sale_id','!=',False),
							('sale_line_id','=',rec.sale_line.id),
							('product_id','=',rec.product_id.id)],order='id desc')
		if search_id:
			numbers=[srch for srch in search_id]
			result_batches=subset_sum_batches(numbers,rec.res_qty)		
		
		if not result_batches:
			raise UserError("There are no group of Batches found with referance to your Entered Quantity\n \
				please Increase or Decrease the quantity")
		release_batch_qty = rec.res_qty
		if result_batches:
			for batch in result_batches:
				if release_batch_qty>0:
					batch.write({'logistic_state':'stored','sale_line_id':False,'sale_id':False})
					release_batch_qty-=batch.approve_qty
        return True

	    

