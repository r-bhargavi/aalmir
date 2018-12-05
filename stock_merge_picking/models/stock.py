# -*- coding: utf-8 -*-
from openerp import models, fields, api,_
from openerp import tools
from datetime import datetime, date, timedelta,time
import time
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare, float_round
from openerp.exceptions import UserError
from urlparse import urljoin
from urllib import urlencode
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import sys
import logging
_logger = logging.getLogger(__name__)

def subset_sum_batches(batches, target):
	try:
		for i,start in enumerate(batches):
			partial = [start]
			partial_sum = sum([q.convert_product_qty for q in partial])
			if partial_sum == target: # check if the partial sum is equals to target
				return partial
				
			flag=False
			ntarget = target - partial_sum
			
			if all([ q.convert_product_qty > ntarget for q in batches[i+1:]]):
				continue
			dif_rem = [x for x in batches[i+1:] if x.convert_product_qty==ntarget ]
			if dif_rem:
				partial.append(dif_rem[0])
				return partial
			remaining=[x for x in batches[i+1:] if x.convert_product_qty<=ntarget ]
			new_partial = []
			for j,next in enumerate(remaining):
				# existing qty + new batch Quantity
				partial_sum += next.convert_product_qty
		    		if target == partial_sum :# check if the partial sum is equals to target
		    			new_partial.append(next)
					partial.extend(new_partial)
					return partial
		    		elif target < partial_sum:	# if sum is greater than quantity continue
					partial_sum -= next.convert_product_qty
		    			diff = target - partial_sum
		    			nremaining = batches[j+1:]
	    				if all([ q.convert_product_qty>diff for q in nremaining]):
						break
				else:
					new_partial.append(next)
					htarget = target - partial_sum
					dif_rem = [x for x in batches[j+1:] if x.convert_product_qty==htarget ]
					if dif_rem:
						new_partial.append(dif_rem[0])
						break
			partial.extend(new_partial)
			if sum([x.convert_product_qty for x in partial ]) == target:
				return partial
		return []
		
	except Exception as e:
		print "Exception in Batch Finding...",e
		pass
		
class stock_picking(models.Model):
    _inherit = "stock.picking"

    merge_notes= fields.Text("Merge Notes")
    total_deliver_qty=fields.Float('Total Qty', compute='total_delivered_quantity')
    n_sale_order_line =fields.Many2one('sale.order.line','Sale order line')
    return_raw_picking=fields.Boolean('Return Raw material Picking filter')

    @api.multi
    def force_assign(self):
    	self.message_post(body='<b>Force Available</b>')
	return super(stock_picking,self).force_assign()
	
    @api.multi
    @api.depends('pack_operation_product_ids')
    def total_delivered_quantity(self):
        for record in self:
		record.total_deliver_qty=sum(line.qty_done for line in record.pack_operation_product_ids)

	
