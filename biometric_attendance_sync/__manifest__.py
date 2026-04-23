{
    'name': "biometric_attendance_sync",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_attendance'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/report_template.xml',
        'wizard/attend_report_action.xml',
        'wizard/attend_wizard.xml',
        'data/fetch_attend.xml',

    ],

}

