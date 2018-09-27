
import openerp
import openerp.modules.registry
import ast

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import Home

import datetime
import pytz

#----------------------------------------------------------
# OpenERP Web web Controllers
#----------------------------------------------------------
class Home(Home):

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        cr = request.cr
        uid = openerp.SUPERUSER_ID
        param_obj = request.registry.get('ir.config_parameter')
        request.params['disable_footer'] = ast.literal_eval(param_obj.get_param(cr, uid, 'login_form_disable_footer')) or False
        request.params['disable_database_manager'] = ast.literal_eval(param_obj.get_param(cr, uid, 'login_form_disable_database_manager')) or False
        request.params['background_src'] = param_obj.get_param(cr, uid, 'login_form_background_night') or ''
        return super(Home, self).web_login(redirect, **kw)
      

