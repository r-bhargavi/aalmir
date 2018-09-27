# -*- coding: utf-8 -*-
from openerp import api, fields, models


class AssignToOtherSalesman(models.TransientModel):
    _name = 'assign.to.other.salesman'

    name = fields.Many2one('res.users', 'Sales Person')
    
    @api.multi
    def assign(self):
        for assign in self:
            active_id = self._context.get('active_id')
            obj = self.env['crm.lead'].sudo().browse(active_id)
            new = assign.name.partner_id.name
            old = obj.user_id.partner_id.name
            obj.sudo().with_context({'from_salesman_assign': True, 'real_user_id':self._uid}).write({'user_id': assign.name.id})
            orders = self.env['sale.order'].search([('opportunity_id','=',active_id)])
            orders.sudo().write({'user_id':assign.name.id})
            body = ''
            if old:
                user = self.env['res.users'].sudo().browse(self.env.uid)
                assign = user.partner_id.name
                print old
                print new
                body += "%s assigned Lead to %s -> %s"%(assign, old, new,)
            else:
                body += "Assigned Sales Person : %s"%(new)
            obj.sudo(self.env.uid).message_post(body=body,subject="Sales Person Chaged")
        return True
