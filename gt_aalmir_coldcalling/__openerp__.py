# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'API ColdCalling Module',
    'version': '1.0',
    'category': 'Sales Management',
    'sequence': 1001,
    'author': 'Aalmir Plastic Industries',
    'summary': 'Manage prelead information using coldcalling',
    'description': """
    """,
    'website': 'http://www.aalmir_plastic.com/',
    'depends': ['base','web','sale_crm', 'sale_stock', 'calendar', 'mail'],
    'data': [
#            'data/crm_action_data.xml',
            'security/crm_security.xml',
            'security/ir.model.access.csv',
            'wizard/crm_lead_to_opportunity_view.xml',
            'wizard/crm_lead_lost_view.xml',
            'wizard/mail_compose_message_view.xml',
            'wizard/import_coldcalling_list_view.xml',
            'wizard/assign_to_other_salesman_view.xml',
            'views/cold_calliing_view.xml',
            'views/crm_lead_view.xml',
            'views/calendar_view.xml',
            'views/contact_interval_mail.xml',
#            'views/form_view_extention.xml'
            'views/asset.xml',			# #CH_N038 add file to make many2one clickble
	    'views/utm_campaign_view.xml', #CH_N045 add file for utm campaign
            'data/ir_config_parameter.xml',
     ],
    'qweb': [
        "static/src/xml/chatter.xml",
        'static/src/xml/web_tree_dynamic_colored_field.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
