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
    'name': 'API Next Activity Reminder',
    'version': '1.0',
    'category': 'notification',
    'sequence': 1002,
    'summary': 'Popup notification',
    'description': '''
    Send Email and Popuo notification for Next Activity task,call and email
''',
    'author': 'Aalmir Plastic Industries',
    'website': 'http://www.aalmirplastic.com',
    'depends': ['gt_aalmir_coldcalling','calendar'],
    'data': [
        'view/crm_lead_view.xml',
        'view/calendar_view.xml',
    ],
    'qweb': [
        'view/sales_team_dashboard.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
