# -*- coding: utf-8 -*-
from openerp import models, fields, api, exceptions
from openerp.tools.translate import _

class stock_picking_merge_wizard(models.TransientModel):
    _inherit = "stock.picking.merge.wizard" 
    @api.model
    def get_partner_name(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        return obj.partner_id and obj.partner_id.id or False
    @api.model
    def get_sale_order(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        return obj and obj.id or False
    partner_id=fields.Many2one("res.partner","Customer Name" ,domain=[('customer', '=', True)], default=get_partner_name)
    sale_id=fields.Many2one("sale.order","Sale Order" ,domain=[('state', '=', 'sale')], default=get_sale_order)
class InvoiceMerge(models.TransientModel):
    _name = "invoice.merge"
    _description = "Merge Partner Invoice"
    @api.model
    def get_partner_name(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        return obj.partner_id and obj.partner_id.id or False
    @api.model
    def get_sale_order(self):
        obj = self.env['sale.order'].browse(self._context.get('active_id'))
        return obj and obj.id or False
    keep_references = fields.Boolean('Keep references'
                                     ' from original invoices',
                                     default=True)
    date_invoice = fields.Date('Invoice Date', default=lambda self: fields.datetime.now())
    partner_id=fields.Many2one('res.partner', string="Customer Name" ,domain=[('customer', '=', True)], default=get_partner_name)
    sale_id=fields.Many2one('sale.order', domain=[('state','=', 'sale')],string="Sale Order" , default=get_sale_order)
    sale_id_name=fields.Char(related='sale_id.name')
    invoice_ids = fields.Many2many("account.invoice", string='Invoices')
    
    @api.model
    def _dirty_check(self):
        if self.env.context.get('active_model', '') == 'account.invoice':
            ids = self.env.context['active_ids']
            if len(ids) < 2:
                raise exceptions.Warning(
                    _('Please select multiple invoice to merge in the list '
                      'view.'))

            invs = self.env['account.invoice'].browse(ids)
            for d in invs:
                if d['state'] != 'draft':
                    raise exceptions.Warning(
                        _('At least one of the selected invoices is %s!') %
                        d['state'])
                if d['account_id'] != invs[0]['account_id']:
                    raise exceptions.Warning(
                        _('Not all invoices use the same account!'))
                if d['company_id'] != invs[0]['company_id']:
                    raise exceptions.Warning(
                        _('Not all invoices are at the same company!'))
                if d['partner_id'] != invs[0]['partner_id']:
                    raise exceptions.Warning(
                        _('Not all invoices are for the same partner!'))
                if d['type'] != invs[0]['type']:
                    raise exceptions.Warning(
                        _('Not all invoices are of the same type!'))
                if d['currency_id'] != invs[0]['currency_id']:
                    raise exceptions.Warning(
                        _('Not all invoices are at the same currency!'))
                if d['journal_id'] != invs[0]['journal_id']:
                    raise exceptions.Warning(
                        _('Not all invoices are at the same journal!'))
        return {}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
       
        res = super(InvoiceMerge, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=False)
        self._dirty_check()
        return res

    @api.multi
    def merge_invoices(self):
        for record in self:
            inv_obj = self.env['account.invoice']
            aw_obj = self.env['ir.actions.act_window']
            ids =record.invoice_ids.ids
            invoices = inv_obj.browse(self.invoice_ids.ids)
            allinvoices = invoices.do_merge(keep_references=self.keep_references,
                                        date_invoice=self.date_invoice)
        
            xid = {
               'out_invoice': 'action_invoice_tree1',
               'out_refund': 'action_invoice_tree3',
               'in_invoice': 'action_invoice_tree2',
                'in_refund': 'action_invoice_tree4',
            }[invoices[0].type]
            action = aw_obj.for_xml_id('account', xid)
            action.update({
            'domain': [('id', 'in', ids + allinvoices.keys())],
            })
        return action
