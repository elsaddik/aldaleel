from odoo import models, fields, api,_
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging
from datetime import date,datetime
_logger = logging.getLogger(__name__)
class Leaves(models.Model):
    _inherit = 'hr.leave'

    replacement_employee_id = fields.Many2one('hr.employee', string="Replacement Employee")

    emergency_degree = fields.Selection([
        ('1', 'الدرجة الأولى'),
        ('2', 'الدرجة الثانية'),
        ('3', 'الدرجة الثالثة'),
        ('other', 'أخرى')
    ], string="درجة القرابة (للإجازة الطارئة)")

    @api.constrains('number_of_days', 'holiday_status_id', 'emergency_degree', 'request_date_from')
    def _check_urgent_leave_constraints(self):
        for leave in self:

            if leave.holiday_status_id.name != 'urgent':
                continue
            degree_days = {
                '1': 3,
                '2': 2,
                '3': 1,
                'other': 1,
            }

            max_days_per_instance = 3
            degree = leave.emergency_degree or 'other'
            allowed_days = min(degree_days.get(degree, 1), max_days_per_instance)

            if leave.emergency_degree and leave.number_of_days > allowed_days:
                raise ValidationError(
                    _("عدد أيام الإجازة الطارئة لهذه الحالة لا يمكن أن يتجاوز %s يومًا.") % allowed_days
                )

            # ===== الحد الأقصى السنوي =====
            year_start = leave.request_date_from.replace(month=1, day=1)
            year_end = leave.request_date_from.replace(month=12, day=31)
            leaves_in_year = self.search([
                ('employee_id', '=', leave.employee_id.id),
                ('holiday_status_id', '=', leave.holiday_status_id.id),
                ('request_date_from', '>=', year_start),
                ('request_date_to', '<=', year_end),
                ('id', '!=', leave.id),
            ])
            total_days_this_year = sum(l.number_of_days for l in leaves_in_year) + leave.number_of_days
            if total_days_this_year > 12:
                raise ValidationError(
                    _("الإجازات الطارئة لهذا الموظف خلال السنة لا يمكن أن تتجاوز 12 يومًا.")
                )

    @api.constrains('replacement_employee_id', 'request_date_from', 'request_date_to')
    def _check_replacement_employee_availability(self):
        for record in self:
            if not record.replacement_employee_id:
                continue

            overlapping_leave = self.env['hr.leave'].search([
                ('employee_id', '=', record.replacement_employee_id.id),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
                ('request_date_from', '<=', record.request_date_to),
                ('request_date_to', '>=', record.request_date_from),
                ('id', '!=', record.id)
            ], limit=1)

            if overlapping_leave:
                raise ValidationError(
                    "this employee have  a leave in the same time!"
                )

    is_exception = fields.Boolean(string="HR Exception")  # للاستثناءات

    @api.constrains('request_date_from', 'request_date_to', 'employee_id')
    def _check_leave_rules(self):
        for record in self:
            if record.holiday_status_id.id != 1:
                continue
            if not record.request_date_from or not record.request_date_to:
                continue

            today = fields.Date.today()

            # 1️⃣ شرط التقديم قبل 3 أيام
            if record.request_date_from < today + timedelta(days=3):
                # عدد الطلبات المتأخرة في السنة
                year_start = today.replace(month=1, day=1)
                year_end = today.replace(month=12, day=31)

                late_requests = self.search_count([
                    ('employee_id', '=', record.employee_id.id),
                    ('request_date_from', '<', fields.Date.today() + timedelta(days=3)),
                    ('create_date', '>=', year_start),
                    ('create_date', '<=', year_end),
                    ('state', 'in', ['confirm', 'validate1', 'validate']),
                ])

                if late_requests >= 5:
                    raise ValidationError("تم استهلاك الحد الأقصى للطلبات المتأخرة (5 مرات سنويًا)")

            # 2️⃣ أقل مدة 3 أيام
            # duration = (record.request_date_to - record.request_date_from).days + 1
            duration = record.number_of_days
            if duration < 3:
                raise ValidationError("يجب أن لا تقل مدة الإجازة عن 3 أيام متصلة")

    def check_annual_leave_balance(self):
        _logger.info("Starting Annual Leave Balance Check...")

        employees = self.env['hr.employee'].search([])
        year_start = fields.Date.today().replace(month=1, day=1)
        year_end = fields.Date.today().replace(month=12, day=31)

        for emp in employees:

            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('request_date_from', '>=', year_start),
                ('request_date_to', '<=', year_end),
            ])

            total_days = sum(l.number_of_days for l in leaves)
            _logger.info(f"{emp.name}: total_days={total_days}")

            if total_days < 15:
                message_body = (
                    f"عزيزي {emp.name}، يرجى العلم أنك استهلكت {total_days} يوم إجازة فقط هذا العام. "
                    "يجب ألا يقل رصيد إجازاتك السنوية المستهلكة عن 15 يوماً."
                )

                if emp.user_id and emp.user_id.partner_id:
                    partner = emp.user_id.partner_id

                    # نجيب أو نعمل channel خاص
                    channel = self.env['discuss.channel'].search([
                        ('channel_type', '=', 'chat'),
                        ('channel_partner_ids', 'in', [partner.id])
                    ], limit=1)

                    if not channel:
                        channel = self.env['discuss.channel'].create({
                            'channel_partner_ids': [(4, partner.id)],
                            'channel_type': 'chat',
                            'name': f'Chat with {emp.name}',
                        })

                    # نبعت الرسالة
                    channel.message_post(
                        body=message_body,
                        message_type="comment",
                        subtype_xmlid="mail.mt_comment",
                    )


                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('hr.employee'),
                    'res_id': emp.id,
                    'user_id': emp.user_id.id if emp.user_id else self.env.uid,
                    'summary': 'تذكير بالإجازة السنوية',
                    'note': message_body,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                })
                # to add hr manger with emp in same channel
                # if emp.user_id and emp.user_id.partner_id:
                #     partner_emp = emp.user_id.partner_id
                #     partner_hr = hr_user.partner_id  # لازم يكون عندك user للـ HR
                #
                #     # نجيب أو نعمل channel فيه الاتنين
                #     channel = self.env['mail.channel'].search([
                #         ('channel_type', '=', 'chat'),
                #         ('channel_partner_ids', 'in', [partner_emp.id]),
                #         ('channel_partner_ids', 'in', [partner_hr.id]),
                #     ], limit=1)
                #
                #     if not channel:
                #         channel = self.env['mail.channel'].create({
                #             'channel_partner_ids': [
                #                 (4, partner_emp.id),
                #                 (4, partner_hr.id),
                #             ],
                #             'channel_type': 'chat',
                #             'name': f'{emp.name} - HR',
                #         })
                #
                #     # نبعت الرسالة
                #     channel.message_post(
                #         body=f"الموظف {emp.name} استهلك {total_days} يوم فقط. تم إرسال تنبيه له.",
                #         message_type="comment",
                #         subtype_xmlid="mail.mt_comment",
                #     )
                # hr_channel.message_post(
                #     body=f"الموظف {emp.name} استهلك {total_days} يوم فقط. تم إرسال تنبيه له.",
                #     message_type="comment",
                #     subtype_xmlid="mail.mt_comment",
                #     partner_ids= emp.user_id.partner_id.ids,
                # )

    def carry_forward_leaves(self):
        employees = self.env['hr.employee'].search([])

        for emp in employees:

            leave_type = self.env['hr.leave.type'].browse(1)

            # balance = emp.virtual_remaining_leaves

            # الحد الأقصى 30 يوم
            carry =  30
            allocation_aval=self.env['hr.leave.allocation'].search([('employee_id', '=', emp.id),('holiday_status_id', '=', leave_type.id),('state', '=', 'validate')], limit=1)
            print(allocation_aval)
            date_to = datetime(datetime.now().year, 12, 31).date()
            date_from = datetime.now()
            print(date_from)
            if allocation_aval:
                print(allocation_aval.virtual_remaining_leaves)
                if allocation_aval.virtual_remaining_leaves > carry :
                    allocation_aval.virtual_remaining_leaves = carry
                    print( allocation_aval.virtual_remaining_leaves)
                allocation_aval.write({
                    'name': 'رصيد اجازة سنوية+المرحل ',
                    # 'employee_id': emp.id,
                    # 'holiday_status_id': leave_type.id,
                    'number_of_days': allocation_aval.virtual_remaining_leaves+30,

                    'allocation_type': 'regular',
                    'date_from': date_from,  # Correct field name
                    'date_to': date_to,  # Correct field name

                })


    def check_sick_leave_documents(self):
        leaves = self.search([
            ('state', 'in', ['confirm', 'validate']),
        ])

        for leave in leaves:
            if leave.holiday_status_id.id != 2:
                continue

            # هل فيه مستند؟
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'hr.leave'),
                ('res_id', '=', leave.id)
            ])

            if attachments:
                continue  # فيه مستند خلاص

            start_date = leave.request_date_from
            if not start_date:
                continue

            # حساب 3 أيام عمل
            working_days = 0
            current_date = start_date

            while working_days < 3:
                current_date += timedelta(days=1)
                if current_date.weekday() not in (5, 6):  # جمعة/سبت
                    working_days += 1

            # لو عدى الوقت
            if date.today() > current_date:
                self._send_notification(leave)



    def _send_notification(self, leave):

        if not leave.employee_id.user_id:
            return

        partner_emp = leave.employee_id.user_id.partner_id

        hr_group = self.env.ref('hr.group_hr_user')

        # نجيب users المرتبطين بالجروب من جدول العلاقة
        self.env.cr.execute("""
            SELECT uid
            FROM res_groups_users_rel
            WHERE gid = %s
        """, (hr_group.id,))

        user_ids = [row[0] for row in self.env.cr.fetchall()]

        hr_users = self.env['res.users'].browse(user_ids)
        print(hr_users)
        hr_partners = hr_users.mapped('partner_id')
        print('hr_partners',hr_partners)


        # =========================================
        # إرسال لكل HR في شات منفصل
        # =========================================
        for hr_partner in hr_partners:
            print(hr_partner)
            partners = [partner_emp.id, hr_partner.id]

            # 🔍 نجيب channel مطابق بالظبط
            channels = self.env['discuss.channel'].search([
                ('channel_type', '=', 'channel'),
                ('name', '=', 'HR')
            ],limit=1)

            channel = channels.filtered(
                lambda c: set(c.channel_partner_ids.ids) == set(partners)
            )

            # 🆕 لو مش موجود
            if not channel:
                channel = self.env['discuss.channel'].create({
                    'channel_partner_ids': [(4, p) for p in partners],
                    'channel_type': 'channel',
                    'name': f'{leave.employee_id.name} - HR',
                })

            # =========================================
            # إرسال الرسالة
            # =========================================
            channel.message_post(
                body=f"""لم يتم رفع الراحة الطبية حتي الان
                {leave.employee_id.name}
                
                {leave.request_date_from}
    """,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )