# -*- coding: utf-8 -*-
# copyright reserved

from openerp import models, fields, api,_
from openerp import tools
import math
from datetime import datetime
from datetime import datetime, date, time, timedelta
from openerp.exceptions import UserError
import sys
import logging
_logger = logging.getLogger(__name__)

class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    @api.multi
    def importProduct(self):
        stock_form = self.env.ref('api_inventory.product_store_import_data', False)
        context=self._context.copy()
        context.update({'default_location':self.id})
        return {
            'name':'Import Stock Quantity',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.store.data.import',
            'views': [(stock_form.id, 'form')],
            'view_id': stock_form.id,
            'context':context,
            'target': 'new',
         }

class StockProductDataImportWizard(models.TransientModel):
    """This wizard is used to Import product quantity and update in store  """   
    _name = 'product.store.data.import'


    @api.model
    def get_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/product_qty_import_file/'
        return url
        
            
    name=fields.Char('File name')
    new_upload=fields.Binary('Upload File',attachment=True)
    location = fields.Many2one('stock.location','Location')
    region = fields.Many2one('stock.location.view','Storage Name')
    import_status = fields.Selection([('draft','Draft'),('error','Error'),('done','Done')],string='Import')
    download_file = fields.Char('Sample Fle',help="Please See the file data format before Importing", default=get_url, readonly="1")
    error_file = fields.Binary('Error Fle',help="If Any error in import data file", readonly="1",attachment=True)
    
    picking_id = fields.Many2one('stock.picking','Location')
    
    @api.multi
    def import_data(self):
    	import base64
    	self.env.cr.execute("select store_fname from ir_attachment where res_model='product.store.data.import' and res_id="+str(self.id))
    	path=self.env.cr.fetchone()
    	
    	file_path='~/.local/share/Odoo/filestore/'+str(self.env.cr.dbname)+'/'+str(path[0])
    	import getpass
    	user=getpass.getuser()
    	FILENAME = "/home/{}/{}".format(str(user),str(self.name))
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
    	import xlrd
    	import xlwt
	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	f_row,master_batch=[],[]
	workbook = xlwt.Workbook(encoding = 'ascii')
	worksheet1 = workbook.add_sheet('ITEM CODE')
	worksheet1.write(0, 1, 'ITEM CODE')
	worksheet1.write(0, 2, 'Error')
	worksheet2 = workbook.add_sheet('Product')
	worksheet2.write(0, 1, 'ITEM CODE')
	worksheet2.write(0, 2, 'Error')
	worksheet3 = workbook.add_sheet('STORE')
	worksheet3.write(0, 1, 'STORE NAME')
	worksheet3.write(0, 2, 'Error')
	worksheet4 = workbook.add_sheet('Packaging')
	worksheet4.write(0, 1, 'ITEM CODE')
	worksheet4.write(0, 2, 'Primary pkg')
	worksheet4.write(0, 3, 'Secondary pkg')
	worksheet5 = workbook.add_sheet('Primary Qty')
	worksheet5.write(0, 1, 'ITEM CODE')
	worksheet5.write(0, 2, 'Qty in system ')
	worksheet5.write(0, 3, 'qty in file')
	worksheet6 = workbook.add_sheet('Secondary Qty')
	worksheet6.write(0, 1, 'ITEM CODE')
	worksheet6.write(0, 2, 'qty in system')
	worksheet6.write(0, 3, 'qty in file')
	worksheet7 = workbook.add_sheet('Sale Order Not found')
	worksheet7.write(0, 1, 'SALE Order')
	worksheet8 = workbook.add_sheet('Master Batch')
	worksheet8.write(0, 1, 'SALE Order')
	count1=count2=count3=count4=count5=count6=count7=count8=1
	flag=False

	for row1 in range(max_nb_row) :
		if row1 != 0:
			data1=book.sheet_by_index(0).row_values(row1)
			product_id=categ_id=unit=False
			
			if data1[4]:
				try :
					if not float(data1[4]):
						flag=True
						worksheet1.write(count1, 1, label =str(int(data1[4])))
						worksheet1.write(count1, 2, label ='Code is not Proper')
						count1 +=1
					product_id=self.env['product.product'].search([('default_code','=',str(int(data1[4])))])
					if not product_id:
						flag=True
						worksheet2.write(count2, 1, label =str(int(data1[4])))
						worksheet2.write(count2, 2, label ='Product Not Found')
						count2 +=1
					elif len(product_id)>1:
						flag=True
						worksheet2.write(count2, 1, label =str(int(data1[4])))
						worksheet2.write(count2, 2, label ='Multiple Product Found')
						count2 +=1
						continue
					unit=product_id.product_tmpl_id.uom_id
				except :
					continue
					'''if str(data1[4])[0]=='1':
						categ_id =self.env['product.category'].search([('cat_type','=','film')])
						unit=self.env['product.uom'].search([('name','=','Kg')])
					elif str(data1[4])[0]=='2':
						categ_id =self.env['product.category'].search([('cat_type','=','injection')])
						unit=self.env['product.uom'].search([('name','=','Pcs')])
					else:
						worksheet1.write(count1, 1, label =str(data1[4]))
						worksheet1.write(count1, 2, label ='Error in code in searching')
						count1 +=1
						continue
					mat_str = self.env['ir.model.data'].get_object_reference('gt_customer_products', 'material_type_data0')
					material_id = self.env['product.material.type'].search([('id','=',mat_str[1])])
					vals={'name':data1[5],'uom_id':unit.id,
						'uom_po_id':unit.id,'categ_id':categ_id.id,
						'type' : 'product','product_material_type':material_id.id,
						'matstrg':material_id.string,
						'description_sale' : str(data1[4]),}
					product_id=self.env['product.product'].create(vals)'''
			n_row = str(data1[0]) if str(data1[0]).isalpha() else str(int(data1[0]))
			n_column = str(data1[1]) if str(data1[1]).isalpha() else str(int(data1[1]))
			n_depth = str(data1[2]) if str(data1[2]).isalpha() else str(int(data1[2]))
			store_id=self.env['n.warehouse.placed.product'].search([('n_location','=',self.location.id),
					  ('n_location_view','=',self.region.id),('n_row','=',n_row),
					  ('n_column','=',n_column),('n_depth','=',n_depth)])
			if not store_id:
				flag=True
				worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
				worksheet3.write(count3, 2, label ="Store Not Found")
				count3 +=1

			elif len(store_id)>1 :
				flag=True
				worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
				worksheet3.write(count3, 2, label ="Multiple Store Found")
				count3 +=1
			elif store_id.state == 'full':
				flag=True
				worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
				worksheet3.write(count3, 2, label ="Store is FULL")
				count3 +=1
			elif store_id.state == 'partial':
				if store_id.product_type == 'single':
					if store_id.pkg_capicity > (store_id.packages+data1[8]):
						flag=True
						worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
						worksheet3.write(count3, 2, label ="Store is out of Capicity")
						count3 +=1
						
				elif store_id.product_type == 'multi':
					per=0.0
					for sub1 in store_id.multi_product_ids:
						if product_id.id==sub1.product_id.id:
							if float(data1[8]) > (sub1.pkg_capicity-sub1.packages):
								flag=True
								worksheet3.write(count3, 1,label=n_row+n_column+n_depth)
								worksheet3.write(count3, 2,label="Store is out of Capicity")
								count3 +=1
								break
						#per +=(sub1.packages*100)/sub1.pkg_capicity
					if per >100:
						flag=True
						worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
						worksheet3.write(count3, 2, label ="Store is out of Capicity")
						count3 +=1
							
			elif store_id.state == 'maintenance':
				flag=True
				worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
				worksheet3.write(count3, 2, label ="Store in maintainance")
				count3 +=1
			elif store_id.state == 'no_use':
				flag=True
				worksheet3.write(count3, 1, label =n_row+n_column+n_depth)
				worksheet3.write(count3, 2, label ="Store is Not in Use")
				count3 +=1
			primary=secondary=unit_type=ck_pri_qty=one_pack=False
			if not product_id:
				continue
			
			if data1[7]:
				data_pkg = data1[7].strip(' ')
				if data_pkg.upper() in ('CTN','CARTONS','CARTON'):
					unit_type=self.env['product.uom'].search([('name','=','Carton')])
				elif data_pkg.upper() in ('BUNDLE','BUNDLES','BNDL','BUN'):
					unit_type=self.env['product.uom'].search([('name','=','Bundle')])
				elif data_pkg.upper() in ('PCS','PALLET'):	
					unit_type=self.env['product.uom'].search([('name','=','Pallet')])
					secondary=one_pack=True
				elif data_pkg.upper() in ('ROLL','ROLLS'):
					unit_type=self.env['product.uom'].search([('name','=','Roll')])
				elif data_pkg.upper() in ('BAG','BAGS'):
					unit_type=self.env['product.uom'].search([('name','in',('Bags','Bag'))],limit=1)
				elif data_pkg.upper() in ('BOX','BOXES'):
					unit_type=self.env['product.uom'].search([('name','=','Box')])
				else:
					err
					#	unit_type=self.env['product.uom'].search([('name','=','Carton')])
					
			if not product_id.product_tmpl_id.packaging_ids:
				name=str(int(data1[6]))+str(unit.name)+'/'+str(unit_type.name)
				pk=self.env['product.packaging'].create({'pkgtype':'primary','name':name,
								'unit_id':unit.id,
							     	'qty':int(data1[8]) if one_pack else int(data1[6]),
							     	'uom_id':unit_type.id,
							     	'product_tmpl_id':product_id.product_tmpl_id.id,})
			        ck_pri_qty=primary=True
			        
		        if not ck_pri_qty:
				for line in product_id.product_tmpl_id.packaging_ids:
					if line.pkgtype=='primary' and line.uom_id.id == unit_type.id :
						if one_pack:
							if int(line.qty) >= int(data1[8]) and not ck_pri_qty:
								ck_pri_qty=True
								unit_type = line.uom_id
						else:
							if int(line.qty) >= int(data1[6]) and not ck_pri_qty:
								ck_pri_qty=True
								unit_type = line.uom_id
						primary=True
							
					if line.pkgtype=='secondary' and not secondary and line.unit_id.id==unit_type.id:
						if int(line.qty)*int(store_id.max_qty) < int(data1[8]):
							flag=True
							worksheet6.write(count6, 1, label =str(product_id.default_code))
							worksheet6.write(count6, 2, label =str(line.qty))
							worksheet6.write(count6, 3, label =str(data1[8]))
							count6 +=1
						secondary=True
			if not ck_pri_qty:
				flag=True
				worksheet5.write(count5, 1, label =str(product_id.default_code))
				worksheet5.write(count5, 2, label =str(line.qty))
				worksheet5.write(count5, 3, label =str(data1[6]))
				count5 +=1
				
			if not primary or not secondary:	
				if not primary:
					flag=True
					worksheet4.write(count4, 1, label =str(product_id.default_code))
					worksheet4.write(count4, 2, label ="Primary packaging not foud")
					count4 +=1
				if not secondary and not one_pack:
					uom_pallet=self.env['product.uom'].search([('name','=','Pallet')])
					name=str(int(data1[8]))+str(unit_type.name)+'/'+str(uom_pallet.name)
					pkg_plt = int(data1[12]) if data1[12] else int(math.ceil(data1[8]))
					self.env['product.packaging'].create({'pkgtype':'secondary','name':name,
								     'unit_id':unit_type.id,
								     'qty': pkg_plt,
								     'uom_id':uom_pallet.id,
								     'product_tmpl_id':product_id.product_tmpl_id.id,})
								     
		     	if data1[11] and data1[11]!='' and product_id:
		     		if data1[11] in master_batch:
					worksheet8.write(count8, 1, label =str(data1[11]))
					worksheet8.write(count8, 2, label ="duplicate Master Batches found in file")
					count8 +=1	     		
		     		else:
		     			if self.env['stock.store.master.batch'].search([('name','=',data1[11]),\
		     								('product_id','=',product_id.id)]):
						worksheet8.write(count8, 1, label =str(data1[11]))
						worksheet8.write(count8, 2, label ="Master Batches already exist for same product")
						count8 +=1
		     		master_batch.append(data1[11])
			     		
		        if data1[12] and data1[12]!='':
		        	print "SSSSSSss",data1[4],data1[12]
		        	
		        	#record_sale=self.env['sale.order'].search([('name','=',str(data1[12]).strip())])
		        	#if not record_sale:
				#	flag=True
				
				#	worksheet7.write(count7, 1, label =str(data1[12]))
				#	worksheet7.write(count7, 2, label ="Sale Order not found")
				#	count7 +=1
	self.env.cr.commit()
	_logger.error("API-Confirmation : Stock Import File validation is Successfully done")
	if flag:
		self.import_status = 'error'
		error_f_name='Inventory_Import_Error_{}.xls'.format(self.region.name)
		error_file_path = '/home/{}/{}'.format(str(user),str(error_f_name))
		url=self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		workbook.save(error_file_path)
		#self.error_file=
		print self,error_file_path
		error_1="File Import ERROR \n Please Contact with Administrate and Open This File \n /home/{}/Inventory_Import_Error_{}.xls in server System.".format(str(user),self.region.name)
		_logger.error(error_1)
		raise UserError(error_1)
		#return {
		#	     'type' : 'ir.actions.act_url',
		#	     'url': '%s/error_download_document/&filename=%s&f_name=%s'%(str(url),str(error_file_path),str(error_f_name)),
		#	     'target': 'new',
		#}                     
		
	product_dic={}				
	for row in range(max_nb_row) :
		if row != 0:
			body=''
			data=book.sheet_by_index(0).row_values(row)
			product_id=unit=primary=secondary=False
			pkg_search=[]
			product_vals={}
			primary_pkg = pallet_pkg = 1
			if data[4]:
				try:	
					if not float(data[4]):
						raise UserError("Product Number"+str(int(data[4]))+"is not Proper")
					product_id=self.env['product.product'].search([('default_code','=',str(int(data[4])))])
					if not product_id:
						raise UserError("Product Number"+str(int(data[4]))+"is not Found")
				
					unit=product_id.product_tmpl_id.uom_id
				except :
					product_id=self.env['product.product'].search([('default_code','=',str(data[4]))])
					if not product_id:
						if str(data[4])[0]=='1':
							categ_id =self.env['product.category'].search([('cat_type','=','film')])
							if data[10]:
								unit=self.env['product.uom'].search([('name','=',data[10])])
							if not unit:
								unit=self.env['product.uom'].search([('name','=','Kg')])
						elif str(data[4])[0]=='2':
							categ_id =self.env['product.category'].search([('cat_type','=','injection')])
							unit=self.env['product.uom'].search([('name','=','Pcs')])
					
						mat_str = self.env['ir.model.data'].get_object_reference('gt_customer_products', 'material_type_data0')
						material_id = self.env['product.material.type'].search([('id','=',mat_str[1])])
						vals={'name':data[5],'uom_id':unit.id,'default_code':str(data[4]),
							'uom_po_id':unit.id,'categ_id':categ_id.id,
							'type' : 'product','product_material_type':material_id.id,
							'matstrg':material_id.string,
							'description_sale' : str(data[4]),}
						product_id=self.env['product.product'].create(vals)
					unit=product_id.product_tmpl_id.uom_id
					
			primary=secondary=pkg_type=one_pack=False
			if data[7]:	
				if data[7].upper() in ('CTN','CARTONS','CARTON'):
					pkg_type=self.env['product.uom'].search([('name','=','Carton')])
				elif data[7].upper() in ('ROLL','ROLLS','ROL'):
					pkg_type=self.env['product.uom'].search([('name','=','Roll')])
				elif data[7].upper() in ('BUNDLE'):
					pkg_type=self.env['product.uom'].search([('name','=','Bundle')])
				elif data[7].upper() in ('BOX','BOXES'):
					pkg_type=self.env['product.uom'].search([('name','=','Boxes')])
				elif data_pkg.upper() in ('BAG','BAGS'):
					pkg_type=self.env['product.uom'].search([('name','in',('Bags','Bag'))],limit=1)
				elif data[7].upper() in ('PALLET',):	
					pkg_type=self.env['product.uom'].search([('name','=','Pallet')])
					secondary=one_pack=True
				else:
					pkg_type=self.env['product.uom'].search([('name','=','Carton')])
					
			if not product_id.product_tmpl_id.packaging_ids:
				name=str(int(data[6]))+str(unit.name)+'/'+str(pkg_type.name)
				pkg=self.env['product.packaging'].create({'pkgtype':'primary','name':name,
								'unit_id':unit.id,
							     	'qty':int(data[12]) if one_pack else int(data[6]),
							     	'uom_id':pkg_type.id,
							     	'product_tmpl_id':product_id.product_tmpl_id.id,})
				primary=pkg
				if not one_pack:
					uom_pallet=self.env['product.uom'].search([('name','=','Pallet')])
					name=str(int(data[8]))+str(pkg_type.name)+'/'+str(uom_pallet.name)
					pkg_plt = int(data[12]) if data[12] else int(math.ceil(data[8]))
					pkg2=self.env['product.packaging'].create({'pkgtype':'secondary','name':name,
								     'unit_id':pkg_type.id,
								     'qty':pkg_plt,
								     'uom_id':uom_pallet.id,
								     'product_tmpl_id':product_id.product_tmpl_id.id,})
					secondary=pkg2
							     
			if not primary:
				for line in product_id.product_tmpl_id.packaging_ids:
					if line.pkgtype=='primary':
						primary=line
						if not primary.uom_id:
							line.uom_id=pkg_type.id
			if one_pack:
				secondary=primary
				
			if not secondary:
				uom_pallet=self.env['product.uom'].search([('name','=','Pallet')])
				for line in product_id.product_tmpl_id.packaging_ids:
					if line.pkgtype=='secondary':
						secondary=line
						if not line.uom_id:
							line.uom_id=uom_pallet.id
					
			if not primary or not secondary:
				raise UserError("Product Number"+str(product_id.default_code)+"is packaging is not Found")	
			n_row = str(data[0]) if str(data[0]).isalpha() else str(int(data[0]))
			n_column = str(data[1]) if str(data[1]).isalpha() else str(int(data[1]))
			n_depth = str(data[2]) if str(data[2]).isalpha() else str(int(data[2]))
			
			sale_id=self.env['sale.order'].search([('name','=',str(data[12]).strip())]).id
			store_id=self.env['n.warehouse.placed.product'].search([('n_location','=',self.location.id),
							('n_location_view','=',self.region.id),('n_row','=',n_row),
							('n_column','=',n_column),('n_depth','=',n_depth)])
							
			if len(store_id)>1 or not store_id:
				raise UserError("Store selection ERROR")
				
			elif store_id.state in ('full','maintenance','no_use'):
				raise UserError("Store {}{}{} IS {} in use".format(store_id.n_row,n_column,n_depth,store_id.state))
			
			elif  store_id.product_type == 'single':
				if not store_id.product_id:
					store_id.product_id=product_id.id
				elif store_id.product_id.id!= product_id.id:
					raise UserError("You can not store Two different products in single product type location \n Please Selection Multi store Location for two different product in same store")
					
				body+="<li>Product add : "+str(product_id.name)+" </li>"
				if primary and secondary:
					if store_id.pkg_capicity > (store_id.packages+int(data[9])):
						raise UserError("Storag is out of capicity")
					capacity=secondary.qty*store_id.max_qty
					store_id.pkg_capicity=capacity
					store_id.pkg_capicity_unit =secondary.unit_id.id
					body+="<li>Packaging Capicity : "+str(capacity)+" "+str(secondary.unit_id.name)+" </li>"
				store_id.packages += int(data[8])
				store_id.pkg_unit = secondary.unit_id.id
				body+="<li>No of Packages : "+str(data[8])+" "+str(secondary.unit_id.name)+" </li>"
				store_id.total_quantity += int(data[9])
				store_id.total_qty_unit = unit.id
				body+="<li>Quantity Added : "+str(data[9])+" "+str(unit.name)+" </li>"
				store_id.Packaging_type = primary.id
				body+="<li>Packaging : "+str(primary.name)+" </li>"
				store_id.state = 'full' if store_id.pkg_capicity==store_id.packages else 'partial'
				
			elif  store_id.product_type == 'multi':	
				sub_loc=False
				for sub in store_id.multi_product_ids:
					if sub.product_id.id==product_id.id:
						sub_loc=sub
						if (data[9]/primary.qty) > (sub.pkg_capicity-sub.packages):
							raise UserError("Store {}/{}/{} is out of Capicity for product {} ".format(store_id.n_row,store_id.n_column,store_id.n_depth,product_id.name))
						break
				per=0.0
				#for sub1 in store_id.multi_product_ids:
				#	per +=(sub1.packages*100)/sub1.pkg_capicity
					
				if sub_loc:
					body+="<li>Product Update :["+str(product_id.default_code)+"]"+str(product_id.name)+" </li>"
				else:
					add_vals={'product_id':product_id.id}
					body+="<li>Product add :["+str(product_id.default_code)+"]"+str(product_id.name)+" </li>"
					#per +=(data[8]*100)/(store_id.max_qty*secondary.qty)
				if per >100:
					raise UserError("Store {}/{}/{} is out of Capicity for product {} by {} ".format(store_id.n_row,store_id.n_column,store_id.n_depth,product_id.name,str(per-100)))
					
				if not sub_loc:
					if primary and secondary:
						capacity=secondary.qty*store_id.max_qty
						add_vals.update({'pkg_capicity':capacity})
						add_vals.update({'pkg_capicity_unit':secondary.unit_id.id})
						body+="<li>Package Capicity : "+str(capacity)+" "+str(secondary.unit_id.name)+" </li>"
				if sub_loc:
					sub_loc.packages +=math.ceil(data[8])
					
					sub_loc.total_quantity +=data[9]
				else:
					add_vals.update({'packages':math.ceil(data[8])})
					add_vals.update({'pkg_unit':secondary.unit_id.id})
					add_vals.update({'total_quantity':data[9]})
					add_vals.update({'total_qty_unit':unit.id})
					add_vals.update({'Packaging_type':primary.id})
					body+="<li>Packaging : "+str(primary.name)+" </li>"
					store_id.multi_product_ids=[(0,0,add_vals)]
				body+="<li>No of Packages added:"+str(data[9]/primary.qty)+" "+str(secondary.unit_id.name)+" </li>"
				body+="<li>Quantity Added:"+str(data[9])+" "+str(unit.name)+" </li>"
				
				#per=0.0
				
				#for sub1 in store_id.multi_product_ids:
				#	per +=(sub1.packages*100)/sub1.pkg_capicity
				store_id.state = 'partial' #if per<100 else 'full'
			else:
				raise UserError("Store Updation error")
			matser_id=False,
			n_qty = int(data[9])
			if one_pack:
				pallet_pkg = primary.qty
			elif secondary:
				pallet_pkg = secondary.qty
			for plt in range(int(math.ceil(int(data[9])/pallet_pkg))):
				if n_qty <= 0:
					break;
				matser_id=self.env['stock.store.master.batch'].create({'product_id':product_id.id,
						 'name':'{}'.format(data[11]),'location_id':store_id.n_location.id,
						 'store_id':store_id.id,'logistic_state':'transit_in',
						 'packaging':primary.id})
					
				if data[8]:
					batch_obj = self.env['mrp.order.batch.number']
					batch_history_obj = self.env['mrp.order.batch.number.history']
					for batct in range(int(pallet_pkg)):
						if n_qty <= 0:
							break;
						a_qty= n_qty if n_qty < data[6] else data[6]
						n_qty -= data[6]
						code = self.env['ir.sequence'].next_by_code('mrp.order.batch.number') or 'New'
						b_t=batch_obj.create({'product_id':product_id.id,
						 	'approve_qty':a_qty,'product_qty':a_qty,'uom_id':unit.id,
						 	'qty_unit_id':unit.id,'produce_qty_date':datetime.now(),
						 	'name':'{}/{}'.format('Import',code),
						 	'store_id':store_id.id,'request_state':'done','sale_id':sale_id,
							'logistic_state':'transit_in','master_id':matser_id.id})
						batch_history_obj.create({'batch_id':b_t.id,'operation':'import',
								'description':'New Batch create in Stock from Import'})
				 
			store_id.message_post(body)
			self.env['location.history'].create({'stock_location':store_id.id,
							'product_id':product_id.id,'operation_name':'File import',
							'qty':data[9],'n_type':'in','operation':'im'})
			
			if  product_dic.get(str(product_id.id)):
				product_dic[str(product_id.id)] += int(data[9]) 
			else:
				 product_dic.update({str(product_id.id):int(data[9])})
			_logger.error("API-Confirmation : Product [{}]{} Imported ".format(product_id.default_code,product_id.name))
	stock_inv=self.env['stock.inventory'].create({'name':'Inventory-Import '+str(self.region.name),
							'location_id':self.location.id,'filter':'partial'})	
	stock_inv.prepare_inventory()
	stock_lines=[]
	for line in product_dic:
		product_id=self.env['product.product'].search([('id','=',line)])
		quants=self.env['stock.quant'].search([('product_id','=',product_id.id),	
							('location_id','=',self.location.id)])
						
		avl_qty=sum([ q.qty for q in quants if q.qty>0 ])
		stock_lines.append([0,0,{'product_id':product_id.id,'product_qty':avl_qty+product_dic[line],
					'product_uom_id': product_id.product_tmpl_id.uom_id.id,
			  		'location_id':self.location.id}])
	stock_inv.line_ids = stock_lines
	stock_inv.action_done()
	self.import_status = 'done'	
						
    @api.multi
    def manufacturing_product_import(self):
    	import base64
    	self.env.cr.execute("select store_fname from ir_attachment where res_model='product.store.data.import' and res_id="+str(self.id))
    	path=self.env.cr.fetchone()
    	
    	file_path='~/.local/share/Odoo/filestore/'+str(self.env.cr.dbname)+'/'+str(path[0])
    	import getpass
    	user=getpass.getuser()
    	FILENAME = "/home/{}/{}".format(str(user),str(self.name))
    	with open(FILENAME, "wb") as f:
            text = self.new_upload
            f.write(base64.b64decode(text))
            
    	import xlrd
    	import xlwt
	book = xlrd.open_workbook(FILENAME)
	max_nb_row=book.sheet_by_index(0).nrows
	move_line_data=[]
	
	for row1 in range(max_nb_row) :
		if row1 != 0:
			data1=book.sheet_by_index(0).row_values(row1)
			product_id=categ_id=unit=False
			
			if data1[1]:
				if not float(data1[1]):
					raise UserError("Default Code is not Proper")
				product_id=self.env['product.product'].search([('default_code','=',str(int(data1[1])))])
				if not product_id:
					raise UserError("Product Not Found")
				elif len(product_id)>1:
					raise UserError("Multiple Product Found")
				unit=product_id.product_tmpl_id.uom_id
				qty = float(data1[2])
				move_line_data.append((0,0,{'product_id':product_id.id,'product_uom_qty':qty,
					'product_uom':unit.id}))
					
	self.picking_id.move_lines = move_line_data

