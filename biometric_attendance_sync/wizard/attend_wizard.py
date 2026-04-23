from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Attendance Report Wizard'

    # استخدام default_get لجعل التجربة أفضل
    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)

    def action_print_report(self):
        self.ensure_one()


        if self.date_to < self.date_from:
            raise UserError(_("End Date cannot be before Start Date!"))

        # جلب الموظفين المحددين أو جلب جميع الموظفين إذا تم فتحه من المنيو
        # active_ids = self.env.context.get('active_ids')
        # if active_ids and self.env.context.get('active_model') == 'hr.employee':
        #     employees = self.env['hr.employee'].browse(active_ids)
        active_ids = self.env.context.get('active_ids')

        active_ids = self.env.context.get('active_ids')
        # active_id = self.env.context.get('active_id')

        if active_ids:
            employees = self.env['hr.employee'].browse(active_ids)
        # elif active_id:
        #     employees = self.env['hr.employee'].browse([active_id])
        else:
            raise UserError("من فضلك اختار موظفين")
        # else:
        #     employees = self.env['hr.employee'].search([])

        # if not employees:
        #     raise UserError(_("No employees found to generate the report."))

        data = {
            'doc_ids': self.ids,
            'doc_model': self._name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': employees.ids,
        }

        return self.env.ref('biometric_attendance_sync.attendance_report_pdf').report_action(self, data=data)