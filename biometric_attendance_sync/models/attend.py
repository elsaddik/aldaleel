from datetime import datetime, time
import pytz

from odoo import api, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model
    def auto_close_open_attendance(self):

        attendances = self.search([
            ('check_in', '!=', False),
            ('check_out', '=', False)
        ])

        for attendance in attendances:

            employee = attendance.employee_id

            calendar = employee.resource_calendar_id

            if not calendar:
                continue

            weekday = str(attendance.check_in.weekday())

            lines = calendar.attendance_ids.filtered(
                lambda l: l.dayofweek == weekday
            )

            if not lines:
                continue

            official_hour_to = max(lines.mapped('hour_to'))

            hour = int(official_hour_to)
            minute = int(round((official_hour_to % 1) * 60))

            tz = pytz.timezone(
                calendar.tz or 'Africa/Tripoli'
            )

            # تاريخ يوم الحضور بالتوقيت المحلي للجدول
            local_checkin_date = (
                pytz.UTC.localize(attendance.check_in)
                .astimezone(tz)
                .date()
            )
            print('local in', local_checkin_date)
            # وقت الانصراف الرسمي بالتوقيت المحلي
            local_checkout = tz.localize(
                datetime.combine(
                    local_checkin_date,
                    time(hour, minute)
                )
            )
            print('loc ccout',local_checkout)
            # تحويله إلى UTC مثل check_in
            official_checkout = (
                local_checkout
                .astimezone(pytz.UTC)
                .replace(tzinfo=None)
            )
            print('official',official_checkout)

            if attendance.check_in >= official_checkout:
                attendance.write({
                    'check_out': attendance.check_in
                })
            else:
                attendance.write({
                    'check_out': official_checkout
                })