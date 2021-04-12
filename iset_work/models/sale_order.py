from odoo import _, api, fields, models

import logging

_logger = logging.getLogger(__name__)


class SaleOrderiSet(models.Model):
    _inherit = 'sale.order'

    iset_work_id = fields.Many2one('iset.work', 'iSet Work')
