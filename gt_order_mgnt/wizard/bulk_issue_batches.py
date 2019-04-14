# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from datetime import datetime, date, time, timedelta




class AssignBatchNO(models.TransientModel):

    _name = "assign.batch.no"
    _description = "Batches Bulk Produce"

    supplier_btc_no=fields.Many2many('mrp.order.batch.number', string='Supplier Batch Number')
    @api.model
    def default_get(self,fields):
        rec = super(AssignBatchNO, self).default_get(fields)
        context = dict(self._context or {})
        if context.get('supplier_btc_no',False):
            rec.update({'supplier_btc_no':context.get('supplier_btc_no')})
        return rec
    
    @api.onchange('supplier_btc_no')
    def supp_ids_onchange(self):
        if self.supplier_btc_no:
            return {'domain': {'supplier_btc_no':[('id', 'in', self.supplier_btc_no.ids)]}}
    @api.multi
    def assign_batches_now(self):
        context = dict(self._context or {})
        if self.supplier_btc_no:
            context.update({'bacth_assigned_ids':self.supplier_btc_no.ids})
        form_id = self.env.ref('gt_order_mgnt.bulk_issue_batches_form_view')
        return {
                    'name':'Assign Supplier btach NO',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'issue.bulk.batches',
                    'views': [(form_id.id, 'form')],
                    'view_id': form_id.id,
                    'target': 'new',
                    'res_id': context.get('issue_id'),
                    'context':context

                    }


class IssueBulkBatches(models.TransientModel):

    _name = "issue.bulk.batches"
    _description = "Batches Bulk Produce"
    
    batch_ids=fields.Many2many('mrp.order.batch.number',string='Batch No.') 
    wo_id=fields.Many2one('mrp.production.workcenter.line',string='WO ID') 
    first_order=fields.Boolean(related='wo_id.first_order',store=True,string='First Wo') 
    previous_batch_id=fields.Many2one('mrp.order.batch.number',string='Previous Batch No.')
    previous_order_id=fields.Many2one('mrp.production.workcenter.line', string='Previous Work Order No.')

    previous_order_ids=fields.Many2many('mrp.production.workcenter.line', string='Previous Work Order No.')
    employee_ids=fields.Many2many('hr.employee', string='Operators Name')
    produce_qty=fields.Float('Produce Qty')
    supplier_batch_no=fields.Char('Supplier Batch No.')


    @api.onchange('batch_ids')
    def batch_ids_onchange(self):
        for record in self:
            if record.wo_id:
                batch_ids=self.env['mrp.order.batch.number'].search([('convert_product_qty','=',0.0),('order_id','=',record.wo_id.id),('production_id','=',record.wo_id.production_id.id)])
                ids_cus = [] 
                prev_batch = [] 
                if record.wo_id.batch_no_ids_prev:
                   for batch in record.wo_id.batch_no_ids_prev:
                       ids_cus.append(batch.order_id.id)
                else:
                   if record.wo_id.parent_id:
                      for batch in record.wo_id.parent_id.batch_no_ids_prev:
                          ids_cus.append(batch.order_id.id)
                   else:
                      ids_cus = [] 
                if record.wo_id.batch_no_ids_prev:
                    for each_rec in record.wo_id.batch_no_ids_prev:
                        if each_rec.remain_used_qty!=0.0:
                            prev_batch.append(each_rec.id)
