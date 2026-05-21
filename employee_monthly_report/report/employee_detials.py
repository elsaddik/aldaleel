from odoo import models, api

class EmployeeDetailsReport(models.AbstractModel):
    _name = 'report.employee_monthly_report.report_details_template'
    _description = 'Employee Report Details'

    @api.model
    def _get_report_values(self, docids, data=None):

        docs = []
        print('data get',data.get('report_data', []))
        for line in data.get('report_data', []):
            print(line)
            docs.append({
                'employee': self.env['hr.employee'].browse(line['employee_id']),
                'attend': line['attend'],
                'late': line['late'],
                'abs': line['abs_count'],
            })

        return {
            'doc_ids': data.get('doc_ids'),
            'doc_model': data.get('doc_model'),
            'docs': docs,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        }