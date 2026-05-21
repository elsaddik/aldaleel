from odoo import models, fields, api,_
from ..services.attendance_engine import AttendanceEngine
from markupsafe import Markup

class AttendancePenalty(models.Model):
    _name = "bank.attendance.penalty"
    _description = "Attendance Penalty"

    employee_id = fields.Many2one("hr.employee")
    period_start = fields.Date()
    period_end = fields.Date()
    late_count = fields.Integer()
    absence_count = fields.Integer()
    early_leave_count = fields.Integer()
    delay_hours = fields.Float()
    early_hours = fields.Float()

    def create_payroll_input(self, employee, absence,late,start,end):

        existing_abs = self.env['hr.payslip.input'].search([
            ('employee_id','=',employee.id),
            ('input_type_id.code','=','ABSENCE')
        ], limit=1)
        if existing_abs:
            print('existing_abs',existing_abs)
            existing_abs.write({'amount':absence,'start_period':start,'end_period':end})
        else:
            input_type = self.env['hr.payslip.input.type'].search([("code","=", "ABSENCE")])
            if input_type :
                print(input_type.id)
                self.env['hr.payslip.input'].sudo().create({
                "id": input_type.id,
                "amount":absence,
                "start_period":start,
                "end_period":end,
                "employee_id":employee.id
                })

    @api.model
    def run_attendance_engine(self):
        engine = AttendanceEngine(self.env)
        employees = self.env['hr.employee'].search([])
        # employees = self.env['hr.employee'].browse(27)
        start, end = engine.compute_period()
        for emp in employees:
            result = engine.analyze_employee(emp)
            rec = self.search([
                ('employee_id','=',emp.id),
                ('period_start','=',start)
            ], limit=1)
            if result['absence'] == 1:
                alert = self.env['employee.alert'].create({
                    'name': 'Absence Warning',
                    'message': 'First absence detected',
                    'employee_id': emp.id,
                    'date': fields.Date.today(),
                })
                if alert:
                    message = Markup(f"""
                               تم ملاحظة عدم تواجدك اليوم {emp.name}
                               <br/>
                               <a href="#"
                                  data-oe-model="{alert._name}"
                                  data-oe-id="{alert.id}">
                                  طلب رقم {alert.id}
                               </a>
                               """)

                    # 👤 إشعار الموظف
                    if emp.user_id:
                        alert.send_channel_notification(
                            emp.user_id.partner_id,
                            message,
                        )

                    admins = self.env.ref('base.group_system').user_ids.mapped('partner_id')
                    if admins:
                        alert.send_channel_notification(
                            admins,
                            message
                        )

                    # 🧑‍💼 إشعار HR
                    hr_users = self.env.ref('aldaleel_attendance_policy.group_hr_payroll_user_custom').user_ids
                    hr_partners = hr_users.mapped('partner_id')

                    if hr_partners:
                        alert._send_channel_notification(
                            hr_partners,
                            message
                        )

                # if emp.user_id and emp.user_id.partner_id:
                #     alert.message_notify(
                #         partner_ids=[emp.user_id.partner_id.id],
                #         subject='Absence Warning',
                #         body='⚠️ You have your first absence today',
                #     )

                result['absence'] = 0
            vals = {
                "employee_id": emp.id,
                "period_start": start,
                "period_end": end,
                "late_count": result["late"],
                "absence_count": result["absence"],
                "early_leave_count": result["early_leave"],
                "early_hours": result["early_hours"],
                "delay_hours": result["delay_hours"],

            }
            if rec:
                rec.write(vals)
            else:
                self.create(vals)
            # if result["absence"] > 0:
            #     self.create_payroll_input(emp, result["absence"],result["late"],start,end)