#                
                if batch_ids:
                    return {'domain': {'previous_batch_id':[('id', 'in', prev_batch)],'previous_order_id':record.wo_id.batch_no_ids_prev[0].order_id.id if record.wo_id.batch_no_ids_prev else '','previous_order_ids':[('id', 'in', ids_cus)],'batch_ids': [('id', 'in', (batch_ids.ids))],'employee_ids':[('id', 'in', (record.wo_id.employee_ids.ids))]}}
                else:
                    return  {'domain': {'previous_batch_id':[('id', 'in', prev_batch)],'previous_order_id':record.wo_id.batch_no_ids_prev[0].order_id.id if record.wo_id.batch_no_ids_prev else '','previous_order_ids':[('id', 'in', ids_cus)],'batch_ids': [('id', 'in', False)],'employee_ids':[('id', 'in', (record.wo_id.employee_ids.ids))]}}



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
            rec.update({'supplier_btc_no':[(6,0,[batches[0]])]})
        ids_cus = [] 
        if wo_line_id.batch_no_ids_prev:
           for batch in wo_line_id.batch_no_ids_prev[0]:
               ids_cus.append(batch.order_id.id)
        else:
           if wo_line_id.parent_id:
              for batch in wo_line_id.parent_id.batch_no_ids_prev[0]:
                  ids_cus.append(batch.order_id.id)
           else:
              ids_cus = [] 
        if wo_line_id.employee_ids:
            rec.update({
            'employee_ids':[(6,0,[wo_line_id.employee_ids[0].id])],
            })
        prev_batch_id=False
        if wo_line_id.batch_no_ids_prev:
            for each_rec in wo_line_id.batch_no_ids_prev:
                if each_rec.remain_used_qty!=0.0:
                    prev_batch_id=each_rec.id
        rec.update({
            'previous_batch_id':prev_batch_id if prev_batch_id else False
            })       
        print "ids_cusids_cusids_cus",ids_cus
        if wo_line_id.batch_ids:
            rec.update({'wo_id':wo_line_id.id,'previous_order_ids':[(6,0,ids_cus)],
        'previous_order_id':wo_line_id.batch_no_ids_prev[0].order_id.id if wo_line_id.batch_no_ids_prev else '',

        })
        print "rec--------------------------",rec
	return rec


    @api.multi
    def assign_batch_no(self):
        if not self.batch_ids:
            raise UserError(_("There are no Batches selected!!!Please Select Batches First"))
        batches=[]
        context = self._context.copy()
        if self.wo_id.production_id:
            rm_ids=self.env['mrp.raw.material.request'].search([('production_id','=',self.wo_id.production_id.id)])
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
        if not batches:
            raise UserError(_("No Supplier Batch Number to Select!!"))

        context.update({'supplier_btc_no':[(6,0,batches)],'issue_id':self.id})	                                       
        assign_form = self.env.ref('gt_order_mgnt.assign_batch_no_form_view', False)
        if assign_form:
                return {
                    'name':'Assign Supplier btach NO',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'assign.batch.no',
                    'views': [(assign_form.id, 'form')],
                    'view_id': assign_form.id,
                    'target': 'new',
                    'context': context,
                    'domain' : {'supplier_btc_no':[('id', 'in', batches)]},

             }
    @api.multi
    def issue_bulk_batches(self):
        for record in self:
            context = self._context.copy()
            print "dsfdsfsdfds",context
            if not record.batch_ids:
                raise UserError(_("There are no Batches to issue!"))
            if record.produce_qty==0.0:
                raise UserError(_("Please Input Proper Qty to Produce!"))
            if record.produce_qty>record.batch_ids[0].req_product_qty:
                raise UserError(_("Produce Qty cannot be greater then Required Qty of Batch!!"))

            print "len----------------",record.batch_ids.ids
            body=''
            batch_numbers=''
            for each in record.batch_ids:
                machine_id=self.env['mrp.order.machine.produce'].search([('batch_id','=',each.id)])
                if not machine_id:
                    vals=({'order_id':record.wo_id.id, 
                               'batch_id':each.id,
                               'previous_batch_id':record.previous_batch_id.id,
                               'employee_ids':[(6,0,record.employee_ids.ids)],
                               'produced_qty':record.produce_qty,
                             'product_qty':(each.req_product_qty - each.product_qty) if each.req_product_qty > each.product_qty else 0.0,'uom_id':record.wo_id.wk_required_uom.id,'user_id':record.wo_id.user_ids.ids,
                                'supplier_batch':True if record.wo_id.process_type == 'raw' else False,
                                'raw_material':True if record.wo_id.raw_materials_id else False,
                               'product_id':record.wo_id.product.id, 'production_id':record.wo_id.production_id.id})
                    if record.previous_order_ids:
                        vals.update({'previous_order_ids':[(6,0,record.previous_order_ids.ids)]})
                    if record.previous_order_id:
                        vals.update({'previous_order_id':record.previous_order_id.id})
                    if context.get('bacth_assigned_ids',False):
                        vals.update({'supplier_btc_no':[(6,0,context.get('bacth_assigned_ids',False))]})
                    machine_id=self.env['mrp.order.machine.produce'].create(vals)
                    machine_id.confirmation()
                    machine_id.with_context({'bulk_issue':True}).orderProduceqty()
                else:
                    if self.previous_order_ids:
                        machine_id.write({'previous_order_ids':[(6,0,record.previous_order_ids.ids)]})
                    if self.previous_order_id:
                        machine_id.write({'previous_order_id':record.previous_order_id.id})
                    if context.get('bacth_assigned_ids',False):
                        vals.update({'supplier_btc_no':[(6,0,context.get('bacth_assigned_ids',False))]})
                    machine_id.write({'produced_qty':record.produce_qty,'employee_ids':[(6,0,[record.employee_ids.ids])],'previous_batch_id':record.previous_batch_id.id})
                    machine_id.confirmation()
                    machine_id.orderProduceqty()
                batch_numbers += str(each.name) +' '

            body='<b>Product Produced In Work Order:</b>'
     #               body +='<ul><li> Produced Qty    : '+str(record.product_qty) +'</li></ul>'
            body +='<ul><li> Produced Qty    : '+str(machine_id.produced_qty) +'</li></ul>'
            body +='<ul><li> Production No. : '+str(machine_id.production_id.name) +'</li></ul>'
            body +='<ul><li> Work Order No.  : '+str(machine_id.order_id.name) +'</li></ul>'
            body +='<ul><li> Batch Numbers   : '+batch_numbers +'</li></ul>'
            body +='<ul><li> User Name      : '+str(self.create_uid.name) +'</li></ul>' 
            body +='<ul><li> Produced Time   : '+str(datetime.now() + timedelta(hours=4)) +'</li></ul>' 
            if body:
               record.wo_id.message_post(body=body)
               record.wo_id.production_id.message_post(body=body)
        return True
    
