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
    def send_channel_notification(self, partners, message, emp=None):
        for partner in partners:
            # 🔹 البحث عن chat بين المستخدم الحالي والـ partner
            channel = self.env['discuss.channel'].search([
                ('channel_type', '=', 'chat'),
                ('channel_partner_ids', 'in', [partner.id]),
                ('channel_partner_ids', 'in', [self.env.user.partner_id.id]),
            ], limit=1)

            # 🔹 لو مش موجود نعمل channel جديد
            if not channel:
                channel = self.env['discuss.channel'].create({
                    'channel_partner_ids': [
                        (4, partner.id),
                        (4, self.env.user.partner_id.id),
                    ],
                    'channel_type': 'chat',
                    'name': f'Chat with {partner.name}',
                })

            # 🔹 إرسال الرسالة
            channel.message_post(
                body=message,
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )



