 # -*- coding: utf-8 -*-
##############################################################################
#
#
#    Copyright (C) 2013-Today(www.aalmirplastic.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'API Gmail Integration',
    'version': '1.0',
    'category': 'Mail',
    'sequence': 1004,
    'summary': 'Lead From Gmail',
    'description': '''
        Using This Module we can Fetch Lead data from Gmail, Integrate Gmail with Odoo CRM
    ''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://aalmir_plastic.com/',
    'depends': ['crm','fetchmail','tko_mail_smtp_per_user'],
    'data': [
        'fetchmail_data.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
