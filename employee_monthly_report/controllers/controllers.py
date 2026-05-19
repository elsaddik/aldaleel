# from odoo import http


# class EmployeeMonthlyReport(http.Controller):
#     @http.route('/employee_monthly_report/employee_monthly_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_monthly_report/employee_monthly_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_monthly_report.listing', {
#             'root': '/employee_monthly_report/employee_monthly_report',
#             'objects': http.request.env['employee_monthly_report.employee_monthly_report'].search([]),
#         })

#     @http.route('/employee_monthly_report/employee_monthly_report/objects/<model("employee_monthly_report.employee_monthly_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_monthly_report.object', {
#             'object': obj
#         })

