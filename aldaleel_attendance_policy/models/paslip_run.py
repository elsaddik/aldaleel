from odoo import models, fields, api, _
from odoo.exceptions import UserError

from datetime import date, datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError

STATUS_COLOR = {
    '01_ready': 4,
    'manager': 0,
    'account': 0,
    '02_close': 10,
    '03_paid': 5,
    '04_cancel': 0,
    False: 0,
}


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.today()

        # 1. Iterate through the list of dictionaries
        for vals in vals_list:
            if not vals.get('date_start'):
                continue  # Skip validation for this record if date_start is missing

            date_start = fields.Date.from_string(vals['date_start'])

            # الشهر الخاص بالـ batch
            year = date_start.year
            month = date_start.month

            # حساب آخر يوم في نفس الشهر
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            # ❌ ممنوع قبل نهاية الشهر
            if today < last_day:
                raise ValidationError(
                    "لا يمكن إنشاء Payroll Batch إلا بعد انتهاء الشهر (آخر يوم أو بعده)"
                )

        # 2. Pass the entire list to the super() method
        return super().create(vals_list)

    state = fields.Selection([
        ('01_ready', 'Ready'),
        ('manager', 'Manager Approval'),
        ('account', 'Accounting'),
        ('02_close', 'Done'),
        ('03_paid', 'Paid'),
        ('04_cancel', 'Cancelled'),
    ],
        string='Status', index=True, readonly=True, copy=False,
        default='01_ready', tracking=True,
        compute='_compute_state', store=True)

    @api.depends('state')
    def _compute_color(self):
        for payslip_run in self:
            payslip_run.color = STATUS_COLOR[payslip_run.state]

    def action_send_to_manager(self):
        for rec in self:
            slip_ids = rec.mapped('slip_ids')
            for slip in slip_ids:
                if slip.state != 'draft':
                    raise UserError("يمكن الإرسال فقط من حالة Draft")
                elif slip.state == 'draft':
                    rec.state = '01_ready'
                    slip.state = 'manager'

    def action_manager_approve(self):
        for rec in self:
            slip_ids = rec.mapped('slip_ids')
            for slip in slip_ids:
                if slip.state != 'manager':
                    raise UserError("يمكن الموافقة فقط من حالة انتظار المدير")
                elif slip.state == 'manager':
                    rec.state = 'account'
                    slip.state = 'account'

    def action_manager_reject(self):
        for rec in self:
            slip_ids = rec.mapped('slip_ids')
            for slip in slip_ids:
                if slip.state != 'manager':
                    raise UserError("يمكن الرفض فقط من حالة انتظار المدير")
                elif slip.state == 'manager':
                    rec.state = '01_ready'
                    slip.state = 'draft'

    @api.depends("slip_ids.state")
    def _compute_state(self):
        for payslip_run in self:
            states = payslip_run.mapped('slip_ids.state')
            if any(state == "draft" for state in states) or not payslip_run.slip_ids:
                payslip_run.state = '01_ready'
            elif any(state == "manager" for state in states):
                payslip_run.state = 'manager'

            elif any(state == "account" for state in states):
                payslip_run.state = 'account'

            elif any(state == "validated" for state in states):
                payslip_run.state = '02_close'
            elif any(state == "paid" for state in states):
                payslip_run.state = '03_paid'
            elif all(state == "cancel" for state in states):
                payslip_run.state = '04_cancel'
            else:
                payslip_run.state = '01_ready'
