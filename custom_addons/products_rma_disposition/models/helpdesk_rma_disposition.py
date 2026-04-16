from odoo import api, fields, models
from odoo.exceptions import UserError


class HelpdeskRMALine(models.Model):
    _inherit = 'helpdesk.rma.line'

    disposition = fields.Selection([
        ('dispose', 'Dispose'),
    ], string='Disposition')
    
    disposal_reason_ids = fields.Many2many(
        comodel_name='stock.scrap.reason.tag',
        string='Dispose Reason',
    )
    
    scrap_id = fields.Many2one(
        'stock.scrap',
        string='Scrap Record',
        readonly=True,
        copy=False
    )

    @api.constrains('disposition', 'disposal_reason_ids')
    def _check_disposal_reason(self):
        for line in self:
            if line.disposition == 'dispose' and not line.disposal_reason_ids:
                raise UserError('Disposal Reason is required when Disposition is set to Dispose.')

    def action_process_disposition(self):
        for line in self:
            if not line.disposition:
                raise UserError('Please select a disposition before processing.')
            elif line.disposition == 'dispose':
                line._process_dispose()

    def _process_dispose(self):
        self.ensure_one()
        
        if self.scrap_id:
            raise UserError('Scrap record already created for this line.')
        
        if not self.disposal_reason_ids:
            raise UserError('Disposal Reason is required.')
        
        if not self.product_id:
            raise UserError('Product is required to process disposal.')
        
        # Get product variant from lot/serial if available
        if self.rma_lot_id and self.rma_lot_id.product_id:
            product = self.rma_lot_id.product_id
        else:
            product = self.env['product.product'].search([
                ('product_tmpl_id', '=', self.product_id.id)
            ], limit=1)
        
        if not product:
            raise UserError(f'No product variant found for {self.product_id.name}.')
        
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        location_src = warehouse.lot_stock_id if warehouse else False
        
        scrap_vals = {
            'product_id': product.id,
            'scrap_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'location_id': location_src.id if location_src else False,
            'lot_id': self.rma_lot_id.id if self.rma_lot_id else False,
            'origin': self.ticket_id.name,
            'scrap_reason_tag_ids': [(6, 0, self.disposal_reason_ids.ids)],
        }
        
        scrap = self.env['stock.scrap'].create(scrap_vals)
        scrap.action_validate()
        
        self.scrap_id = scrap.id
