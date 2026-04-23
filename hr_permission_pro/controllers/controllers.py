# from odoo import http


# class HrPermissionPro(http.Controller):
#     @http.route('/hr_permission_pro/hr_permission_pro', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hr_permission_pro/hr_permission_pro/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hr_permission_pro.listing', {
#             'root': '/hr_permission_pro/hr_permission_pro',
#             'objects': http.request.env['hr_permission_pro.hr_permission_pro'].search([]),
#         })

#     @http.route('/hr_permission_pro/hr_permission_pro/objects/<model("hr_permission_pro.hr_permission_pro"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_permission_pro.object', {
#             'object': obj
#         })

