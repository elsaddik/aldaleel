{
    'name': 'HR Permission Pro',
    'version': '1.0',
    'category': 'HR',
    'summary': 'Late, Early Leave, and Missions Management',
    'depends': ['base','hr', 'hr_attendance','hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_permission_views.xml',
        'views/leaves.xml',
    ],
    'installable': True,
    'application': True,
}