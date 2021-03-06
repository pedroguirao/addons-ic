# Copyright
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from odoo import fields, models, api
import base64
from odoo.exceptions import ValidationError

class ViafirmaAccount(models.Model):
    _inherit = 'account.invoice'


    viafirma_ids = fields.One2many('viafirma','invoice_id')

    @api.multi
    def _get_viafirma(self):
        results = self.env['viafirma'].search([('invoice_id', '=', self.id)])
        self.viafirma_count = len(results)

    viafirma_count = fields.Integer('Viafirmas', compute=_get_viafirma, stored=False)

    @api.multi
    def action_view_viafirma(self):
        action = self.env.ref(
            'viafirma_account.action_viafirma_in_invoice').read()[0]
        return action

    @api.multi
    def do_viafirma(self):

        line_ids=[]
        line_id = self.env['viafirma.lines'].create({
            'partner_id': self.partner_id.id,
        })
        line_id_2 = self.env['viafirma.lines'].create({
            'partner_id': self.user_id.id,
        })
        line_ids.append(line_id.id)
        line_ids.append(line_id_2.id)

        view_id = self.env.ref('viafirma.viafirma_form').id

        viafirma_id = self.env['viafirma'].create({
            'name': str(self.env.user.name) + '-' + str(self.sequence_number_next_prefix) + str(
                self.sequence_number_next),
            'noti_text': str(self.env.user.name) + '-' + str(self.sequence_number_next_prefix) + str(
                self.sequence_number_next),
            'noti_subject': str(self.env.user.name) + '-' + str(self.sequence_number_next_prefix) + str(
                self.sequence_number_next),
            'line_ids': [(6, 0, line_ids)],
            'template_type': 'base64',
            # 'noti_text': 'texto',
            # 'noti_subject': 'subject',
            'invoice_id': self.id,
            'res_model': 'Facturas',
            'res_id': self.id,
            'res_id_name': str(self.sequence_number_next_prefix) + str(self.sequence_number_next),
            'document_policies': True,
        })

        pdf = self.env.ref('viafirma_account.viafirma_account_report').sudo().render_qweb_pdf([self.id])[0]

        viafirma_id.document_to_send = base64.encodebytes(pdf)

        return {
            'name': "Nuevo Viafirma",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'viafirma',
            'res_id': viafirma_id.id,
            #'view_id': view_id,
            'domain':[('id','=',viafirma_id)],
            'target': 'new',
        }


