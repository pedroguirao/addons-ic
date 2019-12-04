# Copyright 2019 Vicent Cubells - Ingeniería Cloud
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': "Sale Timesheet Logistic",
    'summary': "",
    'author': "Cubells",
    'license': 'AGPL-3',
    'website': "https://ingenieriacloud.com",
    'category': 'Generic',
    'version': '13.0.1.0.0',
    'depends': [
        'sale_timesheet',
        'project_enterprise',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_line_views.xml',
        'views/project_task_views.xml',
        'views/res_partner_views.xml',
        'wizards/create_route_views.xml',
        'wizards/merge_route_views.xml',
    ],
    'installable': True,
}
