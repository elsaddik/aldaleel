from odoo import models, fields, api, _
from datetime import date, datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError


class PayslipInput(models.Model):
    _inherit = "hr.payslip.input"
    start_period = fields.Date("Start Date")
    end_period = fields.Date("End Date")
    employee_id= fields.Many2one('hr.employee')



class ContractType(models.Model):
    _inherit = "hr.contract.type"
    include_in_payslip = fields.Boolean(string="Include in Payslip", default=True)


class HrPayslipInherit(models.Model):
    _inherit = "hr.payslip"



    @api.constrains('date_from')
    def _check_generate_after_month_end(self):
        for rec in self:
            if not rec.date_from:
                continue

            # الشهر الخاص بالـ payslip
            year = rec.date_from.year
            month = rec.date_from.month

            # حساب آخر يوم في نفس الشهر
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            today = fields.Date.today()

            # ❌ ممنوع قبل نهاية الشهر
            if today < last_day:
                raise ValidationError(
                    "لا يمكن إنشاء مسير الرواتب قبل انتهاء الشهر (آخر يوم من الشهر)"
                )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager', 'General Manager Approval'),
        ('account', 'Accounting'),
        ('validated', 'Validated'),
        ('paid', 'Paid'),
        ('cancel', 'Canceled')],
        string='State', index=True, readonly=True, copy=False,
        default='draft', tracking=True)


    state_display = fields.Selection([
        ('draft', 'Draft'),
        ('manager', 'General Manager Approval'),
        ('account', 'Accounting'),
        ('validated', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Canceled'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ],
        string='Status',
        compute='_compute_state_display',
        store=True,
        readonly=True,
    )

    reject_reason = fields.Text(string="Reject Reason", tracking=True)


    # ===============================
    # HR ➜ Manager
    # ===============================
    def action_send_to_manager(self):
        for rec in self:

            rec.state = 'manager'

            rec.message_post(body="تم إرسال كشف المرتبات إلى المدير العام")
    #
    # # ===============================
    # # Manager Approve
    # # ===============================
    def action_manager_approve(self):
        for rec in self:
            rec.state = 'account'
            rec.message_post(body="تمت الموافقة من المدير العام")
    #
    # # ===============================
    # # Manager Reject
    # # ===============================
    def action_manager_reject(self):
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body="تم رفض كشف المرتبات وإرجاعه للشؤون الإدارية")

    # ===============================
    # Accounting ➜ Paid
    # ===============================
    def action_mark_paid(self):
        for rec in self:
            rec.state = 'paid'
            rec.message_post(body="تم صرف المرتبات")

    abs_count = fields.Float(string="Total Abc", readonly=True)
    abs_count_to_add = fields.Float(string="Abc Count to Add")
    add_deduct = fields.Boolean(string="Include in Payslip", default=False)

    include_in_payslip = fields.Boolean(
        # related='employee_id.contract_type_id.include_in_payslip',
        # readonly=True,

    )

    def compute_sheet(self):
        self = self.exists()
        print(self)
        for payslip in self:
            employee = payslip.employee_id

            if not employee:
                continue

            start = payslip.date_from
            end = payslip.date_to

            penalties = self.env['bank.attendance.penalty'].search([
                ('employee_id', '=', employee.id),
                ('period_end', '>=', start),
                ('period_end', '<=', end),
            ])

            total_absence = sum(penalties.mapped('absence_count'))
            payslip.abs_count = total_absence

            input_type = self.env['hr.payslip.input.type'].search([
                ('code', '=', 'ABS')
            ], limit=1)

            if not employee.contract_type_id:
                continue  # بدل error عشان ما يكسرش batch

            # حذف القديم
            lines = payslip.input_line_ids.filtered(
                lambda l: l.input_type_id.code == 'ABS'
            )
            if lines:
                lines.unlink()

            # إضافة الجديد
            if total_absence > 0 and input_type and employee.contract_type_id.include_in_payslip:
                self.env['hr.payslip.input'].create({
                    "payslip_id": payslip.id,
                    "input_type_id": input_type.id,
                    "amount": total_absence,
                    "start_period": start,
                    "end_period": end,
                })

            elif not employee.contract_type_id.include_in_payslip and payslip.add_deduct:
                self.env['hr.payslip.input'].create({
                    "payslip_id": payslip.id,
                    "input_type_id": input_type.id,
                    "amount": payslip.abs_count_to_add,
                    "start_period": start,
                    "end_period": end,
                })

        return super().compute_sheet()

    # def compute_sheet(self):
    #
    #     for payslip in self:
    #         print(payslip.id)
    #         employee = payslip.employee_id
    #
    #         start = payslip.date_from
    #         end = payslip.date_to
    #
    #         penalties = self.env['bank.attendance.penalty'].search([
    #             ('employee_id', '=', employee.id),
    #             ('period_end', '>=', start),
    #             ('period_end', '<=', end),
    #         ])
    #
    #         print("Penalties:", penalties)
    #
    #         total_absence = sum(penalties.mapped('absence_count'))
    #         payslip.abs_count = total_absence
    #
    #         print("TOTAL ABSENCE:", total_absence)
    #
    #         input_type = self.env['hr.payslip.input.type'].search([
    #             ('code', '=', 'ABS')
    #         ], limit=1)
    #         print(employee)
    #         if not employee.contract_type_id:
    #             raise UserError(_("you must select a contract type."))
    #
    #         # حذف القديم
    #         lines=payslip.input_line_ids.filtered(
    #             lambda l: l.input_type_id.code == 'ABS'
    #         )
    #         if lines:
    #             lines.unlink()
    #         # إضافة الجديد
    #         if total_absence > 0 and input_type and employee.contract_type_id.include_in_payslip == True:
    #             self.env['hr.payslip.input'].create({
    #                 "payslip_id": payslip.id,
    #                 "input_type_id": input_type.id,
    #                 "amount": total_absence,
    #                 "start_period": start,
    #                 "end_period": end,
    #             })
    #         elif not employee.contract_type_id.include_in_payslip and payslip.add_deduct:
    #             self.env['hr.payslip.input'].create({
    #                 "payslip_id": payslip.id,
    #                 "input_type_id": input_type.id,
    #                 "amount": payslip.abs_count_to_add,
    #                 "start_period": start,
    #                 "end_period": end,
    #             })
    #
    #     return super().compute_sheet()
    #     # return res
