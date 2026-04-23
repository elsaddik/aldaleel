{
    'name': 'Payroll Cheque Batch',
    'version': '1.0',
    'depends': ['hr_payroll', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/cheque_batch_views.xml',
        'report/cheque_batch_report.xml',
    ],
    'installable': True
}
