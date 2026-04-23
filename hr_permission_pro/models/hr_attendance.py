from odoo import models, fields, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    delay_minutes = fields.Float(compute="_compute_delay", store=True)
    early_minutes = fields.Float(compute="_compute_early", store=True)
    is_late= fields.Boolean()
    is_early= fields.Boolean()
    is_mission= fields.Boolean()
    delay_display = fields.Char(compute="_compute_display")
    early_display = fields.Char(compute="_compute_display")

    # -------------------------
    # Helpers
    # -------------------------

    def _to_local(self, dt):
        if not dt:
            return dt

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)
        utc = pytz.utc

        dt_utc = utc.localize(dt) if dt.tzinfo is None else dt.astimezone(utc)
        return dt_utc.astimezone(local).replace(tzinfo=None)
    def _float_to_datetime(self, base_date, hour_float):
        hours = int(hour_float)
        minutes = int((hour_float - hours) * 60)
        return base_date.replace(hour=hours, minute=minutes, second=0)

    def _format_duration(self, minutes):
        total_seconds = int(minutes * 60)

        hours = total_seconds // 3600
        total_seconds %= 3600

        mins = total_seconds // 60
        secs = total_seconds % 60

        return f"{hours:02d}:{mins:02d}:{secs:02d}"

    # -------------------------
    # Delay
    # -------------------------
    @api.depends('check_in', 'employee_id')
    def _compute_delay(self):
        for rec in self:
            rec.delay_minutes = 0

            if not rec.check_in or not rec.employee_id:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue


            mission = self.env['hr.permission'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '=', rec.check_in.date()),
                ('permission_type', '=', 'mission'),
                ('state', '=', 'approved')
            ], limit=1)

            leave = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('request_date_from', '=',  rec.check_in.date()),
                ('holiday_status_id.request_unit', '=', 'hour'),
                ('state', '=', 'validate')
            ],limit=1)

            check_in = self._to_local(rec.check_in)

            if mission:
                rec.is_mission = True
                rec.delay_minutes = 0
                continue
            elif leave:
                rec.delay_minutes = 0
                continue

            weekday = str(check_in.weekday())

            attendance_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday
            )

            if not attendance_lines:
                continue

            start_hour = min(attendance_lines.mapped('hour_from'))
            start_dt = self._float_to_datetime(check_in, start_hour)

            if check_in <= start_dt:
                continue

            rec.delay_minutes = (
                check_in - start_dt
            ).total_seconds() / 60
            if rec.delay_minutes > 0:
                 rec.is_late = True


    @api.depends('check_out', 'employee_id')
    def _compute_early(self):
        for rec in self:
            rec.early_minutes = 0

            if not rec.check_out or not rec.employee_id:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue


            mission = self.env['hr.permission'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('date', '=', rec.check_out.date()),
                ('permission_type', '=', 'mission'),
                ('state', '=', 'approved')
            ], limit=1)
            leave = self.env['hr.leave'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('request_date_from', '=', rec.check_in.date()),
                ('holiday_status_id.request_unit', '=', 'hour'),
                ('state', '=', 'validate')
            ], limit=1)

            check_out = self._to_local(rec.check_out)
            if mission:
                rec.early_minutes = 0
                rec.is_mission = True
                continue
            elif leave:
                rec.early_minutes = 0
                continue

            weekday = str(check_out.weekday())

            attendance_lines = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == weekday
            )

            if not attendance_lines:
                continue

            end_hour = max(attendance_lines.mapped('hour_to'))
            end_dt = self._float_to_datetime(check_out, end_hour)

            if check_out >= end_dt:
                continue

            rec.early_minutes = (
                end_dt - check_out
            ).total_seconds() / 60
            if rec.early_minutes > 0:
                 rec.is_early = True


    @api.depends('delay_minutes', 'early_minutes')
    def _compute_display(self):
        for rec in self:
            rec.delay_display = self._format_duration(rec.delay_minutes)
            rec.early_display = self._format_duration(rec.early_minutes)


