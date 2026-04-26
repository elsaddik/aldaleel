from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError
import calendar
from datetime import date

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    state = fields.Selection(selection_add=[
        ('manager_approve', 'Waiting Manager Approval'),
        ('hr_approve', 'Waiting HR Approval'),
        ('gm_approve', 'Waiting GM Approval'),
    ], ondelete={
        'manager_approve': 'cascade',
        'hr_approve': 'cascade',
        'gm_approve': 'cascade',
    })



    @api.constrains('holiday_status_id', 'employee_id', 'request_date_from')
    def check_limit_permission(self):
        for rec in self:
            if not rec.request_date_from:
                continue

            year = rec.request_date_from.year
            month = rec.request_date_from.month
            last_day = calendar.monthrange(year, month)[1]

            date_from = date(year, month, 1)
            date_to = date(year, month, last_day)

            # ----------------------------------
            # 1. Permissions (hour-based)
            # ----------------------------------
            if rec.holiday_status_id.request_unit == 'hour':
                count = self.env['hr.leave'].search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('holiday_status_id.request_unit', '=', 'hour'),
                    ('request_date_from', '>=', date_from),
                    ('request_date_from', '<=', date_to),
                    ('id', '!=', rec.id),
                ])

                if count >= 3:
                    raise ValidationError(
                        f"{rec.employee_id.name} cannot take more than 3 permissions this month"
                    )

            # ----------------------------------
            # 2. Urgent leaves (عارضة)
            # ----------------------------------
            URGENT_TYPE_ID = 87  # الأفضل تجيبه بـ XML ID مش رقم ثابت

            if rec.holiday_status_id.id == URGENT_TYPE_ID:
                count_urgent = self.env['hr.leave'].search_count([
                    ('employee_id', '=', rec.employee_id.id),
                    ('holiday_status_id', '=', URGENT_TYPE_ID),
                    ('request_date_from', '>=', date_from),
                    ('request_date_from', '<=', date_to),
                    ('id', '!=', rec.id),
                ])

                if count_urgent >= 3:
                    raise ValidationError(
                        f"{rec.employee_id.name} cannot take more than 3 urgent leaves this month"
                    )

    def action_submit_for_approval(self):
        for leave in self:
            if leave.state != 'confirm':
                raise UserError("Request must be in confirm state")

            leave.state = 'manager_approve'

        return True

    def _get_next_states_by_state(self):
        res = super()._get_next_states_by_state()

        res.update({
            'confirm': {'manager_approve': True},
            'manager_approve': {'hr_approve': True},
            'hr_approve': {'gm_approve': True},
            'gm_approve': {'validate': True},
        })

        return res

    def action_approve(self, check_state=True):
        user = self.env.user

        for leave in self:

            # 1️⃣ Manager
            if leave.state == 'manager_approve':
                if leave.employee_id.parent_id.user_id != user:
                    raise UserError("Only direct manager can approve")

                leave.state = 'hr_approve'
                continue

            # 2️⃣ HR
            if leave.state == 'hr_approve':
                if not user.has_group('aldaleel_attendance_policy.group_hr_payroll_user_custom'):
                    raise UserError("Only HR can approve")

                leave.state = 'gm_approve'
                continue

            # 3️⃣ GM
            if leave.state == 'gm_approve':
                if not user.has_group('aldaleel_attendance_policy.group_general_manager'):
                    raise UserError("Only GM can approve")

                leave._action_validate(check_state)
                continue

        return True

