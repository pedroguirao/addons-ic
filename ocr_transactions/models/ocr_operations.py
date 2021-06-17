# Copyright
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
from time import sleep
from datetime import datetime, timedelta
import json
from random import randint
import requests
import img2pdf
from PIL import Image
import io
from odoo import fields, models, api
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.queue_job.job import job
except ImportError:
    _logger.debug('Can not `import queue_job`.')
    import functools


class OcrOperations(models.Model):
    _name = 'ocr.operations'
    _description = 'Comunication methods for OCR API'

    @api.multi
    def create_apikey_list(self):
        ApiKeys = []
        if self.env.user.company_id.ocr_delivery_company:
            ocr_clients = self.env['partner.credentials'].sudo().search([])
            for client in ocr_clients:
                if client.client_api_key:
                    ApiKeys.append(client.client_api_key)
        if self.env.user.company_id.api_key:
            ApiKeys.append(self.env.user.company_id.api_key)
        if len(ApiKeys) > 0:
            return ApiKeys
        else:
            raise ValidationError(
                "You must set Api Key in company and/or credentials form.")

    @api.multi
    def get_header(self, api_key):
        if api_key:
            header = {
                'X-API_KEY': api_key,
            }
            return header

    @api.multi
    def random_with_n_digits(self, n):
        range_start = 10 ** (n - 1)
        range_end = (10 ** n) - 1
        return randint(range_start, range_end)

    @api.multi
    def clean_vat(self, vat):
        if len(vat) > 9:
            vat_cleaned = vat[2:11]
        else:
            vat_cleaned = vat
        #vat_cleaned = vat.replace('-', '')
        #vat_cleaned = vat_cleaned.replace(" ", "")
        #vat_cleaned = vat_cleaned.replace('ES', '')
        #vat_cleaned = vat_cleaned.replace('FR', '')
        #vat_cleaned = vat_cleaned.replace('IT', '')
        #vat_cleaned = vat_cleaned.replace('PR', '')
        #vat_cleaned = vat_cleaned.replace('DE', '')
        vat_cleaned.upper()
        return vat_cleaned

    @api.multi
    def get_partner_by_vat(self, vat):
        vat_cleaned = self.clean_vat(vat.value)
        partner = self.env['res.partner'].search(["|",
                                                  ('vat', '=', vat.value),
                                                  ('vat', '=', vat_cleaned),
                                                  ], limit=1)

        if partner:
            return partner
        else:
            partners = self.env['res.partner'].search([])
            for p in partners:
                if p.vat != False:
                    p_vat = self.clean_vat(p.vat)
                    if p_vat == vat_cleaned:
                        partner = p
            if partner:
                return partner
            else:
                return False

    @api.multi
    def get_documents_data(self, api_transaction_url, headers):
        response = requests.get(api_transaction_url, headers=headers)

        if response.status_code == 200:
            return json.loads(response.content.decode('utf-8'))
        else:
            error = json.loads(response.content.decode('utf-8'))
            _logger.info(
                "Error from OCR server  %s" % error
            )

    @api.multi
    def create_queue_invoice_transactions(self, transactions_by_state, key):
        #### Comprobar si hay que crearlo, actualizarlo o ignorarlo ####
        for i in range(len(transactions_by_state['FACTURAS'])):
            token = transactions_by_state['FACTURAS'][i]['token']
            #client = transactions_by_state['FACTURAS'][i]['client']
            exist = self.env['ocr.transactions'].search([
                ("token", "=", token),
            ], limit=1)
            # No se Borran facturas, solo actualizamos el transaction si no hay líneas de factura
            # Si hay lineas no debe actualizar estado
            if exist.token:
                if exist.state != transactions_by_state['FACTURAS'][i]['status']:
                    exist.state = transactions_by_state['FACTURAS'][i]['status']
            else:

                type_doc = transactions_by_state['FACTURAS'][i]['type']
                if transactions_by_state['FACTURAS'][i]['type'] == "emitida":
                    type_doc = "out_invoice"
                if transactions_by_state['FACTURAS'][i]['type'] == "recibida":
                    type_doc = "in_invoice"
                # Añadir método para name = cliente limpiando NIF. Actualmente si viene de fuera de Odoo se crea con el NIF que manda biyectiva que no es el registrado en Odoo.
                ocr_transaction = self.env['ocr.transactions'].create({
                    'state': transactions_by_state['FACTURAS'][i]['status'],
                    'type': type_doc,
                    'name': transactions_by_state['FACTURAS'][i]['client'],
                    'token': transactions_by_state['FACTURAS'][i]['token'],
                    'customer_api_key': key,
                    'next_token': False,
                    'previus_token': False,
                    'create_date': transactions_by_state['FACTURAS'][i]['created_at'],
                    'write_date': transactions_by_state['FACTURAS'][i]['updated_at'],
                })

    @api.multi
    def update_transactions_error_code(self, t, api_transaction_url, header):
        #for t in transactions_with_errors:
        api_transaction_url_token = "%s%s" % (api_transaction_url, t.token)
        ocr_document_data = self.get_documents_data(api_transaction_url_token, header)
        t.json_text = ocr_document_data
        if ocr_document_data:
            if ocr_document_data["result"]["status"] == "ERROR":
                t.transaction_error = ocr_document_data["result"]["reason"]
                t.state = 'error'
                t.cleared = True

    @api.multi
    def ocr_update_values(self, t, ocr_document_data, type_values):
        for v in ocr_document_data["result"][type_values].values():
            ocr_values = self.env['ocr.values'].sudo().search([
                ('token', '=', t.token),
                ('name', '=', v["ERPName"])])
            for ocrv in ocr_values:
                ocrv.value = v["Value"]["Text"]
            if not ocr_values:
                self.env['ocr.values'].sudo().create({
                    'token': t.token,
                    'name': v["ERPName"],
                    'value': v["Value"]["Text"],
                    'ocr_transaction_id': t.id,
                })
        t.state = 'downloaded'

    @api.multi
    def create_invoices(self, t, api_transaction_url, header):
        #for t in transactions_processed:
        invoice = self.env['account.invoice'].sudo().search([
            ("ocr_transaction_id.token", "=", t.token),
        ], limit=1)
        previus_ocr_values = self.env['ocr.values'].sudo().search([
            ("ocr_transaction_id", "=", t.id)
        ])

        api_transaction_url_token = "%s%s" % (api_transaction_url, t.token)
        ocr_document_data = self.get_documents_data(api_transaction_url_token, header)
        t.json_text = ocr_document_data

        if ocr_document_data:
            if invoice:
                if not invoice.invoice_line_ids:
                    basic_values = self.ocr_update_values(t, ocr_document_data, "basic")
                    extended_values = self.ocr_update_values(t, ocr_document_data, "extended")
                    t.state = 'downloaded'
                else:
                    t.state = 'downloaded'

            elif not previus_ocr_values:

                #if ocr_document_data["result"]["status"] == "ERROR":
                #    t.transaction_error = ocr_document_data["result"]["reason"]
                #    t.state = 'downloaded'
                for v in ocr_document_data["result"]["basic"].values():
                    self.env['ocr.values'].sudo().create({
                        'token': t.token,
                        'name': v["ERPName"],
                        'value': v["Value"]["Text"],
                        'ocr_transaction_id': t.id,
                    })
                for v in ocr_document_data["result"]["extended"].values():
                    self.env['ocr.values'].sudo().create({
                        'token': t.token,
                        'name': v["ERPName"],
                        'value': v["Value"]["Text"],
                        'ocr_transaction_id': t.id,
                    })

                account600_id = self.env['ir.model.data'].search([
                    ('name', '=', '1_account_common_600'),
                    ('model', '=', 'account.account')
                ])
                account600 = self.env['account.account'].search([('id', '=', account600_id.res_id)])
                account700_id = self.env['ir.model.data'].search([
                    ('name', '=', '1_account_common_7000'),
                    ('model', '=', 'account.account')
                ])
                account700 = self.env['account.account'].search([('id', '=', account700_id.res_id)])

                partner_vat = self.env['ocr.values'].sudo().search([
                    ('token', '=', t.token), ('name', '=', 'CIF')], limit=1)

                if partner_vat:
                    if len(partner_vat.value) != 11:
                        partner = self.get_partner_by_vat(partner_vat)
                        partner_name_value = "NIF_no_valido_" + str(partner_vat.value)
                        partner_vat = False
                else:
                    random = self.random_with_n_digits(11)
                    partner_name_value = "NIF_no_válido_" + str(random)

                if not partner:
                    partner = self.env['res.partner'].sudo().create({
                        'name': str(partner_name_value),
                        #'vat': False,
                        'company_type': 'company',
                        'ocr_sale_account_id': account700.id,
                        'ocr_purchase_account_id': account600.id,
                    })
                    #partner = self.env['res.partner'].search([('vat', "=", 'ES12345678Z'),'|',('active', "=", False),('active', "=", True)])

                if partner:
                    date = self.env['ocr.values'].sudo().search([
                        ('token', '=', t.token), ('name', '=', 'Fecha')], limit=1)
                    #ValueError: time data '25 Junio 2020' does not match format '%d/%m/%Y'
                    if date.value:
                        try:
                            date_invoice = datetime.strptime(date.value, '%d/%m/%Y').date()
                        except Exception as e:
                            date_invoice = False
                            t.transaction_error = e
                    else:
                        date_invoice = False

                    reference = self.env['ocr.values'].sudo().search([
                        ('token', '=', t.token), ('name', '=', 'NumFactura')], limit=1)

                    if not reference:
                        reference_value = False
                    else:
                        reference_value = reference.value

                    if t.type == 'in_invoice':
                        invoice = self.env['account.invoice'].sudo().create({
                            'partner_id': partner.id,
                            'type': t.type,
                            'reference': reference_value,
                            'date_invoice': date_invoice,
                            'ocr_transaction_id': t.id,
                            'is_ocr': True,
                        })
                    else:
                        invoice = self.env['account.invoice'].sudo().create({
                            'partner_id': partner.id,
                            'type': t.type,
                            'date_invoice': date_invoice,
                            'ocr_transaction_id': t.id,
                            'is_ocr': True,
                        })

                if invoice:
                    t.state = 'downloaded'
                    t.invoice_id = invoice.id

                    if "document" in ocr_document_data:
                        link = ocr_document_data['document']
                        file_type = 'application/pdf'
                        attachment = self.generate_attachment(link, header, invoice, t, file_type)
                    else:
                        link = ocr_document_data['image']
                        file_type = 'image/jpeg'
                        attachment = self.img_2_pdf(link, header, invoice, t, file_type)
                    #attachment = self.generate_attachment(link, header, invoice, t, file_type)

                    body = "<p>created with OCR Documents</p>"
                    if attachment:
                        invoice.message_post(body=body, attachment_ids=[attachment.id])
                        invoice.message_main_attachment_id = [(4, attachment.id)]

            else:
                t.state = 'downloaded'

    @api.multi
    def img_2_pdf(self, api_img_url, headers, document, ocr_document, file_type):

        response = requests.get(api_img_url, headers=headers)

        if response.status_code == 200:

            with open('/tmp/img.jpg', 'wb') as f:
                f.write(response.content)

            img = Image.open('/tmp/img.jpg')
            pdf_bytes = img2pdf.convert(img.filename)

            img_file_encode = base64.b64encode(pdf_bytes)

            return self.env['ir.attachment'].sudo().create({
                'name': str(ocr_document.name) + "_" + str(ocr_document.id),
                'type': 'binary',
                'datas': img_file_encode,
                'datas_fname': str(ocr_document.name) + "_" + str(ocr_document.id),
                'store_fname': str(ocr_document.name) + "_" + str(ocr_document.id),
                'res_model': 'account.invoice',
                'res_id': document.id,
                'mimetype': 'application/pdf'
            })

        elif response.status_code == 400:
            ocr_document.transaction_error = "Error 400"
            _logger.info(
                "Error from OCR server  %s" % ocr_document.transaction_error
            )
        else:
            ocr_document.transaction_error = json.loads(response.content.decode('utf-8'))
            _logger.info(
                "Error from OCR server  %s" % ocr_document.transaction_error
            )

    @api.multi
    def generate_attachment(self, api_img_url, headers, document, ocr_document, file_type):

        response = requests.get(api_img_url, headers=headers)

        if response.status_code == 200:

            img_file_encode = base64.b64encode(response.content)

            return self.env['ir.attachment'].sudo().create({
                'name': str(ocr_document.name) + "_" + str(ocr_document.id),
                'type': 'binary',
                'datas': img_file_encode,
                'datas_fname': str(ocr_document.name) + "_" + str(ocr_document.id),
                'store_fname': str(ocr_document.name) + "_" + str(ocr_document.id),
                'res_model': 'account.invoice',
                'res_id': document.id,
                'mimetype': file_type
            })

        elif response.status_code == 400:
            ocr_document.transaction_error = "Error 400"
            _logger.info(
                "Error from OCR server  %s" % ocr_document.transaction_error
            )
        else:
            ocr_document.transaction_error = json.loads(response.content.decode('utf-8'))
            _logger.info(
                "Error from OCR server  %s" % ocr_document.transaction_error
            )

    @api.multi
    def mark_uploads_done(self, t):
        #for t in transactions_processed:
        if t.ocr_upload_id:
            if t.ocr_upload_id.state != "done":
                f_state = "done"
                for transaction in t.ocr_upload_id.ocr_transaction_ids:
                    if transaction.state == "error":
                        f_state = "error"
                    elif transaction.state == "processing" or transaction.state == "sending":
                        f_state = "processing"

                t.ocr_upload_id.state = f_state

    @api.multi
    def check_dbcopy_instance(self):
        company = self.env.user.company_id

        if company.master_db_name != self.env.cr.dbname:
            cron_job = self.env['ir.cron'].sudo().search([('name', '=', '=> OCR transactions GET')])
            if cron_job:
                cron_job.active = False
            jobs_started = self.env['queue.job'].sudo().search([
                                                        ('state', '=', 'started'),
                                                        ])
            for job in jobs_started:
                job.unlink()
            jobs = self.env['queue.job'].sudo().search(["|",
                                                        ('state', '=', 'pending'),
                                                        ('state', '=', 'enqueued'),
                                                        ])
            for job in jobs:
                job.state = 'done'

    @api.multi
    def prepare_ocr_get_transactions(self):
        company = self.env.user.company_id

        if company.ocr_disable_queue_jobs:
            company.action_get_invoices()
        else:
            jobs = self.env['queue.job'].sudo().search(["|",
                                                        ('state', '=', 'pending'), ('state', '=', 'enqueued')
                                                        ])
            eta = 20 + (len(jobs) * 20)

            queue_obj = self.env['queue.job'].sudo()
            new_delay = company.sudo().with_context(
                company_id=company.id
            ).with_delay(eta=eta).action_queue_get_invoices()
            job = queue_obj.search([
                ('uuid', '=', new_delay.uuid)
            ], limit=1)
            company.sudo().ocr_transactions_jobs_ids |= job

    @job
    @api.multi
    def action_queue_get_invoices(self):

        self.action_get_invoices()

    @api.multi
    def action_get_invoices(self):
        ########## Comprobamos si somos OCR Manager ####################
        ApiKeys = self.create_apikey_list()
        ########## Actualmente solo traemos facturas ###################
        api_transaction_url = "%s/facturas/" % self.env.user.company_id.api_domain
        ########## Hacemos una consulta por cada ApiKey ################
        for key in ApiKeys:
            header = self.get_header(key)
            print("key", key)
            transactions_by_state = self.get_documents_data(api_transaction_url, header)
            ############### Control status donwloaded #######################
            if transactions_by_state:
                self.create_queue_invoice_transactions(transactions_by_state, key)

            transactions_processed = self.env['ocr.transactions'].search([
                                                                            ("state", "=", 'processed'),
                                                                            ("customer_api_key", "=", key),
                                                                        ], limit=30)
            transactions_with_errors = self.env['ocr.transactions'].search([
                                                                        ("state", "=", 'error'),
                                                                        ("customer_api_key", "=", key),
                                                                        ("cleared", "=", False),
                                                                          ], limit=10)
            if transactions_with_errors:
                for t_error in transactions_processed:
                    try:
                        self.update_transactions_error_code(t_error, api_transaction_url, header)
                    except Exception as e:
                        t_error.transaction_error = str(t_error.transaction_error) + str(e)
                    try:
                        self.create_invoices(t_error, api_transaction_url, header)
                    except Exception as e:
                        t_error.transaction_error = str(t_error.transaction_error) + str(e)
                    try:
                        self.mark_uploads_done(t_error)
                    except Exception as e:
                        t_error.transaction_error = str(t_error.transaction_error) + str(e)

            if transactions_processed:
                for t in transactions_processed:
                    try:
                        self.create_invoices(t, api_transaction_url, header)
                    except Exception as e:
                        t.transaction_error = str(t.transaction_error) + str(e)
                    try:
                        self.mark_uploads_done(t)
                    except Exception as e:
                        t.transaction_error = str(t.transaction_error) + str(e)

            time = datetime.now()
            self.env.user.company_id.last_conn_date = time.strftime('%Y-%m-%d %H:%M:%S')
            sleep(3)

    @api.multi
    def ocr_delete_old_transactions(self):
        transactions = self.env['ocr.transactions'].sudo().search([])
        ## DOMAIN : '|', ("state", "=", 'downloaded'), ("state", "=", 'error')
        for transaction in transactions:
            if (datetime.utcnow() - transaction.write_date) > timedelta(days=25):
                transaction.cleared = True

    @api.multi
    def ocr_restart_halted_queue_jobs(self):
        jobs = self.env['queue.job'].sudo().search(["|",
                                                    ('state', '=', 'started'), ('state', '=', 'enqueued')
                                                    ])
        for job in jobs:
            desired_eta = datetime.now() + timedelta(seconds=200)

            if (datetime.utcnow() - job.date_created) > timedelta(minutes=30):
                job.state = 'pending'

    @api.multi
    def ocr_mark_invoice_as_ocr(self):
        invoices = self.env['account.invoice'].sudo().search([('type', '=', 'in_invoice')])
        for invoice in invoices:
            invoice.is_ocr = True



