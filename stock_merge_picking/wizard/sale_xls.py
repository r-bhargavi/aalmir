from openerp.addons.stock_merge_picking.wizard.report_xlsx import ReportXlsx
import datetime
from datetime import datetime, date, time, timedelta

class SaleReportXls(ReportXlsx):

    def get_lines(self, data):
        lines = []
        sale_history=False
        if data['form'].get('id',False):
           sale_history=self.env['product.report'].search([('id','=',data['form'].get('id',False))])
        for obj in sale_history.product_line:
            print ".....",obj.product_id
            vals = {
                  'sale_id':obj.sale_id.name,
                  'product_id':'['+str(obj.product_id.default_code)+']'+str(obj.product_id.name),
                  'unit':obj.product_uom.name,
                  'unit_price':obj.price_unit,
                  'date':obj.order_date,
                  'lpo_number':obj.lpo_number,
                  'do_number':',\n'.join([x.name for x in obj.delivery_ids]),
                  'order_amount':obj.sale_id.amount_total,
                  'currency':obj.sale_id.report_currency_id.name,
                  'qty_ordered':obj.qty_ordered,
                  'qty_delivered':obj.qty_delivered,
                  'qty_remaining':obj.qty_remaining,
                  'qty_invoiced':obj.qty_invoiced,
                  
            }
            lines.append(vals)
        return lines

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'right': True, 'left': True, 'bottom': True, 'top': True, 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        font_size_8 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8})
        red_mark = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8,
                                        'bg_color': 'red'})
        justify = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 12})
        partner_id=self.env['res.partner'].search([('id','=',data['form'].get('partner_id', False))]) 
        format3.set_align('center')
        font_size_8.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')
        p_col_no1 =7
        sheet.set_column('L:L',10)
        sheet.set_column('M:P',15)
        sheet.merge_range('A3:G3', 'Report Date: ' + str(datetime.now().date() + timedelta(hours=4)), format1)
        sheet.merge_range('H3:M3', 'Filter By: ' + str(data['form'].get('filter_option', False)), format1)
        sheet.merge_range('A4:M4', 'Customer Name:'+str(partner_id.name), format11)
        sheet.write(4, 0, 'Order Date', format21)
        sheet.merge_range(4, 1, 4, 3, 'Product Name ', format21)
        sheet.merge_range(4, 4, 4, 5, 'Sale Order No.', format21)
        sheet.merge_range(4, 6, 4, 7, 'Delivery No.', format21)
        sheet.write('I5','LPO No', format21)
        sheet.merge_range('J5:K5', 'Order Amount', format21)
        sheet.write('L5', 'Currency', format21)
        sheet.write('M5', 'Ordered Qty ', format21)
        sheet.write('N5', 'Delievered Qty ', format21)
        sheet.write('O5', 'Remaining Qty', format21)
        sheet.write('P5', 'Invoiced Qty', format21)
        sheet.write('Q5', 'Unit ', format21)
        sheet.write('R5', 'Unit Price', format21)
        prod_row = 5  
        prod_col = 0
        get_line = self. get_lines(data)
        for each in get_line:
            sheet.write(prod_row, prod_col, each['date'], font_size_8)
            sheet.merge_range(prod_row, prod_col + 1, prod_row, prod_col + 3, each['product_id'], font_size_8)
            sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['sale_id'], font_size_8)
            sheet.merge_range(prod_row, prod_col + 6, prod_row, prod_col + 7, each['do_number'], font_size_8)
            sheet.write(prod_row, prod_col + 8, each['lpo_number'], font_size_8)
            sheet.merge_range(prod_row, prod_col + 9, prod_row, prod_col + 10, each['order_amount'], font_size_8)
            sheet.write(prod_row,prod_col + 11,each['currency'], font_size_8)
            sheet.write(prod_row, prod_col + 12, each['qty_ordered'], font_size_8)
            sheet.write(prod_row, prod_col + 13, each['qty_delivered'] , font_size_8)
            sheet.write(prod_row, prod_col + 14, each['qty_remaining'], font_size_8)
            sheet.write(prod_row, prod_col + 15, each['qty_invoiced'], font_size_8)
            sheet.write(prod_row, prod_col + 16, each['unit'], font_size_8)
            sheet.write(prod_row, prod_col + 17, each['unit_price'], font_size_8)
            prod_row = prod_row + 1
        
SaleReportXls('report.export_sale_xls.sale_report_xls.xlsx', 'sale.order.line')

