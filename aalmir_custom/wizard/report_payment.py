# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from io import BytesIO,StringIO
import xlwt
import io
from base64 import b64decode
import base64
from openerp import http
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
from odoo.exceptions import ValidationError

class Binary(http.Controller):
 @http.route('/opt/download', type='http', auth="public")
 @serialize_exception
 def download_document(self,model,field,id,filename=None, **kw):
    """ Download link for files stored as binary fields.
    :param str model: name of the model to fetch the binary from
    :param str field: binary field
    :param str id: id of the record from which to fetch the binary
    :param str filename: field holding the file's name, if any
    :returns: :class:`werkzeug.wrappers.Response`
    """
    cr, uid, context = request.cr, request.uid, request.context
    env = api.Environment(cr, 1, {})  
    out_brw=env['output'].browse(int(id))
    filecontent = base64.b64decode(out_brw.xls_output or '')
    if not filecontent:
        return request.not_found()
    else:
       if not filename:
           filename = '%s_%s' % (model.replace('.', '_'), id)
       return request.make_response(filecontent,
                      [('Content-Type', 'application/octet-stream'),
                       ('Content-Disposition', content_disposition(filename))])


#class DailyPaymentReport(models.TransientModel):
#
#    _name = "payment.report"
#    _description = "Payment Report"
    
class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = "Payment Report"

    
    def print_excel_report(self):
        cr= self.env.cr
        workbook = xlwt.Workbook()
        pay_ids=self.env['account.payment'].search([('payment_date','=','2018-10-26')])
        style1 = xlwt.easyxf('pattern: pattern solid, fore_colour ice_blue;alignment: horiz centre;font: bold on; borders: left medium, top medium, bottom medium,right medium')
        style2 = xlwt.easyxf('pattern: pattern solid, fore_colour ivory;alignment: horiz centre;font: bold on; borders: left medium, top medium, bottom medium,right medium')
        Header_Text ='Payment Report'
        sheet = workbook.add_sheet('Payment Report')
#        sheet.row(0).height = 256 * 4
        sheet.col(0).width = 256 * 30
        sheet.col(1).width = 256 * 30
        sheet.col(2).width = 256 * 30
        sheet.col(3).width = 256 * 30
        sheet.col(4).width = 256 * 30
        sheet.col(5).width = 256 * 30
        sheet.write_merge(0, 0,0,5,'PAYMENT REPORT',style1)
        sheet.write_merge(1,2, 0,0,'PAYMENT ID',style1)
        sheet.write_merge(1,2, 1,1,'PARTNER ANME',style1)
        sheet.write_merge(1,2, 2,2,'AMOUNT',style1)
        sheet.write_merge(1,2, 3,3,'PAYMENT DATE',style1)
        sheet.write_merge(1,2, 4,4,'USERNAME',style1)
        sheet.write_merge(1,2, 5,5,'INVOICE STATUS',style1)
        sheet.write_merge(1,2, 6,6,'INVOICE AMOUNT',style1)
        sheet.write_merge(1,2, 7,7,'INVOICE DUEDATE',style1)
        sheet.write_merge(1,2, 8,8,'INVOICE REFERENCE',style1)
        sheet.write_merge(1,2, 9,9,'INVOICE ORIGIN',style1)
#        sheet.write(3,0,"",style1)
#        row=3
#        for inv_id in inv_ids:
##            sheet.write(row,0,inv_id.client_service_manager_id.name)
#            sheet.write(row,1,inv_id.branch_id.name)
#            sheet.write(row,2,inv_id.amount_total)
#            row+=1
        stream =BytesIO()
        workbook.save(stream)
        cr.execute(""" DELETE FROM output""")
        attach_id = self.env['output'].create({'name':Header_Text+'.xls', 'xls_output': base64.b64encode(stream.getvalue())})
        return {
             'type' : 'ir.actions.act_url',
             'url': '/opt/download?model=output&field=xls_output&id=%s&filename=Payment Report.xls'%(attach_id.id),
             'target': 'new',
            } 