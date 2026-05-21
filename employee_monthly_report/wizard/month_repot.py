from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class MonthlyReportWizard(models.TransientModel):
    _name = 'monthly.report.wizard'
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


            alerts_count = self.env['employee.alert'].search_count([
                ('employee_id', '=', emp.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])

            # 🟢 Leaves
            # 84
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.id', 'not in', [84,86]),
                ('request_date_from', '<=', self.date_to),
                ('request_date_to', '>=', self.date_from),
            ])
            leave_days = sum(leaves.mapped('number_of_days'))

            # 🟡 Late
            late_count = self.env['hr.attendance'].search_count([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', self.date_from),
                ('check_in', '<=', self.date_to),
                ('is_late', '=', True),
            ])

            leave_permissions = self.env['hr.leave'].search_count([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.id', 'in', [84, 86]),
                ('request_date_from', '<=', self.date_to),
                ('request_date_to', '>=', self.date_from),
            ])

            # mission_count = self.env['hr.permission'].search_count([
            #     ('employee_id', '=', emp.id),
            #     ('date', '>=', self.date_from),
            #     ('date', '<=', self.date_to),
            # ])

            report_data.append({
                'employee_id': emp.id,
                'employee_name': emp.name,
                'alerts': alerts_count,
                'leaves': leave_days,
                'late': late_count,
                # 'mission': mission_count,
                'permissions': leave_permissions,
            })


        data = {
            'doc_ids': employees.ids,
            'doc_model': 'hr.employee',
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_data': report_data,
        }

        return self.env.ref('employee_monthly_report.report_monthly_action').report_action(self, data=data)