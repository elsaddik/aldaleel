# from odoo import http


# class EmployeeAlerts(http.Controller):
#     @http.route('/employee_alerts/employee_alerts', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/employee_alerts/employee_alerts/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('employee_alerts.listing', {
#             'root': '/employee_alerts/employee_alerts',
#             'objects': http.request.env['employee_alerts.employee_alerts'].search([]),
#         })

#     @http.route('/employee_alerts/employee_alerts/objects/<model("employee_alerts.employee_alerts"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('employee_alerts.object', {
#             'object': obj
#         })

