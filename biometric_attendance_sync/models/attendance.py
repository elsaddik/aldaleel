from odoo import models, fields, api
import logging
import requests


_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    device_id = fields.Char(string="Device ID")


    source = fields.Selection([
        ('manual', 'Manual'),
        ('biometric', 'Biometric')
    ], default='manual')


    @api.model
    def fetch_and_send_to_endpoint(self):
        try:
            # 🔹 1. هات الداتا من الـ middleware
            middleware_url = "http://middleware-server/api/data"  # غيرها

            response = requests.get(middleware_url, timeout=10)
            data = response.json()

            # 🔹 2. ابعت للد endpoint بتاعك
            odoo_url = "http://localhost:8071/api/attendance/import"

            res = requests.post(
                odoo_url,
                json=data,
                timeout=15
            )

            _logger.info(f"Attendance Sync Response: {res.text}")

        except Exception as e:
            _logger.error(f"Attendance Cron Error: {str(e)}")


    # @api.model
    # def create_from_device(self, data):
    #     #                    {
    #     #                        "user_id": "123",
    #     #                        "timestamp": "2026-04-02 08:30:00",
    #     #                        "device_id": "DEV01",
    #     #                           "token":"hhh"
    #
    #     #                    }
    #     #                    """
    #     _logger.info("📥 Received attendance: %s", data)
    #
    #     try:
    #         # =========================
    #         # 1. Validate
    #         # =========================
    #         if not data.get('user_id') or not data.get('timestamp'):
    #             _logger.warning("❌ Missing required fields")
    #             return {'error': 'Missing data'}
    #
    #         try:
    #             timestamp = fields.Datetime.to_datetime(data.get('timestamp'))
    #         except Exception:
    #             _logger.error("❌ Invalid datetime format: %s", data.get('timestamp'))
    #             return {'error': 'Invalid datetime'}
    #
    #         # =========================
    #         # 2. Get Employee
    #         # =========================
    #         employee = self.env['hr.employee'].sudo().search([
    #             ('device_id', '=', data.get('user_id'))
    #         ], limit=1)
    #
    #         if not employee:
    #             _logger.warning("❌ Employee not found: %s", data.get('user_id'))
    #             return {'error': 'Employee not found'}
    #
    #         # =========================
    #         # 3. Get Last Attendance
    #         # =========================
    #         last_attendance = self.search([
    #             ('employee_id', '=', employee.id)
    #         ], order='check_in desc', limit=1)
    #
    #         # =========================
    #         # 4. Duplicate Protection
    #         # =========================
    #         if last_attendance:
    #             diff_seconds = abs((timestamp - last_attendance.check_in).total_seconds())
    #
    #             if diff_seconds < 60:
    #                 _logger.info("⚠️ Duplicate scan ignored for %s", employee.name)
    #                 return {'status': 'ignored_duplicate'}
    #
    #         # =========================
    #         # 5. Smart Fix (New Day + Auto Close)
    #         # =========================
    #         if last_attendance and not last_attendance.check_out:
    #             diff_hours = (timestamp - last_attendance.check_in).total_seconds() / 3600
    #
    #             if diff_hours > 12:
    #                 _logger.info("🟡 Auto closing old attendance for %s", employee.name)
    #
    #                 try:
    #                     last_attendance.write({
    #                         'check_out': last_attendance.check_in + timedelta(hours=6, minutes=30)
    #                     })
    #                 except Exception as e:
    #                     _logger.error("❌ Failed to auto close attendance ID %s: %s", last_attendance.id, str(e))
    #
    #                 # نعتبره يوم جديد
    #                 last_attendance = False
    #
    #         # =========================
    #         # 6. Toggle Logic
    #         # =========================
    #
    #         # 🟢 Check In
    #         if not last_attendance or last_attendance.check_out:
    #             record = self.create({
    #                 'employee_id': employee.id,
    #                 'check_in': timestamp,
    #                 'device_id': data.get('device_id'),
    #                 'source': 'biometric'
    #             })
    #
    #             _logger.info("✅ Check-in for %s at %s", employee.name, timestamp)
    #
    #             return {
    #                 'status': 'check_in',
    #                 'attendance_id': record.id
    #             }
    #
    #         # 🔴 Check Out
    #         else:
    #             if timestamp <= last_attendance.check_in:
    #                 _logger.warning("❌ Invalid checkout time for %s", employee.name)
    #                 return {'error': 'Invalid checkout time'}
    #
    #             last_attendance.write({
    #                 'check_out': timestamp
    #             })
    #
    #             _logger.info("✅ Check-out for %s at %s", employee.name, timestamp)
    #
    #             return {
    #                 'status': 'check_out',
    #                 'attendance_id': last_attendance.id
    #             }
    #
    #     except Exception as e:
    #         _logger.exception("🔥 Error processing attendance: %s", str(e))
    #         return {'error': 'Internal server error'}
