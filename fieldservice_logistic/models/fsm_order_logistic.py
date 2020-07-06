from odoo import fields, models, api


class FsmOrderLogistic(models.Model):
    _inherit = 'fsm.order'

    km = fields.Float('Kilómetros')
    kg = fields.Float('Kg')
    units = fields.Float('Unidades')

    location_dest_id = fields.Many2one(
        relation='res.partner',
        related='sale_id.partner_shipping_id',
        string='Dir. de entrega',
        help='Delivery address for current sales order.'
    )

    logistic_route_line_id = fields.Many2one('logistic.route.line',string='Ruta')

    date_up = fields.Datetime('Cargardo')
    date_down = fields.Datetime('Descargado')

    @api.depends('location_dest_id', 'location_id', 'date_up', 'date_down')
    def _get_next_location(self):
        # Si no hay fecha de recogida, hay que ir a location_id, en caso contrario si no hay de entrega hay que ir a
        # x_location_dest_id, y si están ambas la ruta está hecha y este campo es nulo
        for record in self:
            if (not record.date_up and not record.date_down):
                record['location_next_id'] = record.location_id.partner_id.id
            elif (record.date_up and not record.date_down):
                record['location_next_id'] = record.location_dest_id.id

    location_next_id = fields.Many2one(
        relation='res.partner',
        string='Siguiente parada',
        compute=_get_next_location
    )

    #location_next_latitude = fields.Float(related='location_next_id.partner_latitude', stored='False')
    #location_next_longitude = fields.Float(related='location_next_id.partner_longitude', stored='False')
    #location_next_country = fields.Float(related='location_next_id.country_id.name', stored='False')


    @api.multi
    def delivered_collected(self):
        #self.ensureone()
        #Traido de V13
        for porte in self:
            if porte.date_up:
                porte.date_down = fields.datetime.now()
            else:
                porte.date_up = fields.datetime.now()

    def action_complete_auto(self):
        self.date_end = fields.datetime.now()
        self.action_complete()

    def action_start_auto(self):
        self.date_start = fields.datetime.now()
        self.action_start()
