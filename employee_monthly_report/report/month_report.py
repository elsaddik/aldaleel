from odoo import models, api


class MonthlyReport(models.AbstractModel):
    _name = 'report.employee_monthly_report.report_monthly_template'
    _description = 'Monthly Employee Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        docs = []

        for line in data.get('report_data', []):
            docs.append({
                'employee': self.env['hr.employee'].browse(line['employee_id']),
                'alerts': line['alerts'],
                'leaves': line['leaves'],
                'late': line['late'],
                'permissions': line['permissions'],
            })

        return {
            'doc_ids': data.get('doc_ids'),
            'doc_model': data.get('doc_model'),
            'docs': docs,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        }