#CH_N053>>>>
    @api.multi
    def do_transfer(self):
	for rec in self:
		if rec.picking_type_id.code=='incoming' and not self._context.get('do_only_split'): 
			po_ids=self.env['purchase.order'].search([('name','=',rec.origin)])
			if po_ids:
				for p_line in po_ids.order_line:
					for n_line in rec.pack_operation_product_ids:
						if p_line.product_id.id == n_line.product_id.id:
							n_qty= n_line.qty_done if n_line.qty_done else n_line.product_qty
			
							n_status_rel=[]
							recipient_partners=str(po_ids.request_id.n_sale_order_line.order_id.user_id.login)
							if po_ids.production_ids:
								search_id=self.env['sale.order.line.status'].search([('n_string','=','manufacture')],limit=1) ## add status
								if search_id:
									n_status_rel.append((4,search_id.id))
								po_ids.request_id.n_state='scheduled'
								if po_ids.request_id.n_category.cat_type=='film':
									for usr in self.env['res.groups'].search([('name', '=', 'group_film_product')]).users:
					    					recipient_partners += ","+str(usr.login)
								if po_ids.request_id.n_category.cat_type=='injection':
									for usr in self.env['res.groups'].search([('name', '=', 'gropu_injection_product')]).users:
						    				recipient_partners += ","+str(usr.login)
							else:	
								search_id=self.env['sale.order.line.status'].search([('n_string','=','quality_check')],limit=1) ## add status
								if search_id:
									n_status_rel.append((4,search_id.id))

                                                                if po_ids.request_id:
								   po_ids.request_id.n_state='done'
								for usr in self.env['res.groups'].search([('name', '=', 'Sales Support Email')]).users:
					    				recipient_partners += ","+str(usr.login)
								
							if n_qty >= p_line.product_qty:
								new_id=self.env['sale.order.line.status'].search([('n_string','=','purchase')],limit=1) ## remove status
								if new_id:
									n_status_rel.append((3,new_id.id))
							if po_ids.request_id:
                                                                #ADD VML
                                                                vals={'product_id':po_ids.request_id.n_product_id.id,
                                                              'res_qty':n_qty,'n_status':'reserve',
                                                              'n_reserve_Type':'po',
						              'res_date':date.today(),
                                                               'sale_line':po_ids.request_id.n_sale_order_line.id
                                                               }
                                                                ids=self.env['reserve.history'].create(vals)
								self.env['sale.order.line'].sudo().browse(po_ids.request_id.n_sale_order_line.id).write({'n_status_rel':n_status_rel, 'reserved_qty':(po_ids.request_id.n_sale_order_line.reserved_qty + n_qty)}) 

			#CH_N069 <<<
			#CH_N078 >>> add code to send mail on production complete >>>
								temp_id = self.env.ref('gt_order_mgnt.email_template_MRP_complete')
								if temp_id:
								
									user_obj = self.env['res.users'].browse(self.env.uid)
									base_url = self.env['ir.config_parameter'].get_param('web.base.url')
									query = {'db': self._cr.dbname}
									fragment = {
									    'model': 'sale.order.line',
									    'view_type': 'form',
									    'id': po_ids.request_id.n_sale_order_line.id,
									}
									url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))

									body_html = """<div>
						    <p> <strong>Product Requset is Complete </strong></p><br/>
						    <p>Dear Sir/Madam,<br/>
							Your sale order No-:<b> %s </b> product_no-:'%s ' (%s) Qty are Purchased on Date :<b>%s \n</b> and Move to Quality Checking
						    </p>
						    </div>"""%(po_ids.request_id.n_sale_order_line.order_id.name or '',po_ids.request_id.n_sale_order_line.product_id.name+po_ids.request_id.n_sale_order_line.product_id.default_code or '',str(n_qty),str(date.today()))

									body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'sale.order.line',po_ids.request_id.n_sale_order_line.id, context=self._context)
				
									temp_id.write({'body_html': body_html,
									 'email_to':recipient_partners,
									 'email_from': user_obj.partner_id.email})
									temp_id.send_mail(po_ids.request_id.n_sale_order_line.id)
	#  Pre-Stock Operation start >>>>>>>>>>>>
		if rec.picking_type_id.code=='internal' and rec.picking_type_id.default_location_src_id.pre_ck == True :
			po_ids=self.env['purchase.order'].search([('name','=',rec.origin)])
			message=''
			if not po_ids:
			   for n_line in rec.pack_operation_product_ids:
				n_qty=p_qty= n_line.qty_done if n_line.qty_done else n_line.product_qty
				message += '<h4 style="color:green">Qty move to '+str(rec.location_dest_id.name)+'</h4> <li>Product: '+str(n_line.product_id.name)+'</li><li>Quantity :'+str(n_qty)+str(n_line.product_uom_id.name)+'</li>'
				if n_line.n_sale_order_line:
					n_status_rel=[]
					reserve_qty =extra_qty=0.0
					for line in self.env['reserve.history'].search([('sale_line','=',n_line.n_sale_order_line.id)]):
						if line.n_status in ('release','cancel','delivered'):
							reserve_qty -= float(line.res_qty)
						if line.n_status in ('reserve'):
							reserve_qty += float(line.res_qty)
					if n_line.n_sale_order_line.product_uom_qty < (reserve_qty + n_qty):
						extra_qty = (reserve_qty + n_qty) - n_line.n_sale_order_line.product_uom_qty
						n_qty = n_line.n_sale_order_line.product_uom_qty - reserve_qty
					if n_qty > 0.0:
						vals={'product_id':n_line.product_id.id,'res_qty':n_qty,
							'sale_line':n_line.n_sale_order_line.id,
							'n_status':'reserve','n_reserve_Type':'mo',
							'res_date':date.today(),}
						ids=self.env['reserve.history'].create(vals)
					search_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1) 
					if search_id:
						n_status_rel.append((4,search_id.id))
					new_id=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')],limit=1) 
					if new_id:
						n_status_rel.append((3,new_id.id))
					
					n_line.n_sale_order_line.write({'reserved_qty':(reserve_qty+n_qty),
								'n_extra_qty':extra_qty,'n_status_rel':n_status_rel})
			else:
			   for n_line in rec.pack_operation_product_ids:
				n_qty=p_qty= n_line.qty_done if n_line.qty_done else n_line.product_qty
				message += '<h4 style="color:green">Qty move to '+str(rec.location_dest_id.name)+'</h4> <li>Product: '+str(n_line.product_id.name)+'</li><li>Quantity :'+str(n_qty)+' '+str(n_line.product_uom_id.name)+'</li>'
				if po_ids.request_id.n_sale_order_line and not po_ids.production_ids:
					n_status_rel=[]
					reserve_qty =extra_qty=0.0
					for line in self.env['reserve.history'].search([('sale_line','=',po_ids.request_id.n_sale_order_line.id)]):
						if line.n_status in ('release','cancel','delivered'):
							reserve_qty -= float(line.res_qty)
						if line.n_status in ('reserve'):
							reserve_qty += float(line.res_qty)
			
					if po_ids.request_id.n_sale_order_line.product_uom_qty < (reserve_qty + n_qty):
						extra_qty = (reserve_qty + n_qty) - po_ids.request_id.n_sale_order_line.product_uom_qty
						n_qty = po_ids.request_id.n_sale_order_line.product_uom_qty - reserve_qty
					if n_qty > 0.0:
						vals={'product_id':po_ids.request_id.n_sale_order_line.product_id.id,'res_qty':n_qty,
							'sale_line':po_ids.request_id.n_sale_order_line.id,
							'n_status':'reserve','n_reserve_Type':'po','res_date':date.today(),}
						ids=self.env['reserve.history'].create(vals)
					search_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1) 
					if search_id:
						n_status_rel.append((4,search_id.id))
					new_id=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')],limit=1) 
					if new_id:
						n_status_rel.append((3,new_id.id))
					
					po_ids.request_id.n_sale_order_line.write({'reserved_qty':(reserve_qty+n_qty),
								'n_extra_qty':extra_qty,'n_status_rel':n_status_rel})
			if message:
				rec.message_post(message)
	# Pre-Stock opeartion end <<<<<<<<<<<<<<
	#QC opeartion start>>>>		
		if rec.picking_type_id.code=='internal' and rec.picking_type_id.n_quality_ck == True:
			for n_line in rec.pack_operation_product_ids:
				n_status_rel=[]
				if n_line.n_sale_order_line:
					search_id=self.env['sale.order.line.status'].search([('n_string','=','pre_stock')],limit=1) 
					if search_id:
						n_status_rel.append((4,search_id.id))
				
					new_id=self.env['sale.order.line.status'].search([('n_string','=','quality_check')],limit=1) 
					if new_id:
						n_status_rel.append((3,new_id.id))
					n_line.n_sale_order_line.write({'n_status_rel':n_status_rel})
	#QC opeartion END<<<<<<<<<<		
		super(stock_picking,self).do_transfer()
		if rec.picking_type_id.code=='outgoing' and not self._context.get('do_only_split'):
			rec.action_first_validation()
	return True
	
    @api.multi
    def send_to_dispatch(self):
	for rec in self:
		if rec.picking_type_id.code=='outgoing' and not self._context.get('do_only_split'):
			delivery_ids=[]	
			for line in rec.pack_operation_product_ids:
				#CH_N061 code to update status in sale order line >>>
				qty=0.0
                                n_status_list=[]
         			qty = line.qty_done if line.qty_done > 0 else line.product_qty
		        		
				if line.n_sale_order_line:
				    #CH_N062 >>>
					delivery_ids.append(line.n_sale_order_line.id)
					if qty>0.0:
						vals={'product_id':line.product_id.id,'res_qty':qty,
							'n_status':'r_t_dispatch', 'res_date':datetime.now(),
							'sale_line':line.n_sale_order_line.id,'picking_id':rec.id}
						self.env['reserve.history'].create(vals)
				   #CH_N062<<<<
					#CH_N074>>>>
					n_type='partial'
					qty=0.0
					for n_line in line.n_sale_order_line.res_ids:
						if n_line.n_status in ('delivered','r_t_dispatch'):
							qty += n_line.res_qty 
					if line.n_sale_order_line.product_uom_qty <= qty:
						n_type='full'

					date_rec = self.env['mrp.delivery.date'].search([
								('n_picking_id','=',line.picking_id.id),
								('n_line_id1','=',line.n_sale_order_line.id)],limit=1)

					if not date_rec :
						self.env['mrp.delivery.date'].create(
								{'n_dispatch_date_d':line.picking_id.min_date,
								'n_status':'r_t_dispatch',
								'n_picking_id':line.picking_id.id,'n_type':n_type,
								'n_line_id1':line.n_sale_order_line.id})
					else:
						self.env['schedule.delivery.date.history'].create({
									'n_nextdate':date.today(),
									'n_status':'validate',
									'n_picking_id':line.picking_id.id,
									'n_line_id':line.n_sale_order_line.id,
									'delivery_id':date_rec[0].id})
									
						date_rec.write({'n_status':'r_t_dispatch','n_type':n_type,
									'n_dispatch_date_d':date.today()})
					
					#line.n_sale_order_line.n_schdule_date=line.picking_id.min_date
					line.n_sale_order_line._get_schedule_date()
				    #CH_N074<<<<
					search_id=self.env['sale.order.line.status'].search([('n_string','=','r_t_dispatch')],limit=1) #Add
					if search_id:
						n_status_list.append((4,search_id.id))
					if n_type=='full':
						new_id=self.env['sale.order.line.status'].search([('n_string','=','warehouse')],limit=1) # remove
						if new_id:
						   n_status_list.append((3,new_id.id))

                                if line.n_sale_order_line:
				   line.n_sale_order_line.n_status_rel=n_status_list

				#CH_N061<<<<
				delivery_rec = self.env['mrp.delivery.date'].search([
						('n_picking_id','=',line.picking_id.id),
						('n_line_id1','not in',delivery_ids)])
				if delivery_rec:
					date_ids=self.env['schedule.delivery.date.history'].search([
								('delivery_id','in',[ d.id for d in delivery_rec])])
					if date_ids:
						date_ids.unlink()
					delivery_rec.unlink()
	return super(stock_picking,self).send_to_dispatch()
	
    @api.multi
    def schedule_date_change(self):
	order_form = self.env.ref('stock_merge_picking.schedule_delivery_date_change_form_view', False)
	context = self._context.copy()
	context.update({'default_n_prevoiusdate':self.min_date,
			'default_n_prevoiusdate1':self.min_date,'default_n_status':'scheduled',
			'default_n_picking_id':self.id})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'schedule.delivery.date.history',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,}

    @api.multi
    def dispatch_date_change(self):
	order_form = self.env.ref('stock_merge_picking.dispatch_date_change_form_view', False)
	context = self._context.copy()
	context.update({'default_n_prevoiusdate':self.dispatch_date,
			'default_n_prevoiusdate1':self.dispatch_date,'default_n_status':'schedule_dispatch',
			'default_n_picking_id':self.id})
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'schedule.delivery.date.history',
            'views': [(order_form.id, 'form')],
            'view_id': order_form.id,
            'target': 'new',
	    'context':context,}

