# -*- coding: utf-8 -*-
from openerp import models, fields, api, _, modules
from openerp import http
from openerp.http import request
import base64
class PDFControl(http.Controller):

    @http.route(['/credit_profile_form/'], type='http', website=True)
    def credit_profile_form(self, stmt=None):
        pdf = modules.get_module_path('gt_order_mgnt') + "/credit_profile_pdf/credit_profile_pdf.pdf"
        f = open(pdf, 'rb')
        image_base64 = f.read()
        response = request.make_response(
            image_base64,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'attachment; filename=credit_profile_pdf.pdf;')
            ]
        )
        return response
    
#    @http.route(['/coldcalling_import_formate/'], type='http', website=True)
#    def credit_profile_form(self, stmt=None):
#        pdf = modules.get_module_path('gt_order_mgnt') + "/import_csv/coldcalling.csv"
#        f = open(pdf, 'rb')
#        image_base64 = f.read()
#        response = request.make_response(
#            image_base64,
#            headers=[
#                ('Content-Type', 'application/pdf'),
#                ('Content-Disposition', 'attachment; filename=credit_profile_pdf.pdf;')
#            ]
#        )
#        return response