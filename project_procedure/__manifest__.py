{
    'name': 'Procedures',
    'version': '12.0.0.1',
    'category': 'Projects',
    'description': u"""

""",
    'author': 'Serincloud',
    'depends': [
        'project_stage_closed',
        'project_task_dependency',
        'hr',
        'base_automation',
    ],
    'data': [
        'views/views.xml',
        'views/views_menu.xml',
        'security/ir.model.access.csv',
        'views/project_view.xml',
        'data/actions.xml'
    ],
    'installable':True,
}