class StockMove(models.Model):
	_inherit="stock.move"
	
	@api.multi
	def force_assign(self):
		result= super(StockMove,self).force_assign()
		for res in self:
			if res.picking_id.picking_type_code=='outgoing' and res.n_sale_line_id:
		   		move = self.env['stock.move'].search([('n_sale_line_id','=',res.n_sale_line_id.id),
		   						     ('picking_id','=',res.picking_id.id),
		   						     ('product_id','=',res.product_id.id)])
				quants = self.env['stock.quant'].search([('reservation_id','=',res.id),
        							       ('product_id','=',res.product_id.id)])
		 		reserve_qty = sum([x.qty for x in quants])
				reserve_qty = (res.product_qty - reserve_qty) if res.product_qty > reserve_qty else (reserve_qty - res.product_qty)
				sale_line_vals={'res_ids':[(0,0,{'product_id':res.product_id.id,'n_reserve_Type':'do',
					'res_qty':reserve_qty,'n_status':'force_reserve'})]}
				n_status_rel=[]
				search_id=self.env['sale.order.line.status'].search([
					('n_string','=','force_reserve')],limit=1)
				if search_id:
					n_status_rel.append((4,search_id.id))
				new_id=self.env['sale.order.line.status'].search([('n_string','=','new')],limit=1)
				if new_id:
					n_status_rel.append((3,new_id.id))
			
				sale_line_vals.update({'reserved_qty':res.n_sale_line_id.reserved_qty+reserve_qty,
						       'n_status_rel':n_status_rel})
				res.n_sale_line_id.write(sale_line_vals)
				delivery_ids=self.env['mrp.delivery.date'].search([
								('n_line_id1','=',res.n_sale_line_id.id)])
				if not delivery_ids:
					self.env['mrp.delivery.date'].create({'n_line_id':res.n_sale_line_id.id,
									'n_line_id1':res.n_sale_line_id.id})
									
			elif res.picking_id.picking_type_code=='internal':
				if res.location_dest_id.actual_location and res.location_id.actual_location:
					res.picking_id.picking_status ='pick_list'
					#for pack in res.picking_id.pack_operation_product_ids:
					#	pack.qty_done=pack.product_qty
					raise	
				if res.location_id.actual_location and res.location_dest_id.usage == 'production':
					res.picking_id.picking_status ='pick_list'
					for pack in res.picking_id.pack_operation_product_ids:
						pack.qty_done=pack.product_qty
								
				#if res.location_dest_id.actual_location and res.location_id.pre_ck:
				#	raise UserError('You can\'t perform this opeartion(froce assign).')
		return result

	@api.multi
	def action_assign(self,no_prepare=False):
		# Update Context to avoid unreserve and reserve of Batches
		self = self.with_context(reserve_api=True)
		result = super(StockMove,self).action_assign(no_prepare)
		for res in self:
			domain=[('picking_id','=',res.picking_id.id),('product_id','=',res.product_id.id)]
			if res.picking_id.picking_status !='draft':
				return result
			# check only for stockable products
			if res.picking_id.picking_type_code=='outgoing' and res.product_id.type =='product':
			   sale_line = res.n_sale_line_id.id if res.n_sale_line_id else False
			   if sale_line:
			   	domain.append(('n_sale_line_id','=',sale_line))
			   move = self.env['stock.move'].search(domain)
			   _logger.info("Start BATCH Reserve Process {}....\n".format(res.product_id.default_code))
			   if res.picking_id :#and res.picking_id.location_dest_id.usage=='customer':
				quants=self.env['stock.quant'].search([('reservation_id','in',move._ids),
        							       ('product_id','=',res.product_id.id)])
		 		reserve_qty=sum([x.qty for x in quants])
                                print "reserve qty condidtion if picking idd-----",reserve_qty
		 		if not reserve_qty :
					if res.picking_id.quant_reserved_exist == True:
						continue
	 				pack_id = self.env['stock.pack.operation'].search([
							('picking_id','=',res.picking_id.id),
							('product_id','=',res.product_id.id)])
			 		if pack_id:
	 					raise UserError("Reserved quantity not found for product [{}]{},\n  Please contact administrator.".format(res.product_id.default_code,res.product_id.name))
	 				else:
		 				continue
		 		product_packaging_qty = 0.0		
 				if sale_line and not res.product_packaging:
 					raise UserError("Product packaging not found, Please Contact Administrator")
 				
 				elif not sale_line:
 					pkg=self.env['product.packaging'].search([('pkgtype','=','primary'),
						('product_tmpl_id','=',res.product_id.product_tmpl_id.id)],
						limit=1,order='qty desc')
					res.product_packaging = pkg.id
					pack_id = self.env['stock.pack.operation'].search([
							('picking_id','=',res.picking_id.id),
							('product_id','=',res.product_id.id)])
			 		if pack_id:
			 			pack_id.packaging_id = pkg.id
					
				product_packaging_qty = res.product_packaging.qty
				# Check Existing reserve batches >>start
				back_id=self.env['mrp.order.batch.number'].search([('convert_product_qty','>',0),
						('store_id','!=',False),
						('store_id.n_location','=',res.location_id.id),
						('logistic_state','in',('reserved','transit')),
						('picking_id','=',res.picking_id.id),
						('product_id','=',res.product_id.id)],order='id')
				reserve_qty -= sum([ i.convert_product_qty for i in back_id])
                                print "reserve_qtyin main if cons=dition of outgoing",reserve_qty,back_id
				res_btch_qty = reserve_qty # get new reserved qty
				packets = int(reserve_qty / res.product_packaging.qty)
				result_batches = []
				if packets >0: 
					# Get batches with quantity of sale order in backorder
					sale_line_batches=self.env['mrp.order.batch.number'].search([
						('convert_product_qty','>',0.0),
						('store_id','!=',False),('logistic_state','in',('stored','transit_in')),
						('sale_line_id','=',sale_line),('product_id','=',res.product_id.id),
						('picking_id','=',False),
						('store_id.n_location','=',res.location_id.id),
						],order='id',limit=packets)
					reserve_qty -= sum([ i.convert_product_qty for i in sale_line_batches])
                                        print "reserve_qtyreserve_qty in sale line batcjes if packets>0",reserve_qty,sale_line_batches
					if sale_line_batches:
						numbers=[srch for srch in sale_line_batches]
						result_batches.extend(numbers)
					packets -= len(sale_line_batches)
				if reserve_qty and packets >0:
					# Get batches with quantity of sale order packaging
					search_id=self.env['mrp.order.batch.number'].search([
						('convert_product_qty','=',product_packaging_qty),
						('store_id','!=',False),('logistic_state','in',('stored','transit_in')),
						('sale_line_id','=',False),('product_id','=',res.product_id.id),
						('picking_id','=',False),
						('store_id.n_location','=',res.location_id.id),
						],order='id',limit=packets)
					reserve_qty -= sum([ i.convert_product_qty for i in search_id])
                                        print "reserve_qtyreserve_qty in search id condition",reserve_qty,search_id
					packets -= len(search_id)
					if search_id:
						numbers=[srch for srch in search_id]
						result_batches.extend(numbers)
					if reserve_qty and packets:
						exist_id = [srch.id for srch in result_batches]
						search_id=self.env['mrp.order.batch.number'].search([
						('convert_product_qty','=',product_packaging_qty),
						('store_id','!=',False),('logistic_state','in',('stored','transit_in')),
						('id','not in',exist_id),('product_id','=',res.product_id.id),
						('picking_id','=',False),
						('store_id.n_location','=',res.location_id.id)
						],order='id',limit=packets)
						reserve_qty -= sum([ i.convert_product_qty for i in search_id])
                                                print "reserve_qty if reserve_qty and packets condition",reserve_qty,
						if search_id:
							numbers=[srch for srch in search_id]
							result_batches.extend(numbers)
				
				loose_batches=[]
				print ";,,,,,,,,,",result_batches,reserve_qty
				if reserve_qty <0 :
					raise UserError("Error IN Quantity found for product [{}]{} \n Please \
						Contact Administrator".format(
								res.product_id.default_code,res.product_id.name))
				elif reserve_qty>0 :
					loose_batches=self.env['mrp.order.batch.number'].search([
						('convert_product_qty','<',product_packaging_qty),
						('store_id','!=',False),('logistic_state','in',('stored','transit_in')),
						('sale_line_id','=',False),('product_id','=',res.product_id.id),
						('picking_id','=',False),
						('store_id.n_location','=',res.location_id.id),],order='id')
				if loose_batches and reserve_qty > 0:
					batches_qty = [ i.convert_product_qty for i in loose_batches]
					qty_batches = sum(batches_qty)
					numbers=[srch for srch in loose_batches]
					loose_btch = numbers
					if round(qty_batches,2) > round(reserve_qty,2):
						loose_btch = subset_sum_batches(numbers,reserve_qty)
