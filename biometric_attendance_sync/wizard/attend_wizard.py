from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Attendance Report Wizard'


    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, default=fields.Date.context_today)

    def action_print_report(self):
        self.ensure_one()


        if self.date_to < self.date_from:
            raise UserError(_("End Date cannot be before Start Date!"))



        active_ids = self.env.context.get('active_ids')


        if active_ids:
            employees = self.env['hr.employee'].browse(active_ids)

        else:
            raise UserError("من فضلك اختار موظفين")


        data = {
            'doc_ids': self.ids,
            'doc_model': self._name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': employees.ids,
        }

        return self.env.ref('biometric_attendance_sync.attendance_report_pdf').report_action(self, data=data)