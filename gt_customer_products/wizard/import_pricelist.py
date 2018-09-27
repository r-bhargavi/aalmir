# -*- coding: utf-8 -*-
import base64
import csv

from openerp import api, fields, models
from tempfile import TemporaryFile

class ImportPricelist(models.TransientModel):
    _name = 'import.pricelist'
    
    name = fields.Binary(string="File")
    
    @api.one
    def import_pricelist(self):
        partner_obj = self.env['res.partner']
#        user_obj = self.env['res.users']
        pricelist_obj = self.env['product.pricelist']
        cust_product_obj = self.env['customer.product']
        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        uom_obj = self.env['product.uom']
        uom_cat_obj = self.env['product.uom.categ']
        pricelist_item_obj = self.env['product.pricelist.item']
        obj = self
        fileobj = TemporaryFile('w+')
        try:
            fileobj.write(base64.decodestring(obj.name))
            fileobj.seek(0)
            reader = csv.reader(fileobj, delimiter=',', quotechar="'")
            line = 0
            for row in reader:
                line = line +1 
                if line == 1:
                    continue
                #check customer
                if not row[0]:
                    continue
                customer = row[0].encode('utf-8').strip()
                p_ids = partner_obj.sudo().search([('name','=', customer)])
                if p_ids:
                    p_id = p_ids[0]
                else:
                    p_id = partner_obj.sudo().create({'name': customer, 'company_type' : 'company'})
#                uobj = user_obj.browse(self.env.uid)
#                currency = uobj.partner_id.company_id and uobj.partner_id.company_id.currency_id.id

                #create Pricelist
                pricelist_ids = pricelist_obj.sudo().search([('customer', '=', p_id.id)])
                if pricelist_ids:
                    pricelist_id = pricelist_ids[0]
                else:
                    pricelist_id = pricelist_obj.create({
                        'name' : p_id.name + "'s Pricelist",
                        'customer' :  p_id.id
                    })
                p_id.write({'property_product_pricelist' : pricelist_id.id})
                 #create product
                if not row[2]:
                    continue
                product = row[2].encode('utf-8').strip()
                
                #create category
                categ_id = False
                if product[0] == '2':
                    c_ids = category_obj.sudo().search([('cat_type', '=', 'injection')])
                    if c_ids:
                        categ_id = c_ids[0]
                elif product[0] == '1':
                    c_ids = category_obj.sudo().search([('cat_type', '=', 'film')])
                    if c_ids:
                        categ_id = c_ids[0]
                if not categ_id:   
                    continue
                cust_prod_vals = {}
                prod_ids = product_obj.sudo().search([('default_code','=', product)])
                if prod_ids:
                    prod_id = prod_ids[0]
                    cust_prod_vals = {
                        'existing_product' : True,
                        'product_type' : prod_id.categ_id.id,
                    }
                else:
                    #create Unit of Measure
                    if not row[8]:
                        continue
                    uom = row[8].encode('utf-8').strip().lower()
                    if not uom:
                        continue
                    
                    uom_ids = uom_obj.sudo().search([('name', '=', uom)])
                    if uom_ids:
                        uom_id = uom_ids[0]
                    else:
                        uom_cat_ids = uom_cat_obj.sudo().search([('name', '=', 'Weight')])
                        if uom_cat_ids:
                            uom_cat_id = uom_cat_ids[0]
                        else:
                            uom_cat_id = uom_cat_obj.sudo().create({'name': 'Weight'})
                        uom_id = uom_obj.sudo().create({
                            'name' : uom,
                            'category_id' : uom_cat_id.id,
                            'uom_type' : 'reference'
                        })
                    prod_id = product_obj.sudo().create({
                        'name' : row[3].encode('utf-8').strip(),
                        'description_sale' : row[3].encode('utf-8').strip(),
                        'categ_id' : categ_id.id,
                        'child_prod_name' : row[3].encode('utf-8').strip(),
                        'type' : 'product',
                        'default_code' : product,
                        'uom_id' : uom_id.id,
                        'uom_po_id' : uom_id.id
                    })
                    cust_prod_vals = {
                        'existing_product' : False,
                        'product_type' : prod_id.categ_id.id,
                    }
                #create customer product
                cust_prod_ids = cust_product_obj.sudo().search([('product_id','=', prod_id.id), ('pricelist_id', '=', pricelist_id.id)])
                if cust_prod_ids:
                    cust_prod_id = cust_prod_ids[0]
                else:
                    #create packaging
                    pack = row[10].encode('utf-8').strip()
                    if pack:
                        cust_prod_pack_ids = uom_obj.sudo().search([('name','=', pack)])
                        if cust_prod_pack_ids:
                            cust_prod_pack_id = cust_prod_pack_ids[0]
                        else:
                            cust_prod_pack_id = uom_obj.sudo().create({'name': pack})
                    else:
                        cust_prod_pack_id = False
                    
                    cust_prod_vals.update({
                        'product_id' : prod_id.id,
                        'pricelist_id' : pricelist_id.id,
                        'product_name' : prod_id.name,
                        'product_description' : prod_id.description_sale,
                        'avg_price' : row[5] and float(row[5].encode('utf-8').strip()) or 0.0,
                        'lowest_price' : row[5] and float(row[5].encode('utf-8').strip()) or '0.0',
                        'floor_price' : row[6] and float(row[6].encode('utf-8').strip()) or 0.0,
                        'min_qty': row[7] and float(row[7].encode('utf-8').strip()) or 0.0,
                        'uom_id' : prod_id.uom_id.id,
                        'type_of_packaging' : cust_prod_pack_id and cust_prod_pack_id.id or False,
                        'qty_per_package' : row[9] and row[9].isdigit() and row[9].encode('utf-8').strip() or 0,
                    })
                    
                    external_no = row[1].encode('utf-8').strip()
                    if external_no:
                        cust_prod_vals.update({'ext_product_number': external_no})
                    cust_prod_id = cust_product_obj.sudo().create(cust_prod_vals)
                    
                    pricelist_item_obj.sudo().create({
                        'cus_product_id' : cust_prod_id.id,
                        'min_quantity' : 1,
                        'qty' : 10000,
                        'fixed_price'  : row[5] and float(row[5].encode('utf-8').strip()) or 0.0
                    })
                
        finally:
            fileobj.close()
        return True
    
    @api.one
    def import_search_pricelist(self):
        cust_product_obj = self.env['customer.product']
       
        obj = self
        fileobj = TemporaryFile('w+')
        print "fileobj", fileobj
        try:
            fileobj.write(base64.decodestring(obj.name))
            fileobj.seek(0)
            reader = csv.reader(fileobj, delimiter=',', quotechar="'")
            print "reader", reader
            line = 0
            for row in reader:
                print "row",row
                line = line +1 
                if line == 1:
                    continue
                external = row[1].encode('utf-8').strip()
                if not external:
                    continue
                else:
                    customer = row[0].encode('utf-8').strip()
                    default_code = row[2].encode('utf-8').strip()
                    
                    cust_id = cust_product_obj.search([('pricelist_id.customer.name','=',customer), ('product_id.default_code','=',default_code)])
                    print "cust_id", cust_id
                    if cust_id:
                        cust_id.write({'ext_product_number':external})
                    
        finally:
            fileobj.close()       
        return True

