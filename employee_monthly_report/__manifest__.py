{
    'name': 'Employee Monthly Report',
    'version': '1.0',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/month_report.xml',
        'wizard/details.xml',

        'report/details_report.xml',
        'report/report_monthly.xml',
        'report/report_action.xml',
    ],
    'installable': True,
}