class InvocieReportXls(ReportXlsx):

    def get_invoice_lines(self, data):
        lines = []
        invoice_history=False
        all_partner_ids = []
        if data['form'].get('partner_id', False):
           partners=data['form'].get('partner_id', False)
           all_partner_ids.append(partners)
        domain=[('type','in',('out_invoice', 'out_refund'))]
        if data.get('form', False) and data['form'].get('lpo_id_inv', False):
        	domain += [('document_id','in',tuple(data['form'].get('lpo_id_inv', False)))]
        if data.get('form', False) and data['form'].get('date_to', False) and data['form'].get('date_from', False):
           domain +=[('date_invoice','<=',data['form'].get('date_to', False)),('date_invoice','>=',data['form'].get('date_from', False))]
        if data['form'].get('partner_id', False) and data['form'].get('filter_by', False) =='customer': 
           domain +=['|',('partner_id.parent_id','in',all_partner_ids),('partner_id','in',all_partner_ids)]
          
        if data['form'].get('filter_by',False) == 'submission':
           domain +=['|',('partner_id.parent_id','in',all_partner_ids),('partner_id','in',all_partner_ids)]
           if data['form'].get('invoice_status',False) != 'all':
              domain +=[('state','=',data['form'].get('invoice_status',False))]
           else:
              domain +=[('state','in',('draft','open','paid'))]
              
        invoice_history = self.env['account.invoice'].search(domain)
        for obj in invoice_history:
            invoice = obj
            lpo_number=''            
            if obj.document_id:
            	lpo_number = ','.join([ str(doc.lpo_number) for doc in obj.document_id ])
            else:
            	lpo_number = obj.sale_id.sale_lpo_number
            	
            vals = {
                'Customer': invoice.partner_id.name,
                'Invoice Date':invoice.date_invoice,
                'number':invoice.number,
                'salesperson':invoice.user_id.name,
                'due date':invoice.date_due,
                'sale':invoice.origin, 
                'total':invoice.amount_total_signed,
                'due':invoice.residual_signed,
                'currency':invoice.currency_id.name,
                'state':invoice.state,
                'LPO': lpo_number,
                'do_numbers':',\n'.join([ str(doc.name) for doc in obj.picking_ids]),
            }
            lines.append(vals)
            lpo_number=''
        return lines

    def generate_xlsx_invoice_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format({'font_size': 14, 'bottom': True, 'right': True, 'left': True, 'top': True, 'align': 'vcenter', 'bold': True})
        format11 = workbook.add_format({'font_size': 12, 'align': 'center', 'right': True, 'left': True, 'bottom': True, 'top': True, 'bold': True})
        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        format3 = workbook.add_format({'bottom': True, 'top': True, 'font_size': 12})
        font_size_8 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8})
        red_mark = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 8,
                                        'bg_color': 'red'})
        justify = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'font_size': 12})
        format3.set_align('center')
        font_size_8.set_align('center')
        justify.set_align('justify')
        format1.set_align('center')
        red_mark.set_align('center')
        p_col_no1 =7
        sheet.set_column('G:H',10)
        sheet.set_column('M:Q',10)
        sheet.merge_range('A3:G3', 'Report Date: ' + str(datetime.now().date() + timedelta(hours=4)), format1)
        sheet.merge_range('H3:M3', 'Filter By: ' + str(data['form'].get('filter_by', False)), format1)
        sheet.merge_range('A4:G4', 'Invoice Information', format11)
        sheet.write(4, 0, 'Invoice Date', format21)
        sheet.merge_range(4, 1, 4, 3, 'Customer Name', format21)
        sheet.merge_range(4, 4, 4, 5, 'Invoice No.', format21)
        sheet.write('G5', 'LPO No.', format21)
        sheet.write('H5', 'Delivery No.', format21)
        sheet.merge_range('I5:J5', 'Salesperson.', format21)
        sheet.merge_range('K5:L5', 'Sale order', format21)
        sheet.write('M5', 'Payment Due Date ', format21)
        sheet.write('NP5', 'Total Amount', format21)
        sheet.write('O5', 'Due  Amount', format21)
        sheet.write('P5', 'Currency', format21)
        sheet.write('Q5', 'Status', format21)
        prod_row = 5  
        prod_col = 0
        get_line = self.get_invoice_lines(data)
        for each in get_line:
                sheet.write(prod_row, prod_col, each['Invoice Date'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 1, prod_row, prod_col + 3, each['Customer'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 4, prod_row, prod_col + 5, each['number'], font_size_8)
                sheet.write(prod_row, prod_col + 6, each['LPO'], font_size_8)
                sheet.write(prod_row, prod_col + 7, each['do_numbers'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 8, prod_row, prod_col + 9, each['salesperson'], font_size_8)
                sheet.merge_range(prod_row, prod_col + 10, prod_row, prod_col + 11,each['sale'], font_size_8)
                sheet.write(prod_row, prod_col + 12, each['due date'],font_size_8)
                sheet.write(prod_row, prod_col + 13, each['total'], font_size_8)
                sheet.write(prod_row, prod_col + 14, each['due'], font_size_8)
                sheet.write(prod_row, prod_col + 15, each['currency'], font_size_8)
                sheet.write(prod_row, prod_col + 16, each['state'], font_size_8)
                prod_row = prod_row + 1
        
InvocieReportXls('report.export_invoice_xls.invoice_report_xls.xlsx', 'account.invoice')

