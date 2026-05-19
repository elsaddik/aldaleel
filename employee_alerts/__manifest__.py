{
    'name': 'Employee Alerts',
    'version': '1.0',
    'depends': ['hr', 'mail'],
    'author': 'Custom Dev',
    'category': 'Human Resources',
    'data': [
        'security/ir.model.access.csv',
        'views/employee_alert_views.xml',
    ],
    'installable': True,
    'application': True,
}