#					if not loose_btch:
#						raise UserError("There are no group of Batches found for product \
#						[{}]{} with referance to your Quantity {}#".format(
#						res.product_id.default_code,res.product_id.name,reserve_qty))
					result_batches.extend(loose_btch)
					
#				if not loose_batches and reserve_qty >0.0 and res.location_id.scrap_location==False:
#                                        print "resss---------",res
#					raise UserError("There are no group of Batches found for product \
#						[{}]{} with referance to your Quantity {}#".format(
#						res.product_id.default_code,res.product_id.name,reserve_qty))
				for batch in result_batches:
					if not batch:
						raise UserError("No Batch found for product [{}]{}".format(
							res.product_id.default_code,res.product_id.name))
					res_btch_qty -= batch.convert_product_qty
					operation_t ='reserve' if res.n_sale_line_id else 'logistics'
					batch.write({'logistic_state':'reserved',
							'sale_line_id':sale_line,
							'picking_id':res.picking_id.id,
							'batch_history':[(0,0,{'operation':operation_t,
			   			'description':'Reserved for order {} in Operation {}'.format(
			   				res.picking_id.sale_id.name,res.picking_id.name)})]})
					if res_btch_qty<0:
						err

				if res.n_sale_line_id and result_batches:
					new_add_qty=sum([ i.convert_product_qty for i in result_batches])
					sale_line_vals={'reserved_qty':res.n_sale_line_id.reserved_qty+new_add_qty}	
					sale_line_vals.update({'res_ids':[(0,0,{'product_id':res.product_id.id,
							'n_reserve_Type':'do','res_qty':new_add_qty,
							'n_status':'reserve','picking_id':res.picking_id.id})]})
					
					n_status_rel=[]
					search_id=self.env['sale.order.line.status'].search([
									('n_string','=','warehouse')],limit=1)
					if search_id:
						n_status_rel.append((4,search_id.id))
					new_id=self.env['sale.order.line.status'].search(
									[('n_string','=','new')],limit=1)
					if new_id:
						n_status_rel.append((3,new_id.id))
			
					sale_line_vals.update({'n_status_rel':n_status_rel})
					res.n_sale_line_id.write(sale_line_vals)
					delivery_ids=self.env['mrp.delivery.date'].search([
									('n_line_id1','=',res.n_sale_line_id.id)])
					if not delivery_ids:
						self.env['mrp.delivery.date'].create(
								{'n_line_id':res.n_sale_line_id.id,
									'n_line_id1':res.n_sale_line_id.id})
				if not res.n_sale_line_id:
					# Update Done qty in case of Inventory Adjustment DO.
					for pack in res.picking_id.pack_operation_product_ids:
						pack.qty_done=pack.product_qty
				_logger.info("End Batch Reserve Process {}....\n".format(res.product_id.default_code))		
			elif res.picking_id.picking_type_code=='internal':
				move = self.env['stock.move'].search(domain)
				quants=self.env['stock.quant'].search([('reservation_id','in',move._ids),
							       ('product_id','=',res.product_id.id)])
	 			reserve_qty=sum([x.qty for x in quants])
	 			# for warehouse to warehouse transfer
	 			# for send to production
				if res.location_id.actual_location and (res.location_dest_id.actual_location or res.location_dest_id.usage == 'production'):
	 				if reserve_qty :
						res.picking_id.picking_status ='pick_list'
						for pack in res.picking_id.pack_operation_product_ids:
							pack.qty_done=pack.product_qty
						
		return result

	@api.multi
	def do_unreserve(self):
		for res in self:
			order_batch_obj = self.env['mrp.order.batch.number']
			if self._context.get('reserve_api'):
				# Check Context to avoid unreserve and reserve of Batches in Reserve
				return super(StockMove,self).do_unreserve()
				
			if res.picking_type_id.code=='outgoing' and res.picking_id.picking_status =='draft':
				reserve_qty=0.0
				n_status_rel=[]
				sale_batches = order_batch_obj.search([
							('store_id','!=',False),
							('logistic_state','in',('stored','transit_in','reserved')),
							('sale_line_id','=',res.n_sale_line_id.id),
							('product_id','=',res.product_id.id)],order='id')
				
				picking_batches = order_batch_obj.search([('store_id','!=',False),
						('logistic_state','in',('stored','transit_in','reserved')),
						('picking_id','=',res.picking_id.id),
						('product_id','=',res.product_id.id)],order='id')
				operation_t ='unreserve' if res.n_sale_line_id else 'logistics'
				for batch in [i for i in sale_batches]+[j for j in picking_batches]:
					logic_state = 'transit_in' if batch.store_id.location_type=='transit_in' else 'stored'
					batch.write({'logistic_state':logic_state,
							'sale_line_id':False,
							'sale_id':False,
							'picking_id':False,
							'batch_history':[(0,0,{'operation':operation_t,
				   			'description':'UnReserved for order {} in Operation {}'.format(
				   				res.picking_id.sale_id.name,res.picking_id.name)})]})
					reserve_qty += batch.product_qty

				sale_line_vals={'res_ids':[(0,0,{'product_id':res.product_id.id,
								'n_reserve_Type':'do','res_qty':reserve_qty,
								'n_status':'release'})]}
				search_id=self.env['sale.order.line.status'].search([
					('n_string','=','new')],limit=1)
				if search_id:
					n_status_rel.append((4,search_id.id))
				new_id=self.env['sale.order.line.status'].search([('n_string','in',
							('force_reserve','warehouse'))])
				if new_id:
					n_status_rel.extend([(3,i.id) for i in new_id])
				
				sale_line_vals.update({'reserved_qty':res.n_sale_line_id.reserved_qty-reserve_qty,
						'n_status_rel':n_status_rel})
				res.n_sale_line_id.write(sale_line_vals)
				
			elif res.picking_type_id.code=='internal':
				if res.location_dest_id.actual_location and res.location_id.actual_location:
					res.picking_id.picking_status ='draft'
				
				if res.location_id.actual_location and res.location_dest_id.usage == 'production':
					res.picking_id.picking_status ='draft'
					
		return super(StockMove,self).do_unreserve()
		
#CH_N067 add fields to to get proper location >>>
class stockPickingType(models.Model):
	_inherit = "stock.picking.type"

	n_quality_ck = fields.Boolean("Quality Location", default=False)
	n_scrap_ck	= fields.Boolean("Scrap Location", default=False)

	@api.multi
	def write(self,vals):
		if vals.get('code')== False:
			return True
		return super(stockPickingType,self).write(vals)

from openerp.osv import fields, osv
class stockPickingTypen(osv.osv):
	_inherit = "stock.picking.type"
	
	def _get_picking_count1(self, cr, uid, ids, field_names, arg, context=None):
		obj = self.pool.get('stock.picking')
		domains = {
		    'count_r_t_dispatch': [('picking_status', '!=', 'draft')],
		}
		result = {}
		for field in domains:
		    data = obj.read_group(cr, uid, domains[field] +
		        [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', ids)],
		        ['picking_type_id'], ['picking_type_id'], context=context)
		    count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
		    for tid in ids:
		        result.setdefault(tid, {})[field] = count.get(tid, 0)
		return result
		
	_columns = {	
		'count_r_t_dispatch': fields.function(_get_picking_count1,
            			type='integer', multi='_get_picking_count1'),}
#CH_N067 <<<


