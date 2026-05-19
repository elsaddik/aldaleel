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

    state_employee_exception = fields.Selection([
        ('is_deliver', 'Deliver'),
        ('is_exception_checkout', 'Exception Checkout')
    ])

    
    @api.model
    def fetch_attendance_from_middleware(self):
        url = "http://127.0.0.1:3000/api/v1/getAttendenceData"

        try:
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                _logger.info("Middleware endpoint called successfully")
            else:
                _logger.warning(f"Middleware returned status: {response.status_code}")

        except Exception as e:
            _logger.error(f"Error calling middleware: {str(e)}")



class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    device_id = fields.Char(string="Device ID", readonly=True)
    device_make = fields.Char(string="Make", readonly=True)

    state_employee_exception = fields.Selection([
        ('is_deliver', 'Deliver'),
        ('is_exception_checkout', 'Exception Checkout')
    ])
