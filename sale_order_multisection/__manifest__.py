{
    'name': 'Sale Order Multisection',
    'version': '14.0.0.0.0',
    'category': '',
    'description': u"""

""",
    'author': 'Serincloud',
    'depends': [
        'sale_management',
        'base_automation',

    ],
    'data': [
        #'data/crea_lineas_factura.xml',
        'views/sale_order_views.xml',
        'security/ir.model.access.csv',
        'data/automatic_actions.xml',
    ],
    'installable': True,
}