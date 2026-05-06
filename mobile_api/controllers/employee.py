import json
import logging
import jwt
import datetime
from odoo import http, fields, _
from odoo.http import request, Response
from datetime import date,datetime, time, timedelta
import base64




_logger = logging.getLogger(__name__)


SECRET_KEY = "Odoo19_Mobile_App_Secret_Key_2026"


class HrMobileAPIEmployee(http.Controller):

    # ==========================================
    # دالة التحقق من التوكن (JWT Verification)
    # ==========================================
    def _verify_token(self):
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None, "Missing or invalid Token"

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload.get('user_id'), None  # نرجع الـ ID كـ رقم فقط
        except jwt.ExpiredSignatureError:
            return None, "Token Expired"
        except Exception:
            return None, "Invalid Token"

    def _get_json_data(self):
        try:
            return json.loads(request.httprequest.data.decode('utf-8'))
        except:
            return {}

    def _response(self, data=None, message="", success=True, status=200):
        body = {
            "success": success,
            "message": message,
            "data": data or {}
        }
        return Response(json.dumps(body), status=status, mimetype='application/json')

    @http.route('/api/v1/profile', type='http', auth='none', methods=['GET'], csrf=False)
    def get_profile(self, **kwargs):


        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)


        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user)
        ], limit=1)

        if not employee:
            return self._response(success=False, message="Employee not found", status=404)


        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.employee'),
            ('res_id', '=', employee.id),
            ('mimetype', 'in', ['application/pdf', 'application/msword',
                                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
        ], limit=1, order='id desc')
        cv_data = {}
        if attachment:
            cv_data = {
                "id": attachment.id,
                "name": attachment.name,
                "url": "/web/content/%s" % attachment.id
            }

        bank_accounts = {}
        if employee.bank_account_ids:
            accounts = employee.bank_account_ids
            for acc in accounts:
                print(acc)
                if acc.bank_id:
                    bank = acc.bank_name
                    bank_accounts['bank_name'] = bank
                bank_accounts['bank_accounts'] = acc.acc_number

        data = {
            "id": employee.id,
            "name": employee.name,
            "national_id": employee.identification_id,
            "phone": employee.private_phone,
            "email": employee.private_email,
            "joining_date": str(employee.contract_date_start or ''),
            "manager": {
                "name": employee.parent_id.name if employee.parent_id else '',
                "image": (
                    "/web/image/hr.employee/%s/image_1920" % employee.parent_id.id
                    if employee.parent_id and employee.parent_id.image_1920 else ''
                )
            },
            "profile_image": (
                "/web/image/hr.employee/%s/image_1920" % employee.id
                if employee.image_1920 else ''
            ),
            "bank_accounts": bank_accounts,
            "cv": cv_data
        }
        return self._response(data)

    @http.route('/api/v1/profile', type='http', auth='none', methods=['PUT', 'PATCH'], csrf=False)
    def update_profile(self, **kwargs):
        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
        if not employee:
            return self._response(success=False, message="Employee not found", status=404)

        values = {}

        # بيانات أساسية
        if 'name' in kwargs:
            values['name'] = kwargs.get('name')

        if 'phone' in kwargs:
            values['work_phone'] = kwargs.get('phone')

        if 'email' in kwargs:
            values['work_email'] = kwargs.get('email')

        if 'national_id' in kwargs:
            values['identification_id'] = kwargs.get('national_id')

        # صورة البروفايل (Base64)
        if 'profile_image' in kwargs:
            values['image_1920'] = kwargs.get('profile_image')

        employee.sudo().write(values)

        # تحديث بيانات البنك
        if any(k in kwargs for k in ['account_number', 'iban', 'bank_name']):
            bank = None
            if kwargs.get('bank_name'):
                bank = request.env['res.bank'].sudo().search([('name', '=', kwargs.get('bank_name'))], limit=1)
                if not bank:
                    bank = request.env['res.bank'].sudo().create({'name': kwargs.get('bank_name')})

            if employee.bank_account_id:
                employee.bank_account_id.sudo().write({
                    'acc_number': kwargs.get('account_number') or employee.bank_account_id.acc_number,
                    'bank_id': bank.id if bank else employee.bank_account_id.bank_id.id
                })
            else:
                request.env['res.partner.bank'].sudo().create({
                    'acc_number': kwargs.get('account_number'),
                    'bank_id': bank.id if bank else False,
                    'partner_id': employee.address_home_id.id,
                })
        return self._response(message="Profile updated successfully")

    @http.route('/api/v1/profile/upload_cv', type='http', auth='none', methods=['POST'], csrf=False)
    def upload_cv(self, **kwargs):
        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
        if not employee:
            return self._response(success=False, message="Employee not found", status=404)


        uploaded_file = request.httprequest.files.get('file')

        if not uploaded_file:
            return self._response(success=False, message="File is required", status=400)

        file_name = uploaded_file.filename
        file_content = uploaded_file.read()
        mimetype = uploaded_file.mimetype

        # ✅ التحقق من النوع
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]

        if mimetype not in allowed_types:
            return self._response(success=False, message="Only PDF or Word files allowed", status=400)


        if len(file_content) > 5 * 1024 * 1024:
            return self._response(success=False, message="File too large (max 5MB)", status=400)



        encoded_file = base64.b64encode(file_content)

        attachment = request.env['ir.attachment'].sudo().create({
            'name': file_name,
            'datas': encoded_file,
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'mimetype': mimetype,
        })

        return self._response({
            "message": "CV uploaded successfully",
            "attachment_id": attachment.id
        })


    # @http.route('/api/v1/profile/upload_cv', type='http', auth='none', methods=['POST'], csrf=False)
    # def upload_cv(self, **kwargs):
    #     user, error = self._verify_token()
    #     if error:
    #         return self._response(success=False, message=error, status=401)
    #
    #     employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
    #     if not employee:
    #         return self._response(success=False, message="Employee not found", status=404)
    #
    #     file_content = kwargs.get('file')
    #     file_name = kwargs.get('file_name')
    #     mimetype = kwargs.get('mimetype', 'application/octet-stream')
    #
    #
    #     if not file_content or not file_name:
    #         return self._response(success=False, message="file and file_name are required", status=400)
    #
    #     try:
    #         import base64
    #         base64.b64decode(file_content)
    #     except Exception:
    #         return self._response(success=False, message="Invalid base64 file", status=400)
    #
    #
    #     allowed_types = ['application/pdf', 'application/msword',
    #                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    #     if mimetype not in allowed_types:
    #         return self._response(success=False, message="Only PDF or Word files allowed", status=400)
    #
    #
    #     if len(file_content) > 5_000_000:
    #         return self._response(success=False, message="File too large", status=400)
    #
    #
    #     attachment = request.env['ir.attachment'].sudo().create({
    #         'name': 'CV',
    #         'datas': file_content,
    #         'res_model': 'hr.employee',
    #         'res_id': employee.id,
    #         'mimetype': mimetype,
    #     })
    #
    #     return self._response({
    #         "message": "CV uploaded successfully",
    #         "attachment_id": attachment.id
    #     })

    @http.route('/api/v1/permission/apply', type='http', auth='none', methods=['POST'], csrf=False)
    def api_apply_permission(self, **kwargs):
        user_id, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        data = self._get_json_data()


        permission_type = data.get('permission_type')
        logistic = data.get('logistic')
        date = data.get('date')
        time_from = data.get('time_from')
        time_to = data.get('time_to')

        try:
            # تحويل التاريخ
            date = datetime.strptime(date, "%Y-%m-%d").date()


            user_env = request.env(user=user_id)

            # الحصول على الموظف
            employee = user_env['hr.employee'].sudo().search([
                ('user_id', '=', user_id)
            ], limit=1)

            if not employee:
                return self._response(success=False, message="الموظف غير موجود", status=404)

            existing_permissions = user_env['hr.permission'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '=', date),
                ('state', 'in', ['approved', 'to_approve']),
            ])

            for p in existing_permissions:
                if not (float(time_to) <= p.time_from or float(time_from) >= p.time_to):
                    return self._response(
                        success=False,
                        message="يوجد مهمة في نفس الوقت",
                        status=400
                    )

            # =========================
            # Create
            # =========================
            vals = {
                'employee_id': employee.id,
                'logistic': logistic,
                'date': date,
                'permission_type': permission_type,
                'time_from': float(time_from),
                'time_to': float(time_to),
            }

            permission = user_env['hr.permission'].sudo().create(vals)

            # Submit تلقائي
            permission.action_submit()

            return self._response(
                data={
                    "id": permission.id,
                    "employee_id": permission.employee_id.id,
                    "logistic": permission.logistic,
                    "time_from": permission.time_from,
                    "time_to": permission.time_to,
                    "state": permission.state,
                    "duration": permission.duration
                },
                message="تم إنشاء المهمة بنجاح",
                status=201
            )

        except Exception as e:
            return self._response(success=False, message=str(e), status=400)

    @http.route('/api/v1/notifications', type='http', auth='none', methods=['GET'], csrf=False)
    def get_notifications(self, **kwargs):
        # 1. التحقق من المصادقة بنفس طريقتك
        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        # 2. إعدادات التقسيم (Pagination)
        page = int(kwargs.get('page', 1))
        limit = int(kwargs.get('limit', 10))
        offset = (page - 1) * limit

        user_record = request.env['res.users'].sudo().browse(user)
        partner_id = user_record.partner_id.id

        domain = [
            ('partner_ids', 'in', [partner_id]),

        ]

        notification_model = request.env['mail.message'].sudo()

        total_count = notification_model.search_count(domain)
        notifications = notification_model.search(domain, limit=limit, offset=offset, order='date desc, id desc')

        notification_data = []
        for notif in notifications:
            notification_data.append({
                "id": notif.id,
                "subject": notif.subject or "بدون عنوان",
                "body": notif.body or "",
                "date": str(notif.date),
                "author": notif.author_id.name if notif.author_id else "النظام",
                "model": notif.model,
                "res_id": notif.res_id,
            })

        return self._response({
            "total_records": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "current_page": page,
            "records": notification_data
        })

    @http.route('/api/v1/next-checkout', type='http', auth='none', methods=['GET'], csrf=False)
    def get_next_checkout(self, **kwargs):

            # =========================
            # 1. AUTH
            user, error = self._verify_token()
            if error:
                return self._response(success=False, message=error, status=401)

            # =========================
            # 2. EMPLOYEE
            employee = request.env['hr.employee'].sudo().search([
                ('user_id', '=', user)
            ], limit=1)

            if not employee:
                return self._response(success=False, message="Employee not found", status=404)

            today = fields.Date.today()
            now = fields.Datetime.now()

            # =====================================================
            # Helper
            def float_to_datetime(base_date, float_hour):
                return datetime.combine(base_date, time(
                    hour=int(float_hour),
                    minute=int((float_hour % 1) * 60)
                ))

            # =====================================================
            # 3. CHECK-IN CHECK
            print(datetime.combine(today, time.min))
            print(datetime.combine(today, time.max))
            print(employee.id,employee.name)
            attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', datetime.combine(today, time.min)),
                ('check_in', '<=', datetime.combine(today, time.max)),
            ], order='check_in desc', limit=1)

            if not attendance or attendance.check_out:
                return self._response({
                    "type": "no_active_session",
                    "message": "Employee not checked in"
                })

            # =====================================================
            # 4. DEFAULT CHECKOUT
            DEFAULT_HOUR = 15.5  # 15:30
            default_checkout = float_to_datetime(today, DEFAULT_HOUR)

            # =====================================================
            # 5. EARLY LEAVE
            leave = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('request_date_from', '=', today),
                ('holiday_status_id.id', '=', 77),
                ('state', '=', 'validate')
            ], limit=1)

            if leave and leave.request_hour_from and leave.request_hour_to:
                leave_from = float_to_datetime(today, leave.request_hour_from)
                leave_to = float_to_datetime(today, leave.request_hour_to)


                if now < leave_from:
                    return self._response({
                        "type": "early_leave",
                        "next_checkout": fields.Datetime.to_string(leave_from)
                    })

                # أثناء الإذن (المفروض يكون خارج العمل)
                elif leave_from <= now <= leave_to:
                    return self._response({
                        "type": "early_leave",
                        "next_checkout": fields.Datetime.to_string(leave_to)
                    })


                elif now > leave_to:
                    pass

            # =====================================================
            # 6. MISSION
            mission = request.env['hr.permission'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '=', today),
                ('state', '=', 'approved')
            ], limit=1)

            if mission and mission.time_from and mission.time_to:
                mission_from = float_to_datetime(today, mission.time_from)
                mission_to = float_to_datetime(today, mission.time_to)

                # قبل المهمة
                if now < mission_from:
                    return self._response({
                        "type": "mission",
                        "next_checkout": fields.Datetime.to_string(mission_from)
                    })

                # أثناء المهمة
                elif mission_from <= now <= mission_to:
                    return self._response({
                        "type": "mission",
                        "next_checkout": fields.Datetime.to_string(mission_to)
                    })

                # بعد المهمة → يرجع يكمل شغل
                elif now > mission_to:
                    pass

            # =====================================================
            # 7. END OF DAY CHECK
            if now >= default_checkout:
                return self._response({
                    "type": "day_closed",
                    "message": "Working day finished"
                })

            # =====================================================
            # 8. DEFAULT
            return self._response({
                "type": "default",
                "next_checkout": fields.Datetime.to_string(default_checkout)
            })


    @http.route('/api/v5/employee/performance', type='http', auth='none', methods=['GET'], csrf=False)
    def performance(self, **kwargs):

        # =========================
        # 1. AUTH
        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user)
        ], limit=1)

        if not employee:
            return self._response(success=False, message="Employee not found", status=404)

        # =========================
        # 2. PERIOD
        date_from = kwargs.get('date_from')
        date_to = kwargs.get('date_to')

        today = fields.Date.today()
        start_date = today.replace(day=1)

        # =========================

        stats = request.env['bank.attendance.penalty'].sudo().search([
            ('employee_id', '=', employee.id),
            ('period_start', '=', start_date),
            ('period_end', '>=', today),
        ], limit=1)

        if not stats:
            return self._response(success=False, message="No stats found", status=404)

        absent_days = stats.absence_count or 0
        late_days = stats.late_count or 0
        early_exit_days = stats.early_leave_count or 0

        # =========================
        # 4. TASKS
        tasks = request.env['project.task'].sudo().search([
            ('user_ids', 'in', employee.user_id.id),
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
        ])

        total_tasks = len(tasks)
        done_tasks = len(tasks.filtered(lambda t: t.stage_id.fold))

        # =========================
        # 5. PENALTIES
        base_score = 100

        absence_penalty = absent_days * 10
        late_penalty = late_days * 3
        early_penalty = early_exit_days * 2

        total_penalty = absence_penalty + late_penalty + early_penalty


        task_score = 0

        if total_tasks > 0:
            completion_ratio = done_tasks / total_tasks
            task_score = completion_ratio * 30  # max 30

            # bonus لو أنجز كل المهام
            if completion_ratio == 1:
                task_score += 10

        # =========================
        # 7. FINAL SCORE
        score = base_score - total_penalty + task_score

        # clamp
        score = max(0, min(100, score))

        # =========================
        # 8. RATING
        if score >= 90:
            rating = "Excellent"
        elif score >= 85:
            rating = "Very Good"
        elif score >= 75:
            rating = "Good"
        elif score >= 60:
            rating = "Average"
        else:
            rating = "Needs Improvement"

        # =========================
        # 9. RESPONSE
        return self._response({
            "employee": employee.name,

            "period": {
                "from": date_from,
                "to": date_to
            },

            "stats": {
                "absent_days": absent_days,
                "late_days": late_days,
                "early_exit_days": early_exit_days
            },

            "tasks": {
                "total": total_tasks,
                "done": done_tasks,
                "completion_rate": round((done_tasks / total_tasks) * 100, 2) if total_tasks else 0,
                "task_score": round(task_score, 2)
            },

            "penalties": {
                "absence": absence_penalty,
                "late": late_penalty,
                "early_exit": early_penalty
            },

            "performance": {
                "score": round(score, 2),
                "rating": rating
            }
        })

