from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPermission(models.Model):
    _name = 'hr.permission'
    _description = 'Employee Permission'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(default='New')
    destination = fields.Char()
    mission_desc = fields.Char()

    employee_id = fields.Many2one('hr.employee', required=True)

    date = fields.Date()

    datetime_from = fields.Datetime(required=True)
    datetime_to = fields.Datetime(required=True)

    duration = fields.Float(compute="_compute_duration", store=True)

    permission_type = fields.Selection([
        ('mission', 'Mission')
    ], default='mission', required=True)

    logistic_id = fields.Many2one('hr.logistic')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused')
    ], default='draft')

    # =========================
    # Compute Duration
    # =========================
    @api.depends('datetime_from', 'datetime_to')
    def _compute_duration(self):
        for rec in self:
            if rec.datetime_from and rec.datetime_to:
                delta = rec.datetime_to - rec.datetime_from
                rec.duration = max(0, delta.total_seconds() / 3600.0)
            else:
                rec.duration = 0

    # =========================
    # Validation
    # =========================
    @api.constrains('datetime_from', 'datetime_to', 'employee_id')
    def _check_time(self):
        for rec in self:
            if rec.datetime_from and rec.datetime_to:

                # =========================
                # 1. Check range
                # =========================
                if rec.datetime_from >= rec.datetime_to:
                    raise ValidationError("Invalid time range")

                # =========================
                # 2. Max 3 missions per day
                # =========================
                day_start = rec.datetime_from.replace(hour=0, minute=0, second=0)
                day_end = rec.datetime_from.replace(hour=23, minute=59, second=59)

                count = self.search_count([
                    ('id', '!=', rec.id),
                    ('employee_id', '=', rec.employee_id.id),
                    ('permission_type', '=', 'mission'),
                    ('datetime_from', '>=', day_start),
                    ('datetime_from', '<=', day_end),
                    ('state', 'in', ['approved', 'to_approve']),
                ])

                if count >= 3:
                    raise ValidationError("لا يمكن إضافة أكثر من 3 مهام في نفس اليوم")


    @api.constrains('employee_id', 'datetime_from', 'datetime_to', 'state')
    def _check_overlap(self):
        for rec in self:
            if not rec.datetime_from or not rec.datetime_to:
                continue

            domain = [
                ('id', '!=', rec.id),
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['approved', 'to_approve']),
            ]

            others = self.search(domain)

            for o in others:
                if not (rec.datetime_to <= o.datetime_from or rec.datetime_from >= o.datetime_to):
                    raise ValidationError("Overlapping permission!")

    # =========================
    # Actions
    # =========================
    def action_submit(self):
        self.state = 'to_approve'

    def action_approve(self):
        self.state = 'approved'

    def action_refuse(self):
        self.state = 'refused'


