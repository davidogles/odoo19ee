from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    is_rma = fields.Boolean(default=False, string='Is RMA?')
    rma_line_ids = fields.One2many('helpdesk.rma.line', 'ticket_id', string='RMAs')


class HelpdeskRMA(models.Model):
    _name = 'helpdesk.rma.line'
    _description = 'Helpdesk RMA Line'

    ticket_id = fields.Many2one('helpdesk.ticket')
    rma_lot_id = fields.Many2one('stock.lot', string="Lot/Serial")
    product_id = fields.Many2one('product.product', string="Product")
    sale_line_id = fields.Many2one('sale.order.line')
    reason_id = fields.Many2one('rma.reason', string="Return Reason")
