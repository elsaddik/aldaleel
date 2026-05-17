from odoo import models, fields, api

import pytz
from collections import defaultdict
from datetime import timedelta


class AttendanceReportParser(models.AbstractModel):
    _name = 'report.biometric_attendance_sync.attendance_report_template'
    _description = 'Attendance Report Custom Logic'


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



    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     employees = self.env['hr.employee'].browse(data.get('employee_ids'))
    #     tz = pytz.timezone(self.env.user.tz or 'UTC')
    #
    #     date_from_naive = fields.Datetime.to_datetime(data.get('date_from'))
    #     date_to_naive = fields.Datetime.to_datetime(data.get('date_to'))
    #
    #     date_from = tz.localize(date_from_naive)
    #     date_to = tz.localize(date_to_naive)
    #
    #     result = []
    #
    #     for emp in employees:
    #
    #         calendar = emp.resource_calendar_id
    #         if not calendar or not emp.resource_id:
    #             continue
    #
    #         # ========================
    #         # Work Days
    #         # ========================
    #         # ========================
    #         # Work Days (WITHOUT intervals)
    #         # ========================
    #         work_days = set()
    #
    #         if calendar:
    #
    #             working_weekdays = set(int(att.dayofweek) for att in calendar.attendance_ids)
    #
    #             current = date_from.date()
    #             while current <= date_to.date():
    #
    #                 if current.weekday() in working_weekdays:
    #                     work_days.add(fields.Date.to_string(current))
    #
    #                 current += timedelta(days=1)
    #
    #         print("work_days", work_days)
    #
    #
    #         attendances = self.env['hr.attendance'].search([
    #             ('employee_id', '=', emp.id),
    #             ('check_in', '>=', date_from),
    #             ('check_in', '<=', date_to),
    #         ])
    #
    #         att_map = {
    #             fields.Date.to_string(att.check_in.date()): att
    #             for att in attendances
    #         }
    #
    #         # ========================
    #         # Leaves
    #         # ========================
    #         leaves = self.env['hr.leave'].search([
    #             ('employee_id', '=', emp.id),
    #             ('state', '=', 'validate'),
    #             ('request_date_from', '<=', date_to.date()),
    #             ('request_date_to', '>=', date_from.date()),
    #         ])
    #
    #         leave_map = {}
    #
    #         for leave in leaves:
    #             current = leave.request_date_from
    #             while current <= leave.request_date_to:
    #                 day_str = fields.Date.to_string(current)
    #
    #                 leave_map[day_str] = {
    #                     'type_id': leave.holiday_status_id.id,
    #                     'type_name': leave.holiday_status_id.name
    #                 }
    #                 current += timedelta(days=1)
    #
    #         # ========================
    #         # Missions (NEW)
    #         # ========================
    #         missions = self.env['hr.permission'].search([
    #             ('employee_id', '=', emp.id),
    #             ('state', '=', 'approved'),
    #             ('permission_type', '=', 'mission'),
    #             ('datetime_from', '<=', date_to),
    #             ('datetime_to', '>=', date_from),
    #         ])
    #
    #         mission_map = {}
    #
    #         for m in missions:
    #             current = m.datetime_from.date()
    #             end = m.datetime_to.date()
    #
    #             while current <= end:
    #                 day_str = fields.Date.to_string(current)
    #
    #                 mission_map[day_str] = {
    #                     'id': m.id,
    #                     'name': m.name,
    #                     'desc': m.mission_desc,
    #                     'from': m.datetime_from,
    #                     'to': m.datetime_to
    #                 }
    #
    #                 current += timedelta(days=1)
    #
    #         # ========================
    #         # Holidays
    #         # ========================
    #         holidays = self.env['resource.calendar.leaves'].search([
    #             # ('calendar_id', '=', calendar.id),
    #             ('date_from', '<=', date_to),
    #             ('date_to', '>=', date_from),
    #         ])
    #
    #         holiday_days = set()
    #         for h in holidays:
    #             current = h.date_from.date()
    #             while current <= h.date_to.date():
    #                 holiday_days.add(fields.Date.to_string(current))
    #                 current += timedelta(days=1)
    #
    #         # ========================
    #         # Counters
    #         # ========================
    #         late_counter = 0
    #         early_counter = 0
    #
    #         # Leave Types IDs
    #         paid_id = 1
    #         sick_id = 2
    #         early_id = 84
    #         late_id = 86
    #         urgent_id = 87
    #         died_id = 89
    #
    #         # ========================
    #         # Days Loop
    #         # ========================
    #         days = []
    #         current = date_from.date()
    #
    #         while current <= date_to.date():
    #             day_str = fields.Date.to_string(current)
    #
    #             att = att_map.get(day_str)
    #             delay_order = None
    #             early_order = None
    #
    #             # Counters
    #             if att:
    #                 if att.is_late:
    #                     late_counter += 1
    #                     delay_order = late_counter
    #
    #                 if att.is_early:
    #                     early_counter += 1
    #                     early_order = early_counter
    #
    #             # ========================
    #             # Status Logic (UPDATED)
    #             # ========================
    #             if day_str in holiday_days:
    #                 status = 'holiday'
    #
    #             elif day_str not in work_days:
    #                 # status = 'off'
    #                 continue
    #
    #             elif day_str in leave_map:
    #                 leave_info = leave_map[day_str]
    #
    #                 if leave_info['type_id'] == paid_id:
    #                     status = 'paid_leave'
    #                 elif leave_info['type_id'] == sick_id:
    #                     status = 'sick_leave'
    #                 elif leave_info['type_id'] == early_id:
    #                     status = 'permission_early'
    #                 elif leave_info['type_id'] == late_id:
    #                     status = 'permission_late'
    #                 elif leave_info['type_id'] == urgent_id:
    #                     status = 'urgent_leave'
    #                 elif leave_info['type_id'] == died_id:
    #                     status = 'death_leave'
    #                 else:
    #                     status = 'leave'
    #
    #             # ✅ NEW: mission قبل attendance
    #             elif day_str in mission_map:
    #                 status = 'mission'
    #
    #             elif att:
    #                 status = 'present'
    #
    #             else:
    #                 status = 'absent'
    #
    #             # ========================
    #             # Append Day
    #             # ========================
    #             days.append({
    #                 'date': day_str,
    #                 'attendance': att,
    #                 'status': status,
    #
    #                 'leave_type': leave_map.get(day_str, {}).get('type_name'),
    #                 'mission': mission_map.get(day_str),
    #
    #                 'delay_order': delay_order,
    #                 'early_order': early_order,
    #
    #                 'is_mission': status == 'mission',
    #                 # 'is_off': status == 'off',
    #                 'is_leave': 'leave' in status,
    #                 'is_holiday': status == 'holiday',
    #                 'is_absent': status == 'absent',
    #             })
    #
    #             current += timedelta(days=1)
    #
    #         result.append({
    #             'employee': emp,
    #             'days': days,
    #         })
    #
    #     return {
    #         'docs': result,
    #         'date_from': data['date_from'],
    #         'date_to': data['date_to'],
    #     }
    #

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #
    #     employees = self.env['hr.employee'].browse(data.get('employee_ids'))
    #
    #     # ✅ Naive datetime (IMPORTANT)
    #     date_from = fields.Datetime.to_datetime(data.get('date_from'))
    #     date_to = fields.Datetime.to_datetime(data.get('date_to'))
    #
    #     date_from_date = date_from.date()
    #     date_to_date = date_to.date()
    #
    #     # ======================================
    #     # 🔥 Prefetch all data (OPTIMIZED)
    #     # ======================================
    #
    #     attendances = self.env['hr.attendance'].search([
    #         ('employee_id', 'in', employees.ids),
    #         ('check_in', '>=', date_from),
    #         ('check_in', '<=', date_to),
    #     ])
    #
    #     leaves = self.env['hr.leave'].search([
    #         ('employee_id', 'in', employees.ids),
    #         ('state', '=', 'validate'),
    #         ('request_date_from', '<=', date_to_date),
    #         ('request_date_to', '>=', date_from_date),
    #     ])
    #
    #     missions = self.env['hr.permission'].search([
    #         ('employee_id', 'in', employees.ids),
    #         ('state', '=', 'approved'),
    #         ('permission_type', '=', 'mission'),
    #         ('datetime_from', '<=', date_to),
    #         ('datetime_to', '>=', date_from),
    #     ])
    #
    #     holidays = self.env['resource.calendar.leaves'].search([
    #         ('date_from', '<=', date_to),
    #         ('date_to', '>=', date_from),
    #     ])
    #
    #     # ======================================
    #     # 🔥 Build Maps
    #     # ======================================
    #
    #     att_map = {}
    #     for att in attendances:
    #         key = (att.employee_id.id, fields.Date.to_string(att.check_in.date()))
    #         att_map[key] = att
    #
    #     leave_map = defaultdict(dict)
    #     for leave in leaves:
    #         current = leave.request_date_from
    #         while current <= leave.request_date_to:
    #             day_str = fields.Date.to_string(current)
    #             leave_map[(leave.employee_id.id, day_str)] = {
    #                 'type_id': leave.holiday_status_id.id,
    #                 'type_name': leave.holiday_status_id.name
    #             }
    #             current += timedelta(days=1)
    #
    #     mission_map = defaultdict(dict)
    #     for m in missions:
    #         current = m.datetime_from.date()
    #         end = m.datetime_to.date()
    #
    #         while current <= end:
    #             day_str = fields.Date.to_string(current)
    #             mission_map[(m.employee_id.id, day_str)] = {
    #                 'id': m.id,
    #                 'name': m.name,
    #                 'desc': m.mission_desc,
    #                 'from': m.datetime_from,
    #                 'to': m.datetime_to
    #             }
    #             current += timedelta(days=1)
    #
    #     holiday_days = set()
    #     for h in holidays:
    #         current = h.date_from.date()
    #         while current <= h.date_to.date():
    #             holiday_days.add(fields.Date.to_string(current))
    #             current += timedelta(days=1)
    #
    #     # ======================================
    #     # 🔥 Result
    #     # ======================================
    #
    #     result = []
    #
    #     for emp in employees:
    #
    #         calendar = emp.resource_calendar_id
    #         if not calendar:
    #             continue
    #
    #         # ========================
    #         # Work days
    #         # ========================
    #         working_weekdays = set(int(att.dayofweek) for att in calendar.attendance_ids)
    #
    #         # Counters
    #         late_counter = 0
    #         early_counter = 0
    #
    #         # Leave Types
    #         paid_id = 1
    #         sick_id = 2
    #         early_id = 84
    #         late_id = 86
    #         urgent_id = 87
    #         died_id = 89
    #
    #         # ========================
    #         # Days loop
    #         # ========================
    #         days = []
    #         current = date_from_date
    #
    #         while current <= date_to_date:
    #             day_str = fields.Date.to_string(current)
    #
    #             # ✅ skip weekends
    #             if current.weekday() not in working_weekdays:
    #                 current += timedelta(days=1)
    #                 continue
    #
    #             att = att_map.get((emp.id, day_str))
    #             leave_info = leave_map.get((emp.id, day_str))
    #             mission = mission_map.get((emp.id, day_str))
    #
    #             delay_order = None
    #             early_order = None
    #
    #             if att:
    #                 if att.is_late:
    #                     late_counter += 1
    #                     delay_order = late_counter
    #
    #                 if att.is_early:
    #                     early_counter += 1
    #                     early_order = early_counter
    #
    #             # ========================
    #             # Status
    #             # ========================
    #             if day_str in holiday_days:
    #                 # status = 'holiday'
    #                 continue
    #
    #             elif leave_info:
    #                 if leave_info['type_id'] == paid_id:
    #                     status = 'paid_leave'
    #                 elif leave_info['type_id'] == sick_id:
    #                     status = 'sick_leave'
    #                 elif leave_info['type_id'] == early_id:
    #                     status = 'permission_early'
    #                 elif leave_info['type_id'] == late_id:
    #                     status = 'permission_late'
    #                 elif leave_info['type_id'] == urgent_id:
    #                     status = 'urgent_leave'
    #                 elif leave_info['type_id'] == died_id:
    #                     status = 'death_leave'
    #                 else:
    #                     status = 'leave'
    #
    #             elif mission:
    #                 status = 'mission'
    #
    #             elif att:
    #                 status = 'present'
    #
    #             else:
    #                 status = 'absent'
    #
    #             # ========================
    #             # Append
    #             # ========================
    #             days.append({
    #                 'date': day_str,
    #                 'attendance': att,
    #                 'status': status,
    #
    #                 'leave_type': leave_info.get('type_name') if leave_info else None,
    #                 'mission': mission,
    #
    #                 'delay_order': delay_order,
    #                 'early_order': early_order,
    #
    #                 'is_mission': status == 'mission',
    #                 'is_leave': 'leave' in status,
    #                 # 'is_holiday': status == 'holiday',
    #                 'is_absent': status == 'absent',
    #             })
    #
    #             current += timedelta(days=1)
    #
    #         result.append({
    #             'employee': emp,
    #             'days': days,
    #         })
    #
    #     return {
    #         'docs': result,
    #         'date_from': data['date_from'],
    #         'date_to': data['date_to'],
    #     }

    @api.model
    def _get_report_values(self, docids, data=None):

            employees = self.env['hr.employee'].browse(data.get('employee_ids'))

            # ✅ Naive datetime (IMPORTANT)
            date_from = fields.Datetime.to_datetime(data.get('date_from'))
            date_to = fields.Datetime.to_datetime(data.get('date_to'))

            date_from_date = date_from.date()
            date_to_date = date_to.date()

            # ======================================
            # 🔥 Prefetch (مرة واحدة فقط)
            # ======================================

            attendances = self.env['hr.attendance'].search([
                ('employee_id', 'in', employees.ids),
                ('check_in', '>=', date_from),
                ('check_in', '<=', date_to),
            ])

            leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate'),
                ('request_date_from', '<=', date_to_date),
                ('request_date_to', '>=', date_from_date),
            ])

            missions = self.env['hr.permission'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'approved'),
                ('permission_type', '=', 'mission'),
                ('datetime_from', '<=', date_to),
                ('datetime_to', '>=', date_from),
            ])

            holidays = self.env['resource.calendar.leaves'].search([
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ])

            # ======================================
            # 🔥 Maps (بدون تفريغ أيام)
            # ======================================

            # attendance
            att_map = {}
            for att in attendances:
                key = (att.employee_id.id, fields.Date.to_string(att.check_in.date()))
                att_map[key] = att

            # leaves (ranges)
            leave_map = defaultdict(list)
            for leave in leaves:
                leave_map[leave.employee_id.id].append(leave)

            # missions (ranges)
            mission_map = defaultdict(list)
            for m in missions:
                mission_map[m.employee_id.id].append(m)

            # holidays (ranges)
            holiday_ranges = [
                (h.date_from.date(), h.date_to.date())
                for h in holidays
            ]

            # ======================================
            # 🔥 Result
            # ======================================

            result = []

            for emp in employees:

                calendar = emp.resource_calendar_id
                if not calendar:
                    continue

                working_weekdays = set(int(att.dayofweek) for att in calendar.attendance_ids)

                late_counter = 0
                early_counter = 0

                # leave types
                paid_id = 1
                sick_id = 2
                early_id = 84
                late_id = 86
                urgent_id = 87
                died_id = 89

                days = []
                current = date_from_date

                while current <= date_to_date:

                    day_str = fields.Date.to_string(current)

                    # ✅ skip weekend
                    if current.weekday() not in working_weekdays:
                        current += timedelta(days=1)
                        continue

                    # ========================
                    # holiday check (سريع)
                    # ========================
                    if any(start <= current <= end for start, end in holiday_ranges):
                        current += timedelta(days=1)
                        continue

                    # ========================
                    # attendance
                    # ========================
                    att = att_map.get((emp.id, day_str))

                    delay_order = None
                    early_order = None

                    if att:
                        if att.is_late:
                            late_counter += 1
                            delay_order = late_counter

                        if att.is_early:
                            early_counter += 1
                            early_order = early_counter

                    # ========================
                    # leave check
                    # ========================
                    leave_info = None
                    for leave in leave_map.get(emp.id, []):
                        if leave.request_date_from <= current <= leave.request_date_to:
                            leave_info = {
                                'type_id': leave.holiday_status_id.id,
                                'type_name': leave.holiday_status_id.name
                            }
                            break

                    # ========================
                    # mission check
                    # ========================
                    mission = None
                    for m in mission_map.get(emp.id, []):
                        if m.datetime_from.date() <= current <= m.datetime_to.date():
                            mission = {
                                'id': m.id,
                                'name': m.name,
                                'desc': m.mission_desc,
                                'from': m.datetime_from,
                                'to': m.datetime_to
                            }
                            break

                    # ========================
                    # status
                    # ========================
                    if leave_info:
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

                    elif mission:
                        status = 'mission'

                    elif att:
                        status = 'present'

                    else:
                        status = 'absent'

                    # ========================
                    # append
                    # ========================
                    days.append({
                        'date': day_str,
                        'attendance': att,
                        'status': status,

                        'leave_type': leave_info.get('type_name') if leave_info else None,
                        'mission': mission,

                        'delay_order': delay_order,
                        'early_order': early_order,

                        'is_mission': status == 'mission',
                        'is_leave': 'leave' in status,
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


