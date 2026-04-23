from odoo import http
from odoo.http import request

import pytz
from datetime import datetime, time


class AttendanceAPI(http.Controller):

    @http.route('/api/attendance/import', type='jsonrpc', auth='none', methods=['POST'], csrf=False)
    def import_attendance(self, **kwargs):
        try:
            data = request.get_json_data()
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
                employee = request.env['hr.employee'].sudo().search([
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
                attendance = request.env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], order="check_in desc", limit=1)

                # =========================
                # 🟢 الحالة 1: مفيش → create
                # =========================
                if not attendance:
                    if first_in_dt:
                        request.env['hr.attendance'].sudo().create({
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

            return {
                "status": "success",
                "data": results
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
#
#     @http.route('/api/attendance/import', type='jsonrpc', auth='none', methods=['POST'], csrf=False)
#     def import_attendance(self, **kwargs):
#         try:
#             # data = request.jsonrequest
#             jsonrequest = request.get_json_data()
#             data = jsonrequest
#             results = []
#
#             for key, emp_data in data.items():
#
#                 device_id = key
#                 first_in = emp_data.get('firstIn')
#                 last_seen = emp_data.get('lastSeen')
#                 print(first_in)
#                 print(last_seen)
#
#                 first_in_dt = datetime.fromisoformat(first_in)
#
#                 # 2. تحويل التوقيت لـ UTC (أهم خطوة لأودو)
#                 first_in_utc = first_in_dt.astimezone(pytz.utc)
#
#                 # 3. إزالة معلومات الـ timezone عشان أودو بيقبلها Naive (بدون tzinfo) في الداتابيز
#                 first_in_dt = first_in_utc.replace(tzinfo=None)
#
#
#                 last_seen_dt = datetime.fromisoformat(last_seen)
#
#                 # 2. تحويل التوقيت لـ UTC (أهم خطوة لأودو)
#                 last_in_utc = last_seen_dt.astimezone(pytz.utc)
#
#                 # 3. إزالة معلومات الـ timezone عشان أودو بيقبلها Naive (بدون tzinfo) في الداتابيز
#                 last_seen_dt = last_in_utc.replace(tzinfo=None)
#
#
#
#
#                 # print(f"Original: {first_in}")
#                 # print(f"Final for Odoo: {final_first_in}")
#
#                 # first_in_dt = datetime.fromisoformat(first_in).replace(tzinfo=None)
#                 # last_seen_dt = datetime.fromisoformat(last_seen).replace(tzinfo=None)
#
#
#
#                 # first_in_dt = datetime.fromisoformat(first_in)
#                 # last_seen_dt = datetime.fromisoformat(last_seen)
#
#                 # 🔹 هات الموظف من device_id
#                 employee = request.env['hr.employee'].sudo().search([
#                     ('device_id', '=', device_id)
#                 ], limit=1)
#
#                 if not employee:
#                     results.append({
#                         "device_id": device_id,
#                         "status": "employee_not_found"
#                     })
#                     continue
#
#                 # 🔹 نطاق اليوم
#                 date_only = first_in_dt.date()
#                 print(date_only)
#                 start_day = datetime.combine(date_only, time.min)
#                 print(start_day)
#                 end_day = datetime.combine(date_only, time.max)
#                 print(end_day)
#
#                 # 🔥 هات آخر attendance في اليوم
#                 attendance = request.env['hr.attendance'].sudo().search([
#                     ('employee_id', '=', employee.id),
#                     ('check_in', '>=', start_day),
#                     ('check_in', '<=', end_day),
#                 ], order="check_in desc", limit=1)
#
#                 # ==========================================
#                 # 🟢 الحالة 1: مفيش attendance → create
#                 # ==========================================
#                 if not attendance:
#                     request.env['hr.attendance'].sudo().create({
#                         'employee_id': employee.id,
#                         'check_in': first_in_dt,
#                         'check_out': False,
#                     })
#
#                     results.append({
#                         "device_id": device_id,
#                         "status": "check_in_created"
#                     })
#                     continue
#
#                 # ==========================================
#                 # 🟡 الحالة 2: فيه attendance مفتوح → update check_out
#                 # ==========================================
#                 if not attendance.check_out:
#                     attendance.sudo().write({
#                         'check_out': last_seen_dt
#                     })
#
#                     results.append({
#                         "device_id": device_id,
#                         "status": "check_out_updated"
#                     })
#                     continue
#
#                 attendance.sudo().write({
#                     'check_out': last_seen_dt
#                 })
#
#                 results.append({
#                     "device_id": device_id,
#                     "status": "check_out_updated"
#                 })
#
#                 # ==========================================
#                 # 🔵 الحالة 3: فيه attendance مقفول → اعمل واحد جديد
#                 # ==========================================
#                 # request.env['hr.attendance'].sudo().create({
#                 #     'employee_id': employee.id,
#                 #     'check_in': first_in_dt,
#                 #     'check_out': False,
#                 # })
#                 #
#                 # results.append({
#                 #     "device_id": device_id,
#                 #     "status": "new_session_created"
#                 # })
#
#             return {
#                 "status": "success",
#                 "data": results
#             }
#
#         except Exception as e:
#             return {
#                 "status": "error",
#                 "message": str(e)
#             }
#


