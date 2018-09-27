# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.tools import email_re, email_split
from lxml import etree
from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)
class crm_lead2opportunity_partner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    
    def _get_sales_person(self):
        if self.user_has_groups('base.group_sale_salesman') and not self.user_has_groups('base.group_sale_manager'):
            return True
        return False
    
    is_sales_person = fields.Boolean(string="Sales Person", default=_get_sales_person)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(crm_lead2opportunity_partner, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        for node in doc.xpath("//field[@name='opportunity_ids']"):
            lead_obj = self.env['crm.lead']
            lead = lead_obj.browse(int(self._context['active_id']))
            email = lead.partner_id and lead.partner_id.email or lead.email_from
            partner_match_domain = []
            for email in set(email_split(email) + [email]):
                partner_match_domain.append(('email_from', 'ilike', email))
            if lead.partner_id:
                partner_match_domain.append(('partner_id', '=', lead.partner_id.id))
            partner_match_domain = ['|'] * (len(partner_match_domain) - 1) + partner_match_domain
            if not partner_match_domain:
                partner_match_domain = []
            domain = partner_match_domain
            domain += ['&', ('active', '=', True), ('probability', '<', 100), ('stage_id.name','!=', 'Merge'), ('id','!=', lead.id), ('stage_2','in', [False, 'qualified'])]
            node.set('domain', str(domain))
        res['arch'] = etree.tostring(doc)
        return res
    
    @api.model
    def default_get(self, fields):
        res = super(crm_lead2opportunity_partner, self).default_get(fields)
        if res.get('opportunity_ids'):
            ind = res.get('opportunity_ids').index(int(self._context['active_id']))
            res.get('opportunity_ids').pop(ind)
            res.update({'user_id' : self.env.uid, 'opportunity_ids': []})
        res.update({'user_id' : self.env.uid})
        return res
    
    def action_apply(self, cr, uid, ids, context=None):
        _logger.info("action_apply==========")
        if context is None:
            context = {}
        lead_obj = self.pool['crm.lead']
        partner_obj = self.pool['res.partner']

        w = self.browse(cr, uid, ids, context=context)[0]
        opp_ids = [context.get('active_id')]
        opp_ids += [o.id for o in w.opportunity_ids]
        vals = {
            'team_id': w.team_id.id,
        }
       
                
        if w.partner_id:
            vals['partner_id'] = w.partner_id.id
        if w.name == 'merge':
            lead_id = lead_obj.merge_opportunity(cr, uid, opp_ids, context=context)
            lead_ids = [lead_id]
            lead = lead_obj.read(cr, uid, lead_id, ['type', 'user_id'], context=context)
            if lead['type'] == "lead":
                context = dict(context, active_ids=lead_ids)
                vals.update({'lead_ids': lead_ids, 'user_ids': [w.user_id.id]})
                self._convert_opportunity(cr, uid, ids, vals, context=context)
            elif not context.get('no_force_assignation') or not lead['user_id']:
                vals.update({'user_id': w.user_id.id})
                lead_obj.write(cr, uid, lead_id, vals, context=context)
        else:
            lead_ids = context.get('active_ids', [])
            vals.update({'lead_ids': lead_ids, 'user_ids': [w.user_id.id]})
            self._convert_opportunity(cr, uid, ids, vals, context=context)
            for lead in lead_obj.browse(cr, uid, lead_ids, context=context):
                if lead.partner_id and lead.partner_id.user_id != lead.user_id:
                    partner_obj.write(cr, uid, [lead.partner_id.id], {'user_id': lead.user_id.id}, context=context)
                if w.action == 'exist':
                    partner_obj.write(cr, uid, [lead.partner_id.id], {'street': lead.street, 'street2': lead.street2, 'city': lead.city, 'state_id': lead.state_id and lead.state_id.id or False, 'zip': lead.zip, 'country_id': lead.country_id and lead.country_id.id or False, 'phone': lead.phone,'mobile': lead.mobile,'fax': lead.fax,'email': lead.email_from,'name':lead.partner_name})
		    partner_obj.create(cr, uid,{'parent_id':lead.partner_id.id,'street': lead.street, 'street2': lead.street2, 'city': lead.city, 'state_id': lead.state_id and lead.state_id.id or False, 'zip': lead.zip, 'country_id': lead.country_id and lead.country_id.id or False, 'phone': lead.phone,'mobile': lead.mobile,'fax': lead.fax,'email': lead.email_from,'name':lead.contact_name})

        stage_obj = self.pool.get('crm.stage')
        stage_ids = stage_obj.search(cr, uid, [('name','=','Open')])
        if stage_ids:
            vals = {'stage_id': stage_ids[0]}
            if context.get('from_cold_calling'):
                vals.update({'stage_2' : 'qualified'})
            else:
                vals.update({'stage_2' : False})
            _logger.info("lead_ids============>%s"%(lead_ids))
            lead_obj.write(cr, uid, lead_ids, vals)
        return self.pool.get('crm.lead').redirect_opportunity_view(cr, uid, lead_ids[0], context=context)
