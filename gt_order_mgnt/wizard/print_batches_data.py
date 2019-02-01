# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class PrintBatchesData(models.TransientModel):

    _name = "print.batches.data"
    _description = "Batches Data Print"
    
    batch_ids=fields.Many2many('mrp.order.batch.number',string='Batch No.') 
    wo_id=fields.Many2one('mrp.production.workcenter.line',string='WO ID') 
    
    @api.onchange('batch_ids')
    def batch_ids_onchange(self):
        for record in self:
            if record.wo_id:
                return {'domain': {'batch_ids': [('id', 'in', (record.wo_id.batch_ids.ids))]}}



    @api.model
    def default_get(self,fields):
        rec = super(PrintBatchesData, self).default_get(fields)

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        wo_line_id = self.env['mrp.production.workcenter.line'].browse(active_ids)
        print "wo_line_idwo_line_idwo_line_id",wo_line_id
        if wo_line_id.batch_ids:
#            rec.update({'batch_ids' :((6, 0, tuple([v.id for v in wo_line_id.batch_ids])),),'wo_id':wo_line_id.id})
            rec.update({'wo_id':wo_line_id.id})

	return rec
    @api.multi
    
    def select_unselect_all(self):
        for record in self:
            if record.batch_ids:
                if any(batch.print_bool == True for batch in record.batch_ids):
                    for rec in record.batch_ids:
                      rec.print_bool=False
                else:
                    for rec in record.batch_ids:
                        rec.print_bool=True
        return {  "type": "ir.actions.do_nothing",}


    @api.multi
    def print_detailed_batches(self):
        res=[]
        print "len----------------",self.batch_ids.ids
        for each in self.wo_id.batch_ids:
            if each.id not in self.batch_ids.ids:
                each.write({'print_bool':False})
        for line in self.batch_ids:
            print "line----------------------",line
            line.write({'print_bool':True})
            if line.print_bool==True:
                res= self.env['report'].get_action(self, 'gt_order_mgnt.production_batch_details_print_wo')
        return res
    
    @api.multi
    def print_normal_batches(self):
        res=[]
        for each in self.wo_id.batch_ids:
            if each.id not in self.batch_ids.ids:
                each.write({'print_bool':False})
        for line in self.batch_ids:
            line.print_bool=True

            if line.print_bool==True:
                res=self.env['report'].get_action(self, 'gt_order_mgnt.report_workorder_batch_number_barcode')
        return res
