from odoo import fields, models, api


class LogisticRouteLine(models.Model):
    _name = 'fsm.logistic.route.line'
    _description = 'Logistic Route Line'

    name = fields.Char(
        required=True,
        string='Route',
    )
    fleet_vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='License Plate',
    )
    profitability = fields.Float(
         #compute='_compute_profitability',
    )
    is_selectable = fields.Boolean(
        #compute='_compute_is_selectable',
        store=True,
    )
    fsm_order_ids = fields.One2many(
        comodel_name='fsm.order',
        inverse_name='logistic_route_line_id',
        string='Portes',
        #domain="[('is_selectable', '=', True)]",
    )
    active = fields.Boolean(
        default=True,
    )

    note = fields.Html()

    @api.depends('create_date')
    def _compute_task_km(self):
        for record in self:
            this_km = 0
            for ta in record.fsm_order_ids:
                this_km += ta.km
            record['km'] = this_km

    km = fields.Float(
        store=False,
        compute=_compute_task_km,
        string='Km',
    )

    #@api.depends('task_ids.stage_id.is_logistic_draft')
    #def _compute_is_selectable(self):
    #    for route in self:
    #        route.is_selectable = any(route.mapped(
    #            'task_ids.stage_id.is_logistic_draft'))

    #@api.depends('task_ids.profitability')
    #def _compute_profitability(self):
    #    for route in self:
    #        route.profitability = sum(route.mapped('task_ids.profitability'))