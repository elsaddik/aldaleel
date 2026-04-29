from odoo import models, api
from odoo.exceptions import AccessError


# class ProjectTask(models.Model):
#     _inherit = 'project.task'
#
#     def write(self, vals):
#         if self.env.user.has_group('aldaleel_attendance_policy.group_limited_user'):
#             raise AccessError("عفواً، ليس لديك الصلاحية للتعديل مهام جديدة.")
#         return super().write(vals)
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         if  self.env.user.has_group('aldaleel_attendance_policy.group_limited_user'):
#             raise AccessError("عفواً، ليس لديك الصلاحية لإنشاء مهام جديدة.")
#         return (super(ProjectTask, self).create(vals_list))

from odoo import models, api
from odoo.exceptions import AccessError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    # ----------------------------------------
    # Helper: استخراج user_ids من commands
    # ----------------------------------------
    def _extract_user_ids(self, commands, current_ids=None):
        user_ids = set(current_ids or [])

        for cmd in commands:
            if cmd[0] == 6:  # replace all
                user_ids = set(cmd[2])
            elif cmd[0] == 4:  # add
                user_ids.add(cmd[1])
            elif cmd[0] == 3:  # remove
                user_ids.discard(cmd[1])
            elif cmd[0] == 5:  # remove all
                user_ids.clear()

        return list(user_ids)

    # ----------------------------------------
    # Helper: التحقق من التابعين
    # ----------------------------------------
    def _check_subordinates(self, user_ids):
        users = self.env['res.users'].browse(user_ids)

        for user in users:
            employee = user.employee_id

            if not employee or employee.parent_id.user_id != self.env.user:
                raise AccessError("يمكنك إسناد المهام لموظفيك فقط.")

    # ----------------------------------------
    # CREATE
    # ----------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        user = self.env.user

        # 🚫 الموظف العادي
        if user.has_group('aldaleel_attendance_policy.group_limited_user'):
            raise AccessError("عفواً، ليس لديك الصلاحية لإنشاء مهام.")

        # 👨‍💼 رئيس القسم
        if user.has_group('aldaleel_attendance_policy.group_department_manger_user'):
            for vals in vals_list:
                commands = vals.get('user_ids', [])
                user_ids = self._extract_user_ids(commands)

                if user_ids:
                    self._check_subordinates(user_ids)

        return super().create(vals_list)

    # ----------------------------------------
    # WRITE
    # ----------------------------------------
    def write(self, vals):
        user = self.env.user

        # 🚫 الموظف العادي
        if user.has_group('aldaleel_attendance_policy.group_limited_user'):
            raise AccessError("عفواً، ليس لديك الصلاحية لتعديل المهام.")

        # 👨‍💼 رئيس القسم
        if user.has_group('aldaleel_attendance_policy.group_department_manger_user'):

            if 'user_ids' in vals:
                for record in self:
                    current_ids = record.user_ids.ids
                    new_ids = self._extract_user_ids(vals['user_ids'], current_ids)

                    if new_ids:
                        self._check_subordinates(new_ids)

        return super().write(vals)

