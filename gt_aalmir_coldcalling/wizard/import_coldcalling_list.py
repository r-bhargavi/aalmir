# -*- coding: utf-8 -*-
import base64
import csv
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from openerp.exceptions import UserError

from openerp import api, fields, models
from tempfile import TemporaryFile

class ImportColdCallingList(models.TransientModel):
    _name = 'import.coldcallng.list'
    
    name = fields.Char(string="Cold Calling List Name")
    file = fields.Binary(string="File")
    
    @api.one
    def import_coldcalling_list(self):
        group_obj = self.env['utm.campaign']
        partner_obj = self.env['res.partner']
        crm_obj = self.env['crm.lead']
        fileobj = TemporaryFile('w+')
        try:
            fileobj.write(base64.decodestring(self.file))
            fileobj.seek(0)
            reader = csv.reader(fileobj, delimiter=',', quotechar="'")
            line = 0
            for row in reader:
                line = line +1
                if line == 1:
                    continue
                if not self.name:
                    raise UserError(('Add Group Name'))
                group_ids = group_obj.search([('name', '=', self.name)])
                if group_ids:
                    g_id = group_ids[0]
                else:
                    g_id = group_obj.create({'name': self.name})
                company = row[0].encode('utf-8').strip()
                if not company:
                    continue
                
                customer = row[3].encode('utf-8').strip()
                if customer:
                    partners = partner_obj.search([('name', '=', customer)])
                    if partners:
                        partner = partners[0]
                    else:
                        partner = False
                
                phone = row[1].encode('utf-8').strip()      
                mobile = row[2].encode('utf-8').strip()  
                email = row[4].encode('utf-8').strip()  
                
                if not email:
                    continue
                
                if not phone and not mobile:
                    continue
                    
                if not phone:
                    if mobile:
                        phone = mobile
                        
                if not mobile:
                    if phone:
                        mobile = phone
                        
                user_id = False
                if self.user_has_groups('base.group_sale_salesman') and not self.user_has_groups('base.group_sale_manager') and not self.user_has_groups('base.group_system'):
                    user_id = self.env.uid
                else:
                    user_id = False
                    
                vals = {
                    'campaign_id' : g_id.id,
                    'partner_id' : partner and partner.id or False,
                    'name' : company,
                    'contact_name' : partner and partner.name or '',
                    'phone' : phone or partner and partner.phone or False,
                    'mobile' : mobile or partner and partner.mobile or False,
                    'email_from' : email,
                    'stage_2' : 'not_contacted', 
                    'stage_id' : False,
                    'user_id' : user_id,
                    'type' : 'lead'
                    
                }
                print "===vals====>",vals
                lead_id = crm_obj.with_context({'cold_calling': True}).create(vals)
                print "LEAD", lead_id
        finally:
            fileobj.close()
        return True
    
    

    
    
    
    
