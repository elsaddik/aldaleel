# from odoo import models, fields, api


# class employee_monthly_report(models.Model):
#     _name = 'employee_monthly_report.employee_monthly_report'
#     _description = 'employee_monthly_report.employee_monthly_report'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

