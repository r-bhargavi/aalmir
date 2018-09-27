# -*- coding: utf-8 -*-

from openerp.osv import orm, fields


class stock_picking(orm.Model):
    _inherit = "stock.picking"

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Inherit the original function of the 'stock' module
            We select the partner of the sales order as the partner of the
            customer invoice
        """
        sale_line_obj = self.pool['sale.order.line']
        line_ids = sale_line_obj.search(
            cr, uid, [('procurement_group_id', '=', picking.group_id.id)],
            context=context)
        if line_ids:
            lines = sale_line_obj.browse(cr, uid, line_ids, context=context)
            saleorder = lines[0].order_id
            return saleorder.partner_invoice_id.id
        return super(stock_picking, self)._get_partner_to_invoice(
            cr, uid, picking, context=context)

    def _get_sale_id(self, cr, uid, ids, name, args, context=None):
        sale_line_obj = self.pool['sale.order.line']
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                line_ids = sale_line_obj.search(
                    cr, uid,
                    [('procurement_group_id', '=', picking.group_id.id)],
                    context=context)
                if line_ids:
                    lines = sale_line_obj.browse(cr, uid, line_ids,
                                                 context=context)
                    res[picking.id] = lines[0].order_id
        return res

    _columns = {
        'sale_id': fields.function(
            _get_sale_id, type="many2one",
            relation="sale.order", string="Sale Order"),
    }

    def _create_invoice_from_picking(self, cr, uid, picking, vals,
                                     context=None):
        sale_line_obj = self.pool['sale.order.line']
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_id = super(stock_picking, self)._create_invoice_from_picking(
            cr, uid, picking, vals, context=context)
        if picking.group_id:
            line_ids = sale_line_obj.search(
                cr, uid, [('procurement_group_id', '=', picking.group_id.id),
                          ('product_id.type', '=', 'service'),
                          ('invoiced', '=', False)], context=context)

            if line_ids:
                created_lines = sale_line_obj.invoice_line_create(
                    cr, uid, line_ids, context=context)
                invoice_line_obj.write(
                    cr, uid, created_lines, {'invoice_id': invoice_id},
                    context=context)
        return invoice_id
