# Copyright
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models, api

class PartnerCredentials(models.Model):
    _name = 'partner.credentials'
    _description = 'Manage sites and instances from Master Odoo'

    name = fields.Char(string='Nombre')
    url_credentials = fields.Char(string='Url')
    type = fields.Selection([
        ('odoo', 'Odoo'), ('web', 'Web')
    ])
    partner_id = fields.Many2one('res.partner',string='Partner')
    user = fields.Char('User')
    password = fields.Char('Password')
    public = fields.Boolean('Public')

