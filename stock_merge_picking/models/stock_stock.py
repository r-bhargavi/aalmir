
##
	# FIle is use when sale support reserve functionality is on 
	# changes for make partial reserve and release of available quantity of product in stoc_picking move lines
	# if not then it work as like in default file of odoo addons
##

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
    
    
#    to not allow the backorder to be reserved in any case
    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in context and context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]

        if backorder_move_ids:
            backorder_id = self.copy(cr, uid, picking.id, {
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            })
            backorder = self.browse(cr, uid, backorder_id, context=context)
            print "backorderbackorder",backorder
#            to link the bo to the mo
            if backorder.material_request_id:
                backorder.material_request_id.production_id.delivery_ids= [(4,backorder.id)]	
                backorder.write({'expected_comple_date':picking.expected_comple_date})
            self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
            move_obj = self.pool.get("stock.move")
            move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)

            if not picking.date_done:
                self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            self.action_confirm(cr, uid, [backorder_id], context=context)
#            self.action_assign(cr, uid, [backorder_id], context=context)
            return backorder_id
        return False

    
    def action_assign(self, cr, uid, ids, context=None):
        print "pciking moves action assign------------------------"
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        result= super(stock_picking,self).action_assign(cr, uid, ids,context=context)
        pick_brw=self.pool.get('stock.picking').browse(cr,uid,ids[0])
        #if any([ x.state in ('confirmed') for x in pick_brw.move_lines]):
            #raise UserError('Some Products are not available in mentioned source location')
        return result


    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        print "_prepare_pack_ops.................stok_merge..",context
        context = context or {}
        if context.get('sale_support'):
		def _picking_putaway_apply(product):
		    location = False
		    # Search putaway strategy
		    if product_putaway_strats.get(product.id):
		        location = product_putaway_strats[product.id]
		    else:
		        location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
		        product_putaway_strats[product.id] = location
		    return location or picking.location_dest_id.id

		# If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
		product_uom = {} # Determines UoM used in pack operations
		location_dest_id = None
		location_id = None
		for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
		    if not product_uom.get(move.product_id.id):
		        product_uom[move.product_id.id] = move.product_id.uom_id
		    if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
		        product_uom[move.product_id.id] = move.product_uom
		    if not move.scrapped:
		        if location_dest_id and move.location_dest_id.id != location_dest_id:
		            raise UserError(_('The destination location must be the same for all the moves of the picking.'))
		        location_dest_id = move.location_dest_id.id
		        if location_id and move.location_id.id != location_id:
		            raise UserError(_('The source location must be the same for all the moves of the picking.'))
		        location_id = move.location_id.id

		pack_obj = self.pool.get("stock.quant.package")
		quant_obj = self.pool.get("stock.quant")
		vals = []
		qtys_grouped = {}
		lots_grouped = {}
		#for each quant of the picking, find the suggested location
		quants_suggested_locations = {}
		product_putaway_strats = {}
		for quant in quants:
		    if quant.qty <= 0:
		        continue
		    suggested_location_id = _picking_putaway_apply(quant.product_id)
		    quants_suggested_locations[quant] = suggested_location_id

		#find the packages we can movei as a whole
		top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
		# and then create pack operations for the top-level packages found
		for pack in top_lvl_packages:
		    pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
		    pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
		    vals.append({
		            'picking_id': picking.id,
		            'package_id': pack.id,
		            'product_qty': 1.0,
		            'location_id': pack.location_id.id,
		            'location_dest_id': quants_suggested_locations[pack_quants[0]],
		            'owner_id': pack.owner_id.id,
		        })
		    #remove the quants inside the package so that they are excluded from the rest of the computation
		    for quant in pack_quants:
		        del quants_suggested_locations[quant]
		# Go through all remaining reserved quants and group by product, package, owner, source location and dest location
		# Lots will go into pack operation lot object
		for quant, dest_location_id in quants_suggested_locations.items():
		    key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
		    if qtys_grouped.get(key):
		        qtys_grouped[key] += quant.qty
		    else:
		        qtys_grouped[key] = quant.qty
		    if quant.product_id.tracking != 'none' and quant.lot_id:
		        lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
			lots_grouped[key][quant.lot_id.id] += quant.qty

		# Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
		for product, qty in forced_qties.items():
		    if qty <= 0:
		        continue
		    suggested_location_id = _picking_putaway_apply(product)
		    key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
		    if qtys_grouped.get(key):
		        qtys_grouped[key] += qty
		    else:
		        qtys_grouped[key] = qty

		# Create the necessary operations for the grouped quants and remaining qtys
		uom_obj = self.pool.get('product.uom')
		prevals = {}
		for key, qty in qtys_grouped.items():
		    product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
		    uom_id = product.uom_id.id
		    qty_uom = qty
		    if product_uom.get(key[0]):
		        uom_id = product_uom[key[0]].id
		        qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
		    pack_lot_ids = []
		    if lots_grouped.get(key):
		        for lot in lots_grouped[key].keys():
		            pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
		    val_dict = {
		        'picking_id': picking.id,
		        'product_qty': qty_uom,
		        'product_id': key[0],
		        'package_id': key[1],
		        'owner_id': key[2],
		        'location_id': key[3],
		        'location_dest_id': key[4],
		        'product_uom_id': uom_id,
		        'pack_lot_ids': pack_lot_ids,
		    }
		    if key[0] in prevals:
		        prevals[key[0]].append(val_dict)
		    else:
		        prevals[key[0]] = [val_dict]
		# prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
		processed_products = set()
		print "XXXXXXXXXXxx,,",[x for x in picking.move_lines if x.state not in ('done', 'cancel')],picking.move_lines
		for move in context.get('sale_move_id'):#[x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
		    print "xxxxxxxxxxxxxxx",move,processed_products,move.product_id.id
		    if move.product_id.id not in processed_products:
		        print "nnnnnnnnnnnnnnnnnnnn",prevals.get(move.product_id.id, [])
		        vals += prevals.get(move.product_id.id, [])
		        processed_products.add(move.product_id.id)
		print "xYXYYXYXYXYXYYX...",processed_products,vals
		return vals
	else:
		return super(stock_picking,self)._prepare_pack_ops(cr, uid, picking, quants, forced_qties, context=context)


    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        print "DDDDDDDDDDDd...,,,do_prepare_partial",context
        if context.get('sale_support'):
		pack_operation_obj = self.pool.get('stock.pack.operation')

		#get list of existing operations and delete them
		print "context...",context
		existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids),('n_sale_order_line','=',context.get('sale_line_id'))], context=context)
		if existing_package_ids:
		    pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
		print "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii",picking_ids
		for picking in self.browse(cr, uid, picking_ids, context=context):
		    forced_qties = {}  # Quantity remaining after calculating reserved quants
		    picking_quants = []
		    #Calculate packages, reserved quants, qtys of this picking's moves
		    print "//////////****************",picking.move_lines
		    for move in context.get('sale_move_id'):#picking.move_lines:
		        if move.state not in ('assigned', 'confirmed', 'waiting'):
		            continue
		        move_quants = move.reserved_quant_ids
		        picking_quants += move_quants
		        forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
		        #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
		        if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
		            if forced_qties.get(move.product_id):
		                forced_qties[move.product_id] += forced_qty
		            else:
		                forced_qties[move.product_id] = forced_qty
		        print "End FOR...................."
		    print "OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO",picking, picking_quants, forced_qties
		    for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
		    	print "START..............pppppppppppppp"
		        vals['fresh_record'] = False
		        print "BEFOR PACK CREATE",vals
		        if context.get('sale_support'):
		                procu_id=context.get('sale_move_id').procurement_id
		                lpo=[(4,doc.id) for doc in procu_id.sale_line_id.lpo_documents]
		                vals.update({'n_sale_order_line':procu_id.sale_line_id.id,'lpo_documents':lpo})
		                print "kkkkkkkkkkkkkDDDDDDDDDDDDD",procu_id.sale_line_id.lpo_documents,lpo
		        pack_i=pack_operation_obj.create(cr, uid, vals, context=context)
		        print "AFTER Pack CRESTE>........",pack_i
		#recompute the remaining quantities all at once
		print "End.......do_prepare_partial",
		self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
		print "do_recompute_remaining_quantities............"
		self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)
	else:
		super(stock_picking,self).do_prepare_partial(cr, uid, picking_ids, context=context)


    def recompute_remaining_qty(self, cr, uid, picking, done_qtys=False, context=None):
    	context = context or {}
    	if context.get('sale_support'):
		def _create_link_for_index(operation_id, index, product_id, qty_to_assign, quant_id=False):
		    move_dict = prod2move_ids[product_id][index]
		    qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
		    self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
		    if move_dict['remaining_qty'] == qty_on_link:
		        prod2move_ids[product_id].pop(index)
		    else:
		        move_dict['remaining_qty'] -= qty_on_link
		    return qty_on_link

		def _create_link_for_quant(operation_id, quant, qty):
		    """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
		    if not quant.reservation_id.id:
		        return _create_link_for_product(operation_id, quant.product_id.id, qty)
		    qty_on_link = 0
		    for i in range(0, len(prod2move_ids[quant.product_id.id])):
		        if prod2move_ids[quant.product_id.id][i]['move'].id != quant.reservation_id.id:
		            continue
		        qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, quant_id=quant.id)
		        break
		    return qty_on_link
		def _create_link_for_product(operation_id, product_id, qty):
		    '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
		    Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
		    qty_to_assign = qty
		    prod_obj = self.pool.get("product.product")
		    product = prod_obj.browse(cr, uid, product_id)
		    rounding = product.uom_id.rounding
		    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
		    if prod2move_ids.get(product_id):
		        while prod2move_ids[product_id] and qtyassign_cmp > 0:
		            qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, quant_id=False)
		            qty_to_assign -= qty_on_link
		            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
		    return qtyassign_cmp == 0

		uom_obj = self.pool.get('product.uom')
		package_obj = self.pool.get('stock.quant.package')
		quant_obj = self.pool.get('stock.quant')
		link_obj = self.pool.get('stock.move.operation.link')
		quants_in_package_done = set()
		prod2move_ids = {}
		still_to_do = []
		#make a dictionary giving for each product, the moves and related quantity that can be used in operation links
		moves = sorted([x for x in picking.move_lines if x.state not in ('done', 'cancel')], key=lambda x: (((x.state == 'assigned') and -2 or 0) + (x.partially_available and -1 or 0)))
		for move in context.get('sale_move_id'):#moves:
		    if not prod2move_ids.get(move.product_id.id):
		        prod2move_ids[move.product_id.id] = [{'move': move, 'remaining_qty': move.product_qty}]
		    else:
		        prod2move_ids[move.product_id.id].append({'move': move, 'remaining_qty': move.product_qty})

		need_rereserve = False
		#sort the operations in order to give higher priority to those with a package, then a serial number
		operations=picking.pack_operation_ids
		if context.get('sale_support'):
		        print "jjjjjjjjjjjj",picking.pack_operation_ids._ids,context
		        operation=self.pool.get('stock.pack.operation').search(cr,uid,[('id','in',picking.pack_operation_ids._ids),('n_sale_order_line','=',context.get('sale_line_id'))])
		        operations = self.pool.get('stock.pack.operation').browse(cr,uid,operation)
		print "TTTTTTTTTTTTTT...",operations,picking.pack_operation_ids,prod2move_ids
		operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
		#delete existing operations to start again from scratch
		print "SToc pack opearionss....ids..",operations
		links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
		if links:
		    link_obj.unlink(cr, uid, links, context=context)
		#1) first, try to create links when quants can be identified without any doubt
		for ops in operations:
		    lot_qty = {}
		    for packlot in ops.pack_lot_ids:
		        lot_qty[packlot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, packlot.qty, ops.product_id.uom_id.id)
		    #for each operation, create the links with the stock move by seeking on the matching reserved quants,
		    #and deffer the operation if there is some ambiguity on the move to select
		    if ops.package_id and not ops.product_id and (not done_qtys or ops.qty_done):
		        #entire package
		        quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
		        for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
		            remaining_qty_on_quant = quant.qty
		            if quant.reservation_id:
		                #avoid quants being counted twice
		                quants_in_package_done.add(quant.id)
		                qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty)
		                remaining_qty_on_quant -= qty_on_link
		            if remaining_qty_on_quant:
		                still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
		                need_rereserve = True
		    elif ops.product_id.id:
		        #Check moves with same product
		        product_qty = ops.qty_done if done_qtys else ops.product_qty
		        qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, product_qty, ops.product_id.uom_id, context=context)
		        precision_rounding = ops.product_id.uom_id.rounding
		        for move_dict in prod2move_ids.get(ops.product_id.id, []):
		            move = move_dict['move']
		            for quant in move.reserved_quant_ids:
		                if float_compare(qty_to_assign, 0, precision_rounding=precision_rounding) != 1:
		                    break
		                if quant.id in quants_in_package_done:
		                    continue

		                #check if the quant is matching the operation details
		                if ops.package_id:
		                    flag = quant.package_id == ops.package_id
		                else:
		                    flag = not quant.package_id.id
		                flag = flag and (ops.owner_id.id == quant.owner_id.id)
		                if flag:
		                    if not lot_qty:
		                        max_qty_on_link = min(quant.qty, qty_to_assign)
		                        qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
		                        qty_to_assign -= qty_on_link
		                    else:
		                        if lot_qty.get(quant.lot_id.id): #if there is still some qty left
		                            max_qty_on_link = min(quant.qty, qty_to_assign, lot_qty[quant.lot_id.id])
		                            qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
		                            qty_to_assign -= qty_on_link
		                            lot_qty[quant.lot_id.id] -= qty_on_link

		        qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=precision_rounding)
		        if qty_assign_cmp > 0:
		            #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
		            #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
		            still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
		            need_rereserve = True

		#2) then, process the remaining part
		all_op_processed = True
		for ops, product_id, remaining_qty in still_to_do:
		    all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty) and all_op_processed
		return (need_rereserve, all_op_processed)
	else:
		return super(stock_picking,self).recompute_remaining_qty(cr, uid, picking, done_qtys, context)


class stock_move(osv.osv):
    _inherit = "stock.move"
    
    def action_assign(self, cr, uid, ids, no_prepare=False, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        if context.get('sale_support'):
		context = context or {}
		quant_obj = self.pool.get("stock.quant")
		uom_obj = self.pool['product.uom']
		to_assign_moves = set()
		main_domain = {}
		todo_moves = []
		operations = set()
		ancestors_list = {}
		self.do_unreserve(cr, uid, [x.id for x in self.browse(cr, uid, ids, context=context) if x.reserved_quant_ids and x.state in ['confirmed', 'waiting', 'assigned']], context=context)
		print "$$$$$$$$$$$$$$$$$$$$$",ids
		for move in self.browse(cr, uid, ids, context=context):
		    if move.state not in ('confirmed', 'waiting', 'assigned'):
		        continue
		    if move.location_id.usage in ('supplier', 'inventory', 'production'):
		        to_assign_moves.add(move.id)
		        #in case the move is returned, we want to try to find quants before forcing the assignment
		        if not move.origin_returned_move_id:
		            continue
		    if move.product_id.type == 'consu':
		        to_assign_moves.add(move.id)
		        continue
		    else:
		        todo_moves.append(move)

		        #we always search for yet unassigned quants
		        main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

		        #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
		        ancestors = self.find_move_ancestors(cr, uid, move, context=context)
		        ancestors_list[move.id] = True if ancestors else False
		        if move.state == 'waiting' and not ancestors:
		            #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
		            main_domain[move.id] += [('id', '=', False)]
		        elif ancestors:
		            main_domain[move.id] += [('history_ids', 'in', ancestors)]

		        #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
		        if move.origin_returned_move_id:
		            main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
		        for link in move.linked_move_operation_ids:
		            operations.add(link.operation_id)
		# Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
		operations = list(operations)
		operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
		
		if context.get('rel_stok'):
			print "ooooooooooo",operations
		        operations=[]

		for ops in operations:
		    #first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
		    if not (ops.product_id and ops.pack_lot_ids):
		        for record in ops.linked_move_operation_ids:
		            print "MMMMMMMMMMMMMMm@@@@@@@@@@@@",record,record.move_id,main_domain
		            move = record.move_id
		            if move.id in main_domain:
		                qty = record.qty
		                domain = main_domain[move.id]
		                if qty:
		                    quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, domain=domain, preferred_domain_list=[], context=context)
		                    print "nnnnnnnnnnnnnn...."
		                    quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
		                    print "jjjjjjjj"
		                    if context.get('sale_support'):
		                    	break
		    else:
		        lot_qty = {}
		        rounding = ops.product_id.uom_id.rounding
		        for pack_lot in ops.pack_lot_ids:
		            lot_qty[pack_lot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
		        for record in ops.linked_move_operation_ids.filtered(lambda x: x.move_id.id in main_domain):
		            print "TTTTTTTTTT@@@@@@@@@@@@@@@@@",record,record.move_id
		            move_qty = record.qty
		            move = record.move_id
		            domain = main_domain[move.id]
		            print "---///////////",lot_qty
		            for lot in lot_qty:
		                if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
		                    print "7777777777777777777777777",lot_qty[lot], move_qty
		                    qty = min(lot_qty[lot], move_qty)
		                    quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[], context=context)
		                    quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
		                    lot_qty[lot] -= qty
		                    move_qty -= qty


		# Sort moves to reserve first the ones with ancestors, in case the same product is listed in
		# different stock moves.
		print "AAAAAAAAAAAAAAA",ancestors_list
		todo_moves.sort(key=lambda x: -1 if ancestors_list.get(x.id) else 0)
		for move in todo_moves:
		    #then if the move isn't totally assigned, try to find quants without any specific domain
		    print "nmmmmmmmmmmmm...",move,move.state,context
		    if context.get('sale_support') and context.get('res_qty'):
		    	#if context.get('res_qty') == move.product_qty:
		    		ctx = dict(context)
		    		ctx['reserve_only_ops']=False
		    		context=ctx
		    if (move.state != 'assigned') and not context.get("reserve_only_ops"):
		        qty_already_assigned = move.reserved_availability
		        qty = move.product_qty - qty_already_assigned
		        print "----------**********",qty,qty_already_assigned,move.product_qty,move
		        quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain[move.id], preferred_domain_list=[], context=context)
		        quant_obj.quants_reserve(cr, uid, quants, move, context=context)
		#force assignation of consumable products and incoming from supplier/inventory/production
		# Do not take force_assign as it would create pack operations
		if to_assign_moves:
		    self.write(cr, uid, list(to_assign_moves), {'state': 'assigned'}, context=context)
		if not no_prepare:
		    self.check_recompute_pack_op(cr, uid, ids, context=context)
        else:
        	return super(stock_move,self).action_assign(cr, uid, ids, no_prepare,context)
        

