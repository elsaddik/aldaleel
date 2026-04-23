from datetime import datetime, timedelta
import calendar
import pytz
from odoo import fields

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

        # جميع الحضور الموجود
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start),
            ('check_in', '<=', end)
        ])

        late = 0
        absence = 0
        early_leave = 0
        late_hour = 0
        early_hour = 0

        # جلب الإجازات العامة
        public_holidays = self.env['resource.calendar.leaves'].search([
            ('date_from', '<=', start),
            ('date_to', '>=', end)
        ])

        public_holiday_dates = set(h.date for h in public_holidays)

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

        # ====== التعديل هنا (المهمات تعتمد على check_in) ======
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

        # 🔹 تحديد أيام العمل من الجدول
        if calendar_id and calendar_id.attendance_ids:
            working_days = {int(att.dayofweek) for att in calendar_id.attendance_ids}
        else:
            # fallback (لو مفيش جدول)
            working_days =  {6, 0, 1, 2, 3}  # Monday → Friday

        current = start
        while current <= end:
            weekday = current.weekday()

            # 🔹 احسب غياب فقط لو اليوم يوم عمل فعلي للموظف
            if weekday in working_days and \
                    current not in attended_days and \
                    current not in public_holiday_dates and \
                    current not in leave_dates and \
                    current not in mission_dates:
                absence += 1

            current += timedelta(days=1)



        # current = start
        # while current <= end:
        #     weekday = current.weekday()
        #
        #     if current not in attended_days and \
        #             current not in public_holiday_dates and \
        #             current not in leave_dates and \
        #             current not in mission_dates and \
        #             weekday not in [4, 5]:
        #         absence += 1

            # current += timedelta(days=1)

        for att in attendances:
            if not att.check_in:
                continue

            user_tz = pytz.timezone(self.env.user.tz or 'Africa/Cairo')
            local_time = att.check_in.astimezone(user_tz)
            checkin = self.to_minutes(local_time)

            if checkin >= self.policy.absence_after_minutes:
                absence += 1
            elif checkin > (self.policy.work_start_minutes + self.policy.grace_minutes):
                late += 1
                late_hour += att.delay_minutes

            if att.check_out:
                checkout = self.to_minutes(att.check_out)
                if checkout < self.policy.checkout_minutes:
                    early_leave += 1
                    early_hour += att.early_minutes

        abs_from_late = late // self.policy.late_to_absence
        absence += abs_from_late

        return {
            "late": late,
            "absence": absence,
            "early_leave": early_leave,
            "delay_hours": late_hour,
            "early_hours": early_hour
        }

    # def analyze_employee(self, employee):
    #     start, end = self.compute_period()
    #
    #     # جميع الحضور الموجود
    #     attendances = self.env['hr.attendance'].search([
    #         ('employee_id', '=', employee.id),
    #         ('check_in', '>=', start),
    #         ('check_in', '<=', end)
    #     ])
    #
    #
    #     late = 0
    #     absence = 0
    #     early_leave = 0
    #     late_hour=0
    #     early_hour=0
    #
    #     # جلب الإجازات العامة
    #     public_holidays = self.env['resource.calendar.leaves'].search([
    #
    #         ('date_from', '<=', start),
    #         ('date_to', '>=', end)
    #     ])
    #
    #
    #
    #     public_holiday_dates = set(h.date for h in public_holidays)
    #
    #     leaves = self.env['hr.leave'].search([
    #         ('employee_id', '=', employee.id),
    #         ('request_date_from', '<=', end),
    #         ('request_date_to', '>=', start),
    #         ('state', '=', 'validate')
    #     ])
    #
    #     leave_dates = set()
    #     for lv in leaves:
    #         d = lv.request_date_from
    #         while d <= lv.request_date_to:
    #             leave_dates.add(d)
    #             d += timedelta(days=1)
    #
    #
    #     attended_days = set(att.check_in.date() for att in attendances if att.check_in)
    #
    #
    #     current = start
    #     mission = self.env['hr.permission'].search([
    #         ('employee_id', '=', employee.id),
    #         ('date', '=', rec.check_in.date()),
    #         ('permission_type', '=', 'mission'),
    #         ('state', '=', 'approved')
    #     ], limit=1)
    #
    #     while current <= end:
    #         weekday = current.weekday()
    #
    #         if current not in attended_days and \
    #                 current not in public_holiday_dates and \
    #                 current not in leave_dates and \
    #                 weekday not in [4, 5]:  # فقط أيام العمل (0=Monday .. 6=Sunday)
    #             absence += 1
    #
    #         current += timedelta(days=1)
    #
    #
    #     for att in attendances:
    #         if not att.check_in:
    #             continue
    #         user_tz = pytz.timezone(self.env.user.tz or 'Africa/Cairo')
    #         local_time = att.check_in.astimezone(user_tz)
    #         checkin = self.to_minutes(local_time)
    #
    #         if checkin >= self.policy.absence_after_minutes:
    #             absence += 1
    #         elif checkin > (self.policy.work_start_minutes + self.policy.grace_minutes):
    #             late += 1
    #             print('att.delay_hours',att.delay_hours)
    #             late_hour += att.delay_hours
    #         if att.check_out:
    #             checkout = self.to_minutes(att.check_out)
    #             if checkout < self.policy.checkout_minutes:
    #                 early_leave += 1
    #                 early_hour += att.early_hours
    #
    #     abs_from_late = late // self.policy.late_to_absence
    #
    #     # carry = late % self.policy.late_to_absence
    #     # print('abs before late', absence)
    #     absence += abs_from_late
    #     # print('late', late_hour)
    #     # print('early', early_hour)
    #     # print('abs', absence)
    #     # print('early', early_leave)
    #     return {
    #         "late": late,
    #         "absence": absence,
    #         "early_leave": early_leave,
    #         "delay_hours":late_hour,
    #         "early_hours":early_hour
    #     }
