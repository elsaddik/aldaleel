from odoo import models,fields ,api
from datetime import timedelta

class AttendanceReportParser(models.AbstractModel):
    _name = 'report.biometric_attendance_sync.attendance_report_template'
    _description = 'Attendance Report Custom Logic'


    @api.model
    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(data.get('employee_ids'))

        date_from = fields.Date.from_string(data.get('date_from'))
        date_to = fields.Date.from_string(data.get('date_to'))

        result = []

        for emp in employees:
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', data['date_from']),
                ('check_in', '<=', data['date_to']),
            ], order='check_in asc')

            # 🔥 mapping حسب اليوم
            att_map = {}
            for att in attendances:
                day = fields.Date.to_string(fields.Datetime.to_datetime(att.check_in).date())
                att_map[day] = att

            # 🔥 generate كل الأيام
            days = []
            current = date_from
            while current <= date_to:
                day_str = fields.Date.to_string(current)

                days.append({
                    'date': day_str,
                    'attendance': att_map.get(day_str)
                })

                current += timedelta(days=1)

            result.append({
                'employee': emp,
                'days': days
            })

        return {
            'docs': result,
            'date_from': data['date_from'],
            'date_to': data['date_to'],
        }


    # @api.model
    # def _get_report_values(self, docids, data=None):
    #
    #     date_from = data.get('date_from')
    #     date_to = data.get('date_to')
    #     employee_ids = data.get('employee_ids')
    #
    #     employees = self.env['hr.employee'].browse(employee_ids)
    #
    #     docs = []
    #     print('employee_ids', employee_ids)
    #     for employee in employees:
    #         # جلب سجلات الحضور لهذا الموظف في الفترة المحددة
    #         attendances = self.env['hr.attendance'].search([
    #             ('employee_id', '=', employee.id),
    #             ('check_in', '>=', date_from),
    #             ('check_in', '<=', date_to)
    #         ], order='check_in asc')
    #
    #         if attendances:
    #             docs.append({
    #                 'employee': employee,
    #                 'attendances': attendances,
    #             })
    #
    #     return {
    #         'doc_ids': docids,
    #         'doc_model': 'hr.employee',
    #         'date_from': date_from,
    #         'date_to': date_to,
    #         'docs': docs,  # هذه هي الـ docs التي يدور حولها الـ foreach في الـ XML
    #     }