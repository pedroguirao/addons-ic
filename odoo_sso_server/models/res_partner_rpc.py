# Copyright
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api


class PartnerConnFields(models.Model):
    _inherit = 'res.partner'


    rpcu = fields.Char()
    rpcp = fields.Char()
