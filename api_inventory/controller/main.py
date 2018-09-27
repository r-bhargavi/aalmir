# -*- coding: utf-8 -*-
from openerp import models, fields, api, _, modules
from openerp import http
from openerp.http import request,Response
import base64
from urlparse import urljoin
from urllib import urlencode
import werkzeug

class PDFControl(http.Controller):

    @http.route(['/product_qty_import_file/'], type='http', website=True)
    def product_qty_import(self, stmt=None):
        pdf = modules.get_module_path('api_inventory') + "/controller/product_qty_import_file.xlsx"
        f = open(pdf, 'rb')
        image_base64 = f.read()
        response = request.make_response(
            image_base64,
            headers=[
                ('Content-Type', 'application/xlsx'),
                ('Content-Disposition', 'attachment; filename=product_qty_import_file.xlsx;')
            ]
        )
        return response
        
    @http.route('/web/binary/download_document', type='http', auth="public")
    #@serialize_exception
    def download_document(self,model,field,id,filename=None, **kw):
	     """ Download link for files stored as binary fields.
	     :param str model: name of the model to fetch the binary from
	     :param str field: binary field
	     :param str id: id of the record from which to fetch the binary
	     :param str filename: field holding the file's name, if any
	     :returns: :class:`werkzeug.wrappers.Response`
	     """
	     Model = request.registry[model]
	     cr, uid, context = request.cr, request.uid, request.context
	     fields = [field]
	     res = Model.read(cr, uid, [int(id)], fields, context)[0]
	     filecontent = base64.b64decode(res.get(field) or '')
	     if not filecontent:
		 return request.not_found()
	     else:
		 if not filename:
		     filename = '%s_%s' % (model.replace('.', '_'), id)
		     return request.make_response(filecontent,
		                    [('Content-Type', 'application/octet-stream'),
		                     ('Content-Disposition', content_disposition(filename))])     

    @http.route(['/store_view/<int:bin_id>/'],method="post", type='http',csrf=False)
    def store_view_url(self,bin_id,stmt=None):
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
	query = {'db': request._cr.dbname}
	fragment = {
		'type': 'ir.actions.act_url',
		'model': 'n.warehouse.placed.product',
		'view_type': 'form',
		#'target': 'new',
		'id': bin_id,
		}
    	pick_url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
    	return werkzeug.utils.redirect(pick_url)
    
    @http.route(['/pick_data_picking_list/<int:pick_id>/<int:picking>/<int:bin_id>/<int:master_batch>/'],method="post", type='http',csrf=False)
    def product_pick_url(self,pick_id,picking,bin_id,master_batch,stmt=None):
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
	query = {'db': request._cr.dbname}
	fragment = {
		'model': 'store.picking.list',
		'view_type': 'form',
		'target': 'current',
		'id': pick_id,
		'flags': {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}},
		}
    	pick_url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
    	picklist_id = request.env['store.picking.list'].search([('id','=',pick_id)],limit=1)
	master_batch_id = request.env['stock.store.master.batch'].search([('id','=',master_batch)],limit=1)
	store_id=request.env['n.warehouse.placed.product'].search([('id','=',bin_id)])
	location_view = request.env['stock.location.view'].search([('location_type','=','transit_out'),('location_id','=',store_id.n_location.id)])
	transit_id = request.env['n.warehouse.placed.product'].search([('n_location_view','=',location_view.id)])
	for res in store_id:
		qty=pkg_capicity=0.0
		product_id = master_batch_id.product_id
		Packaging_type = master_batch_id.packaging
		pkg_capicity_unit = pkg_unit = master_batch_id.packaging.uom_id
		total_qty_unit = master_batch_id.uom_id
				
		#batches = request.env['mrp.order.batch.number'].search([('master_id','=',master_batch),('store_id','=',res.id)])
		master_batch_id.write({'store_id':transit_id.id,'picking_id':picking,'logistic_state':'transit'})
		for btch in master_batch_id.batch_id:
			btch.write({'store_id':transit_id.id,'picking_id':picking,'logistic_state':'transit'})
			btch.sale_id=btch.picking_id.sale_id.id
			qty += btch.convert_product_qty
			
		total_quantity = qty
		packages = len(master_batch_id.batch_id._ids)
		body1 ='<ul>Picking Operation for {} </ul>'.format(master_batch_id.picking_id.name)
		if res.product_type == 'single': ## do operation for Single product
			pkg_capicity_unit = res.pkg_capicity_unit
			pkg_unit = res.pkg_unit
			if total_quantity < res.total_quantity:
				res.write({'state':'partial','total_quantity':res.total_quantity-total_quantity,
				'packages':float(res.packages)-float(packages)})
			elif total_quantity == res.total_quantity:
				res.write({'state':'empty','product_id':False,'total_quantity':0.0,
					'total_qty_unit':False,'qty_unit':False,'pkg_capicity':0.0,
					'pkg_capicity_unit':False,'packages':0.0,'pkg_unit':False,
					'Packaging_type':False})
			else:
				print "ERROR in selecting..."
				raise
			
		else:
			# do operation for multi product
			for multi in request.env['store.multi.product.data'].search([('store_id','=',res.id),
									('product_id','=',product_id.id),
									('Packaging_type','=',Packaging_type.id)]):
				if qty>0:
					if multi.total_quantity <= qty :
						qty -= multi.total_quantity
						multi.sudo().unlink()
						
					elif multi.total_quantity > qty :
						multi.write({'total_quantity':multi.total_quantity-qty, 
							     'packages':multi.packages - packages})
					     	qty =0.0
			     		else:
						print "ERROR in multi product..."
						raise
		
		request.env['location.history'].create({'stock_location':res.id,
						'product_id':product_id.id,
						'operation_name':'Send To Transit-OUT for Dispatch',
						'operation':'do',
						'qty':total_quantity,
						'n_type':'out'})
										
		# search for product Transit -OUT location..	according packagig
		store_product=request.env['store.multi.product.data'].search([('product_id','=',product_id.id),
									      ('store_id','=',transit_id.id),
									('Packaging_type','=',Packaging_type.id)])
									
		body1+='<li>Master Batch :{} </li>'.format(master_batch_id.name)
		if not store_product: # If product is not found add product
			transit_id.state='partial'
			add_vals={'product_id':product_id}
			body1 +="<li>Product add : "+str(product_id.name)+" </li>"
			add_vals.update({'total_quantity':total_quantity})
			add_vals.update({'total_qty_unit':total_qty_unit.id})
			body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
		
			#add_vals.update({'pkg_capicity':pkg_capicity})
			#add_vals.update({'pkg_capicity_unit':pkg_capicity_unit.id})
			body1+="<li>Packag Capicity : "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
		
			add_vals.update({'packages':packages})
			add_vals.update({'pkg_unit':pkg_unit.id})
			add_vals.update({'Packaging_type':Packaging_type.id})
			body1+="<li>Packaging : "+str(Packaging_type.name)+" </li>"
			transit_id.multi_product_ids=[(0,0,add_vals)]	
			transit_id.message_post(body1)		
			
		elif store_product: # if found update quantity and packages
			body1 +="<li>Product update qty : "+str(product_id.name)+" </li>"
			store_product.total_quantity += total_quantity
			body1+="<li>Quantity Added : "+str(total_quantity)+" "+str(total_qty_unit.name)+" </li>"
			#store_product.pkg_capicity += pkg_capicity
			#body1+="<li>Package Capicity updated: "+str(pkg_capicity)+" "+str(pkg_capicity_unit.name)+" </li>"
			store_product.packages += packages
			body1+="<li>Packages updated: "+str(packages)+" </li>"
			transit_id.message_post(body1)
		
		request.env['location.history'].create({'stock_location':transit_id.id,
						'product_id':product_id.id,
						'operation_name':'for Dispatch',
						'operation':'do',
						'qty':total_quantity,
						'n_type':'in'})
						
	if picklist_id.dispatch_qty == picklist_id.qty_pick:
		fragment = {
			'model': 'stock.picking',
			'view_type': 'form',
			'target': 'current',
			'id': picking,
			}
    		pick_url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))	
    				
	return werkzeug.utils.redirect(pick_url)
        
        
