from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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

            URGENT_TYPE_ID = 87
            DIED_TYPE_ID = 89

            if rec.holiday_status_id.id == DIED_TYPE_ID:
                if rec.number_of_days >= 3:
                    raise ValidationError(
                        f"{rec.employee_id.name} cannot take more than 3 days leaves at the same leave"
                    )

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
            SICK_TYPE_ID = 2
            if leave.holiday_status_id.id == SICK_TYPE_ID:

                attachments_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'hr.leave'),
                    ('res_id', '=', leave.id),
                ])

                if attachments_count == 0:
                    raise ValidationError("يجب إرفاق مستند مع الإجازة المرضية")

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

    # def _notify_employee(self):
    #     leaves = self.filtered(lambda hol: (
    #             (hol.validation_type == 'both' and hol.state in ['validate1', 'validate']) or
    #             (hol.validation_type == 'manager' and hol.state == 'validate')
    #     ))
    #
    #     model_description = self.env['ir.model']._get('hr.holidays').name
    #
    #     for holiday in leaves:
    #         employee_partner = holiday.employee_id.user_id.partner_id
    #         manager_partner = holiday.employee_id.leave_manager_id.partner_id
    #
    #         partners = (employee_partner | manager_partner).ids
    #
    #         if partners:
    #             holiday.sudo().message_notify(
    #                 partner_ids=partners,
    #                 model_description=model_description,
    #                 subject=_('Accepted Time Off'),
    #                 body=_('%(holiday_name)s has been Accepted.', holiday_name=holiday.display_name),
    #                 email_layout_xmlid="mail.mail_notification_layout",
    #                 subtitles=[holiday.display_name],
    #             )
    #
    # def _notify_manager(self):
    #
    #     res = super()._notify_manager()
    #
    #     leaves = self.filtered(lambda hol: (
    #             (hol.validation_type == 'both' and hol.state in ['validate1', 'validate']) or
    #             (hol.validation_type == 'manager' and hol.state == 'validate')
    #     ))
    #
    #     model_description = self.env['ir.model']._get('hr.holidays').name
    #
    #     for holiday in leaves:
    #         employee_partner = holiday.employee_id.user_id.partner_id.ids
    #
    #         if employee_partner:
    #             holiday.sudo().message_notify(
    #                 partner_ids=employee_partner,
    #                 model_description=model_description,
    #                 subject=_('Refused Time Off'),
    #                 body=_('%(holiday_name)s has been refused.', holiday_name=holiday.display_name),
    #                 email_layout_xmlid="mail.mail_notification_layout",
    #                 subtitles=[holiday.display_name],
    #             )
    #
    #     return res
    
    def action_approve(self, check_state=True):
        user = self.env.user

        for leave in self:

            # 1️⃣ Manager
            if leave.state == 'manager_approve':
                if leave.employee_id.parent_id.user_id != user and not user.has_group('aldaleel_attendance_policy.group_hr_payroll_user_custom'):
                    raise UserError("Only direct manager or HR  can approve")

                leave.state = 'hr_approve'
                continue

            # 2️⃣ HR
            if leave.state == 'hr_approve':
                if not user.has_group('aldaleel_attendance_policy.group_hr_payroll_user_custom'):
                    raise UserError("Only HR can approve")

                leave.state = 'gm_approve'
                continue

            if leave.state == 'gm_approve':
                user = self.env.user
                # attendance_leave_types = [84, 86]
                attendance_leave_types = 1
                if leave.holiday_status_id.id != attendance_leave_types:
                    if not user.has_group('aldaleel_attendance_policy.group_hr_payroll_user_custom'):
                        raise UserError("Only HR  can approve this type of leave.")
                else:
                    if not user.has_group('aldaleel_attendance_policy.group_general_manager'):
                        raise UserError("Only General Manager can approve this leave.")

                leave._action_validate(check_state)
                # self._notify_employee()


        return True
