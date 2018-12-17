# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models, _
from datetime import datetime, date, timedelta
from openerp.exceptions import UserError, ValidationError
from openerp import tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta

class resCompany(models.Model):
    _inherit = 'res.company'
	
    @api.multi
    def price_update_products(self):
        so_ids_cancelled=self.env['purchase.order'].search([('state','=','done')])

        po_ids_cancelled=self.env['purchase.order'].search([('state','=','cancel')])
        if po_ids_cancelled:
            print "po_ids_cancelledpo_ids_cancelledpo_ids_cancelled",po_ids_cancelled
            for each_po in po_ids_cancelled:
                if each_po.order_line[0].invoice_lines and each_po.order_line[0].invoice_lines.invoice_id.state!='cancel':
                    print "each_po.order_line[0].invoice_lines.invoice_id",each_po.order_line[0].invoice_lines.invoice_id
                    each_po.order_line[0].invoice_lines.invoice_id.signal_workflow('invoice_cancel')
            return True
#        exp_ids=self.env['hr.expense'].search([('state','=','done'),('expense_type','=','emp_expense')])
#        for each_exp in exp_ids:
#            for each_je in each_exp.account_move_id:
#                for each_move_line in each_je.line_ids:
#                    if not each_move_line.partner_id:
#                        each_move_line.write({'partner_id':each_exp.employee_id.address_home_id.commercial_partner_id.id})
#        warehouse_place_product_ids=self.env['n.warehouse.placed.product'].search([])
##        warehouse_place_product_ids=self.env['n.warehouse.placed.product'].browse(1)
#        for each_wh in warehouse_place_product_ids:
#            count_multi_line=0
#            for each_line in each_wh.multi_product_ids:
#                print "each_lineeach_line product",each_line.product_id.name,each_line.product_id.default_code
#                count_multi_line+=1
#                coutn_in_lines=0
#                approve_qty=0.0
#                for each_multi in each_line.multi_product_ids:
#                    coutn_in_lines+=1
#                    approve_qty+=each_multi.approve_qty
#                print "approve_qtyapprove_qty",approve_qty
#                print "coutn_in_linescoutn_in_lines",coutn_in_lines
#                each_line.write({'total_quantity':approve_qty})
#                if approve_qty==0.0:
#                    each_line.unlink()
#            print "count_multi_linecount_multi_line",count_multi_line
#        pay_ids=self.env['account.payment'].search([])
#        for res in pay_ids:
#            if res.payment_method=='cheque':
#                for each_cheque in res.cheque_details:
#                    each_cheque._onchange_amount()
#        return True
#        pay_ids=self.env['account.payment'].search([])
#        for res in pay_ids:
#            if res.payment_method=='cheque':
#                for each_cheque in res.cheque_details:
#                    each_cheque._onchange_amount()
#        return True
#        pay_ids=self.env['account.payment'].search([])
#        for res in pay_ids:
#            if res.invoice_ids:
#                for each_inv in res.invoice_ids:
#                    bill_line_vals,pick_ids,vals=[],[],{}
#
#                    if each_inv.picking_ids:
#                        for each_pick in each_inv.picking_ids:
#                            pick_ids.append(each_pick.id)
#                        vals={'receiving_id':[(4, pick_ids)]}
#                    vals.update({'bill_id':each_inv.id,'payterm_id':each_inv.payment_term_id.id})
#                    bill_line_vals.append((0,0,vals))
#                    bill_line=res.write({'bill_line':bill_line_vals})
#                    print "bill_linebill_linebill_line",bill_line
#        all_mat=self.env['raw.material.pricelist'].search([])
#        for each in all_mat:
#            each.write({'qty_range_8':each.qty_range_3,'qty_range_9':each.qty_range_3})
#        return True
#        all_banks = self.env['res.partner.bank'].search([])
#        for each_bank in all_banks:
#            if each_bank.bank_id:
#                if each_bank.bank_id.bic:
#                    each_bank.write({'swift_code':each_bank.bank_id.bic})
#        return True
        all_prods = self.env['product.template'].search([])
        for each in all_prods:
            product_id=self.env['product.product'].search([('product_tmpl_id','=',each.id)],limit=1)
            if product_id:
                sol_id=self.env['sale.order.line'].search([('price_unit','>',0.0),('product_id','=',product_id.id),('order_id.state', 'in', ('sale','done'))],order='id desc',limit=1)
                if not sol_id:
                    pol_id=self.env['purchase.order.line'].search([('product_id','=',product_id.id),('price_unit','>',0.0),('order_id.state','in',('to approve','sent po','purchase','done'))],order='id desc',limit=1)
                    print "pol_idpol_idpol_idpol_id",pol_id
                    if not pol_id:
#                        if not sol and pol the chekc pricelist
                        pricelist_id=self.env['customer.product'].search([('product_id','=',product_id.id),('avg_price','>',0.0)],order='id desc',limit=1)
                        print "no sol no pol so fould pricelist---------------------",pricelist_id
                        if not pricelist_id:
                            each.write({'list_price':0.0,'standard_price':0.0})
                        else:
                            if pricelist_id.currency_id.id!=self.currency_id.id:
                                from_currency = pricelist_id.currency_id
                                to_currency = self.currency_id
                                price_con = from_currency.compute(pricelist_id.avg_price, to_currency, round=False)
                                print "price price_con afre conversion=============",price_con
                                each.write({'list_price':price_con,'standard_price':price_con})
                            else:
                                each.write({'list_price':pricelist_id.avg_price,'standard_price':pricelist_id.avg_price})
                    else:
#                        convertng price first to kg if the uom is MT
                        if pol_id.product_uom.name=='MT':
                            print "yes the uom is MT----------------"
                            price_pol=pol_id.price_unit/1000
                        else:
                            price_pol=pol_id.price_unit
                        print "price_polprice_pol",price_pol
                        if pol_id.order_id.currency_id.id!=self.currency_id.id:
                            print "currency not equalll-----------------",pol_id.order_id,pol_id.order_id.currency_id.name,self.currency_id.name
                            from_currency = pol_id.order_id.currency_id
                            to_currency = self.currency_id
                            price_pol = from_currency.compute(price_pol, to_currency, round=False)
                            print "price pol afre conversion=============",price_pol
                        each.write({'list_price':price_pol,'standard_price':price_pol})
                else:
                    print "sol_idsol_idsol_idsol_id",sol_id
#                        convertng price first to kg if the uom is MT
                    if sol_id.product_uom.name=='MT':
                        price_sol=sol_id.price_unit/1000
                    else:
                        price_sol=sol_id.price_unit
                    print "price_solprice_solprice_sol",price_sol
                    if sol_id.p_currency_id.id!=self.currency_id.id:
                        from_currency = sol_id.p_currency_id
                        to_currency = self.currency_id
                        price_sol = from_currency.compute(price_sol, to_currency, round=False)
                    each.write({'list_price':price_sol,'standard_price':price_sol})
        return True
    
