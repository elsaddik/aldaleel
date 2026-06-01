{
    'name': 'HR Permission Pro',
    'version': '1.0',
    'category': 'HR',
    'summary': 'Late, Early Leave, and Missions Management',
    'depends': ['base','mail','hr', 'hr_attendance','hr_holidays','aldaleel_attendance_policy'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_permission_views.xml',
        'views/leaves.xml',
        'views/logistic.xml',
    ],
    'installable': True,
    'application': True,
}