{
    'name': 'OCR transactions',
    'version': '12.0.10.0.4',
    'category': '',
    'description': u"""

""",
    'author': 'Serincloud',
    'depends': [
        'account',
        'contacts',
        'dbcopy_post_actions',
        'queue_job_cron',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/crea_lineas_factura.xml',
        'views/views.xml',
        'views/views_menu.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'data/ocr_queue_job.xml',
        'data/ocr_dbcopy_post_actions_job.xml',
        'data/dictionary_data.xml',
        'views/template.xml',
        'wizards/ocr_invoice_combination.xml',
    ],
    'installable': True,
}
