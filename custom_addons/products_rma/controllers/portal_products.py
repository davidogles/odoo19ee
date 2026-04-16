from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from collections import defaultdict


class CustomerPortal(portal.CustomerPortal):

    def _get_my_products_count(self, partner):
        SaleOrderLine = request.env['sale.order.line'].sudo()

        domain = [
            ('order_id.partner_id', 'child_of', partner.id),
            ('order_id.state', 'in', ['sale', 'done']),
            ('product_id', '!=', False),
        ]

        return len(SaleOrderLine.search(domain).mapped('product_id'))

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'product_count' in counters:
            values['product_count'] = self._get_my_products_count(
                request.env.user.partner_id
            )

        return values

    def _get_my_products_searchbar_filters(self):
        return {
            'all': {
                'label': 'All',
                'domain': []
            },
            'serialized': {
                'label': 'Serialized',
                'domain': [('product_id.tracking', '=', 'serial')]
            },
            'non_serialized': {
                'label': 'Non-Serialized',
                'domain': [('product_id.tracking', '!=', 'serial')]
            },
        }

    @http.route(['/my/products','/my/products/page/<int:page>',], type='http', auth="user", website=True)
    def portal_my_products(self, page=1, filterby='all', **kw):

        partner = request.env.user.partner_id
        commercial_partner = partner.commercial_partner_id
        searchbar_filters = self._get_my_products_searchbar_filters()

        MoveLine = request.env['stock.move.line'].sudo()

        all_lines = MoveLine.search([
            ('state', '=', 'done'),
            ('move_id.picking_id.partner_id', 'child_of', commercial_partner.id),
        ])

        lot_balance = defaultdict(int)
        product_balance = defaultdict(float)

        latest_outgoing_per_lot = {}
        latest_outgoing_per_product = {}

        for line in all_lines:
            picking = line.move_id.picking_id
            picking_code = picking.picking_type_id.code
            product = line.product_id

            if product.tracking == 'serial' and line.lot_id:

                lot_id = line.lot_id.id

                if picking_code == 'outgoing':
                    lot_balance[lot_id] += 1

                    if (
                            lot_id not in latest_outgoing_per_lot
                            or line.date > latest_outgoing_per_lot[lot_id].date
                    ):
                        latest_outgoing_per_lot[lot_id] = line

                elif picking_code == 'incoming':
                    lot_balance[lot_id] -= 1

            else:
                product_id = product.id

                if picking_code == 'outgoing':
                    product_balance[product_id] += line.qty_done

                    if (
                            product_id not in latest_outgoing_per_product
                            or line.date > latest_outgoing_per_product[product_id].date
                    ):
                        latest_outgoing_per_product[product_id] = line

                elif picking_code == 'incoming':
                    product_balance[product_id] -= line.qty_done

        owned_lot_ids = [
            lot_id for lot_id, qty in lot_balance.items() if qty > 0
        ]

        owned_product_ids = [
            product_id for product_id, qty in product_balance.items() if qty > 0
        ]

        move_lines = MoveLine.browse(
            [latest_outgoing_per_lot[l].id for l in owned_lot_ids if l in latest_outgoing_per_lot]
            +
            [latest_outgoing_per_product[p].id for p in owned_product_ids if p in latest_outgoing_per_product]
        )

        extra_domain = searchbar_filters.get(
            filterby, searchbar_filters['all']
        )['domain']

        if extra_domain:
            move_lines = move_lines.filtered_domain(extra_domain)

        # Sort newest first
        move_lines = move_lines.sorted(key=lambda l: l.date, reverse=True)

        page_size = 10
        total = len(move_lines)

        pager = portal_pager(
            url="/my/products",
            url_args={'filterby': filterby},
            total=total,
            page=page,
            step=page_size,
        )

        offset = pager['offset']
        move_lines = move_lines[offset: offset + page_size]

        has_products = bool(move_lines)

        values = {
            'move_lines': move_lines,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'page_name': 'my_products',
            'default_url': '/my/products',
            'pager': pager,
            'has_serialized_products': has_products,
        }

        return request.render('products_rma.portal_my_products', values)

    def _rma_get_search_domain(self, search_in, search):
        if not search:
            return []

        if search_in == 'serial':
            return [('lot_id.name', 'ilike', search)]

        elif search_in == 'product':
            return [('product_id.name', 'ilike', search)]

        else:  # 'all'
            return ['|',
                    ('lot_id.name', 'ilike', search),
                    ('product_id.name', 'ilike', search)]

    def _rma_get_searchbar_inputs(self):
        return {
            'serial': {
                'input': 'serial',
                'label': 'Serial',
            },
            'product': {
                'input': 'product',
                'label': 'Product',
            },
            'all': {
                'input': 'all',
                'label': 'Serial & Product',
            },
        }

    def _rma_get_searchbar_sortings(self):
        return {
            'date': {
                'label': 'Newest',
                'order': 'date desc',
            },
            'serial': {
                'label': 'Serial',
                'order': 'lot_id.name asc',
            },
            'product': {
                'label': 'Product',
                'order': 'product_id.name asc',
            },
        }

    @http.route(['/my/products/rma', '/my/products/rma/page/<int:page>'], type='http', auth='user', website=True)
    def portal_rma_form(self, page=1, search=None, search_in='serial', sortby='date', **kw):

        partner = request.env.user.partner_id
        commercial_partner = partner.commercial_partner_id

        MoveLine = request.env['stock.move.line'].sudo()

        domain = [
            ('state', '=', 'done'),
            ('move_id.picking_id.partner_id', 'child_of', commercial_partner.id),
            ('lot_id', '!=', False),
        ]

        searchbar_inputs = self._rma_get_searchbar_inputs()
        searchbar_sortings = self._rma_get_searchbar_sortings()

        # default fallback
        sortby = sortby or 'date'

        order = searchbar_sortings[sortby]['order']
        search_in = search_in or 'serial'

        domain += self._rma_get_search_domain(search_in, search)

        all_lines = MoveLine.search(domain)

        from collections import defaultdict
        lot_balance = defaultdict(int)
        latest_outgoing_per_lot = {}

        for line in all_lines:
            picking_code = line.move_id.picking_id.picking_type_id.code
            lot_id = line.lot_id.id

            if picking_code == 'outgoing':
                lot_balance[lot_id] += 1
                if lot_id not in latest_outgoing_per_lot or line.date > latest_outgoing_per_lot[lot_id].date:
                    latest_outgoing_per_lot[lot_id] = line

            elif line.move_id.origin_returned_move_id:
                lot_balance[lot_id] -= 1

        owned_lot_ids = [lot_id for lot_id, qty in lot_balance.items() if qty > 0]

        move_lines = MoveLine.browse([
            latest_outgoing_per_lot[lot_id].id
            for lot_id in owned_lot_ids
            if lot_id in latest_outgoing_per_lot
        ]).sorted(key=lambda l: l.date, reverse=True)

        if sortby == 'date':
            move_lines = move_lines.sorted(key=lambda l: l.date, reverse=True)

        elif sortby == 'serial':
            move_lines = move_lines.sorted(key=lambda l: l.lot_id.name or '')

        elif sortby == 'product':
            move_lines = move_lines.sorted(key=lambda l: l.product_id.name or '')

        page_size = 10
        total = len(move_lines)

        url_args = dict(
            search=search,
            search_in=search_in,
            sortby=sortby,
            filterby='all',
        )

        pager = portal_pager(
            url="/my/products/rma",
            url_args=url_args,
            total=total,
            page=page,
            step=page_size,
        )

        move_lines = move_lines[pager['offset']: pager['offset'] + page_size]

        reasons = request.env['rma.reason'].sudo().search([])

        existing_rmas = request.env['helpdesk.rma.line'].sudo().search([
            ('rma_lot_id', 'in', owned_lot_ids),
            ('ticket_id.stage_id.name', 'not in', ['Solved', 'Cancelled']),
        ])

        rma_map = {rma.rma_lot_id.id: rma.ticket_id for rma in existing_rmas}


        return request.render('products_rma.portal_rma_form', {
            'move_lines': move_lines,
            'reasons': reasons,
            'rma_map': rma_map,
            'pager': pager,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': {'all': {'label': 'All', 'domain': []}},
            'filterby': 'all',
            'default_url': '/my/products/rma',
        })

    @http.route('/my/products/rma/confirm', type='http', auth="user", website=True, methods=['POST'])
    def portal_rma_confirm(self, **post):

        selected_lines = []

        for key, value in post.items():
            if key.startswith('line_'):

                move_id = int(key.split('_')[1])
                reason_id = post.get(f'reason_{move_id}')

                if value == 'on' and reason_id:
                    move = request.env['stock.move.line'].sudo().browse(move_id)
                    reason = request.env['rma.reason'].sudo().browse(int(reason_id))

                    selected_lines.append({
                        'move_id': move.id,
                        'serial': move.lot_id.name,
                        'product': move.product_id.display_name,
                        'reason_id': reason.id,
                        'reason_name': reason.name,
                    })

        if not selected_lines:
            return request.redirect('/my/products')

        return request.render('products_rma.portal_rma_confirm_template', {
            'selected_lines': selected_lines
        })

    @http.route('/my/products/rma/submit', type='http', auth="user", website=True, methods=['POST'])
    def portal_rma_submit(self, **post):

        MoveLine = request.env['stock.move.line'].sudo()
        Reason = request.env['rma.reason'].sudo()
        ReturnWizard = request.env['stock.return.picking'].sudo()

        rma_lines_vals = request.env['helpdesk.rma.line'].sudo()
        selected_move_lines = request.env['stock.move.line']

        user = request.env.user

        for key, value in post.items():
            if key.startswith('move_'):

                move_id = int(value)
                reason_id = post.get(f'reason_{move_id}')

                if not reason_id:
                    continue

                move = MoveLine.browse(move_id)

                # Security: ensure move belongs to logged partner
                if not move.exists() or \
                        move.picking_id.partner_id.commercial_partner_id != user.partner_id.commercial_partner_id:
                    continue

                reason = Reason.browse(int(reason_id))

                selected_move_lines |= move

                rma_lines_vals |= rma_lines_vals.create({
                    'product_id': move.product_id.id,
                    'reason_id': reason.id,
                    'rma_lot_id': move.lot_id.id if move.lot_id else False,
                })

        if not selected_move_lines:
            return request.redirect('/my/products')

        company = request.env['res.company'].sudo().search([('id', '=', 1)], limit=1)

        if not company:
            return request.redirect('/my/products')

        team = request.env['helpdesk.team'].sudo().search([
            ('name', '=', 'Customer Care'),
            ('company_id', '=', company.id)
        ], limit=1)

        ticket = request.env['helpdesk.ticket'].sudo().create({
            'name': f'RMA Request - {user.partner_id.name}',
            'partner_id': user.partner_id.id,
            'team_id': team.id if team else False,
            'description': post.get('note'),
            'is_rma': True,
            'rma_line_ids': [(6, 0, rma_lines_vals.ids)],
        })

        pickings = selected_move_lines.mapped('picking_id').filtered(lambda p: p.state == 'done')

        for picking in pickings:

            picking_move_lines = selected_move_lines.filtered(lambda ml: ml.picking_id == picking)

            wizard = ReturnWizard.create({
                'picking_id': picking.id,
            })

            for return_line in wizard.product_return_moves:

                matching_lines = picking_move_lines.filtered(lambda ml: ml.move_id == return_line.move_id)

                if matching_lines:
                    # Sum delivered quantities for that move
                    return_line.quantity = sum(matching_lines.mapped('qty_done'))
                else:
                    return_line.quantity = 0

            # Create actual return picking
            new_picking = wizard._create_return()  # returns single stock.picking record

            # Link return picking to ticket (smart button logic)
            ticket.write({'picking_ids': [(4, new_picking.id)]})

        return request.redirect(ticket.access_url)
