{
    'name': 'aldaleel Attendance Policy',
    'version': '1.0',
    'author': 'abd elsadek',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_payroll',
        'hr_payroll_account',

    ],
    'data': [
        'security/security.xml',  # 1. عرف المجموعات أولاً
        'security/ir.model.access.csv',  # 2. أعطِ الصلاحيات للمجموعات
        'views/attendance_policy_views.xml',
        'views/attendance_penalty_views.xml',
        'views/hr.xml',
        'views/payslip.xml',
        'views/menu.xml',

        'data/cron.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'aldaleel_attendance_policy/static/src/**/*']
    },

    'installable': True
}
