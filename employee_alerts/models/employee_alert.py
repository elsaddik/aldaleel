from odoo import models, fields, api

class EmployeeAlert(models.Model):
    _name = 'employee.alert'
    _description = 'Employee Alert'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Title", required=True)
    message = fields.Text(string="Message", required=True)

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")

    date = fields.Date(string="Date")

