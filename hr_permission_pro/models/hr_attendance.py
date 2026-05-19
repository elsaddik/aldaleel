from odoo import models, fields, api

import pytz





class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # =========================
    # Fields
    # =========================
    delay_minutes = fields.Float(compute="_compute_delay", store=True)
    early_minutes = fields.Float(compute="_compute_early", store=True)

    is_late = fields.Boolean(compute="_compute_delay", store=True)
    is_early = fields.Boolean(compute="_compute_early", store=True)
    is_mission = fields.Boolean(compute="_compute_mission", store=True)

    delay_display = fields.Char(compute="_compute_display")
    early_display = fields.Char(compute="_compute_display")

    # =========================
    # Utils
    # =========================
    def _to_local(self, dt):
        if not dt:
            return dt

        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        dt = fields.Datetime.from_string(dt)
        return fields.Datetime.context_timestamp(self, dt)

    def _float_to_datetime(self, base_date, hour_float):
        hours = int(hour_float)
        minutes = int((hour_float - hours) * 60)
        return base_date.replace(hour=hours, minute=minutes, second=0)

    def _format_duration(self, minutes):
        if not minutes:
            return "00:00:00"

        total_seconds = int(minutes * 60)
        hours = total_seconds // 3600
        total_seconds %= 3600
        mins = total_seconds // 60
        secs = total_seconds % 60

        return f"{hours:02d}:{mins:02d}:{secs:02d}"

    # =========================
    # Mission (FIX مهم)
    # =========================
    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_mission(self):
        for rec in self:
            rec.is_mission = False

            if not rec.employee_id:
                continue

            dt = rec.check_in or rec.check_out
            if not dt:
                continue

            mission = self.env['hr.permission'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('permission_type', '=', 'mission'),
                ('datetime_from', '<=', dt),
                ('datetime_to', '>=', dt),
            ], limit=1)

            if mission:
                rec.is_mission = True

    # =========================
    # Delay
    # =========================
    @api.depends('check_in', 'employee_id', 'is_mission')
    def _compute_delay(self):
        policy = self.env['bank.attendance.policy'].search([], limit=1)

        for rec in self:
            rec.delay_minutes = 0
            rec.is_late = False
            if rec.employee_id.state_employee_exception == 'is_delivery':
                continue
            if not rec.check_in or not rec.employee_id:
                continue

            if rec.is_mission:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue

            check_in = self._to_local(rec.check_in)

            # leave (hour-based)
            leave = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('request_date_from', '=', check_in.date()),
                ('holiday_status_id.request_unit', '=', 'hour'),
                ('state', '=', 'validate')
            ], limit=1)

            if leave:
                continue

            weekday = str(check_in.weekday())

            attendance_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday
            )

            if not attendance_lines:
                continue

            start_hour = min(attendance_lines.mapped('hour_from'))

            if policy:
                start_hour += (policy.grace_minutes / 60)

            start_dt = self._float_to_datetime(check_in, start_hour)

            if check_in <= start_dt:
                continue

            rec.delay_minutes = (check_in - start_dt).total_seconds() / 60
            rec.is_late = rec.delay_minutes > 0

    # =========================
    # Early Leave
    # =========================
    @api.depends('check_out', 'employee_id', 'is_mission')
    def _compute_early(self):
        policy = self.env['bank.attendance.policy'].search([], limit=1)
        exec_checkout = 14.92
        for rec in self:
            rec.early_minutes = 0
            rec.is_early = False
            if rec.employee_id.state_employee_exception == 'is_deliver':
                continue
            if not rec.check_out or not rec.employee_id:
                continue

            if rec.is_mission:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue

            check_out = self._to_local(rec.check_out)
            print(check_out)
            leave = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('request_date_from', '=', check_out.date()),
                ('holiday_status_id.request_unit', '=', 'hour'),
                ('state', '=', 'validate')
            ], limit=1)

            if leave:
                continue

            weekday = str(check_out.weekday())

            attendance_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday
            )

            if not attendance_lines:
                continue
            end_hour = max(attendance_lines.mapped('hour_to'))

            if policy:
                grace_minutes =policy.grace_minutes
                end_hour -= (grace_minutes / 60) - (5/60)
            end_dt = self._float_to_datetime(check_out, end_hour)

            if check_out >= end_dt:
                continue
            exec_checkout_dt = self._float_to_datetime(check_out, exec_checkout)

            if rec.employee_id.state_employee_exception == 'is_exception_checkout':

                if check_out < exec_checkout_dt:
                    end_hour= 14.92
                    end_dt = self._float_to_datetime(check_out, end_hour)
                    rec.early_minutes = (end_dt - check_out).total_seconds() / 60
                    rec.is_early = rec.early_minutes > 0
                else: continue
            else:
                rec.early_minutes = (end_dt - check_out).total_seconds() / 60
                rec.is_early = rec.early_minutes > 0

    # =========================
    # Display
    # =========================
    @api.depends('delay_minutes', 'early_minutes')
    def _compute_display(self):
        for rec in self:
            rec.delay_display = self._format_duration(rec.delay_minutes)
            rec.early_display = self._format_duration(rec.early_minutes)

   #  delay_minutes = fields.Float(compute="_compute_delay", store=True)
   #  early_minutes = fields.Float(compute="_compute_early", store=True)
   #  is_late= fields.Boolean()
   #  is_early= fields.Boolean()
   #  is_mission= fields.Boolean()
   #  delay_display = fields.Char(compute="_compute_display")
   #  early_display = fields.Char(compute="_compute_display")
   #
   #
   #  def _to_local(self, dt):
   #      if not dt:
   #          return dt
   #
   #      user_tz = self.env.user.tz or 'UTC'
   #      local = pytz.timezone(user_tz)
   #      utc = pytz.utc
   #
   #      dt_utc = utc.localize(dt) if dt.tzinfo is None else dt.astimezone(utc)
   #      return dt_utc.astimezone(local).replace(tzinfo=None)
   #
   #  def _float_to_datetime(self, base_date, hour_float):
   #      print('hours',hour_float)
   #      hours = int(hour_float)
   #      minutes = int((hour_float - hours) * 60)
   #      return base_date.replace(hour=hours, minute=minutes, second=0)
   #
   #  def _format_duration(self, minutes):
   #      total_seconds = int(minutes * 60)
   #
   #      hours = total_seconds // 3600
   #      total_seconds %= 3600
   #
   #      mins = total_seconds // 60
   #      secs = total_seconds % 60
   #
   #      return f"{hours:02d}:{mins:02d}:{secs:02d}"
   #
   #  # -------------------------
   #  # Delay
   #  # -------------------------
   #  @api.depends('check_in', 'employee_id')
   #  def _compute_delay(self):
   #      for rec in self:
   #          rec.delay_minutes = 0
   #          rec.is_late = False
   #          rec.is_mission = False
   #
   #          if not rec.check_in or not rec.employee_id:
   #              continue
   #
   #          calendar = rec.employee_id.resource_calendar_id
   #          if not calendar:
   #              continue
   #
   #          check_in = self._to_local(rec.check_in)
   #
   #          # =========================
   #          # NEW: mission باستخدام datetime
   #          # =========================
   #          mission = self.env['hr.permission'].search([
   #              ('employee_id', '=', rec.employee_id.id),
   #              ('state', '=', 'approved'),
   #              ('permission_type', '=', 'mission'),
   #              ('datetime_from', '<=', rec.check_in),
   #              ('datetime_to', '>=', rec.check_in),
   #          ], limit=1)
   #
   #          # =========================
   #          # leave
   #          # =========================
   #          leave = self.env['hr.leave'].search([
   #              ('employee_id', '=', rec.employee_id.id),
   #              ('request_date_from', '=', check_in.date()),
   #              ('holiday_status_id.request_unit', '=', 'hour'),
   #              ('state', '=', 'validate')
   #          ], limit=1)
   #
   #          attend_policy = self.env['bank.attendance.policy'].search([], limit=1)
   #
   #          # =========================
   #          # Skip لو mission أو leave
   #          # =========================
   #          if mission:
   #              rec.is_mission = True
   #              continue
   #
   #          if leave:
   #              continue
   #
   #          # =========================
   #          # Attendance rules
   #          # =========================
   #          weekday = str(check_in.weekday())
   #
   #          attendance_lines = calendar.attendance_ids.filtered(
   #              lambda a: a.dayofweek == weekday
   #          )
   #
   #          if not attendance_lines:
   #              continue
   #
   #          start_hour = min(attendance_lines.mapped('hour_from'))
   #
   #
   #          if attend_policy:
   #              start_hour += (attend_policy.grace_minutes / 60)
   #
   #          start_dt = self._float_to_datetime(check_in, start_hour)
   #
   #          if check_in <= start_dt:
   #              continue
   #
   #          rec.delay_minutes = (check_in - start_dt).total_seconds() / 60
   #
   #          if rec.delay_minutes > 0:
   #              rec.is_late = True
   #
   #  # -------------------------
   #  # Early Leave
   #  # -------------------------
   #  @api.depends('check_out', 'employee_id')
   #  def _compute_early(self):
   #      for rec in self:
   #          rec.early_minutes = 0
   #          rec.is_early = False
   #          rec.is_mission = False
   #
   #          if not rec.check_out or not rec.employee_id:
   #              continue
   #
   #          calendar = rec.employee_id.resource_calendar_id
   #          if not calendar:
   #              continue
   #
   #          check_out = self._to_local(rec.check_out)
   #
   #          # =========================
   #          # NEW: mission باستخدام datetime
   #          # =========================
   #          mission = self.env['hr.permission'].search([
   #              ('employee_id', '=', rec.employee_id.id),
   #              ('state', '=', 'approved'),
   #              ('permission_type', '=', 'mission'),
   #              ('datetime_from', '<=', rec.check_out),
   #              ('datetime_to', '>=', rec.check_out),
   #          ], limit=1)
   #
   #          leave = self.env['hr.leave'].search([
   #              ('employee_id', '=', rec.employee_id.id),
   #              ('request_date_from', '=', check_out.date()),
   #              ('holiday_status_id.request_unit', '=', 'hour'),
   #              ('state', '=', 'validate')
   #          ], limit=1)
   #
   #          # =========================
   #          # Skip
   #          # =========================
   #          if mission:
   #              rec.is_mission = True
   #              continue
   #
   #          if leave:
   #              continue
   #
   #          weekday = str(check_out.weekday())
   #
   #          attendance_lines = calendar.attendance_ids.filtered(
   #              lambda a: a.dayofweek == weekday
   #          )
   #
   #          if not attendance_lines:
   #              continue
   #
   #          end_hour = max(attendance_lines.mapped('hour_to'))
   #          end_dt = self._float_to_datetime(check_out, end_hour)
   #
   #          if check_out >= end_dt:
   #              continue
   #
   #          rec.early_minutes = (end_dt - check_out).total_seconds() / 60
   #
   #          if rec.early_minutes > 0:
   #              rec.is_early = True
   #
   #  # -------------------------
   #  # Display
   #  # -------------------------
   #  @api.depends('delay_minutes', 'early_minutes')
   #  def _compute_display(self):
   #      for rec in self:
   #          rec.delay_display = self._format_duration(rec.delay_minutes)
   #          rec.early_display = self._format_duration(rec.early_minutes)
   #
   #