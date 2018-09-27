# -*- coding: utf-8 -*-
# copyright reserved

from openerp import api,models,fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from urlparse import urljoin
from urllib import urlencode
import json

class chnageCurrencyValue(models.TransientModel):
    _name = "change.pricelist.currency"
    
    rm_pricelist_id = fields.Many2one("raw.material.pricelist", "Pricelist")
    currency_id = fields.Many2one("res.currency", "Currency")
    keep_val = fields.Boolean("Keep",default=False,help="If You select this, then after currency change process the values of prices columns are not updated")
    
    @api.multi
    def process(self):
    	for res in self:
    		vals={}
    		if not res.currency_id:
    			raise UserError('Please Select Currency')
    		if res.rm_pricelist_id:
    			vals.update({'currency_id':res.currency_id.id})
			if not res.keep_val:
				if res.rm_pricelist_id.base_price:
					print "111111",res.currency_id,self.currency_id
					print "22222",res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.base_price,self.currency_id)
					vals.update({'base_price':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.base_price,self.currency_id)})
				if res.rm_pricelist_id.qty_range_1:
					vals.update({'qty_range_1':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_1,self.currency_id)})
				if res.rm_pricelist_id.qty_range_2:
					vals.update({'qty_range_2':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_2,self.currency_id)})
				if res.rm_pricelist_id.qty_range_3:
					vals.update({'qty_range_3':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_3,self.currency_id)})
				if res.rm_pricelist_id.qty_range_4:	
					vals.update({'qty_range_4':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_4,self.currency_id)})
				if res.rm_pricelist_id.qty_range_5:
					vals.update({'qty_range_5':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_5,self.currency_id)})
				if res.rm_pricelist_id.qty_range_6:
					vals.update({'qty_range_6':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_6,self.currency_id)})
				if res.rm_pricelist_id.qty_range_7:	
					vals.update({'qty_range_7':res.rm_pricelist_id.currency_id.compute(res.rm_pricelist_id.qty_range_7,self.currency_id)})

		if vals:
			print ".................",vals
			res.rm_pricelist_id.write(vals)			

    		
    		
    		
