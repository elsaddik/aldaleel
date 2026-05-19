{
    'name': 'Employee Monthly Report',
    'version': '1.0',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/employee.xml',
        'wizard/report_monthly.xml',
        'wizard/report_action.xml',
    ],
    'installable': True,
}