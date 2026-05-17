from odoo import models, fields, api
from datetime import timedelta
import pytz


class AttendanceReportParser(models.AbstractModel):
    _name = 'report.biometric_attendance_sync.attendance_report_template'
    _description = 'Attendance Report Custom Logic'

    #
    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     employees = self.env['hr.employee'].browse(data.get('employee_ids'))
    #
    #     date_from = fields.Date.from_string(data.get('date_from'))
    #     date_to = fields.Date.from_string(data.get('date_to'))
    #
    #     result = []
    #
    #     for emp in employees:
    #         attendances = self.env['hr.attendance'].search([
    #             ('employee_id', '=', emp.id),
    #             ('check_in', '>=', data['date_from']),
    #             ('check_in', '<=', data['date_to']),
    #         ], order='check_in asc')
    #
    #         # 🔥 mapping حسب اليوم
    #         att_map = {}
    #         for att in attendances:
    #             day = fields.Date.to_string(fields.Datetime.to_datetime(att.check_in).date())
    #             att_map[day] = att
    #
    #         # 🔥 generate كل الأيام
    #         days = []
    #         current = date_from
    #         while current <= date_to:
    #             day_str = fields.Date.to_string(current)
    #
    #             days.append({
    #                 'date': day_str,
    #                 'attendance': att_map.get(day_str)
    #             })
    #
    #             current += timedelta(days=1)
    #
    #         result.append({
    #             'employee': emp,
    #             'days': days
    #         })
    #
    #     return {
    #         'docs': result,
    #         'date_from': data['date_from'],
    #         'date_to': data['date_to'],
    #     }
    #
    #

    @api.model
    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(data.get('employee_ids'))

        tz = pytz.timezone(self.env.user.tz or 'UTC')

        date_from = tz.localize(fields.Datetime.to_datetime(data.get('date_from')))
        date_to = tz.localize(fields.Datetime.to_datetime(data.get('date_to')))

        result = []

        for emp in employees:

            calendar = emp.resource_calendar_id
            if not calendar or not emp.resource_id:
                continue

            # ========================
            # Work Days
            # ========================
            work_intervals = calendar._work_intervals_batch(
                date_from,
                date_to,
                resources=emp.resource_id
            )[emp.resource_id.id]

            work_days = set(
                fields.Date.to_string(start.date())
                for start, _, _ in work_intervals
            )

            # ========================
            # Attendance
            # ========================
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', date_from),
                ('check_in', '<=', date_to),
            ])

            att_map = {
                fields.Date.to_string(att.check_in.date()): att
                for att in attendances
            }

            # ========================
            # Leaves
            # ========================
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', date_to.date()),
                ('request_date_to', '>=', date_from.date()),
            ])

            leave_map = {}

            for leave in leaves:
                current = leave.request_date_from
                while current <= leave.request_date_to:
                    day_str = fields.Date.to_string(current)

                    leave_map[day_str] = {
                        'type_id': leave.holiday_status_id.id,
                        'type_name': leave.holiday_status_id.name
                    }
                    current += timedelta(days=1)

            # ========================
            # Missions (NEW)
            # ========================
            missions = self.env['hr.permission'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'approved'),
                ('permission_type', '=', 'mission'),
                ('datetime_from', '<=', date_to),
                ('datetime_to', '>=', date_from),
            ])

            mission_map = {}

            for m in missions:
                current = m.datetime_from.date()
                end = m.datetime_to.date()

                while current <= end:
                    day_str = fields.Date.to_string(current)

                    mission_map[day_str] = {
                        'id': m.id,
                        'name': m.name,
                        'desc': m.mission_desc,
                        'from': m.datetime_from,
                        'to': m.datetime_to
                    }

                    current += timedelta(days=1)

            # ========================
            # Holidays
            # ========================
            holidays = self.env['resource.calendar.leaves'].search([
                ('calendar_id', '=', calendar.id),
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ])

            holiday_days = set()
            for h in holidays:
                current = h.date_from.date()
                while current <= h.date_to.date():
                    holiday_days.add(fields.Date.to_string(current))
                    current += timedelta(days=1)

            # ========================
            # Counters
            # ========================
            late_counter = 0
            early_counter = 0

            # Leave Types IDs
            paid_id = 1
            sick_id = 2
            early_id = 84
            late_id = 86
            urgent_id = 87
            died_id = 89

            # ========================
            # Days Loop
            # ========================
            days = []
            current = date_from.date()

            while current <= date_to.date():
                day_str = fields.Date.to_string(current)

                att = att_map.get(day_str)
                delay_order = None
                early_order = None

                # Counters
                if att:
                    if att.is_late:
                        late_counter += 1
                        delay_order = late_counter

                    if att.is_early:
                        early_counter += 1
                        early_order = early_counter

                # ========================
                # Status Logic (UPDATED)
                # ========================
                if day_str in holiday_days:
                    status = 'holiday'

                elif day_str not in work_days:
                    status = 'off'

                elif day_str in leave_map:
                    leave_info = leave_map[day_str]

                    if leave_info['type_id'] == paid_id:
                        status = 'paid_leave'
                    elif leave_info['type_id'] == sick_id:
                        status = 'sick_leave'
                    elif leave_info['type_id'] == early_id:
                        status = 'permission_early'
                    elif leave_info['type_id'] == late_id:
                        status = 'permission_late'
                    elif leave_info['type_id'] == urgent_id:
                        status = 'urgent_leave'
                    elif leave_info['type_id'] == died_id:
                        status = 'death_leave'
                    else:
                        status = 'leave'

                # ✅ NEW: mission قبل attendance
                elif day_str in mission_map:
                    status = 'mission'

                elif att:
                    status = 'present'

                else:
                    status = 'absent'

                # ========================
                # Append Day
                # ========================
                days.append({
                    'date': day_str,
                    'attendance': att,
                    'status': status,

                    'leave_type': leave_map.get(day_str, {}).get('type_name'),
                    'mission': mission_map.get(day_str),

                    'delay_order': delay_order,
                    'early_order': early_order,

                    'is_mission': status == 'mission',
                    'is_off': status == 'off',
                    'is_leave': 'leave' in status,
                    'is_holiday': status == 'holiday',
                    'is_absent': status == 'absent',
                })

                current += timedelta(days=1)

            result.append({
                'employee': emp,
                'days': days,
            })

        return {
            'docs': result,
            'date_from': data['date_from'],
            'date_to': data['date_to'],
        }

