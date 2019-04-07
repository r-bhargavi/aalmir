# -*- coding: utf-8 -*-
# copyright reserved

from openerp.osv import fields, osv
from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
from datetime import datetime,date,timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
import logging
import time
import math
from urlparse import urljoin
from openerp import tools, SUPERUSER_ID
from urllib import urlencode
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class MrpProductionExtraRM(models.Model):
   _name='mrp.extra.raw.material'
   
   production_id=fields.Many2one('mrp.production', string='Production No.')
   wastage_qty=fields.Float('Wastage Qty')
   required_qty=fields.Float('Required Qty')
   wastage_uom_id=fields.Many2one('product.uom')
   required_uom_id=fields.Many2one('product.uom')
   extra_product_ids=fields.One2many('mrp.extra.raw.material.line','line_id', string='Required Product')
   note=fields.Text('Remark')
   document=fields.Binary('Document') 
   reason=fields.Selection([('wastage','Wastage'),('extra production','Extra Production')], string='Reason')
   used_raw_matrial_ids=fields.One2many('mrp.extra.raw.material.line','use_line_id', string='Required Product')
   remain_qty=fields.Float('Remain Qty', compute='_get_remain_qty')
   
   @api.constrains('wastage_qty')
   def _check_qty(self):
        for record in self:
            if record.used_raw_matrial_ids:
               sm=sum(line.qty for line in record.used_raw_matrial_ids)
               if record.wastage_qty < sm:
                  raise ValidationError("Total Used Wastage Qty is not greater than Wastage Qty.") 

   @api.multi
   @api.depends('used_raw_matrial_ids.qty') 
   def _get_remain_qty(self):
       for record in self:
           qty=0
           for line in record.used_raw_matrial_ids:
               qty=sum(line.qty for line in record.used_raw_matrial_ids)
           if qty:
              record.remain_qty=record.wastage_qty-qty
           else:
              record.remain_qty=record.wastage_qty

   @api.multi
   @api.onchange('required_qty')
   def required_rmqty(self):
       for record in self:
           if record.extra_product_ids:
              pcs_qty=(record.required_qty/record.production_id.product_id.weight)
              lst=[]
              for ln in record.extra_product_ids:
                  qty=self.env['mrp.bom.line'].search([('product_id','=',ln.product_id.id),
                                 '|',('bom_packaging_id','=',record.production_id.bom_id.id),
                                  ('bom_id','=',record.production_id.bom_id.id)], limit=1)
                  ln.qty= (pcs_qty * qty.product_qty)
          
   @api.multi
   def extra_rawmaterials(self):
       for rec in self:
         print "use_rawuse_raw",self._context
         if self._context.get('use_raw'):
            print'TEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE'
            for record in rec.used_raw_matrial_ids:
                product_id=0
                if record.used_type == 'grinding':
                   if not rec.production_id.product_id.check_grinding:
                      raise UserError(_('Please Select Grinding product in Manufacturing Product.')) 
                   else:
                      product_id=rec.production_id.product_id.grinding_product_id.id
                else:
                   if not rec.production_id.product_id.check_scrap:
                      raise UserError(_('Please Select Scrap product in Manufacturing Product.')) 
                   else:
                      product_id=rec.production_id.product_id.scrap_product_id.id
                batch=self.env['mrp.order.batch.number'].sudo().create({'name':str(record.used_type)+'-'+str(rec.production_id.name)+'-' +str(rec.production_id.product_id.default_code),
		                               'production_id':rec.production_id.id,
                                                'uom_id':record.uom_id.id,
		                                'product_qty':record.qty, 
                                                'wastage_product':product_id,
                                                #'wastage_allow':record.production_id.wastage_allow,
                                               # 'wastage_qty':rec.production_id.total_wastage_qty,
                                                'used_type':record.used_type})
                print "batch--------------------------",batch
            rec.production_id.requested_wastage_qty +=sum(line.qty for line in rec.used_raw_matrial_ids)
         
         else:
            print"jkkkkkkkkkkkkkkkkkkkkkk"
            request=self.env['mrp.raw.material.request'].create({'production_id':rec.production_id.id,
		                    'wastage_qty':rec.wastage_qty,'required_qty':rec.required_qty,
		                    'wastage_uom_id':rec.wastage_uom_id.id,'required_uom_id':rec.required_uom_id.id,
		                    'product_id':rec.production_id.product_id.id ,'request_type':'extra',
		                    'wastage_allow':rec.production_id.wastage_allow,
		                    'request_date':time.strftime('%Y-%m-%d %H:%M:%S'),
		                    'allow_wastage_uom_id':rec.production_id.allow_wastage_uom_id.id,
		                    'note':rec.note,'document':rec.document,'reason':rec.reason})
                               
            for line in rec.extra_product_ids:
		request_line=self.env['mrp.raw.material.request.line'].create({
						'material_request_id':request.id,
                                                'product_id':line.product_id.id, 'qty':line.qty,
                                                'uom_id':line.uom_id.id})
                for product in rec.production_id.product_lines:
                	if product.product_id.id == line.product_id.id:
                		product.product_qty += line.qty
                
            temp_id = self.env.ref('api_raw_material.email_template_extra_raw_material')
            if temp_id:
		       user_obj = self.env['res.users'].browse(self.env.uid)
		       base_url = self.env['ir.config_parameter'].get_param('web.base.url')
		       query = {'db': self._cr.dbname}
		       fragment = {
			    'model': 'mrp.production',
			     'view_type': 'form',
			     'id': rec.production_id.id,
			      }
		       url = urljoin(base_url, "/web?%s#%s" % (urlencode(query), urlencode(fragment)))
		       text_link = _("""<a href="%s">%s</a> """) % (url,rec.production_id.name)
		       body_html = """<div> 
					<p> <strong>Extra Raw Material Request</strong><br/>
					 <b>Dear: %s,</b><br/>
					 <b>Production Number :</b>%s ,<br/> 
					 <b>Customer Name :</b>%s ,<br/>
					  <b>Product Name :</b>%s ,<br/>
					  <b>Allowed Wastage :</b>%s %s,<br/>
					  <b>  Wastage Qty : %s %s</b><br/>
					  <b>  Required Qty : %s %s</b><br/>
					  <b>  Reason : </b>%s<br/>
					  <b>  Remark : </b>%s
					</p>
					</div>"""%(rec.production_id.user_id.name, text_link or '',rec.production_id.partner_id.name,
					    rec.production_id.product_id.name, round(rec.production_id.wastage_allow,2),
					   rec.production_id.allow_wastage_uom_id.name,
					  round(rec.wastage_qty,2), rec.wastage_uom_id.name, rec.required_qty, 
					 rec.required_uom_id.name,rec.reason, rec.note)
		       body_html +="<table class='table' style='width:80%; height: 50%;font-family:arial; text-align:left;'><tr><th>Material Name </th><th> qty</th></tr>"                  
		       for line in rec.extra_product_ids:
		           body_html +="<tr><td>%s</td><td>%s %s</td></tr>"%(str(line.product_id.name), round(line.qty, 2), str(line.uom_id.name)) 
		       body_html +="</table>"
		       body_html = self.pool['mail.template'].render_template(self._cr, self._uid, body_html, 'mrp.production',rec.production_id.id, context=self._context)
		       n_emails=str(rec.production_id.user_id.login)
		       temp_id.write({'body_html': body_html, 'email_to' : n_emails, 'email_from': str(rec.production_id.user_id.login)})
		       temp_id.send_mail(rec.production_id.id)
          
class MrpProductionWastageProduct(models.Model):
   _name='mrp.extra.raw.material.line'
   
   @api.model
   def get_qty(self):
       if self._context.get('wastage'):
          return self._context.get('wastage_qty')
   @api.model
   def get_uom(self):
       if self._context.get('wastage'):
          return self._context.get('uom_id')
   

   product_id=fields.Many2one('product.product', string='Product')
   qty=fields.Float('Quantity', default=get_qty)
   name=fields.Char()
   uom_id=fields.Many2one('product.uom', string="Unit", default=get_uom)
   line_id=fields.Many2one('mrp.extra.raw.material', 'Wastage No.')
   use_line_id=fields.Many2one('mrp.extra.raw.material', 'Wastage No.')
   used_type=fields.Selection([('grinding','Grinding'),('scrap','Scrap')],string='Used Type')


