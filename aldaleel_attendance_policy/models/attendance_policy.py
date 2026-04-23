from odoo import models, fields

class BankAttendancePolicy(models.Model):
    _name = "bank.attendance.policy"
    _description = "aldaleel Attendance Policy"

    name = fields.Char(default="Default aldaleel Policy")

    work_start_minutes = fields.Integer(default=510)      # 8:30
    grace_minutes = fields.Integer(default=14)            # 8:44
    absence_after_minutes = fields.Integer(default=540)   # 9:00
    checkout_minutes = fields.Integer(default=930)        # 15:30
    late_to_absence = fields.Integer(default=3)
    # cutoff_day = fields.Integer(default=15)