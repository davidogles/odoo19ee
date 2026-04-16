from odoo import http
from odoo.http import request

class CustomLandingController(http.Controller):

    @http.route('/t-one-portal', type='http', auth='user', website=True)
    def t_one_portal(self, **kwargs):
        return request.render('t_one_portal.t_one_portal_template', {})
