# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'API-Logo',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 1012,
    'author': 'Aalmir Plastic Industries',
    'summary': 'Change odoo logo and text',
    'description': "",
    'website': 'http://aalmir.com/',
    
    'depends': [
        'web',
        'web_settings_dashboard',
        'web_planner',
        ],
    'data': [
        'view/res_config_view.xml',
        'view/ir_config_parameter.xml',
        'view/webclient_templates.xml',
        ],
    'demo': [
        ],
    'test': [
        'test/crm_access_group_users.yml',
        'test/crm_lead_message.yml',
        ],
    'css': ['static/src/css/crm.css'],
    
    'qweb': ['static/src/xml/*.xml',
            ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


