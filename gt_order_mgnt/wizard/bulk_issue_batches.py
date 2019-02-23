# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError



class IssueBulkBatches(models.TransientModel):

    _name = "issue.bulk.batches"
    _description = "Batches Bulk Produce"
    
    batch_ids=fields.Many2many('mrp.order.batch.number',string='Batch No.') 
    wo_id=fields.Many2one('mrp.production.workcenter.line',string='WO ID') 
    first_order=fields.Boolean(related='wo_id.first_order',store=True,string='First Wo') 
    previous_batch_id=fields.Many2one('mrp.order.batch.number',string='Previous Batch No.')
    previous_order_ids=fields.Many2many('mrp.production.workcenter.line', string='Previous Work Order No.')
    employee_ids=fields.Many2many('hr.employee', string='Operators Name')
    supplier_btc_no=fields.Many2many('mrp.order.batch.number', string='Supplier Batch Number')
    produce_qty=fields.Float('Produce Qty')


    @api.onchange('batch_ids')
    def batch_ids_onchange(self):
        for record in self:
            if record.wo_id:
                batch_ids=self.env['mrp.order.batch.number'].search([('convert_product_qty','=',0.0),('order_id','=',record.wo_id.id),('production_id','=',record.wo_id.production_id.id)])
                ids_cus = [] 
                if record.wo_id.batch_no_ids_prev:
                   for batch in record.wo_id.batch_no_ids_prev:
                       ids_cus.append(batch.order_id.id)
                else:
                   if record.wo_id.parent_id:
                      for batch in record.wo_id.parent_id.batch_no_ids_prev:
                          ids_cus.append(batch.order_id.id)
                   else:
                      ids_cus = [] 
                batches=[]
                if record.wo_id.production_id:
                    rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',record.wo_id.production_id.id)])
                    print "rm_idsrm_idsrm_ids",rm_ids
                    if rm_ids:
                        for each_rm in rm_ids:
                            pick_ids=self.env['stock.picking'].search([('material_request_id','=',each_rm.id),('state','=','done')])
                            print "pick_idspick_idspick_ids",pick_ids
                            if pick_ids:
                                for each in pick_ids:
                                    if each.store_ids:
                                        for each_store in each.store_ids:
                                            for each_batches in each_store.batches_ids:
                                                batches.append(each_batches.batch_number.id)
                if batch_ids:
                    return {'domain': {'previous_order_id':record.wo_id.batch_no_ids_prev[0].order_id.id if record.wo_id.batch_no_ids_prev else '','previous_order_ids':[('id', 'in', ids_cus)],'supplier_btc_no': [('id', 'in', batches)],'batch_ids': [('id', 'in', (batch_ids.ids))],'employee_ids':[('id', 'in', (record.wo_id.employee_ids.ids))]}}
                else:
                    return {'domain': {'batch_ids': [('id', 'in', False)]}}



    @api.model
    def default_get(self,fields):
        rec = super(IssueBulkBatches, self).default_get(fields)

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        wo_line_id = self.env['mrp.production.workcenter.line'].browse(active_ids)
        print "wo_line_idwo_line_idwo_line_id",wo_line_id
        batches=[]
        if wo_line_id.production_id:
            rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',wo_line_id.production_id.id)])
            print "rm_idsrm_idsrm_ids",rm_ids
            if rm_ids:
                for each_rm in rm_ids:
                    pick_ids=self.env['stock.picking'].search([('material_request_id','=',each_rm.id),('state','=','done')])
                    print "pick_idspick_idspick_ids",pick_ids
                    if pick_ids:
                        for each in pick_ids:
                            if each.store_ids:
                                for each_store in each.store_ids:
                                    for each_batches in each_store.batches_ids:
                                        batches.append(each_batches.batch_number.id)
        if batches:
            rec.update({'default_supplier_btc_no':[(6,0,[batches])]})
        ids_cus = [] 
        if wo_line_id.batch_no_ids_prev:
           for batch in self.wo_id.batch_no_ids_prev:
               ids_cus.append(batch.order_id.id)
        else:
           if wo_line_id.parent_id:
              for batch in self.wo_id.parent_id.batch_no_ids_prev:
                  ids_cus.append(batch.order_id.id)
           else:
              ids_cus = [] 
        if wo_line_id.batch_ids:
#            rec.update({'batch_ids' :((6, 0, tuple([v.id for v in wo_line_id.batch_ids])),),'wo_id':wo_line_id.id})
            rec.update({'wo_id':wo_line_id.id,'default_previous_order_ids':[(6,0,ids_cus)],
            'default_previous_order_id':wo_line_id.batch_no_ids_prev[0].order_id.id if wo_line_id.batch_no_ids_prev else '',

            })

	return rec
    @api.multi


    @api.multi
    def issue_bulk_batches(self):
        if not self.batch_ids:
            raise UserError(_("There are no Batches to issue!"))
        if self.produce_qty==0.0:
            raise UserError(_("Please Input Proper Qty to Produce!"))
        if self.produce_qty>self.batch_ids[0].req_product_qty:
            raise UserError(_("Produce Qty cannot be greater then Required Qty of Batch!!"))

        res=[]
        print "len----------------",self.batch_ids.ids
        for each in self.batch_ids:
            machine_id=self.env['mrp.order.machine.produce'].search([('batch_id','=',each.id)])
            if not machine_id:
                vals=({'order_id':self.wo_id.id, 
                             'previous_order_id':self.wo_id.batch_no_ids_prev[0].order_id.id if self.wo_id.batch_no_ids_prev else '',
                           'batch_id':each.id,
                           'produced_qty':self.produce_qty,
                         'product_qty':(each.req_product_qty - each.product_qty) if each.req_product_qty > each.product_qty else 0.0,'uom_id':self.wo_id.wk_required_uom.id,'user_id':self.wo_id.user_ids.ids,
#                          'previous_order_ids':[(6,0,ids_cus)],
                            'supplier_batch':True if self.wo_id.process_type == 'raw' else False,
                            'raw_material':True if self.wo_id.raw_materials_id else False,
                           'product_id':self.wo_id.product.id, 'production_id':self.wo_id.production_id.id})
                machine_id=self.env['mrp.order.machine.produce'].create(vals)
                machine_id.confirmation()
                machine_id.orderProduceqty()
            else:
                machine_id.write({'produced_qty':self.produce_qty,'employee_ids':[(6,0,[self.employee_ids.ids])],'previous_batch_id':self.previous_batch_id.id,'supplier_btc_no':[(6,0,[self.supplier_btc_no.ids])]})
                machine_id.confirmation()
                machine_id.orderProduceqty()
        return res
    