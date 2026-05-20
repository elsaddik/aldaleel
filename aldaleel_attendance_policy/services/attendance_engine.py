from datetime import datetime, timedelta
import calendar
import pytz
from odoo import fields
import logging

_logger = logging.getLogger(__name__)
class AttendanceEngine:

    def __init__(self, env):
        self.env = env
        self.policy = env['bank.attendance.policy'].search([], limit=1)

    def to_minutes(self, dt):

        return dt.hour * 60 + dt.minute

    def compute_period(self):
        today = fields.Date.today()

        # بداية الشهر
        start = today.replace(day=1)

        # آخر يوم في الشهر
        last_day = calendar.monthrange(today.year, today.month)[1]
        period_end = today.replace(day=last_day)

        return start, period_end

    def analyze_employee(self, employee):
        start, end = self.compute_period()


        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start),
            ('check_in', '<=', end),


        ])

        late = 0
        absence = 0
        early_leave = 0
        late_hour = 0
        early_hour = 0


        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('date_from', '<=', end),
            ('date_to', '>=', start),

        ])
        public_holiday_dates = set()
        for h in public_holidays:
            current = h.date_from.date()
            while current <= h.date_to.date():
                public_holiday_dates.add(current)
                current += timedelta(days=1)



        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('request_date_from', '<=', end),
            ('request_date_to', '>=', start),
            ('state', '=', 'validate')
        ])

        leave_dates = set()
        for lv in leaves:
            d = lv.request_date_from
            while d <= lv.request_date_to:
                leave_dates.add(d)
                d += timedelta(days=1)

        # الأيام اللي فيها حضور
        attended_days = set(att.check_in.date() for att in attendances if att.check_in)
        print(attended_days)

        missions = self.env['hr.permission'].search([
            ('employee_id', '=', employee.id),
            ('permission_type', '=', 'mission'),
            ('state', '=', 'approved')
        ])

        mission_dates = set(
            att.check_in.date()
            for att in attendances
            if att.check_in and any(m.date == att.check_in.date() for m in missions)
        )
        calendar_id = employee.resource_calendar_id


        if calendar_id and calendar_id.attendance_ids:
            working_days = set(int(att.dayofweek) for att in calendar_id.attendance_ids)
            print(working_days)
        else:
            working_days =  {0,1,2,3,6}

        current = start
        while current <= end:
            weekday = current.weekday()

            if weekday in working_days:

                if current in attended_days:
                    _logger.info("%s -> attended", current)

                elif current in public_holiday_dates:
                    _logger.info("%s -> public holiday", current)

                elif current in leave_dates:
                    _logger.info("%s -> leave", current)

                elif current in mission_dates:
                    _logger.info("%s -> mission", current)

                else:
                    _logger.info("%s -> absence", current)
                    absence += 1

            current += timedelta(days=1)

        _logger.info("above absence = %s", absence)

        for att in attendances:
            if not att.check_in:
                continue
            if att.employee_id.state_employee_exception == 'is_deliver':
                continue

            employee = att.employee_id

            tz_name = (
                    employee.resource_calendar_id.tz
                    or employee.resource_id.tz
                    or employee.user_id.tz
                    or 'UTC'
            )
            user_tz = pytz.timezone(tz_name)
            local_time_in = att.check_in.astimezone(user_tz)
            # print(local_time_in,att.employee_id.name)
            local_time_out = att.check_out.astimezone(user_tz)
            # print(local_time_out, att.employee_id.name)
            checkin = self.to_minutes(local_time_in)
            # print(checkin,att.employee_id.name)
            start=self.policy.work_start_minutes + self.policy.grace_minutes
            # print(start,att.employee_id.name)
            checkout = self.to_minutes(local_time_out)


            # print(att.check_in,checkin, att.check_out,checkout)
            if checkin > self.policy.absence_after_minutes:
                absence += 1
            elif checkin > start:
                # print(late)
                # print(employee.name)
                # print(checkin)
                # print(local_time_in)

                late += 1
                # print(late)
                late_hour += att.delay_minutes

            if att.check_out:
                # checkout = self.to_minutes(att.check_out)
                exec_checkout = 895
                if checkout < (self.policy.checkout_minutes - (self.policy.grace_minutes-5)):
                    if att.employee_id.state_employee_exception == 'is_exception_checkout':
                        # print(checkout ,exec_checkout)
                        if checkout < exec_checkout :
                            early_leave += 1
                            early_hour += att.early_minutes
                    else:
                        early_leave += 1
                        early_hour += att.early_minutes

        abs_from_late = late // self.policy.late_to_absence
        abs_from_early_out = early_leave // self.policy.late_to_absence
        # print(late)
        # print(early_leave)
        # print(abs_from_late)
        # print(abs_from_early_out)
        absence += (abs_from_late + abs_from_early_out)
        # print(absence)
        # print(early_leave)
        return {
            "late": late,
            "absence": absence,
            "early_leave": early_leave,
            "delay_hours": late_hour,
            "early_hours": early_hour
        }

