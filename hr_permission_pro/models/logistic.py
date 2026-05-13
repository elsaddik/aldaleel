from odoo import models, fields, api


class HrLogistic(models.Model):
    _name = 'hr.logistic'
    _description = 'Logistic / Transportation'
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    note = fields.Text()