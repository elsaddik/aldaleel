
from odoo import models, fields, api
from num2words import num2words
from decimal import Decimal, ROUND_DOWN


class ChequeBatch(models.Model):
    _name = 'cheque.batch'
    _description = 'Cheque Batch'

    name = fields.Char(string="رقم الصك", required=True)
    date = fields.Date(string="تاريخ الصك", default=fields.Date.today)

    bank_id = fields.Many2one('res.bank', string="البنك",required=True)

    date_from = fields.Date(required=True,string="من تاريخ")
    date_to = fields.Date(required=True,string="إلى تاريخ")

    line_ids = fields.One2many('cheque.batch.line', 'batch_id')


    amount_text = fields.Char(compute='_compute_amount_text')


    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    total_amount = fields.Float(compute='_compute_total',digits=(16, 3) ,store=True)



    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))



    @api.depends('total_amount')
    def _compute_amount_text(self):
        for rec in self:
            if rec.total_amount:

                amount = Decimal(str(rec.total_amount))

                integer_part = int(amount)
                decimal_part = str(amount).split('.')[-1] if '.' in str(amount) else ''

                integer_words = num2words(integer_part, lang='ar')

                if decimal_part and int(decimal_part) != 0:
                    decimal_words = num2words(int(decimal_part), lang='ar')
                    rec.amount_text = f"{integer_words} دينار و {decimal_words} درهم لا غير"
                else:
                    rec.amount_text = f"{integer_words} دينار ليبي لا غير"
            else:
                rec.amount_text = ''

    def action_load_payslips(self):
        for rec in self:

            domain = [('state', '=', 'validated')]

            if rec.date_from:
                domain.append(('date_from', '>=', rec.date_from))

            if rec.date_to:
                domain.append(('date_to', '<=', rec.date_to))

            if rec.bank_id:
                domain.append((
                    'employee_id.bank_account_ids.bank_id',
                    '=', rec.bank_id.id
                ))

            payslips = self.env['hr.payslip'].search(domain).exists()

            lines = []
            used_slips = set()

            for slip in payslips:
                if not slip.exists():
                    continue

                if slip.id in used_slips:
                    continue
                used_slips.add(slip.id)

                net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
                amount = net_line.total if net_line else 0.0

                lines.append((0, 0, {
                    'employee_id': slip.employee_id.id,
                    'payslip_id': slip.id,
                    'amount': amount
                }))

            rec.line_ids = [(5, 0, 0)]
            rec.line_ids = lines
    # def action_load_payslips(self):
    #     for rec in self:
    #
    #         # -------- Domain --------
    #         domain = [
    #             ('state', '=', 'validated')  # أو validated حسب سيستمك
    #         ]
    #
    #         # فلترة بالتاريخ
    #         if rec.date_from:
    #             domain.append(('date_from', '>=', rec.date_from))
    #
    #         if rec.date_to:
    #             domain.append(('date_to', '<=', rec.date_to))
    #
    #         # فلترة بالبنك
    #         if rec.bank_id:
    #             domain.append((
    #                 'employee_id.bank_account_ids.bank_id',
    #                 '=',
    #                 rec.bank_id.id
    #             ))
    #
    #         # -------- Search --------
    #         payslips = self.env['hr.payslip'].search(domain)
    #
    #         # -------- Prepare --------
    #         lines = []
    #         used_slips = set()
    #
    #         for slip in payslips:
    #
    #             # منع التكرار
    #             if slip.id in used_slips:
    #                 continue
    #             used_slips.add(slip.id)
    #
    #             # صافي المرتب
    #             net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
    #             amount = net_line.total if net_line else 0.0
    #             print(amount)
    #             lines.append((0, 0, {
    #                 'employee_id': slip.employee_id.id,
    #                 'payslip_id': slip.id,
    #                 'amount': amount
    #             }))
    #
    #         # مسح القديم وإضافة الجديد
    #         rec.line_ids = [(5, 0, 0)]
    #         rec.line_ids = lines


class ChequeBatchLine(models.Model):
    _name = 'cheque.batch.line'
    _description = 'Cheque Batch Line'

    batch_id = fields.Many2one('cheque.batch', ondelete='cascade')

    employee_id = fields.Many2one('hr.employee')
    payslip_id = fields.Many2one('hr.payslip', ondelete='cascade')




    currency_id = fields.Many2one(
        'res.currency',
        related='batch_id.company_id.currency_id',
        readonly=True
    )

    amount = fields.Monetary(

        currency_field='currency_id'
    )