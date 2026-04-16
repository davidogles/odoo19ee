from odoo import api, fields, models


class RmaReason(models.Model):
    _name = 'rma.reason'
    _description = 'RMA Return Reason'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Short code for integrations")
    active = fields.Boolean(default=True)
