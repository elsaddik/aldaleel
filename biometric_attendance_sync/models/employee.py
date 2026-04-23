from odoo import models, fields
import requests
import pytz
import logging
from datetime import datetime
from odoo import models, api

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id = fields.Char(string="Device User ID")
    device_make = fields.Char(string="Device Make")

    @api.model
    def fetch_attendance_from_middleware(self):
        try:

            middleware_url = "http://middleware-server/api/data"
            response = requests.get(middleware_url, timeout=15)


            if response.status_code != 200:
                _logger.error(f"Failed to fetch data: {response.status_code}")
                return

            data = response.json()
            results = []


            for device_id, emp_data in data.items():

                first_in = emp_data.get('firstIn')
                last_seen = emp_data.get('lastSeen')
                deviceMac = emp_data.get('deviceMac')

                # =========================
                # 🔹 تحويل الوقت لـ UTC
                # =========================
                first_in_dt = None
                last_seen_dt = None

                if first_in:
                    first_in_dt = datetime.fromisoformat(first_in)
                    first_in_dt = first_in_dt.astimezone(pytz.utc).replace(tzinfo=None)

                if last_seen:
                    last_seen_dt = datetime.fromisoformat(last_seen)
                    last_seen_dt = last_seen_dt.astimezone(pytz.utc).replace(tzinfo=None)

                # =========================
                # 🔹 هات الموظف
                # =========================
                # تم تغيير request.env إلى self.env ليعمل داخل الموديل
                employee = self.env['hr.employee'].sudo().search([
                    ('device_id', '=', device_id),
                    ('device_make', '=', deviceMac)
                ], limit=1)

                if not employee:
                    results.append({
                        "device_id": device_id,
                        "status": "employee_not_found"
                    })
                    continue

                # =========================
                # 🔥 هات attendance مفتوح فقط
                # =========================
                attendance = self.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], order="check_in desc", limit=1)

                # =========================
                # 🟢 الحالة 1: مفيش → create
                # =========================
                if not attendance:
                    if first_in_dt:
                        self.env['hr.attendance'].sudo().create({
                            'employee_id': employee.id,
                            'check_in': first_in_dt,
                        })

                        results.append({
                            "device_id": device_id,
                            "status": "check_in_created"
                        })
                    else:
                        results.append({
                            "device_id": device_id,
                            "status": "no_first_in"
                        })

                    continue

                # =========================
                # 🟡 الحالة 2: فيه → update check_out
                # =========================
                if last_seen_dt and last_seen_dt > attendance.check_in:
                    attendance.sudo().write({
                        'check_out': last_seen_dt
                    })

                    results.append({
                        "device_id": device_id,
                        "status": "check_out_updated"
                    })
                else:
                    results.append({
                        "device_id": device_id,
                        "status": "no_valid_checkout"
                    })

            # طباعة النتيجة في اللوج بدل إرجاعها كـ API Response
            _logger.info(f"Attendance Cron Completed Successfully. Results: {results}")

        except Exception as e:
            _logger.error(f"Attendance Cron Error: {str(e)}")


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    device_id = fields.Char(string="Device ID", readonly=True)
    device_make = fields.Char(string="Make", readonly=True)
