# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class utmCampaign(models.Model):
    _inherit = 'utm.campaign'
    
    user_id=fields.Many2one('res.users','User')
    user_m2m =fields.Many2many('res.users','n_user_campaign_rel','id','user_id','Assign UsersName')
        
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
	if context.get('n_user'):
		term_qry="select distinct id from n_user_campaign_rel where user_id={}".format(uid)
    		cr.execute(term_qry)
    		n_args=([i[0] for i in cr.fetchall()])
		args.extend([('id','in',n_args)])
    	return super(utmCampaign,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)
