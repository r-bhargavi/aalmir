# -*- coding: utf-8 -*-



from openerp import api, fields, models

class ProcurementOrder(models.Model):
    _inherit='procurement.order'
    delivery_address_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        )
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _prepare_procurement_group_by_line(self, line):
        vals = super(SaleOrder, self)._prepare_procurement_group_by_line(line)
        # for compatibility with sale_quotation_sourcing
        if line._get_procurement_group_key()[0] == 10:
            if line.warehouse_id:
                vals['name'] += '/' + line.warehouse_id.name
                vals['partner_id']= line.delivery_address_id.id
        return vals

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help="If no source warehouse is selected on line, "
             "this warehouse is used as default. ")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        'Source Warehouse',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help="If a source warehouse is selected, "
             "it will be used to define the route. "
             "Otherwise, it will get the warehouse of "
             "the sale order")
    delivery_address_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        )
    
    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        values = super(SaleOrderLine,
                       self)._prepare_order_line_procurement(group_id=group_id)
        if self.warehouse_id:
            values['warehouse_id'] = self.warehouse_id.id
            values['delivery_address_id']=self.delivery_address_id.id
        return values

    @api.multi
    def _get_procurement_group_key(self):
        """ Return a key with priority to be used to regroup lines in multiple
        procurement groups

        """
        priority = 10
        key = super(SaleOrderLine, self)._get_procurement_group_key()
        # Check priority
        if key[0] >= priority:
            return key
        return priority, self.warehouse_id.id ,self.delivery_address_id.id
