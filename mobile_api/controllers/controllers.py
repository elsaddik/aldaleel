import json
import logging
import jwt
import datetime
from odoo import http, fields, _
from odoo.http import request, Response


from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)


SECRET_KEY = "Odoo19_Mobile_App_Secret_Key_2026"


class HrMobileAPI(http.Controller):

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

    # ==========================================
    # 1. Login & Token Generation
    # ==========================================
    @http.route('/api/v1/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        # استخراج البيانات من الـ Request Body
        data = self._get_json_data()
        db = data.get('db')
        login = data.get('login')
        password = data.get('password')
        print(db, login, password)
        # التأكد من وجود البيانات الأساسية
        if not db or not login or not password:
            return self._response(success=False, message="Missing db, login or password", status=400)

        try:
            # التصحيح هنا: نمرر فقط الـ 3 معاملات المطلوبة
            # Odoo سيتولى ربط الجلسة تلقائياً
            credential = {'login': login, 'password': password, 'type': 'password'}
            request.session.db = db
            uid = request.session.authenticate(request.env, credential)
            print(' request.session.db', request.session.db)
            if uid:
                # نستخدم sudo() لأن auth='none' تعني أننا لا نملك صلاحيات وصول بعد
                user = request.env['res.users'].sudo().browse(uid['uid'])
                print('user',user)
                employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
                print('employee',employee)
                # إعداد الـ Payload للـ JWT
                payload = {
                    'user_id': user.id,
                    # تنتهي الصلاحية بعد 30 يوم
                    'exp': datetime.utcnow() + timedelta(days=30),
                    'iat': datetime.utcnow(),
                }

                # إنشاء التوكن
                token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
                print(token)
                # تأكد من تحويل التوكن لـ string إذا كنت تستخدم إصدار قديم من PyJWT
                if isinstance(token, bytes):
                    token = token.decode('utf-8')

                return self._response({
                    "token": token,
                    "employee_id": employee.device_id if employee else None,
                    "user_id": user.id,
                    "name": employee.name if employee else user.name,
                    "job": employee.job_title or ""
                }, message="Login successful")

            return self._response(success=False, message="Invalid credentials", status=401)

        except Exception as e:
            _logger.error(f"Login Error: {str(e)}")
            return self._response(success=False, message="An internal error occurred", status=500)
    # ==========================================
    # 2. Leaves with Pagination (سجل الإجازات)
    # ==========================================
    @http.route('/api/v1/leaves', type='http', auth='none', methods=['GET'], csrf=False)
    def get_leaves(self, **kwargs):
        user, error = self._verify_token()
        if error: return self._response(success=False, message=error, status=401)

        # التعامل مع الـ Pagination
        page = int(kwargs.get('page', 1))
        limit = int(kwargs.get('limit', 10))
        offset = (page - 1) * limit

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
        print('employee',employee)
        domain = [('employee_id', '=', employee.id)]

        # حساب العدد الإجمالي للصفحات
        total_count = request.env['hr.leave'].sudo().search_count(domain)
        leaves = request.env['hr.leave'].sudo().search(domain, limit=limit, offset=offset, order='date_from desc')

        leave_data = []
        for leave in leaves:
            leave_data.append({
                "id": leave.id,
                "type": leave.holiday_status_id.name,
                "from": str(leave.date_from),
                "to": str(leave.date_to),
                "days": leave.number_of_days,
                "state": leave.state,
                # "description": leave.name or ""
            })

        return self._response({
            "total_records": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "current_page": page,
            "records": leave_data
        })

    # ==========================================
    # 3. Leave Balance (رصيد الإجازات)
    # ==========================================
    @http.route('/api/v1/leaves/balance', type='http', auth='none', methods=['GET'], csrf=False)
    def get_leave_balance(self, **kwargs):
        user, error = self._verify_token()
        if error: return self._response(success=False, message=error, status=401)
        _logger.info('user: %s', user)
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
        _logger.info('employee: %s', employee)
        leave_types = request.env['hr.leave.type'].sudo().search([])

        balances = []

        for l_type in leave_types:
            stats = l_type.get_allocation_data(employee)

            if employee in stats and stats[employee]:
                # ناخد أول عنصر
                data_tuple = stats[employee][0]

                # data في index 1
                data = data_tuple[1]

                balances.append({
                    "name": data_tuple[0],  # 'Paid Time Off'
                    "total": data.get('max_leaves', 0),
                    "used": data.get('leaves_taken', 0),
                    "remaining": data.get('virtual_remaining_leaves', 0),
                })
        return self._response({"balances": balances})

    @http.route('/api/v1/leaves/apply', type='http', auth='none', methods=['POST'], csrf=False)
    def api_apply_leave(self, **kwargs):
        user_id, error = self._verify_token()
        if error: return self._response(success=False, message=error, status=401)

        data = self._get_json_data()
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        holiday_status_id = data.get('leave_type_id')
        date_from = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S").date()

        try:
            user_env = request.env(user=user_id)
            employee = user_env['hr.employee'].sudo().search([('user_id', '=', user_id)], limit=1)


            existing_leave = user_env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date_from', '=', date_from),
                ('date_to', '=', date_to),
                ('state', 'not in', ['refuse', 'cancel'])
            ], limit=1)

            if existing_leave:
                return self._response(success=False, message="هذا الطلب موجود بالفعل أو يتداخل مع إجازة أخرى",
                                      status=400)

            # --- الإنشاء ---
            leave_vals = {
                'employee_id': employee.id,
                'holiday_status_id': int(holiday_status_id),
                # 'date_from': date_from,
                # 'date_to': date_to,
                'request_date_from': date_from,
                'request_date_to': date_to,
                'name': data.get('reason', ''),
            }

            # نستخدم sudo() لمرة واحدة عند الإنشاء فقط
            new_leave = user_env['hr.leave'].sudo().create(leave_vals)

            # التأكيد (Confirm)
            # ملحوظة: في Odoo 19 بعض الإعدادات قد تجعل create تطلق confirm تلقائياً
            # if new_leave.state == 'draft':
            #     new_leave.action_confirm()

            return self._response(data={"id": new_leave.id}, message="تم تقديم الطلب بنجاح", status=201)

        except Exception as e:
            return self._response(success=False, message=str(e), status=400)



    @http.route('/api/v1/payslips', type='http', auth='none', methods=['GET'], csrf=False)
    def get_payslips(self, **kwargs):
        user, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        page = int(kwargs.get('page', 1))
        limit = int(kwargs.get('limit', 10))
        offset = (page - 1) * limit

        user_env = request.env(user=user)

        employee = user_env['hr.employee'].sudo().search([
            ('user_id', '=', user)
        ], limit=1)

        if not employee:
            return self._response(success=False, message="الموظف غير موجود", status=404)

        domain = [
            ('employee_id', '=', employee.id),
            ('state', '=', 'validated')
        ]

        total_count = user_env['hr.payslip'].sudo().search_count(domain)

        slips = user_env['hr.payslip'].sudo().search(
            domain,
            limit=limit,
            offset=offset,
            order='date_from desc'
        )

        slip_data = []

        for slip in slips:

            # =========================
            # Payslip Lines
            # =========================
            lines = []
            for line in slip.line_ids:
                lines.append({
                    "name": line.name,
                    # "code": line.code,
                    # "quantity": line.quantity,
                    # "rate": line.rate,
                    "amount": line.amount,
                    # "total": line.total,
                    # "category": line.category_id.name if line.category_id else None
                })

            slip_data.append({
                "id": slip.id,
                "number": slip.name,
                "employee": slip.employee_id.name,
                "state": slip.state,
                "date_from": str(slip.date_from),
                "date_to": str(slip.date_to),

                # مهم: حسب النسخة
                "net_wage": slip.net_wage if hasattr(slip, 'net_wage') else None,
                "gross_wage": slip.gross_wage if hasattr(slip, 'gross_wage') else None,

                # fallback لو مفيش fields
                "total": sum(l.total for l in slip.line_ids),

                "lines": lines
            })

        return self._response({
            "total_records": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "current_page": page,
            "records": slip_data
        })

    # ==========================================
    # @http.route('/api/v1/payslips', type='http', auth='none', methods=['GET'], csrf=False)
    # def get_payslips(self, **kwargs):
    #     user, error = self._verify_token()
    #     if error: return self._response(success=False, message=error, status=401)
    #
    #     page = int(kwargs.get('page', 1))
    #     limit = int(kwargs.get('limit', 10))
    #     offset = (page - 1) * limit
    #
    #     employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)
    #     domain = [('employee_id', '=', employee.id), ('state', '=', 'validated')]
    #     print('user',user)
    #     total_count = request.env['hr.payslip'].sudo().search_count(domain)
    #     slips = request.env['hr.payslip'].sudo().search(domain, limit=limit, offset=offset, order='date_from desc')
    #
    #     slip_data = []
    #     for slip in slips:
    #         slip_data.append({
    #             "id": slip.id,
    #             "number": slip.name,
    #             "amount": slip.amount,
    #             "period": f"{slip.date_from} to {slip.date_to}",
    #         })
    #
    #     return self._response({
    #         "total_records": total_count,
    #         "total_pages": (total_count + limit - 1) // limit,
    #         "current_page": page,
    #         "records": slip_data
    #     })


    @http.route('/api/v1/permission/apply', type='http', auth='none', methods=['POST'], csrf=False)
    def api_apply_permission(self, **kwargs):
        user_id, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)

        data = self._get_json_data()

        date = data.get('date')
        permission_type = data.get('permission_type')
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

            # =========================
            # Check Overlap (زي الموديل)
            # =========================
            existing_permissions = user_env['hr.permission'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '=', date),
                ('state', 'in', ['approved', 'to_approve']),
            ])

            for p in existing_permissions:
                if not (float(time_to) <= p.time_from or float(time_from) >= p.time_to):
                    return self._response(
                        success=False,
                        message="يوجد إذن متداخل في نفس الوقت",
                        status=400
                    )

            # =========================
            # Create
            # =========================
            vals = {
                'employee_id': employee.id,
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
                    "state": permission.state,
                    "duration": permission.duration
                },
                message="تم إنشاء الإذن بنجاح",
                status=201
            )

        except Exception as e:
            return self._response(success=False, message=str(e), status=400)

    @http.route('/api/v1/attendance', type='http', auth='none', methods=['GET'], csrf=False)
    def get_attendance(self, **kwargs):
        user_id, error = self._verify_token()
        if error:
            return self._response(success=False, message=error, status=401)
        data = self._get_json_data()

        date_from = data.get('date_from')
        date_to = data.get('date_to')

        try:
            user_env = request.env(user=user_id)

            employee = user_env['hr.employee'].sudo().search([
                ('user_id', '=', user_id)
            ], limit=1)

            if not employee:
                return self._response(success=False, message="الموظف غير موجود", status=404)

            # =========================
            # Date Range
            # =========================
            if not date_from or not date_to:
                return self._response(success=False, message="يجب تحديد الفترة", status=400)

            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
            date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

            # =========================
            # Attendance Records
            # =========================
            attendances = user_env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', date_from),
                ('check_in', '<=', date_to),
            ])

            attendance_map = {}
            for att in attendances:
                day = att.check_in.date()
                attendance_map[day] = {
                    "check_in": str(att.check_in),
                    "check_out": str(att.check_out) if att.check_out else None,
                    "status": "present"
                }

            # =========================
            # Build Full Days List
            # =========================
            result = []
            current = date_from

            while current <= date_to:
                if current in attendance_map:
                    result.append({
                        "date": str(current),
                        "status": "present",
                        "check_in": attendance_map[current]["check_in"],
                        "check_out": attendance_map[current]["check_out"],
                        "is_absent": False
                    })
                else:
                    result.append({
                        "date": str(current),
                        "status": "absent",
                        "check_in": None,
                        "check_out": None,
                        "is_absent": True
                    })
                current += timedelta(days=1)

            return self._response(
                data=result,
                message="تم جلب الحضور بنجاح"
            )

        except Exception as e:
            return self._response(success=False, message=str(e), status=400)

    # ==========================================
    # 5. Apply for Loan (تقديم طلب سلفة)
    # ==========================================
    @http.route('/api/v1/loans/apply', type='http', auth='none', methods=['POST'], csrf=False)
    def apply_loan(self, **kwargs):
        user, error = self._verify_token()
        if error: return self._response(success=False, message=error, status=401)

        data = self._get_json_data()
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user)], limit=1)

        try:
            # ملاحظة: موديول السلف يختلف من شركة لأخرى، هذا مثال للـ OCA Loan
            loan = request.env['hr.loan'].sudo().create({
                'employee_id': employee.id,
                'loan_amount': data.get('amount'),
                'installment': data.get('installments'),  # عدد الأقساط
                'date': fields.Date.today(),
                'notes': data.get('reason', '')
            })
            return self._response({"loan_id": loan.id}, message="Loan request submitted")
        except Exception as e:
            return self._response(success=False, message=str(e), status=400)