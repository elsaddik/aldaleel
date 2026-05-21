from odoo import models, fields, api, _
from odoo.exceptions import UserError



class DetailsReportWizard(models.TransientModel):
    _name = 'details.report.wizard'
    _description = 'Monthly Report Wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    def action_print_report(self):
        self.ensure_one()

        # ✅ Validation
        if self.date_to < self.date_from:
            raise UserError(_("End Date cannot be before Start Date!"))

        # ✅ Get selected employees
        active_ids = self.env.context.get('active_ids')

        if not active_ids:
            raise UserError(_("من فضلك اختار موظفين"))

        employees = self.env['hr.employee'].browse(active_ids)

        report_data = []

        for emp in employees:

            abs = self.env['bank.attendance.penalty'].search([
                ('employee_id', '=', emp.id),
                ('period_end', '>=', self.date_from),
                ('period_end', '<=', self.date_to),

            ])
            abs_count = sum(abs.mapped('absence_count'))


            attend = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', self.date_from),
                ('check_in', '<=', self.date_to),

            ])
            if not attend:
                continue
            attend_count =len(attend)
            late_count = len(attend.filtered(lambda l: l.is_late == True and emp.state_employee_exception != 'deliver'))


            report_data.append({
                'employee_id': emp.id,
                'employee_name': emp.name,
                'attend':attend_count,
                'late': late_count,
                'abs_count': abs_count
            })

        print('report data',report_data)
        data = {
            'doc_ids': employees.ids,
            'doc_model': 'hr.employee',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_data': report_data,
        }

        return self.env.ref('employee_monthly_report.report_detail_action').report_action(self, data=data)