from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrPermission(models.Model):
    _name = 'hr.permission'
    _description = 'Employee Permission'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(default='New')
    employee_id = fields.Many2one('hr.employee', required=True)
    date = fields.Date(required=True)

    permission_type = fields.Selection([
        # ('late', 'Late'),
        # ('early', 'Early Leave'),
        ('mission', 'Mission')
    ], required=True)

    time_from = fields.Float(required=True)
    time_to = fields.Float(required=True)

    duration = fields.Float(compute="_compute_duration", store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused')
    ], default='draft')

    # =========================
    # Compute
    # =========================
    @api.depends('time_from', 'time_to')
    def _compute_duration(self):
        for rec in self:
            rec.duration = max(0, rec.time_to - rec.time_from)

    # =========================
    # Validation
    # =========================
    @api.constrains('time_from', 'time_to')
    def _check_time(self):
        for rec in self:
            if rec.time_from >= rec.time_to:
                raise ValidationError("Invalid time range")

    @api.constrains('employee_id', 'date', 'time_from', 'time_to')
    def _check_overlap(self):
        for rec in self:
            domain = [
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('date', '=', rec.date),
                ('state', 'in', ['approved', 'to_approve']),
            ]
            others = self.search(domain)

            for o in others:
                if not (rec.time_to <= o.time_from or rec.time_from >= o.time_to):
                    raise ValidationError("Overlapping permission!")

    # =========================
    # Workflow
    # =========================
    def action_submit(self):
        self.state = 'to_approve'

    def action_approve(self):
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refused'